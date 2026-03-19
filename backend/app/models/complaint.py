from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Complaint:
    ticket_id: str
    citizen_name: str
    mobile: str
    description: str
    department: str
    channel: str
    latitude: float
    longitude: float
    ward: str
    assigned_officer: str
    status: str = "Open"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "citizen_name": self.citizen_name,
            "mobile": self.mobile,
            "description": self.description,
            "department": self.department,
            "channel": self.channel,
            "location": {
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
            "ward": self.ward,
            "assigned_officer": self.assigned_officer,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
