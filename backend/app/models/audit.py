"""Tier-transfer audit model with tamper-detection checksum."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class TierTransferAudit:
    """Immutable record of a ticket moving between governance tiers."""
    audit_id: str
    ticket_id: str
    from_tier: str
    to_tier: str
    from_department: str
    to_department: str
    reason: str
    initiated_by: str
    approved_by: str = ""
    transfer_type: str = "escalation"
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    checksum: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "ticket_id": self.ticket_id,
            "from_tier": self.from_tier,
            "to_tier": self.to_tier,
            "from_department": self.from_department,
            "to_department": self.to_department,
            "reason": self.reason,
            "initiated_by": self.initiated_by,
            "approved_by": self.approved_by,
            "transfer_type": self.transfer_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "checksum": self.checksum,
        }


def compute_audit_checksum(audit: TierTransferAudit) -> str:
    """Deterministic SHA-256 of all audit fields for integrity verification."""
    payload = json.dumps(
        {
            "audit_id": audit.audit_id,
            "ticket_id": audit.ticket_id,
            "from_tier": audit.from_tier,
            "to_tier": audit.to_tier,
            "from_department": audit.from_department,
            "to_department": audit.to_department,
            "reason": audit.reason,
            "initiated_by": audit.initiated_by,
            "approved_by": audit.approved_by,
            "transfer_type": audit.transfer_type,
            "timestamp": audit.timestamp.isoformat(),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()
