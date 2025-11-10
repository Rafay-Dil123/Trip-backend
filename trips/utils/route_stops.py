import requests
import logging
import os
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class SimpleStopsAPI:
    def __init__(self):
        self.nominatim_url = os.getenv("NOMINATIM_URL")

    def find_stops_along_route(
        self, pickup_coords: Tuple, dropoff_coords: Tuple, duty_blocks: List[Dict]
    ) -> Dict:
        try:
            midpoint = self._calculate_midpoint(pickup_coords, dropoff_coords)
            stops = self._find_amenities_at_points(
                pickup_coords, midpoint, dropoff_coords, duty_blocks
            )

            return {
                "stops": stops,
                "total_stops": len(stops),
                "route_info": {
                    "pickup": pickup_coords,
                    "dropoff": dropoff_coords,
                    "midpoint": midpoint,
                },
            }

        except Exception as e:
            logger.error(f"Error finding stops: {str(e)}")
            return self._get_basic_stops(duty_blocks)

    def _calculate_midpoint(self, coord1: Tuple, coord2: Tuple) -> Tuple:
        """Calculate midpoint between two coordinates"""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        mid_lat = (lat1 + lat2) / 2
        mid_lon = (lon1 + lon2) / 2
        return (mid_lat, mid_lon)

    def _find_amenities_at_points(
        self, pickup: Tuple, midpoint: Tuple, dropoff: Tuple, duty_blocks: List[Dict]
    ) -> List[Dict]:
        """Find amenities at key points along the route"""
        stops = []

        search_points = [
            ("midpoint", midpoint, 10000), 
            ("near dropoff", dropoff, 100000),  
        ]

        for point_name, coords, radius in search_points:
            amenities = self._search_nominatim(coords, radius)
            stops.extend(amenities)

        return (stops, duty_blocks)

    def _search_nominatim(self, coords: Tuple, radius: int = 5000) -> List[Dict]:
        """Return top 10 restaurants near the given coordinates using Nominatim."""
        lat, lon = coords
        params = {
            "q": "restaurant",
            "format": "json",
            "lat": lat,
            "lon": lon,
            "radius": radius,
            "limit": 10,
        }
        headers = {"User-Agent": "TripLogApp/1.0"}
        try:
            response = requests.get(
                self.nominatim_url, params=params, headers=headers, timeout=10
            )
            if response.status_code == 200:
                places = response.json()
                restaurants = []
                for place in places:
                    restaurant = {
                        "name": place.get("display_name", "Unknown").split(",")[0],
                        "coordinates": (float(place["lat"]), float(place["lon"])),
                        "address": place.get("display_name", ""),
                    }
                    restaurants.append(restaurant)
                return restaurants
            else:
                logger.warning(f"Nominatim returned status {response.status_code}")
                return []
        except Exception as e:
            logger.warning(f"Failed to search for restaurants: {e}")
            return []

    def _get_basic_stops(self, duty_blocks: List[Dict]) -> Dict:
        """Fallback: basic stops without actual locations"""
        stops = []
        for block in duty_blocks:
            if self._is_stop_activity(block["activity"]):
                stops.append(
                    {
                        "day": block["day"],
                        "scheduled_activity": block["activity"],
                        "duration_hours": block["hours"],
                        "stop_type": self._map_stop_type(block["activity"]),
                        "note": "Actual location to be determined",
                    }
                )

        return {
            "stops": stops,
            "total_stops": len(stops),
            "note": "Used basic stop calculation",
        }
