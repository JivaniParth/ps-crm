from datetime import datetime, timezone

from flask import Blueprint, request

from app.models.complaint import Complaint
from app.repositories.complaint_repository import complaint_repo, log_repo
from app.repositories.user_repository import ADMIN, CITIZEN, MAYOR, OFFICER, user_repo
from app.services.analytics import build_analytics
from app.services.auth_service import parse_bearer_token, sessions
from app.services.classifier import classifier
from app.services.geo_router import route_by_location
from app.services.ticketing import generate_ticket_id
from app.services.timeline import build_timeline

api_bp = Blueprint("api", __name__)
TICKET_NOT_FOUND = "ticket not found"
UNAUTHORIZED = "unauthorized"
FORBIDDEN = "forbidden"
STATUS_OPEN = "Open"
STATUS_IN_PROGRESS = "In Progress"
STATUS_ESCALATED = "Escalated"
STATUS_RESOLVED = "Resolved"


def _require_auth(roles: list[str] | None = None):
    token = parse_bearer_token(request.headers.get("Authorization"))
    user = sessions.get_user(token or "") if token else None
    if user is None:
        return None, token, ({"error": UNAUTHORIZED}, 401)
    if roles and user.role not in roles:
        return user, token, ({"error": FORBIDDEN}, 403)
    return user, token, None


@api_bp.post("/auth/register")
def register_citizen():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip().lower()
    password = str(payload.get("password", ""))
    display_name = str(payload.get("display_name", "")).strip()
    mobile = str(payload.get("mobile", "")).strip()

    if not username or not password or not display_name or not mobile:
        return {"error": "username, password, display_name and mobile are required"}, 400

    try:
        user = user_repo.create_citizen(
            username=username,
            password=password,
            display_name=display_name,
            mobile=mobile,
        )
    except ValueError as exc:
        return {"error": str(exc)}, 409

    token = sessions.issue(user)
    return {
        "token": token,
        "user": user.to_public_dict(),
    }, 201


@api_bp.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip().lower()
    password = str(payload.get("password", ""))

    user = user_repo.verify_password(username, password)
    if user is None:
        return {"error": "invalid credentials"}, 401

    token = sessions.issue(user)
    return {
        "token": token,
        "user": user.to_public_dict(),
    }


@api_bp.post("/auth/logout")
def logout():
    _, token, error = _require_auth()
    if error:
        return error

    sessions.revoke(token or "")
    return {"status": "logged_out"}


@api_bp.get("/auth/me")
def me():
    user, _, error = _require_auth()
    if error:
        return error
    return {"user": user.to_public_dict()}


@api_bp.post("/classify")
def classify_text():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "")

    if not isinstance(text, str):
        return {"error": "text must be a string"}, 400

    result = classifier.classify(text)
    return {
        "department": result.department,
        "confidence": round(result.confidence, 4),
    }


@api_bp.post("/complaints")
def create_complaint():
    user, _, error = _require_auth([CITIZEN, ADMIN])
    if error:
        return error

    payload = request.get_json(silent=True) or {}

    description = str(payload.get("description", "")).strip()
    citizen_name = str(payload.get("citizen_name", "")).strip() if user.role == ADMIN else user.display_name
    mobile = str(payload.get("mobile", "")).strip() if user.role == ADMIN else user.mobile
    channel = str(payload.get("channel", "web")).strip() or "web"

    location = payload.get("location", {}) or {}
    latitude = float(location.get("latitude", 0.0))
    longitude = float(location.get("longitude", 0.0))

    if not description or not citizen_name or not mobile:
        return {"error": "citizen_name, mobile and description are required"}, 400

    class_result = classifier.classify(description)
    route = route_by_location(latitude, longitude)

    complaint = Complaint(
        ticket_id=generate_ticket_id(),
        citizen_name=citizen_name,
        mobile=mobile,
        description=description,
        department=class_result.department,
        channel=channel,
        latitude=latitude,
        longitude=longitude,
        ward=route["ward"],
        assigned_officer=route["assigned_officer"],
    )

    complaint_repo.save(complaint)
    log_repo.append(complaint.ticket_id, "Complaint registered successfully")

    return {
        **complaint.to_dict(),
        "status": "Open",
        "confidence": round(class_result.confidence, 4),
    }, 201


@api_bp.patch("/complaints/<ticket_id>/status")
def update_status(ticket_id: str):
    user, _, error = _require_auth([OFFICER, ADMIN])
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    status = str(payload.get("status", "")).strip()
    allowed_statuses = {STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_ESCALATED, STATUS_RESOLVED}
    if status not in allowed_statuses:
        return {"error": "invalid status value"}, 400

    complaint = complaint_repo.get(ticket_id)
    if complaint is None:
        return {"error": TICKET_NOT_FOUND}, 404

    if user.role == OFFICER and complaint.ward != user.ward:
        return {"error": FORBIDDEN}, 403

    complaint = complaint_repo.update_status(ticket_id, status)
    log_repo.append(ticket_id, f"Status updated to {status} by {user.display_name}")
    return complaint.to_dict()


@api_bp.get("/complaints/<ticket_id>")
def get_complaint(ticket_id: str):
    complaint = complaint_repo.get(ticket_id)
    if complaint is None:
        return {"error": TICKET_NOT_FOUND}, 404

    timeline = build_timeline(complaint.created_at)
    if timeline[-1]["status"] == "Completed":
        complaint.status = "Resolved"
    elif timeline[3]["status"] == "Completed":
        complaint.status = "In Progress"

    return complaint.to_dict()


@api_bp.get("/complaints/<ticket_id>/timeline")
def get_timeline(ticket_id: str):
    complaint = complaint_repo.get(ticket_id)
    if complaint is None:
        return {"error": TICKET_NOT_FOUND}, 404

    steps = build_timeline(complaint.created_at)
    log_repo.append(ticket_id, f"Timeline viewed at {datetime.now(timezone.utc).isoformat()}")
    return {
        "ticket_id": ticket_id,
        "steps": steps,
    }


@api_bp.get("/complaints/<ticket_id>/notifications")
def get_notifications(ticket_id: str):
    complaint = complaint_repo.get(ticket_id)
    if complaint is None:
        return {"error": TICKET_NOT_FOUND}, 404

    steps = build_timeline(complaint.created_at)
    notifications = [
        {
            "message": f"{step['step']} is now {step['status']}",
            "priority": "normal" if step["status"] == "Completed" else "low",
        }
        for step in steps
    ]

    return {
        "ticket_id": ticket_id,
        "notifications": notifications,
        "channel_support": ["web", "mobile"],
        "future_channels": ["sms", "voice_ivr"],
    }


@api_bp.get("/analytics")
def analytics():
    _, _, error = _require_auth([OFFICER, ADMIN, MAYOR])
    if error:
        return error

    complaints = complaint_repo.list_all()
    return build_analytics(complaints)


@api_bp.get("/dashboard/citizen")
def citizen_dashboard():
    user, _, error = _require_auth([CITIZEN])
    if error:
        return error

    complaints = complaint_repo.list_by_mobile(user.mobile)
    open_count = sum(
        1 for item in complaints if item.status in {STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_ESCALATED}
    )
    resolved_count = sum(1 for item in complaints if item.status == STATUS_RESOLVED)

    return {
        "user": user.to_public_dict(),
        "summary": {
            "total_complaints": len(complaints),
            "open_complaints": open_count,
            "resolved_complaints": resolved_count,
        },
        "recent": [item.to_dict() for item in sorted(complaints, key=lambda x: x.created_at, reverse=True)[:5]],
    }


@api_bp.get("/dashboard/officer")
def officer_dashboard():
    user, _, error = _require_auth([OFFICER])
    if error:
        return error

    complaints = complaint_repo.list_by_ward(user.ward)
    pending = [item.to_dict() for item in complaints if item.status != STATUS_RESOLVED]

    return {
        "user": user.to_public_dict(),
        "ward": user.ward,
        "summary": {
            "assigned": len(complaints),
            "pending": len(pending),
            "resolved": len(complaints) - len(pending),
        },
        "queue": pending,
    }


@api_bp.get("/dashboard/admin")
def admin_dashboard():
    user, _, error = _require_auth([ADMIN])
    if error:
        return error

    complaints = complaint_repo.list_all()
    by_officer: dict[str, int] = {}
    by_department: dict[str, int] = {}
    by_citizen: dict[str, dict[str, int | str]] = {}

    for item in complaints:
        by_officer[item.assigned_officer] = by_officer.get(item.assigned_officer, 0) + 1
        by_department[item.department] = by_department.get(item.department, 0) + 1
        if item.mobile not in by_citizen:
            by_citizen[item.mobile] = {
                "citizen_name": item.citizen_name,
                "mobile": item.mobile,
                "complaints": 0,
            }
        by_citizen[item.mobile]["complaints"] += 1

    return {
        "user": user.to_public_dict(),
        "summary": {
            "total_complaints": len(complaints),
            "total_open": sum(1 for item in complaints if item.status != STATUS_RESOLVED),
            "total_resolved": sum(1 for item in complaints if item.status == STATUS_RESOLVED),
            "active_officers": len(by_officer),
            "total_departments": len(by_department),
            "registered_citizens": len(by_citizen),
        },
        "officer_manager": [
            {"officer": officer, "assigned_complaints": count}
            for officer, count in sorted(by_officer.items(), key=lambda item: item[1], reverse=True)
        ],
        "department_manager": [
            {"department": department, "complaints": count}
            for department, count in sorted(by_department.items(), key=lambda item: item[1], reverse=True)
        ],
        "citizen_manager": sorted(
            by_citizen.values(), key=lambda item: item["complaints"], reverse=True
        ),
    }


@api_bp.get("/dashboard/mayor")
def mayor_dashboard():
    user, _, error = _require_auth([MAYOR])
    if error:
        return error

    complaints = complaint_repo.list_all()
    escalated_count = sum(1 for item in complaints if item.status == STATUS_ESCALATED)

    return {
        "user": user.to_public_dict(),
        "summary": {
            "total_complaints": len(complaints),
            "open_complaints": sum(1 for item in complaints if item.status != STATUS_RESOLVED),
            "resolved_complaints": sum(1 for item in complaints if item.status == STATUS_RESOLVED),
            "escalated_complaints": escalated_count,
        },
        "analytics": build_analytics(complaints),
    }


@api_bp.get("/meta/channels")
def channels_meta():
    return {
        "active_channels": ["web", "mobile"],
        "planned_channels": ["sms", "voice_ivr"],
    }
