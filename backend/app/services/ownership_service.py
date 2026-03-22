"""Ownership stake management with rules enforcement."""

from __future__ import annotations

from app.models.enums import OwnershipRole

# Valid ownership roles for validation
_VALID_ROLES = {r.value for r in OwnershipRole}


class OwnershipError(Exception):
    """Raised when an ownership operation violates a rule."""
    pass


def validate_stake(stake: dict) -> None:
    """Validate a single ownership stake dictionary."""
    required = {"tier", "dept", "role"}
    missing = required - set(stake.keys())
    if missing:
        raise OwnershipError(f"Missing required fields: {missing}")

    if stake.get("role") not in _VALID_ROLES:
        raise OwnershipError(f"Invalid role: {stake.get('role')}")

    share = stake.get("share", 0.0)
    if not (0.0 <= share <= 1.0):
        raise OwnershipError(f"Share must be between 0.0 and 1.0, got {share}")


def add_stake(
    existing_stakes: list[dict],
    new_stake: dict,
) -> list[dict]:
    """
    Add a new ownership stake, enforcing rules:
    - Exactly one primary at a time
    - Total shares must not exceed 1.0
    - No duplicate department entries
    """
    validate_stake(new_stake)

    # Check for duplicate department
    for s in existing_stakes:
        if s.get("dept") == new_stake.get("dept") and s.get("tier") == new_stake.get("tier"):
            raise OwnershipError(
                f"Department '{new_stake['dept']}' at tier '{new_stake['tier']}' already has a stake"
            )

    # If new stake is primary, demote existing primary to secondary
    if new_stake.get("role") == OwnershipRole.PRIMARY.value:
        for s in existing_stakes:
            if s.get("role") == OwnershipRole.PRIMARY.value:
                s["role"] = OwnershipRole.SECONDARY.value

    # Validate total shares
    total_share = sum(s.get("share", 0.0) for s in existing_stakes) + new_stake.get("share", 0.0)
    if total_share > 1.0:
        raise OwnershipError(
            f"Total shares would be {total_share:.2f}, exceeding 1.0"
        )

    # If sla_owner is True on the new stake, remove it from others
    if new_stake.get("sla_owner"):
        for s in existing_stakes:
            s["sla_owner"] = False

    updated = list(existing_stakes)
    updated.append(new_stake)
    return updated


def update_stake(
    existing_stakes: list[dict],
    dept: str,
    tier: str,
    updates: dict,
) -> list[dict]:
    """
    Update an existing stake's fields (share, sla_owner, role).
    Enforces rules on the resulting state.
    """
    found = False
    updated = []

    for s in existing_stakes:
        if s.get("dept") == dept and s.get("tier") == tier:
            found = True
            merged = {**s, **updates}
            validate_stake(merged)

            # If promoting to primary, demote others
            if updates.get("role") == OwnershipRole.PRIMARY.value:
                for other in existing_stakes:
                    if other is not s and other.get("role") == OwnershipRole.PRIMARY.value:
                        other["role"] = OwnershipRole.SECONDARY.value

            # If claiming SLA ownership, revoke from others
            if updates.get("sla_owner"):
                for other in existing_stakes:
                    if other is not s:
                        other["sla_owner"] = False

            updated.append(merged)
        else:
            updated.append(s)

    if not found:
        raise OwnershipError(
            f"No stake found for department '{dept}' at tier '{tier}'"
        )

    # Re-validate total shares
    total_share = sum(s.get("share", 0.0) for s in updated)
    if total_share > 1.0:
        raise OwnershipError(
            f"Total shares would be {total_share:.2f}, exceeding 1.0"
        )

    return updated


def remove_stake(
    existing_stakes: list[dict],
    dept: str,
    tier: str,
) -> list[dict]:
    """
    Remove a stake. Cannot remove the primary stake.
    """
    target = None
    for s in existing_stakes:
        if s.get("dept") == dept and s.get("tier") == tier:
            target = s
            break

    if target is None:
        raise OwnershipError(
            f"No stake found for department '{dept}' at tier '{tier}'"
        )

    if target.get("role") == OwnershipRole.PRIMARY.value:
        raise OwnershipError(
            "Cannot remove the primary stake. Reassign primary first."
        )

    return [s for s in existing_stakes if not (s.get("dept") == dept and s.get("tier") == tier)]
