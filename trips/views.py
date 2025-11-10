from rest_framework.decorators import api_view
from .models import Trip

import json
import logging
from django.http import JsonResponse
from rest_framework.decorators import api_view
from .models import Trip

from .utils.route_stops import SimpleStopsAPI
from .utils.duty_scheduler import generate_duty_blocks
from .utils.generate_eld import generate_multiple_eld_sheets, merge_eld_sheets
from .utils.route_stops import SimpleStopsAPI
from .utils.route import geocode_place, get_route_with_waypoints

logger = logging.getLogger(__name__)
truck_stops_api = SimpleStopsAPI()


@api_view(["POST"])
def calculate_trip(request):
    """Main API endpoint that uses real truck stops data"""
    try:
        pickup_location = request.data.get("pickup_location")
        dropoff_location = request.data.get("dropoff_location")
        current_location = request.data.get("current_location", "")
        current_cycle_used = float(request.data.get("current_cycle_used", 0))

        if not pickup_location or not dropoff_location:
            return JsonResponse(
                {"error": "pickup_location and dropoff_location are required."},
                status=400,
            )

        pickup_coords = geocode_place(pickup_location)
        dropoff_coords = geocode_place(dropoff_location)
        current_location_coords = (
            geocode_place(current_location) if current_location else pickup_coords
        )

        current_to_pickup_geometry, current_to_pickup_distance_km, _ = (
            get_route_with_waypoints(current_location_coords, pickup_coords)
        )
        pickup_to_dropoff_geometry, pickup_to_dropoff_distance_km, duration_hr = (
            get_route_with_waypoints(pickup_coords, dropoff_coords)
        )

        logger.info(
            f"[ROUTE] Route calculation complete: {current_to_pickup_distance_km + pickup_to_dropoff_distance_km:.1f}km total"
        )

        duty_blocks, cycle_used = generate_duty_blocks(
            current_to_pickup_miles=current_to_pickup_distance_km * 0.621371,
            pickup_to_dropoff_miles=pickup_to_dropoff_distance_km * 0.621371,
            current_cycle_used=current_cycle_used,
        )

        total_distance_km = (
            current_to_pickup_distance_km + pickup_to_dropoff_distance_km
        )
        full_route_geometry = current_to_pickup_geometry + pickup_to_dropoff_geometry

        stops_data = truck_stops_api.find_stops_along_route(
            pickup_coords, dropoff_coords, duty_blocks
        )

        eld_paths = generate_multiple_eld_sheets(duty_blocks)
        merged_pdf_path = merge_eld_sheets(eld_paths)

        logger.info("[ELD] ELD documents generated")

        trip = Trip.objects.create(
            current_location=current_location,
            current_location_coords=f"{current_location_coords[0]},{current_location_coords[1]}",
            pickup_location=pickup_location,
            pickup_coords=f"{pickup_coords[0]},{pickup_coords[1]}",
            dropoff_location=dropoff_location,
            dropoff_coords=f"{dropoff_coords[0]},{dropoff_coords[1]}",
            current_cycle_used=current_cycle_used,
            total_trip_hours=round(duration_hr, 3),
            total_distance_km=round(total_distance_km, 3),
            route_geojson=json.dumps({"geometry": full_route_geometry}),
            status="processed",
        )

        logger.info(f"[DB] Created Trip ID {trip.id}")

        response_data = {
            "trip_summary": {
                "pickup": pickup_location,
                "dropoff": dropoff_location,
                "total_distance_km": round(total_distance_km, 2),
                "estimated_duration_hr": round(duration_hr, 2),
                "actual_stops_count": stops_data.get("total_stops", 0),
                "total_days": (
                    max([block["day"] for block in duty_blocks]) if duty_blocks else 1
                ),
            },
            "duty_schedule": {"blocks": duty_blocks, "final_cycle_used": cycle_used},
            "stops": stops_data["stops"],
            "total_stops": stops_data["total_stops"],
            "eld_files": {
                "individual_sheets": eld_paths,
                "merged_pdf": merged_pdf_path,
            },
            "route_geometry": full_route_geometry,
            "trip_id": trip.id,
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"[ERROR] Trip calculation failed: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
