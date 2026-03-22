"""Enumerations used across the National Public Grievance Grid."""

from enum import Enum


class GovernanceTier(str, Enum):
    """Government level that currently owns or originated the ticket."""
    LOCAL = "Local"       # Municipal Corporation / ULB / Panchayat
    STATE = "State"       # State PWD, State Health Dept, etc.
    CENTRAL = "Central"   # Central Ministry (MoHUA, MoRTH, etc.)


class TransferType(str, Enum):
    """Direction of a tier transfer."""
    ESCALATION = "escalation"   # Lower tier → higher tier
    DEVOLUTION = "devolution"   # Higher tier → lower tier
    LATERAL = "lateral"         # Same-level transfer between departments


class OwnershipRole(str, Enum):
    """Role a department plays on a shared-responsibility ticket."""
    PRIMARY = "primary"       # Main responsible department
    SECONDARY = "secondary"   # Co-responsible department
    OBSERVER = "observer"     # Read-only, notified of changes
