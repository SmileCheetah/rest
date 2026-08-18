import math
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.schemas.route import Coordinate, RoutePathPoint


class TmapConfigurationError(Exception):
    """TMAP API 설정이 없습니다."""


class TmapProviderError(Exception):
    """TMAP API 요청 또는 응답 처리에 실패했습니다."""


@dataclass(frozen=True)
class PedestrianRoute:
    distance_meters: int
    walking_minutes: int
    path: list[RoutePathPoint]


async def get_pedestrian_route(
    origin: Coordinate,
    destination: Coordinate,
) -> PedestrianRoute:
    """TMAP에서 두 지점 사이 보행 경로를 조회합니다."""
    if not settings.map_api_key:
        raise TmapConfigurationError("MAP_API_KEY is not configured")

    payload = {
        "startX": str(origin.longitude),
        "startY": str(origin.latitude),
        "endX": str(destination.longitude),
        "endY": str(destination.latitude),
        "startName": origin.name or "출발지",
        "endName": destination.name or "도착지",
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response: httpx.Response | None = None
            for attempt in range(2):
                try:
                    response = await client.post(
                        f"{settings.tmap_api_base_url}/routes/pedestrian",
                        params={"version": "1", "format": "json"},
                        headers={
                            "appKey": settings.map_api_key,
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    response.raise_for_status()
                    break
                except httpx.TransportError:
                    if attempt == 1:
                        raise
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code in {401, 403}:
                        raise TmapProviderError(
                            "TMAP AppKey 또는 보행자 경로안내 API 권한을 확인해주세요"
                        ) from exc
                    if exc.response.status_code == 429:
                        raise TmapProviderError(
                            "TMAP 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요"
                        ) from exc
                    if attempt == 1 or exc.response.status_code < 500:
                        raise
            if response is None:
                raise TmapProviderError("TMAP API returned no response")
            response_payload = response.json()
    except TmapProviderError:
        raise
    except httpx.HTTPStatusError as exc:
        raise TmapProviderError(
            f"TMAP API 오류({exc.response.status_code})"
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise TmapProviderError("TMAP API request failed") from exc

    return parse_pedestrian_route(response_payload)


def parse_pedestrian_route(payload: dict[str, Any]) -> PedestrianRoute:
    """TMAP GeoJSON 응답에서 요약값과 경로 좌표를 추출합니다."""
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise TmapProviderError("unexpected TMAP API response")

    summary: dict[str, Any] | None = None
    path: list[RoutePathPoint] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties")
        if isinstance(properties, dict) and "totalDistance" in properties:
            summary = properties

        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") != "LineString":
            continue
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list):
            continue
        for coordinate in coordinates:
            if not isinstance(coordinate, list) or len(coordinate) < 2:
                continue
            point = RoutePathPoint(
                longitude=float(coordinate[0]),
                latitude=float(coordinate[1]),
            )
            if not path or point != path[-1]:
                path.append(point)

    try:
        distance_meters = int(summary["totalDistance"]) if summary else 0
        walking_seconds = int(summary["totalTime"]) if summary else 0
    except (KeyError, TypeError, ValueError) as exc:
        raise TmapProviderError("unexpected TMAP route summary") from exc
    if distance_meters <= 0 or walking_seconds <= 0 or not path:
        raise TmapProviderError("TMAP route data is missing")

    return PedestrianRoute(
        distance_meters=distance_meters,
        walking_minutes=max(1, math.ceil(walking_seconds / 60)),
        path=path,
    )
