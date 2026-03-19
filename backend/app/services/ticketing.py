from datetime import UTC, datetime
from random import randint


def generate_ticket_id() -> str:
    year = datetime.now(UTC).year
    return f"IM-{year}-{randint(10000, 99999)}"
