from celery import shared_task
from ..models import Trip
import logging


@shared_task
def create_trip_task(**trip_data):
    """Handles DB write asynchronously."""
    try:
        Object = Trip.objects.create(
            current_location=trip_data["current_location"],
            current_location_coords=trip_data["current_location_coords"],
            pickup_location=trip_data["pickup_location"],
            pickup_coords=trip_data["pickup_coords"],
            dropoff_location=trip_data["dropoff_location"],
            dropoff_coords=trip_data["dropoff_coords"],
            current_cycle_used=trip_data["current_cycle_used"],
            total_trip_hours=trip_data["total_trip_hours"],
            total_distance_km=trip_data["total_distance_km"],
            route_geojson=trip_data["route_geojson"],
            status="processed",
        )
        logging.info(f"[DB] Created trip ID: {Object.id}")

    except Exception as e:
        print(f"[DB ERROR] Failed to create trip: {e}")
