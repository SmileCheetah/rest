from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import httpx

from app.config import settings
from app.schemas.rest_decision import (
    RestDecision,
    RestDecisionRequest,
    RestNeedLevel,
)
from app.services.rest_need import RestScore
from app.ml.rest_status_classifier import (
    load_rest_status_classifier,
    predict_rest_status,
)

logger = logging.getLogger(__name__)


class RestDecisionService:
    async def decide(
        self,
        request: RestDecisionRequest,
        score: RestScore | None = None,
        model_prediction: dict[str, object] | None = None,
    ) -> tuple[RestDecision, str]:
        payload = self.build_ai_input(request, score)
        if settings.rest_decision_ai_url:
            try:
                decision = await self.request_ai_decision(payload)
                return self.validate_ai_decision(decision, score, request), "AI"
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                logger.warning("rest decision AI failed; using fallback: %s", exc)
        if model_prediction is not None:
            return self.model_decision(model_prediction, request), "MODEL"
        return self.fallback_decision(score.level if score is not None else None, request), "FALLBACK"

    def predict_model_status(
        self,
        request: RestDecisionRequest,
        wbgt: float | None,
    ) -> dict[str, object] | None:
        """Run the local classifier when a WBGT value and model artifact exist."""
        if wbgt is None:
            return None
        model_path = settings.rest_status_model_path
        if model_path is None or not Path(model_path).exists():
            return None
        model = _load_status_model(str(model_path))
        distance = request.distance_to_cooling_spot_meters
        if distance is None:
            # Unknown distance is treated conservatively as outside the 1km
            # accessibility band used by the synthetic MVP labels.
            distance = 3_000
        return predict_rest_status(
            model=model,
            wbgt=wbgt,
            continuous_exposure_minutes=request.continuous_walking_minutes,
            next_travel_minutes=request.next_travel_minutes,
            time_since_rest_minutes=request.minutes_since_last_rest,
            cooling_spot_distance_m=distance,
        )

    def model_decision(
        self,
        prediction: dict[str, object],
        request: RestDecisionRequest,
    ) -> RestDecision:
        status = prediction["decision"]
        if status == "MOVABLE":
            return RestDecision(
                shouldRest=False,
                restTiming="NOT_NEEDED",
                recommendation="현재 이동을 유지할 수 있습니다.",
                reason="AI 분류 결과 이동 가능한 상태입니다.",
                recommendedRestMinutes=0,
            )
        if status == "REST_RECOMMENDED":
            nearby = request.cooling_spot_nearby
            return RestDecision(
                shouldRest=True,
                restTiming="SOON" if nearby else "AFTER_NEXT_VISIT",
                recommendation="다음 이동 전 휴식을 권장합니다.",
                reason="AI 분류 결과 휴식 권장 상태입니다.",
                recommendedRestMinutes=10,
            )
        return RestDecision(
            shouldRest=True,
            restTiming="NOW",
            recommendation="다음 방문 전에 휴식이 필요합니다.",
            reason="AI 분류 결과 다음 방문 전 휴식이 필요한 상태입니다.",
            recommendedRestMinutes=15,
        )

    def build_ai_input(self, request: RestDecisionRequest, score: RestScore | None) -> dict:
        payload = {
            "continuousWalkingMinutes": request.continuous_walking_minutes,
            "totalWalkingMinutes": request.total_walking_minutes,
            "minutesSinceLastRest": request.minutes_since_last_rest,
            "heatLevel": request.heat_level or "UNKNOWN",
            "nextTravelMinutes": request.next_travel_minutes,
            "coolingSpotNearby": request.cooling_spot_nearby,
            "distanceToCoolingSpotMeters": request.distance_to_cooling_spot_meters,
        }
        if score is not None:
            payload.update(
                {"restNeedScore": score.score, "restNeedLevel": score.level}
            )
        return payload

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
        if score is not None and score.score >= settings.rest_decision_high_score_threshold:
            timing = "AFTER_NEXT_VISIT" if request.next_travel_minutes <= 3 else "NOW"
            return decision.model_copy(
                update={"should_rest": True, "rest_timing": timing}
            )
        if (
            score is not None
            and score.score <= settings.rest_decision_low_score_threshold
            and score.level == "LOW"
            and request.heat_level != "HIGH"
        ):
            return decision.model_copy(
                update={"should_rest": False, "rest_timing": "NOT_NEEDED"}
            )
        if score is not None and score.level == "HIGH" and request.heat_level == "HIGH":
            return decision.model_copy(update={"should_rest": True})
        return decision

    def fallback_decision(
        self,
        level: RestNeedLevel | None,
        request: RestDecisionRequest,
    ) -> RestDecision:
        if level is None:
            level = request.heat_level or "LOW"
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


@lru_cache(maxsize=2)
def _load_status_model(path: str):
    return load_rest_status_classifier(Path(path))
