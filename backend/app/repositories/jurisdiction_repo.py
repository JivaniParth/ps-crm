"""In-memory jurisdiction layer repository.

Supports spatial lookups against GeoJSON polygons for overlapping-jurisdiction
resolution. In production this would be backed by MongoDB's 2dsphere indexes.
"""

from __future__ import annotations

from threading import Lock
from typing import Optional

from app.models.jurisdiction import JurisdictionLayer


class JurisdictionRepository:
    """In-memory jurisdiction layer store with overlap detection."""

    def __init__(self) -> None:
        self._store: dict[str, JurisdictionLayer] = {}
        self._lock = Lock()

    def add_layer(self, layer: JurisdictionLayer) -> JurisdictionLayer:
        with self._lock:
            self._store[layer.layer_id] = layer
        return layer

    def get(self, layer_id: str) -> Optional[JurisdictionLayer]:
        return self._store.get(layer_id)

    def list_all(self) -> list[JurisdictionLayer]:
        return list(self._store.values())

    def delete(self, layer_id: str) -> bool:
        with self._lock:
            if layer_id in self._store:
                del self._store[layer_id]
                return True
            return False

    def find_overlapping(
        self,
        latitude: float,
        longitude: float,
        asset_type: str = "",
    ) -> list[JurisdictionLayer]:
        """
        Find all jurisdiction layers whose bounding box contains the point.

        In production with MongoDB, this would use $geoIntersects queries.
        The in-memory implementation uses simple bounding-box checks on the
        GeoJSON coordinates.
        """
        results = []
        for layer in self._store.values():
            # Filter by asset_type if specified
            if asset_type and layer.asset_type != asset_type:
                continue

            if self._point_in_geojson(longitude, latitude, layer.geojson):
                results.append(layer)

        # Sort by priority_weight descending (highest priority first)
        results.sort(key=lambda l: l.priority_weight, reverse=True)
        return results

    @staticmethod
    def _point_in_geojson(lng: float, lat: float, geojson: dict) -> bool:
        """
        Simplified point-in-polygon check.
        Supports GeoJSON Polygon type with a single exterior ring.
        Uses ray-casting algorithm.
        """
        geo_type = geojson.get("type", "")
        coordinates = geojson.get("coordinates", [])

        if geo_type == "Polygon" and coordinates:
            ring = coordinates[0]  # exterior ring
            return JurisdictionRepository._point_in_ring(lng, lat, ring)
        elif geo_type == "MultiPolygon":
            for polygon_coords in coordinates:
                if polygon_coords:
                    ring = polygon_coords[0]
                    if JurisdictionRepository._point_in_ring(lng, lat, ring):
                        return True
        return False

    @staticmethod
    def _point_in_ring(
        x: float, y: float, ring: list[list[float]]
    ) -> bool:
        """Ray-casting point-in-polygon test."""
        n = len(ring)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside


jurisdiction_repo = JurisdictionRepository()
