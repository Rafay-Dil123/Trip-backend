from django.urls import path
from .views import calculate_trip

urlpatterns = [
    path("calculate/", calculate_trip, name="calculate_trip"),
]
