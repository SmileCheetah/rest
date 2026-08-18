"""Fetch and conservatively merge heat-shelter datasets.

The two API response formats are intentionally isolated in FIELD_MAPS. Update
the maps and API URLs when the provider specifications are confirmed.
"""

from __future__ import annotations

import math
import os
import re
import ssl
from io import BytesIO
import unicodedata
from pathlib import Path
from typing import Any, Iterable

import httpx
import pandas as pd
import truststore
from pyproj import Transformer

try:
    from rapidfuzz.fuzz import ratio as fuzzy_ratio
except ImportError:  # Keep the script usable before optional dependencies install.
    from difflib import SequenceMatcher

    def fuzzy_ratio(left: str, right: str) -> float:
        return SequenceMatcher(None, left, right).ratio() * 100


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TIMEOUT_SECONDS = 20.0
DUPLICATE_DISTANCE_METERS = 50.0
ADDRESS_SIMILARITY_THRESHOLD = 92.0
NAME_SIMILARITY_THRESHOLD = 85.0


def _load_local_env() -> None:
    """Load simple KEY=VALUE entries without adding a dotenv dependency."""
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(name, value)


_load_local_env()

# Replace these URLs with the actual provider endpoints.
HEAT_SHELTER_API_URL = os.getenv("HEAT_SHELTER_API_URL", "")
CLIMATE_SHELTER_API_URL = os.getenv("CLIMATE_SHELTER_API_URL", "")
CLIMATE_SHELTER_FILE_URL = os.getenv(
    "CLIMATE_SHELTER_FILE_URL",
    "https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false",
)
CLIMATE_SHELTER_FILE_ID = os.getenv("CLIMATE_SHELTER_FILE_ID", "OA-22386")
CLIMATE_SHELTER_FILE_SEQ = os.getenv("CLIMATE_SHELTER_FILE_SEQ", "1")
CLIMATE_SHELTER_FILE_INF_SEQ = os.getenv("CLIMATE_SHELTER_FILE_INF_SEQ", "3")

# Replace values below if the provider uses different field names.
# Nested JSON can be handled by changing the extract_records() function.
FIELD_MAPS: dict[str, dict[str, tuple[str, ...]]] = {
    "heat_shelter": {
        "name": ("name", "RSTR_NM", "shelterName"),
        "address": ("address", "RN_DTL_ADRES", "DTL_ADRES"),
        "latitude": ("latitude", "lat", "LA"),
        "longitude": ("longitude", "lon", "lng", "LO"),
        "operating_hours": ("operating_hours", "operatingHours", "hours"),
    },
    "climate_shelter": {
        "name": ("name", "shelterName", "facilityName", "쉼터명"),
        "address": ("address", "roadAddress", "jibunAddress", "도로명주소"),
        "latitude": ("latitude", "lat", "y"),
        "longitude": ("longitude", "lon", "lng", "x"),
        "operating_hours": ("operating_hours", "operatingHours", "hours", "운영시간"),
    },
}

COMMON_COLUMNS = (
    "name",
    "address",
    "latitude",
    "longitude",
    "operating_hours",
    "source",
)


def fetch_api_records(
    url: str,
    api_key: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[dict[str, Any]]:
    """Fetch one provider and return raw record dictionaries."""
    if not url:
        raise RuntimeError("API URL is not configured")
    if not api_key:
        raise RuntimeError("API key is not configured")

    # Adjust query parameter names here if a provider does not use serviceKey.
    response = httpx.get(
        url,
        params={"serviceKey": api_key, "returnType": "json"},
        timeout=timeout,
    )
    response.raise_for_status()
    return extract_records(response.json())


def fetch_climate_shelter_file_records() -> list[dict[str, Any]]:
    """Download Seoul's current climate-shelter XLSX snapshot.

    The provider currently exposes this dataset as a file, not a JSON API.
    """
    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    response = httpx.post(
        CLIMATE_SHELTER_FILE_URL,
        data={
            "infId": CLIMATE_SHELTER_FILE_ID,
            "seq": CLIMATE_SHELTER_FILE_SEQ,
            "infSeq": CLIMATE_SHELTER_FILE_INF_SEQ,
        },
        timeout=DEFAULT_TIMEOUT_SECONDS,
        verify=ssl_context,
    )
    response.raise_for_status()
    frame = pd.read_excel(BytesIO(response.content))
    transformer = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)
    records: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        x, y = _to_coordinate(row.get("X좌표")), _to_coordinate(row.get("Y좌표"))
        longitude, latitude = transformer.transform(x, y) if x is not None and y is not None else (None, None)
        records.append(
            {
                "쉼터명": row.get("쉼터명"),
                "도로명주소": row.get("도로명주소"),
                "latitude": latitude,
                "longitude": longitude,
                "운영시간": row.get("운영시간"),
            }
        )
    return records


def extract_records(payload: Any) -> list[dict[str, Any]]:
    """Extract records from common list/data/result response envelopes.

    If an API has a different envelope, add its key in this function.
    """
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "items", "results", "body", "records"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = extract_records(value)
            if nested:
                return nested
    return []


def clean_text(value: Any) -> str:
    """Normalize whitespace, Unicode form, and punctuation for comparisons."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    text = re.sub(r"[^0-9a-z가-힣\s]", " ", text)
    return re.sub(r"\s+", "", text)


def _first_value(record: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            return value
    return None


def normalize_records(
    records: list[dict[str, Any]], source: str
) -> pd.DataFrame:
    """Map provider-specific records to the common Cooling Spot schema."""
    field_map = FIELD_MAPS[source]
    rows: list[dict[str, Any]] = []
    for record in records:
        rows.append(
            {
                "name": _first_value(record, field_map["name"]),
                "address": _first_value(record, field_map["address"]),
                "latitude": _to_coordinate(_first_value(record, field_map["latitude"])),
                "longitude": _to_coordinate(_first_value(record, field_map["longitude"])),
                "operating_hours": _first_value(record, field_map["operating_hours"]),
                "source": source,
            }
        )
    frame = pd.DataFrame(rows, columns=COMMON_COLUMNS)
    if frame.empty:
        return frame
    frame["name_normalized"] = frame["name"].map(clean_text)
    frame["address_normalized"] = frame["address"].map(clean_text)
    return frame


def _to_coordinate(value: Any) -> float | None:
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None
    return coordinate if math.isfinite(coordinate) else None


def haversine_distance_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    radius = 6_371_000.0
    lat_a, lat_b = math.radians(latitude_a), math.radians(latitude_b)
    delta_lat = lat_b - lat_a
    delta_lon = math.radians(longitude_b - longitude_a)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(value))


def is_duplicate(
    left: pd.Series,
    right: pd.Series,
    *,
    distance_threshold_meters: float = DUPLICATE_DISTANCE_METERS,
    address_threshold: float = ADDRESS_SIMILARITY_THRESHOLD,
    name_threshold: float = NAME_SIMILARITY_THRESHOLD,
) -> bool:
    """Use coordinate-first matching with conservative text fallbacks."""
    left_coordinates = (left.get("latitude"), left.get("longitude"))
    right_coordinates = (right.get("latitude"), right.get("longitude"))
    has_coordinates = all(_is_coordinate(value) for value in (*left_coordinates, *right_coordinates))
    left_name = left.get("name_normalized") or clean_text(left.get("name"))
    right_name = right.get("name_normalized") or clean_text(right.get("name"))
    left_address = left.get("address_normalized") or clean_text(left.get("address"))
    right_address = right.get("address_normalized") or clean_text(right.get("address"))
    name_score = fuzzy_ratio(left_name, right_name)
    address_score = fuzzy_ratio(
        left_address, right_address
    )

    if has_coordinates:
        distance = haversine_distance_meters(
            float(left_coordinates[0]),
            float(left_coordinates[1]),
            float(right_coordinates[0]),
            float(right_coordinates[1]),
        )
        # Coordinates alone are not enough: nearby distinct facilities can exist.
        return distance <= distance_threshold_meters and (
            name_score >= name_threshold or address_score >= address_threshold
        )

    # Without coordinates, require both identity signals. Name-only matches are rejected.
    return address_score >= address_threshold and name_score >= name_threshold


def _is_coordinate(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _more_complete(left: Any, right: Any) -> Any:
    left_text, right_text = str(left or "").strip(), str(right or "").strip()
    if not left_text:
        return right
    if not right_text:
        return left
    return left if len(left_text) >= len(right_text) else right


def merge_records(left: pd.Series, right: pd.Series) -> dict[str, Any]:
    """Merge two matched records while preserving both source names."""
    merged = {
        column: _more_complete(left.get(column), right.get(column))
        for column in COMMON_COLUMNS
        if column != "source"
    }
    sources = []
    for source in (left.get("source"), right.get("source")):
        if source and source not in sources:
            sources.append(source)
    merged["source"] = sources
    return merged


def merge_shelter_data(heat_df: pd.DataFrame, climate_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Merge normalized frames and return (result, number_of_merged_duplicates)."""
    result: list[dict[str, Any]] = []
    merged_count = 0
    for _, row in pd.concat([heat_df, climate_df], ignore_index=True).iterrows():
        match_index = next(
            (index for index, existing in enumerate(result) if is_duplicate(existing, row)),
            None,
        )
        if match_index is None:
            result.append(row.to_dict())
        else:
            result[match_index] = merge_records(pd.Series(result[match_index]), row)
            merged_count += 1
    return pd.DataFrame(result, columns=COMMON_COLUMNS), merged_count


def load_and_merge_shelters() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load both APIs and return (heat_df, climate_df, cooling_spots_df)."""
    heat_records = _fetch_if_configured(
        "heat_shelter",
        os.getenv("HEAT_SHELTER_API_URL", HEAT_SHELTER_API_URL),
        os.getenv("HEAT_SHELTER_API_KEY", ""),
    )
    climate_url = os.getenv("CLIMATE_SHELTER_API_URL", CLIMATE_SHELTER_API_URL)
    climate_key = os.getenv("CLIMATE_SHELTER_API_KEY", "")
    if climate_url and climate_key:
        climate_records = fetch_api_records(climate_url, climate_key)
    else:
        print("climate_shelter: using Seoul XLSX snapshot")
        climate_records = fetch_climate_shelter_file_records()
    if not heat_records and not climate_records:
        raise RuntimeError("no shelter API is configured")
    heat_df = normalize_records(heat_records, "heat_shelter")
    climate_df = normalize_records(climate_records, "climate_shelter")
    cooling_spots_df, merged_count = merge_shelter_data(heat_df, climate_df)
    print(f"heat shelter raw count: {len(heat_df)}")
    print(f"climate shelter raw count: {len(climate_df)}")
    print(f"duplicates merged: {merged_count}")
    print(f"final cooling spot count: {len(cooling_spots_df)}")
    return heat_df, climate_df, cooling_spots_df


def _fetch_if_configured(source: str, url: str, api_key: str) -> list[dict[str, Any]]:
    """Skip an unavailable optional provider while keeping the other source usable."""
    if not url or not api_key:
        print(f"skip {source}: API URL or API key is not configured")
        return []
    return fetch_api_records(url, api_key)


if __name__ == "__main__":
    heat_df, climate_df, cooling_spots_df = load_and_merge_shelters()
    output_path = BACKEND_DIR / "data" / "cooling_spots_merged.csv"
    json_output_path = BACKEND_DIR / "data" / "cooling_spots_merged.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cooling_spots_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    json_output_path.write_text(
        cooling_spots_df.to_json(orient="records", force_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved: {output_path}")
    print(f"saved: {json_output_path}")
