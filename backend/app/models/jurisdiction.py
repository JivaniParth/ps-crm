"""Jurisdiction layer model for overlapping-authority resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class JurisdictionLayer:
    """
    A geographic zone that one government body claims authority over.
    Used for resolving overlapping jurisdictions when a complaint falls
    within multiple authorities' boundaries.
    """
    layer_id: str
    tier: str                          # GovernanceTier value
    authority_name: str                # e.g. "NHAI", "MCG", "PWD Haryana"
    department_id: str
    asset_type: str                    # "road" | "drain" | "bridge" | ...
    geojson: dict                      # GeoJSON Polygon / MultiPolygon
    priority_weight: int               # higher = stronger claim
    parent_layer_id: Optional[str] = None   # hierarchical link

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "tier": self.tier,
            "authority_name": self.authority_name,
            "department_id": self.department_id,
            "asset_type": self.asset_type,
            "geojson": self.geojson,
            "priority_weight": self.priority_weight,
            "parent_layer_id": self.parent_layer_id,
        }
