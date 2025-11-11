import asyncio
import os
import logging
import requests
import openrouteservice
from django.core.cache import cache
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

ORS_API_KEY = os.getenv("ORS_API_KEY")
GEOCODE_URL = os.getenv("GEOCODE_URL")
ROUTE_URL = os.getenv("ROUTE_URL")

executor = ThreadPoolExecutor(max_workers=10)
CACHE_TIMEOUT = 60 * 60 * 5  # 5 hours


def _geocode_sync(place_name: str):
    """Sync geocode helper for executor."""
    logger.info(f"[GEOCODE] Attempting geocode for: {place_name}")
    params = {"api_key": ORS_API_KEY, "text": place_name, "size": 1}

    try:
        res = requests.get(GEOCODE_URL, params=params, timeout=10)
        logger.debug(f"[GEOCODE] Response status: {res.status_code} for {place_name}")
        res.raise_for_status()
        data = res.json()
        logger.debug(f"[GEOCODE] Response JSON for {place_name}: {data}")
    except requests.RequestException as e:
        logger.error(f"[GEOCODE] Request failed for '{place_name}': {e}")
        raise ValueError(f"Request error while geocoding {place_name}: {e}")

    if not data.get("features"):
        logger.error(f"[GEOCODE] No features found for {place_name}. Full response: {data}")
        raise ValueError(f"Could not geocode: {place_name}")

    lon, lat = data["features"][0]["geometry"]["coordinates"]
    logger.info(f"[GEOCODE] {place_name} → lat={lat}, lon={lon}")
    return lat, lon


async def geocode_place_cached(place_name: str):
    """Async + cached geocoding."""
    # Sanitize cache key for Memcached
    safe_key = f"geocode:{place_name.lower().replace(' ', '_').replace(':', '_')}"
    logger.debug(f"[CACHE] Using key: {safe_key}")

    if coords := cache.get(safe_key):
        logger.info(f"[CACHE HIT] Geocode {place_name} → {coords}")
        return coords

    loop = asyncio.get_running_loop()
    try:
        coords = await loop.run_in_executor(executor, _geocode_sync, place_name)
        cache.set(safe_key, coords, CACHE_TIMEOUT)
        logger.info(f"[CACHE MISS] Geocode {place_name} cached → {coords}")
        return coords
    except Exception as e:
        logger.exception(f"[ERROR] Geocoding failed for {place_name}: {e}")
        raise


def _route_sync(start_coords, end_coords):
    """Sync route fetcher for executor."""
    logger.info(f"[ROUTE] Fetching route between {start_coords} → {end_coords}")
    body = {
        "coordinates": [
            [start_coords[1], start_coords[0]],
            [end_coords[1], end_coords[0]],
        ],
        "instructions": True,
        "geometry": True,
    }
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}

    try:
        response = requests.post(ROUTE_URL, headers=headers, json=body, timeout=15)
        logger.debug(f"[ROUTE] Response status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        logger.debug(f"[ROUTE] Response JSON: {data}")
    except requests.RequestException as e:
        logger.error(f"[ROUTE] Request failed: {e}")
        raise ValueError(f"Failed to retrieve route data: {e}")

    if "routes" not in data:
        logger.error(f"[ROUTE] Missing 'routes' key. Full response: {data}")
        raise ValueError("Failed to retrieve route data from ORS")

    route = data["routes"][0]
    summary = route["summary"]
    distance_km = summary["distance"] / 1000
    duration_hr = summary["duration"] / 3600
    geometry = openrouteservice.convert.decode_polyline(route["geometry"])["coordinates"]

    logger.info(
        f"[ROUTE] Route summary: distance={distance_km:.2f} km, duration={duration_hr:.2f} hr"
    )

    return geometry, distance_km, duration_hr


async def route_with_cache(start_coords, end_coords):
    """Async + cached routing."""
    cache_key = f"route:{start_coords}:{end_coords}".replace(" ", "_")
    logger.debug(f"[CACHE] Using key: {cache_key}")

    if data := cache.get(cache_key):
        logger.info(f"[CACHE HIT] Route {start_coords} → {end_coords}")
        return data

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(executor, _route_sync, start_coords, end_coords)
        cache.set(cache_key, result, CACHE_TIMEOUT)
        logger.info(f"[CACHE MISS] Route cached for {start_coords} → {end_coords}")
        return result
    except Exception as e:
        logger.exception(f"[ERROR] Route fetch failed between {start_coords} and {end_coords}: {e}")
        raise
