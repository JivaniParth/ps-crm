from collections import Counter

from app.models.complaint import Complaint

OPEN = "Open"
IN_PROGRESS = "In Progress"
ESCALATED = "Escalated"
RESOLVED = "Resolved"


def build_analytics(complaints: list[Complaint]) -> dict:
    if not complaints:
        return {
            "status_breakdown": [
                {"name": OPEN, "value": 0},
                {"name": IN_PROGRESS, "value": 0},
                {"name": ESCALATED, "value": 0},
                {"name": RESOLVED, "value": 0},
            ],
            "department_volume": [],
        }

    status_counter = Counter(item.status for item in complaints)
    dept_counter = Counter(item.department for item in complaints)

    status_breakdown = [
        {"name": OPEN, "value": status_counter.get(OPEN, 0)},
        {"name": IN_PROGRESS, "value": status_counter.get(IN_PROGRESS, 0)},
        {"name": ESCALATED, "value": status_counter.get(ESCALATED, 0)},
        {"name": RESOLVED, "value": status_counter.get(RESOLVED, 0)},
    ]

    department_volume = [
        {"name": department, "complaints": count}
        for department, count in sorted(dept_counter.items(), key=lambda item: item[1], reverse=True)
    ]

    return {
        "status_breakdown": status_breakdown,
        "department_volume": department_volume,
    }
