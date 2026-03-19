from math import asin, cos, radians, sin, sqrt

WARD_CENTROIDS = [
    {"ward": "Ward-12", "officer": "R. Sharma", "lat": 28.6129, "lon": 77.2295},
    {"ward": "Ward-19", "officer": "A. Iyer", "lat": 28.5355, "lon": 77.3910},
    {"ward": "Ward-04", "officer": "P. Das", "lat": 19.0760, "lon": 72.8777},
    {"ward": "Ward-31", "officer": "S. Khan", "lat": 12.9716, "lon": 77.5946},
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * earth_radius * asin(sqrt(a))


def route_by_location(latitude: float, longitude: float) -> dict[str, str]:
    ranked = sorted(
        WARD_CENTROIDS,
        key=lambda ward: _haversine_km(latitude, longitude, ward["lat"], ward["lon"]),
    )
    nearest = ranked[0]
    return {
        "ward": nearest["ward"],
        "assigned_officer": nearest["officer"],
    }
