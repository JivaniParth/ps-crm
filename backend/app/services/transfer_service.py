"""Tier transfer orchestration service."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.audit import TierTransferAudit, compute_audit_checksum
from app.models.enums import GovernanceTier, TransferType

# Valid tier values for quick validation
_VALID_TIERS = {t.value for t in GovernanceTier}
_VALID_TRANSFER_TYPES = {t.value for t in TransferType}


class TransferValidationError(Exception):
    """Raised when a transfer request is invalid."""
    pass


def validate_transfer(
    current_tier: str,
    to_tier: str,
    transfer_type: str,
) -> None:
    """Validate that a tier transfer request is logically sound."""
    if to_tier not in _VALID_TIERS:
        raise TransferValidationError(f"Invalid target tier: {to_tier}")

    if transfer_type not in _VALID_TRANSFER_TYPES:
        raise TransferValidationError(f"Invalid transfer type: {transfer_type}")

    if current_tier == to_tier:
        raise TransferValidationError(
            f"Ticket is already at tier '{current_tier}'"
        )

    # Validate direction matches transfer_type
    tier_order = {
        GovernanceTier.LOCAL.value: 0,
        GovernanceTier.STATE.value: 1,
        GovernanceTier.CENTRAL.value: 2,
    }

    from_level = tier_order.get(current_tier, 0)
    to_level = tier_order.get(to_tier, 0)

    if transfer_type == TransferType.ESCALATION.value and to_level <= from_level:
        raise TransferValidationError(
            "Escalation must move to a higher tier"
        )

    if transfer_type == TransferType.DEVOLUTION.value and to_level >= from_level:
        raise TransferValidationError(
            "Devolution must move to a lower tier"
        )


def create_audit_record(
    ticket_id: str,
    from_tier: str,
    to_tier: str,
    from_department: str,
    to_department: str,
    reason: str,
    initiated_by: str,
    transfer_type: str = "escalation",
    metadata: dict | None = None,
) -> TierTransferAudit:
    """Create a new audit record with a computed checksum."""
    audit = TierTransferAudit(
        audit_id=str(uuid4()),
        ticket_id=ticket_id,
        from_tier=from_tier,
        to_tier=to_tier,
        from_department=from_department,
        to_department=to_department,
        reason=reason,
        initiated_by=initiated_by,
        transfer_type=transfer_type,
        metadata=metadata or {},
        timestamp=datetime.now(timezone.utc),
    )
    audit.checksum = compute_audit_checksum(audit)
    return audit
