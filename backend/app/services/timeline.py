from datetime import datetime, timedelta, timezone

STEPS = [
    "Complaint Registered",
    "AI Categorization",
    "Geo Routing",
    "Field Action",
    "Issue Resolved",
]


def build_timeline(created_at: datetime) -> list[dict[str, str]]:
    now = datetime.now(timezone.utc)
    elapsed = now - created_at

    step_thresholds = [
        timedelta(seconds=0),
        timedelta(seconds=10),
        timedelta(seconds=20),
        timedelta(seconds=40),
        timedelta(seconds=70),
    ]

    output = []
    for index, step in enumerate(STEPS):
        status = "Completed" if elapsed >= step_thresholds[index] else "Pending"
        output.append({"step": step, "status": status})

    return output
