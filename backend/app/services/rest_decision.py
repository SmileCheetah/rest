from __future__ import annotations

import logging

import httpx

from app.config import settings
from app.schemas.rest_decision import (
    RestDecision,
    RestDecisionRequest,
    RestNeedLevel,
)
from app.services.rest_need import RestScore

logger = logging.getLogger(__name__)


class RestDecisionService:
    async def decide(
        self,
        request: RestDecisionRequest,
        score: RestScore,
    ) -> tuple[RestDecision, str]:
        payload = self.build_ai_input(request, score)
        if settings.rest_decision_ai_url:
            try:
                decision = await self.request_ai_decision(payload)
                return self.validate_ai_decision(decision, score, request), "AI"
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                logger.warning("rest decision AI failed; using fallback: %s", exc)
        return self.fallback_decision(score.level, request), "FALLBACK"

    def build_ai_input(self, request: RestDecisionRequest, score: RestScore) -> dict:
        return {
            "restNeedScore": score.score,
            "restNeedLevel": score.level,
            "continuousWalkingMinutes": request.continuous_walking_minutes,
            "totalWalkingMinutes": request.total_walking_minutes,
            "minutesSinceLastRest": request.minutes_since_last_rest,
            "heatLevel": request.heat_level or "UNKNOWN",
            "nextTravelMinutes": request.next_travel_minutes,
            "coolingSpotNearby": request.cooling_spot_nearby,
            "distanceToCoolingSpotMeters": request.distance_to_cooling_spot_meters,
        }

    async def request_ai_decision(self, payload: dict) -> RestDecision:
        headers = {}
        if settings.rest_decision_ai_api_key:
            headers["Authorization"] = f"Bearer {settings.rest_decision_ai_api_key}"
        async with httpx.AsyncClient(timeout=settings.rest_decision_ai_timeout_seconds) as client:
            response = await client.post(
                settings.rest_decision_ai_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return RestDecision.model_validate(response.json())

    def validate_ai_decision(
        self,
        decision: RestDecision,
        score: RestScore,
        request: RestDecisionRequest,
    ) -> RestDecision:
        # MVP safety policy: the AI cannot suppress a high-confidence rest signal.
        if score.score >= settings.rest_decision_high_score_threshold:
            timing = "AFTER_NEXT_VISIT" if request.next_travel_minutes <= 3 else "NOW"
            return decision.model_copy(
                update={"should_rest": True, "rest_timing": timing}
            )
        if (
            score.score <= settings.rest_decision_low_score_threshold
            and score.level == "LOW"
            and request.heat_level != "HIGH"
        ):
            return decision.model_copy(
                update={"should_rest": False, "rest_timing": "NOT_NEEDED"}
            )
        if score.level == "HIGH" and request.heat_level == "HIGH":
            return decision.model_copy(update={"should_rest": True})
        return decision

    def fallback_decision(
        self,
        level: RestNeedLevel,
        request: RestDecisionRequest,
    ) -> RestDecision:
        if level == "HIGH":
            timing = "AFTER_NEXT_VISIT" if request.next_travel_minutes <= 3 else "NOW"
            return RestDecision(
                shouldRest=True,
                restTiming=timing,
                recommendation="현재 휴식을 권장합니다.",
                reason="휴식 필요도 점수가 높거나 열환경·활동 부담이 큽니다.",
                recommendedRestMinutes=15,
            )
        if level == "MEDIUM":
            return RestDecision(
                shouldRest=request.cooling_spot_nearby,
                restTiming="SOON" if request.cooling_spot_nearby else "NOT_NEEDED",
                recommendation=(
                    "가까운 Cooling Spot에서 휴식을 고려하세요."
                    if request.cooling_spot_nearby
                    else "현재 이동을 유지하되 휴식 상태를 확인하세요."
                ),
                reason="휴식 필요도가 중간 수준입니다.",
                recommendedRestMinutes=10 if request.cooling_spot_nearby else 0,
            )
        return RestDecision(
            shouldRest=False,
            restTiming="NOT_NEEDED",
            recommendation="현재 이동을 유지할 수 있습니다.",
            reason="휴식 필요도가 낮습니다.",
            recommendedRestMinutes=0,
        )
