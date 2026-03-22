"""Geo-routing module — ward routing and jurisdiction-aware v2 routing."""

from math import asin, cos, radians, sin, sqrt

WARD_CENTROIDS = [
    {
        "ward": "Ward-12", "officer": "R. Sharma",
        "lat": 28.6129, "lon": 77.2295,
        "state_code": "DL", "city_code": "DEL",
    },
    {
        "ward": "Ward-19", "officer": "A. Iyer",
        "lat": 28.5355, "lon": 77.3910,
        "state_code": "DL", "city_code": "NOI",
    },
    {
        "ward": "Ward-04", "officer": "P. Das",
        "lat": 19.0760, "lon": 72.8777,
        "state_code": "MH", "city_code": "MUM",
    },
    {
        "ward": "Ward-31", "officer": "S. Khan",
        "lat": 12.9716, "lon": 77.5946,
        "state_code": "KA", "city_code": "BLR",
    },
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * earth_radius * asin(sqrt(a))


def route_by_location(latitude: float, longitude: float) -> dict[str, str]:
    """Original v1 router — returns ward and assigned_officer."""
    ranked = sorted(
        WARD_CENTROIDS,
        key=lambda ward: _haversine_km(latitude, longitude, ward["lat"], ward["lon"]),
    )
    nearest = ranked[0]
    return {
        "ward": nearest["ward"],
        "assigned_officer": nearest["officer"],
    }


def route_by_location_v2(latitude: float, longitude: float) -> dict[str, str]:
    """
    Enhanced v2 router — returns ward, officer, state_code, city_code, and tier.
    Used by the Grievance Grid flow to derive regional keys for the Service Registry.
    """
    ranked = sorted(
        WARD_CENTROIDS,
        key=lambda ward: _haversine_km(latitude, longitude, ward["lat"], ward["lon"]),
    )
    nearest = ranked[0]
    return {
        "ward": nearest["ward"],
        "assigned_officer": nearest["officer"],
        "state_code": nearest.get("state_code", "IN"),
        "city_code": nearest.get("city_code", "DEV"),
        "tier": "Local",  # ward-level routing defaults to Local tier
    }
