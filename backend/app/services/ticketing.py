"""Region-scoped universal ticket ID generator."""

from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

_counter_lock = Lock()
_counters: dict[str, int] = {}   # keyed by "YYYY-REGION"


def generate_ticket_id(state_code: str = "IN", city_code: str = "DEV") -> str:
    """
    Generate a collision-safe universal ticket ID.

    Format: IM-YYYY-STATE-CITY-HEX
    Example: IM-2026-MH-MUM-3A7F

    When called without arguments defaults to IM-YYYY-IN-DEV-XXXX
    for backward compatibility with the existing system.
    """
    year = datetime.now(UTC).year
    region = f"{state_code}-{city_code}".upper()
    bucket = f"{year}-{region}"

    with _counter_lock:
        seq = _counters.get(bucket, 0) + 1
        _counters[bucket] = seq

    hex_suffix = f"{seq:04X}" if seq <= 0xFFFF else uuid4().hex[:4].upper()
    return f"IM-{year}-{region}-{hex_suffix}"
