
import json
import logging
import asyncio
from django.http import JsonResponse

from .utils.route_stops import SimpleStopsAPI
from .utils.duty_scheduler import generate_duty_blocks
from .utils.generate_eld import generate_multiple_eld_sheets, merge_eld_sheets
from .utils.route_stops import SimpleStopsAPI
from .utils.route import geocode_place_cached, route_with_cache
from .tasks.trip_creation import create_trip_task
from django.views.decorators.csrf import csrf_exempt
import json
import base64



logger = logging.getLogger(__name__)
truck_stops_api = SimpleStopsAPI()


@csrf_exempt
async def calculate_trip(request):
    """Main async trip calculation API (parallel geocoding + caching + celery for DB)."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    try:
        data = json.loads(request.body.decode("utf-8"))
        pickup_location = data.get("pickup_location")
        dropoff_location = data.get("dropoff_location")
        current_location = data.get("current_location", "")
        current_cycle_used = float(data.get("current_cycle_used", 0))

        if not pickup_location or not dropoff_location:
            return JsonResponse({"error": "pickup_location and dropoff_location are required."}, status=400)

        pickup_task = geocode_place_cached(pickup_location)
        dropoff_task = geocode_place_cached(dropoff_location)
        current_task = (
            geocode_place_cached(current_location)
            if current_location
            else geocode_place_cached(pickup_location)
        )

        pickup_coords, dropoff_coords, current_coords = await asyncio.gather(
            pickup_task, dropoff_task, current_task
        )

        current_to_pickup_task = route_with_cache(current_coords, pickup_coords)
        pickup_to_dropoff_task = route_with_cache(pickup_coords, dropoff_coords)

        (
            (current_to_pickup_geometry, current_to_pickup_distance_km, _),
            (pickup_to_dropoff_geometry, pickup_to_dropoff_distance_km, duration_hr),
        ) = await asyncio.gather(current_to_pickup_task, pickup_to_dropoff_task)

        total_distance_km = current_to_pickup_distance_km + pickup_to_dropoff_distance_km
        full_route_geometry = current_to_pickup_geometry + pickup_to_dropoff_geometry

        duty_blocks, cycle_used = generate_duty_blocks(
            current_to_pickup_miles=current_to_pickup_distance_km * 0.621371,
            pickup_to_dropoff_miles=pickup_to_dropoff_distance_km * 0.621371,
            current_cycle_used=current_cycle_used,
        )

        loop = asyncio.get_running_loop()
        stops_data = await loop.run_in_executor(
            None, truck_stops_api.find_stops_along_route, pickup_coords, dropoff_coords, duty_blocks
        )

        eld_paths = generate_multiple_eld_sheets(duty_blocks)
        merged_pdf_bytes = merge_eld_sheets(eld_paths)

        encoded_pdf = base64.b64encode(merged_pdf_bytes).decode("utf-8")

        create_trip_task.delay(
            current_location=current_location,
            current_location_coords=f"{current_coords[0]},{current_coords[1]}",
            pickup_location=pickup_location,
            pickup_coords=f"{pickup_coords[0]},{pickup_coords[1]}",
            dropoff_location=dropoff_location,
            dropoff_coords=f"{dropoff_coords[0]},{dropoff_coords[1]}",
            current_cycle_used=current_cycle_used,
            total_trip_hours=round(duration_hr, 3),
            total_distance_km=round(total_distance_km, 3),
            route_geojson=json.dumps({"geometry": full_route_geometry}),
        )



        response_data = {
            "trip_summary": {
                "pickup": pickup_location,
                "dropoff": dropoff_location,
                "total_distance_km": round(total_distance_km, 2),
                "estimated_duration_hr": round(duration_hr, 2),
                "actual_stops_count": stops_data.get("total_stops", 0),
                "total_days": max([b["day"] for b in duty_blocks]) if duty_blocks else 1,
                "geometry": full_route_geometry
            },
            "duty_schedule": {"blocks": duty_blocks, "final_cycle_used": cycle_used},
            "stops": stops_data["stops"],
            "eld_files": {
                "individual_sheets": eld_paths,
                "merged_pdf_base64": encoded_pdf
            },
            "message": "Trip calculated successfully (DB insertion queued)",
        }

        return JsonResponse(response_data, status=200)

    except Exception as e:
        logger.exception(f"[ERROR] Trip calculation failed: {e}")
        return JsonResponse({"error": str(e)}, status=500)