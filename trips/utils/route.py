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
    params = {"api_key": ORS_API_KEY, "text": place_name, "size": 1}
    res = requests.get(GEOCODE_URL, params=params, timeout=10)
    data = res.json()

    if not data.get("features"):
        raise ValueError(f"Could not geocode: {place_name}")

    lon, lat = data["features"][0]["geometry"]["coordinates"]
    return lat, lon


async def geocode_place_cached(place_name: str):
    """Async + cached geocoding."""
    cache_key = f"geocode:{place_name.lower()}"
    if coords := cache.get(cache_key):
        logger.info(f"[CACHE HIT] Geocode {place_name} → {coords}")
        return coords

    loop = asyncio.get_running_loop()
    coords = await loop.run_in_executor(executor, _geocode_sync, place_name)
    cache.set(cache_key, coords, CACHE_TIMEOUT)
    logger.info(f"[CACHE MISS] Geocode {place_name} → {coords}")
    return coords


def _route_sync(start_coords, end_coords):
    """Sync route fetcher for executor."""
    body = {
        "coordinates": [
            [start_coords[1], start_coords[0]],
            [end_coords[1], end_coords[0]],
        ],
        "instructions": True,
        "geometry": True,
    }
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    response = requests.post(ROUTE_URL, headers=headers, json=body, timeout=15)
    data = response.json()

    if "routes" not in data:
        raise ValueError("Failed to retrieve route data from ORS")

    route = data["routes"][0]
    summary = route["summary"]
    distance_km = summary["distance"] / 1000
    duration_hr = summary["duration"] / 3600
    geometry = openrouteservice.convert.decode_polyline(route["geometry"])[
        "coordinates"
    ]

    return geometry, distance_km, duration_hr


async def route_with_cache(start_coords, end_coords):
    """Async + cached routing."""
    cache_key = f"route:{start_coords}:{end_coords}"
    if data := cache.get(cache_key):
        logger.info(f"[CACHE HIT] Route {start_coords} → {end_coords}")
        return data

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, _route_sync, start_coords, end_coords)
    cache.set(cache_key, result, CACHE_TIMEOUT)
    logger.info(f"[CACHE MISS] Route {start_coords} → {end_coords}")
    return result
