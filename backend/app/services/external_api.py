import ssl
from typing import Any
from urllib.parse import unquote

import httpx
import truststore


class ExternalApiError(Exception):
    """외부 공공데이터 API 호출 또는 JSON 처리에 실패했습니다."""


async def request_public_data_json(
    url: str,
    api_key: str,
    params: dict[str, object],
    *,
    api_key_name: str = "serviceKey",
) -> dict[str, Any]:
    """공공데이터포털 API를 통신 오류에 한해 한 번 재시도합니다."""
    request_params = {api_key_name: unquote(api_key), **params}
    try:
        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        async with httpx.AsyncClient(
            timeout=20.0,
            verify=ssl_context,
        ) as client:
            response: httpx.Response | None = None
            for attempt in range(2):
                try:
                    response = await client.get(url, params=request_params)
                    response.raise_for_status()
                    break
                except httpx.TransportError:
                    if attempt == 1:
                        raise
                except httpx.HTTPStatusError as exc:
                    if attempt == 1 or exc.response.status_code < 500:
                        raise
            if response is None:
                raise ExternalApiError("external API returned no response")
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ExternalApiError("external API request failed") from exc
    if not isinstance(payload, dict):
        raise ExternalApiError("unexpected external API response")
    return payload
