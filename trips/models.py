from django.db import models


class Trip(models.Model):
    current_location = models.CharField(max_length=255, blank=True, null=True)
    current_location_coords = models.CharField(max_length=100, blank=True, null=True)
    pickup_location = models.CharField(max_length=255)
    pickup_coords = models.CharField(max_length=100, blank=True, null=True)
    dropoff_location = models.CharField(max_length=255)
    dropoff_coords = models.CharField(max_length=100, blank=True, null=True)
    current_cycle_used = models.FloatField(
        default=0.0, help_text="Hours already used in current cycle"
    )
    total_trip_hours = models.FloatField(null=True, blank=True)
    total_distance_km = models.FloatField(null=True, blank=True)
    route_geojson = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=32, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trip {self.id}: {self.pickup_location} → {self.dropoff_location}"
