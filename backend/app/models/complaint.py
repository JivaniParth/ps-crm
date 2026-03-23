"""Unified complaint model for the National Public Grievance Grid."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class Complaint:
    # ── Identity ──────────────────────────────────────────────
    ticket_id: str                            # IM-2026-MH-MUM-3A7F
    citizen_name: str
    mobile: str
    description: str
    department: str
    channel: str
    incident_latitude: float
    incident_longitude: float
    reporting_latitude: float
    reporting_longitude: float
    ward: str
    assigned_officer: str

    # ── Governance tier ───────────────────────────────────────
    origin_tier: str = "Local"                # GovernanceTier value
    current_tier: str = "Local"               # may differ after escalation

    # ── Classification ────────────────────────────────────────
    category: str = ""                        # AI-classified category
    sub_category: str = ""

    # ── Regional geography ────────────────────────────────────
    state_code: str = ""                      # ISO 3166-2:IN (e.g. "MH")
    city_code: str = ""                       # IATA or Census code
    pincode: str = ""

    # ── Assignment ────────────────────────────────────────────
    assigned_department_id: str = ""

    # ── Jurisdiction / Ownership ──────────────────────────────
    ownership_stakes: list[dict] = field(default_factory=list)
    # e.g. [{"tier": "Local", "dept": "Roads", "share": 0.6, "role": "primary", "sla_owner": True}]

    # ── Status ────────────────────────────────────────────────
    status: str = "Open"
    priority: str = "Normal"                  # Low | Normal | High | Critical
    sla_deadline: Optional[datetime] = None

    # ── Timestamps ────────────────────────────────────────────
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "citizen_name": self.citizen_name,
            "mobile": self.mobile,
            "description": self.description,
            "department": self.department,
            "channel": self.channel,
            "location": {
                "incident_latitude": self.incident_latitude,
                "incident_longitude": self.incident_longitude,
                "reporting_latitude": self.reporting_latitude,
                "reporting_longitude": self.reporting_longitude,
                "state_code": self.state_code,
                "city_code": self.city_code,
                "ward": self.ward,
                "pincode": self.pincode,
            },
            "ward": self.ward,
            "assigned_officer": self.assigned_officer,
            "origin_tier": self.origin_tier,
            "current_tier": self.current_tier,
            "category": self.category,
            "sub_category": self.sub_category,
            "ownership_stakes": self.ownership_stakes,
            "status": self.status,
            "priority": self.priority,
            "sla_deadline": self.sla_deadline.isoformat() if self.sla_deadline else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
