import os
import requests
import logging
import openrouteservice


ORS_API_KEY = os.getenv("ORS_API_KEY")
GEOCODE_URL = os.getenv("GEOCODE_URL")
ROUTE_URL = os.getenv("ROUTE_URL")

logger = logging.getLogger(__name__)


def geocode_place(place_name: str):
    """Convert a location name into (lat, lon)."""
    params = {"api_key": ORS_API_KEY, "text": place_name, "size": 1}
    res = requests.get(GEOCODE_URL, params=params)
    data = res.json()

    if not data.get("features"):
        raise ValueError(f"Could not geocode: {place_name}")

    lon, lat = data["features"][0]["geometry"]["coordinates"]
    logger.info(f"[GEOCODE] {place_name} → ({lat}, {lon})")
    return lat, lon


def get_route_with_waypoints(start_coords, end_coords):
    """Get route with geometry, distance, duration"""
    body = {
        "coordinates": [
            [start_coords[1], start_coords[0]],
            [end_coords[1], end_coords[0]],
        ],
        "instructions": True,
        "geometry": True,
    }
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    response = requests.post(ROUTE_URL, headers=headers, json=body)
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
