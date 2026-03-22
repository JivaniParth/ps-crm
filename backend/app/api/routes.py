"""PSCRM API routes — National Public Grievance Grid edition.

This module defines all REST endpoints for the platform, grouped into:
1. Auth (register, login, logout, me)
2. Classification
3. Core Grievance Lifecycle (create, read, status update, delete)
4. Timeline & Notifications
5. Dashboards (citizen, officer, admin, mayor)
6. Meta
7. Admin Management (officers, departments, citizens)
8. Tier Transfer & Audit
9. Ownership Management
10. Search & Discovery
11. Service Registry Admin
12. Jurisdiction Admin
"""

from datetime import datetime, timezone

from flask import Blueprint, request

from app.models.complaint import Complaint
from app.models.enums import GovernanceTier
from app.repositories.complaint_repository import complaint_repo, log_repo
from app.repositories.user_repository import ADMIN, CITIZEN, MAYOR, OFFICER, user_repo
from app.repositories.department_repository import department_repo
from app.repositories.audit_repository import audit_repo
from app.repositories.global_index import global_index
from app.repositories.jurisdiction_repo import jurisdiction_repo
from app.services.analytics import build_analytics
from app.services.auth_service import parse_bearer_token, sessions
from app.services.classifier import classifier
from app.services.geo_router import route_by_location, route_by_location_v2
from app.services.ticketing import generate_ticket_id
from app.services.timeline import build_timeline
from app.services.transfer_service import (
    TransferValidationError,
    create_audit_record,
    validate_transfer,
)
from app.services.ownership_service import (
    OwnershipError,
    add_stake,
    remove_stake,
    update_stake,
)
from app.services.service_registry import RegionalEndpoint, registry

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


def _ok(data, meta=None):
    """Standard response envelope."""
    return {
        "ok": True,
        "data": data,
        "meta": meta or {"timestamp": datetime.now(timezone.utc).isoformat()},
        "errors": [],
    }


def _err(errors, status=400):
    """Standard error response."""
    if isinstance(errors, str):
        errors = [{"code": "error", "message": errors}]
    return {"ok": False, "data": None, "errors": errors}, status


# ═══════════════════════════════════════════════════════════════
# 1. AUTH
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# 2. CLASSIFICATION
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# 3. CORE GRIEVANCE LIFECYCLE
# ═══════════════════════════════════════════════════════════════

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

    # AI classification
    class_result = classifier.classify(description)

    # V2 routing: get ward, officer, AND regional codes
    route = route_by_location_v2(latitude, longitude)

    # Determine governance tier
    origin_tier = str(payload.get("origin_tier", route.get("tier", "Local")))
    if origin_tier not in {t.value for t in GovernanceTier}:
        origin_tier = "Local"

    state_code = str(payload.get("state_code", route.get("state_code", ""))).upper()
    city_code = str(payload.get("city_code", route.get("city_code", ""))).upper()

    # Generate region-scoped ticket ID
    ticket_id = generate_ticket_id(state_code or "IN", city_code or "DEV")

    complaint = Complaint(
        ticket_id=ticket_id,
        citizen_name=citizen_name,
        mobile=mobile,
        description=description,
        department=class_result.department,
        channel=channel,
        latitude=latitude,
        longitude=longitude,
        ward=route["ward"],
        assigned_officer=route["assigned_officer"],
        origin_tier=origin_tier,
        current_tier=origin_tier,
        category=class_result.department,
        state_code=state_code,
        city_code=city_code,
        pincode=str(payload.get("pincode", "")),
        priority=str(payload.get("priority", "Normal")),
    )

    complaint_repo.save(complaint)
    log_repo.append(complaint.ticket_id, "Complaint registered successfully")

    # Update Global Index
    global_index.upsert(complaint.ticket_id, {
        "ticket_id": complaint.ticket_id,
        "origin_tier": complaint.origin_tier,
        "current_tier": complaint.current_tier,
        "state_code": complaint.state_code,
        "city_code": complaint.city_code,
        "department": complaint.department,
        "category": complaint.category,
        "status": complaint.status,
        "priority": complaint.priority,
        "description": complaint.description,
        "channel": complaint.channel,
        "created_at": complaint.created_at.isoformat(),
    })

    return {
        **complaint.to_dict(),
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

    # Update Global Index
    global_index.update_status(ticket_id, status)

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


# ═══════════════════════════════════════════════════════════════
# 4. TIMELINE & NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# 5. DASHBOARDS
# ═══════════════════════════════════════════════════════════════

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
    all_officers = user_repo.list_by_role(OFFICER) + user_repo.list_by_role(MAYOR)
    all_departments = department_repo.list_all()
    all_citizens = user_repo.list_by_role(CITIZEN)

    # Count complaints by officer and department
    complaint_by_officer: dict[str, int] = {}
    complaint_by_department: dict[str, int] = {}
    complaint_by_citizen: dict[str, int] = {}

    for item in complaints:
        complaint_by_officer[item.assigned_officer] = complaint_by_officer.get(item.assigned_officer, 0) + 1
        complaint_by_department[item.department] = complaint_by_department.get(item.department, 0) + 1
        complaint_by_citizen[item.mobile] = complaint_by_citizen.get(item.mobile, 0) + 1

    # Tier-level summary for Grievance Grid
    tier_breakdown = {}
    for item in complaints:
        tier = item.current_tier
        if tier not in tier_breakdown:
            tier_breakdown[tier] = {"total": 0, "open": 0, "resolved": 0}
        tier_breakdown[tier]["total"] += 1
        if item.status == STATUS_RESOLVED:
            tier_breakdown[tier]["resolved"] += 1
        else:
            tier_breakdown[tier]["open"] += 1

    return {
        "user": user.to_public_dict(),
        "summary": {
            "total_complaints": len(complaints),
            "total_open": sum(1 for item in complaints if item.status != STATUS_RESOLVED),
            "total_resolved": sum(1 for item in complaints if item.status == STATUS_RESOLVED),
            "active_officers": len(all_officers),
            "total_departments": len(all_departments),
            "registered_citizens": len(all_citizens),
        },
        "tier_breakdown": tier_breakdown,
        "officer_manager": [
            {
                "username": officer.username,
                "display_name": officer.display_name,
                "ward": officer.ward,
                "role": officer.role,
                "assigned_complaints": complaint_by_officer.get(officer.username, 0),
                "departments": officer.departments,
            }
            for officer in sorted(all_officers, key=lambda o: complaint_by_officer.get(o.username, 0), reverse=True)
        ],
        "department_manager": [
            {
                "id": dept.id,
                "name": dept.name,
                "description": dept.description,
                "complaints": complaint_by_department.get(dept.name, 0),
            }
            for dept in sorted(all_departments, key=lambda d: complaint_by_department.get(d.name, 0), reverse=True)
        ],
        "citizen_manager": [
            {
                "username": citizen.username,
                "citizen_name": citizen.display_name,
                "mobile": citizen.mobile,
                "complaints": complaint_by_citizen.get(citizen.mobile, 0),
            }
            for citizen in sorted(all_citizens, key=lambda c: complaint_by_citizen.get(c.mobile, 0), reverse=True)
        ],
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


# ═══════════════════════════════════════════════════════════════
# 6. META
# ═══════════════════════════════════════════════════════════════

@api_bp.get("/meta/channels")
def channels_meta():
    return {
        "active_channels": ["web", "mobile"],
        "planned_channels": ["sms", "voice_ivr"],
    }


# ═══════════════════════════════════════════════════════════════
# 7. ADMIN MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@api_bp.get("/admin/officers")
def list_officers():
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    officers = user_repo.list_by_role(OFFICER)
    mayors = user_repo.list_by_role(MAYOR)
    all_users = officers + mayors

    return {
        "officers": [
            {
                "username": u.username,
                "display_name": u.display_name,
                "ward": u.ward,
                "role": u.role,
                "departments": u.departments,
            }
            for u in all_users
        ]
    }


@api_bp.post("/admin/officers")
def create_officer():
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip().lower()
    password = str(payload.get("password", "")).strip()
    display_name = str(payload.get("display_name", "")).strip()
    ward = str(payload.get("ward", "")).strip()
    departments = payload.get("departments", [])

    if not username or not password or not display_name or not ward:
        return {"error": "username, password, display_name and ward are required"}, 400

    try:
        new_officer = user_repo.create_officer(
            username=username,
            password=password,
            display_name=display_name,
            ward=ward,
            departments=departments,
        )
        return {
            "username": new_officer.username,
            "display_name": new_officer.display_name,
            "ward": new_officer.ward,
            "departments": new_officer.departments,
        }, 201
    except ValueError as exc:
        return {"error": str(exc)}, 409


@api_bp.put("/admin/officers/<username>")
def update_officer(username: str):
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    display_name = payload.get("display_name", "")
    ward = payload.get("ward", "")
    departments = payload.get("departments", [])

    updated_user = user_repo.update_officer(
        username=username.lower(),
        display_name=display_name,
        ward=ward,
        departments=departments,
    )

    if updated_user is None:
        return {"error": "officer not found"}, 404

    return {
        "username": updated_user.username,
        "display_name": updated_user.display_name,
        "ward": updated_user.ward,
        "departments": updated_user.departments,
    }


@api_bp.delete("/admin/officers/<username>")
def delete_officer(username: str):
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    if user_repo.delete_user(username.lower()):
        return {"status": "deleted"}
    return {"error": "officer not found"}, 404


@api_bp.get("/admin/departments")
def list_departments():
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    departments = department_repo.list_all()
    return {
        "departments": [d.to_dict() for d in departments]
    }


@api_bp.post("/admin/departments")
def create_department():
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()

    if not name:
        return {"error": "name is required"}, 400

    try:
        new_dept = department_repo.create(name, description)
        return new_dept.to_dict(), 201
    except ValueError as exc:
        return {"error": str(exc)}, 409


@api_bp.put("/admin/departments/<name>")
def update_department(name: str):
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    description = payload.get("description", "")

    updated = department_repo.update(name, description)
    if updated is None:
        return {"error": "department not found"}, 404

    return updated.to_dict()


@api_bp.delete("/admin/departments/<name>")
def delete_department(name: str):
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    if department_repo.delete(name):
        return {"status": "deleted"}
    return {"error": "department not found"}, 404


@api_bp.get("/admin/citizens")
def list_citizens():
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    complaints = complaint_repo.list_all()
    citizens_map: dict[str, dict] = {}

    for complaint in complaints:
        if complaint.mobile not in citizens_map:
            citizens_map[complaint.mobile] = {
                "mobile": complaint.mobile,
                "citizen_name": complaint.citizen_name,
                "complaints": 0,
            }
        citizens_map[complaint.mobile]["complaints"] += 1

    return {
        "citizens": sorted(
            citizens_map.values(),
            key=lambda x: x["complaints"],
            reverse=True
        )
    }


@api_bp.delete("/admin/citizens/<mobile>")
def delete_citizen(mobile: str):
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    complaints = complaint_repo.list_by_mobile(mobile)
    if not complaints:
        return {"error": "citizen not found"}, 404

    for complaint in complaints:
        complaint_repo.delete(complaint.ticket_id)

    return {"status": "deleted", "complaints_removed": len(complaints)}


# ═══════════════════════════════════════════════════════════════
# 8. TIER TRANSFER & AUDIT
# ═══════════════════════════════════════════════════════════════

@api_bp.post("/complaints/<ticket_id>/transfer")
def transfer_ticket(ticket_id: str):
    """Escalate or devolve a ticket to another governance tier."""
    user, _, error = _require_auth([OFFICER, ADMIN])
    if error:
        return error

    complaint = complaint_repo.get(ticket_id)
    if complaint is None:
        return {"error": TICKET_NOT_FOUND}, 404

    payload = request.get_json(silent=True) or {}
    to_tier = str(payload.get("to_tier", "")).strip()
    to_department = str(payload.get("to_department", "")).strip()
    reason = str(payload.get("reason", "")).strip()
    transfer_type = str(payload.get("transfer_type", "escalation")).strip()

    if not to_tier or not reason:
        return {"error": "to_tier and reason are required"}, 400

    # Validate the transfer
    try:
        validate_transfer(complaint.current_tier, to_tier, transfer_type)
    except TransferValidationError as exc:
        return {"error": str(exc)}, 400

    # Create audit record
    audit = create_audit_record(
        ticket_id=ticket_id,
        from_tier=complaint.current_tier,
        to_tier=to_tier,
        from_department=complaint.department,
        to_department=to_department or complaint.department,
        reason=reason,
        initiated_by=user.username,
        transfer_type=transfer_type,
    )
    audit_repo.save(audit)

    # Update complaint tier and optionally department
    complaint_repo.update_tier(ticket_id, to_tier)
    
    new_department = complaint.department
    if to_department and to_department != complaint.department:
        new_department = to_department
        complaint_repo.update_department(ticket_id, to_department)
        
        # ACTIVE LEARNING FEEDBACK LOOP:
        # User manually corrected the AI's classification. Feed the ground truth back to partial_fit.
        classifier.retrain(complaint.description, to_department)

    # Update Global Index
    global_index.update_status(ticket_id, complaint.status, current_tier=to_tier, department=new_department)

    # Log the transfer
    log_repo.append(
        ticket_id,
        f"Transferred from {complaint.current_tier} to {to_tier} by {user.display_name}: {reason}",
    )

    return {
        "audit_id": audit.audit_id,
        "ticket_id": ticket_id,
        "from_tier": audit.from_tier,
        "to_tier": audit.to_tier,
        "transfer_type": audit.transfer_type,
        "checksum": audit.checksum,
    }


@api_bp.get("/complaints/<ticket_id>/audit")
def get_ticket_audit(ticket_id: str):
    """Full audit trail for a ticket."""
    _, _, error = _require_auth([OFFICER, ADMIN])
    if error:
        return error

    complaint = complaint_repo.get(ticket_id)
    if complaint is None:
        return {"error": TICKET_NOT_FOUND}, 404

    audits = audit_repo.list_by_ticket(ticket_id)
    return {
        "ticket_id": ticket_id,
        "current_tier": complaint.current_tier,
        "origin_tier": complaint.origin_tier,
        "audit_trail": [a.to_dict() for a in audits],
    }


@api_bp.get("/audit/transfers")
def list_transfers():
    """National transfer analytics — filterable by tier and date range."""
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    tier = request.args.get("tier", "")
    from_date_str = request.args.get("from_date", "")
    to_date_str = request.args.get("to_date", "")

    from_date = None
    to_date = None
    if from_date_str:
        try:
            from_date = datetime.fromisoformat(from_date_str)
        except ValueError:
            pass
    if to_date_str:
        try:
            to_date = datetime.fromisoformat(to_date_str)
        except ValueError:
            pass

    audits = audit_repo.list_by_tier(tier=tier, from_date=from_date, to_date=to_date)
    return {
        "total": len(audits),
        "transfers": [a.to_dict() for a in audits],
    }


# ═══════════════════════════════════════════════════════════════
# 9. OWNERSHIP MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@api_bp.get("/complaints/<ticket_id>/ownership")
def get_ownership(ticket_id: str):
    """List all ownership stakes for a ticket."""
    _, _, error = _require_auth()
    if error:
        return error

    complaint = complaint_repo.get(ticket_id)
    if complaint is None:
        return {"error": TICKET_NOT_FOUND}, 404

    return {
        "ticket_id": ticket_id,
        "ownership_stakes": complaint.ownership_stakes,
    }


@api_bp.post("/complaints/<ticket_id>/ownership")
def add_ownership(ticket_id: str):
    """Add a department stake."""
    user, _, error = _require_auth([OFFICER, ADMIN])
    if error:
        return error

    complaint = complaint_repo.get(ticket_id)
    if complaint is None:
        return {"error": TICKET_NOT_FOUND}, 404

    payload = request.get_json(silent=True) or {}
    new_stake = {
        "tier": str(payload.get("tier", "")).strip(),
        "dept": str(payload.get("department_id", payload.get("dept", ""))).strip(),
        "role": str(payload.get("role", "secondary")).strip(),
        "share": float(payload.get("share", 0.0)),
        "sla_owner": bool(payload.get("sla_owner", False)),
        "added_by": user.username,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        updated_stakes = add_stake(complaint.ownership_stakes, new_stake)
    except OwnershipError as exc:
        return {"error": str(exc)}, 400

    complaint_repo.update_ownership(ticket_id, updated_stakes)
    log_repo.append(
        ticket_id,
        f"Ownership stake added: {new_stake['dept']} ({new_stake['tier']}) by {user.display_name}",
    )

    return {
        "ticket_id": ticket_id,
        "ownership_stakes": updated_stakes,
    }, 201


@api_bp.put("/complaints/<ticket_id>/ownership/<dept_id>")
def update_ownership(ticket_id: str, dept_id: str):
    """Update a department's stake details."""
    user, _, error = _require_auth([OFFICER, ADMIN])
    if error:
        return error

    complaint = complaint_repo.get(ticket_id)
    if complaint is None:
        return {"error": TICKET_NOT_FOUND}, 404

    payload = request.get_json(silent=True) or {}
    tier = str(payload.get("tier", "")).strip()
    updates = {}
    if "share" in payload:
        updates["share"] = float(payload["share"])
    if "sla_owner" in payload:
        updates["sla_owner"] = bool(payload["sla_owner"])
    if "role" in payload:
        updates["role"] = str(payload["role"]).strip()

    # Find the tier for this dept_id from existing stakes
    if not tier:
        for s in complaint.ownership_stakes:
            if s.get("dept") == dept_id:
                tier = s.get("tier", "")
                break

    if not tier:
        return {"error": f"No existing stake found for department '{dept_id}'"}, 404

    try:
        updated_stakes = update_stake(complaint.ownership_stakes, dept_id, tier, updates)
    except OwnershipError as exc:
        return {"error": str(exc)}, 400

    complaint_repo.update_ownership(ticket_id, updated_stakes)
    log_repo.append(
        ticket_id,
        f"Ownership stake updated: {dept_id} by {user.display_name}",
    )

    return {
        "ticket_id": ticket_id,
        "ownership_stakes": updated_stakes,
    }


@api_bp.delete("/complaints/<ticket_id>/ownership/<dept_id>")
def delete_ownership(ticket_id: str, dept_id: str):
    """Remove a department's stake."""
    user, _, error = _require_auth([ADMIN])
    if error:
        return error

    complaint = complaint_repo.get(ticket_id)
    if complaint is None:
        return {"error": TICKET_NOT_FOUND}, 404

    # Find tier for this dept
    tier = ""
    for s in complaint.ownership_stakes:
        if s.get("dept") == dept_id:
            tier = s.get("tier", "")
            break

    if not tier:
        return {"error": f"No stake found for department '{dept_id}'"}, 404

    try:
        updated_stakes = remove_stake(complaint.ownership_stakes, dept_id, tier)
    except OwnershipError as exc:
        return {"error": str(exc)}, 400

    complaint_repo.update_ownership(ticket_id, updated_stakes)
    log_repo.append(
        ticket_id,
        f"Ownership stake removed: {dept_id} by {user.display_name}",
    )

    return {
        "ticket_id": ticket_id,
        "ownership_stakes": updated_stakes,
    }


# ═══════════════════════════════════════════════════════════════
# 10. SEARCH & DISCOVERY
# ═══════════════════════════════════════════════════════════════

@api_bp.get("/search")
def search_complaints():
    """Full-text + faceted search across all regions via Global Index."""
    _, _, error = _require_auth()
    if error:
        return error

    query = request.args.get("q", "")
    tier = request.args.get("tier", "")
    status = request.args.get("status", "")
    state_code = request.args.get("state_code", "")
    department = request.args.get("department", "")
    skip = int(request.args.get("skip", 0))
    limit = min(int(request.args.get("limit", 50)), 100)

    # Build filter
    filters: dict = {}
    if tier:
        filters["current_tier"] = tier
    if status:
        filters["status"] = status
    if state_code:
        filters["state_code"] = state_code.upper()
    if department:
        filters["department"] = department

    if query and not filters:
        results = global_index.search_by_text(query, limit=limit)
    elif query:
        # Text search + filter: search first, then apply filters
        text_results = global_index.search_by_text(query, limit=limit * 5)
        results = []
        for doc in text_results:
            match = all(doc.get(k) == v for k, v in filters.items())
            if match:
                results.append(doc)
        results = results[skip:skip + limit]
    else:
        results = global_index.search(filters, skip=skip, limit=limit)

    return {
        "total": len(results),
        "results": results,
    }


@api_bp.get("/search/by-tier")
def search_by_tier():
    """Aggregate ticket counts by governance tier."""
    _, _, error = _require_auth()
    if error:
        return error

    return {
        "tier_summary": global_index.aggregate_by_tier(),
    }


# ═══════════════════════════════════════════════════════════════
# 11. SERVICE REGISTRY ADMIN
# ═══════════════════════════════════════════════════════════════

@api_bp.get("/admin/registry")
def list_registry():
    """List all registered regional endpoints."""
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    return {
        "regions": [ep.to_dict() for ep in registry.list_regions()],
    }


@api_bp.post("/admin/registry")
def register_region():
    """Register a new regional database endpoint."""
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    region_key = str(payload.get("region_key", "")).strip().upper()
    db_url = str(payload.get("db_url", "")).strip()
    tier = str(payload.get("tier", "")).strip()
    display_name = str(payload.get("display_name", "")).strip()

    if not region_key or not db_url or not tier or not display_name:
        return {"error": "region_key, db_url, tier, and display_name are required"}, 400

    if tier not in {t.value for t in GovernanceTier}:
        return {"error": f"Invalid tier: {tier}"}, 400

    ep = RegionalEndpoint(
        region_key=region_key,
        db_url=db_url,
        tier=tier,
        display_name=display_name,
    )
    registry.register(ep)

    return {"status": "registered", "region": ep.to_dict()}, 201


@api_bp.delete("/admin/registry/<region_key>")
def deregister_region(region_key: str):
    """Deregister a regional endpoint."""
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    if not registry.has_region(region_key.upper()):
        return {"error": f"Region '{region_key}' not found"}, 404

    registry.deregister(region_key.upper())
    return {"status": "deregistered", "region_key": region_key.upper()}


# ═══════════════════════════════════════════════════════════════
# 12. JURISDICTION ADMIN
# ═══════════════════════════════════════════════════════════════

@api_bp.post("/admin/jurisdictions")
def add_jurisdiction():
    """Register a jurisdiction layer."""
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    from uuid import uuid4
    from app.models.jurisdiction import JurisdictionLayer

    payload = request.get_json(silent=True) or {}
    tier = str(payload.get("tier", "")).strip()
    authority_name = str(payload.get("authority_name", "")).strip()
    department_id = str(payload.get("department_id", "")).strip()
    asset_type = str(payload.get("asset_type", "")).strip()
    geojson = payload.get("geojson", {})
    priority_weight = int(payload.get("priority_weight", 10))

    if not tier or not authority_name or not asset_type:
        return {"error": "tier, authority_name, and asset_type are required"}, 400

    if tier not in {t.value for t in GovernanceTier}:
        return {"error": f"Invalid tier: {tier}"}, 400

    layer = JurisdictionLayer(
        layer_id=str(uuid4()),
        tier=tier,
        authority_name=authority_name,
        department_id=department_id,
        asset_type=asset_type,
        geojson=geojson,
        priority_weight=priority_weight,
        parent_layer_id=payload.get("parent_layer_id"),
    )
    jurisdiction_repo.add_layer(layer)

    return layer.to_dict(), 201


@api_bp.get("/admin/jurisdictions")
def list_jurisdictions():
    """List all jurisdiction layers."""
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    layers = jurisdiction_repo.list_all()
    return {
        "jurisdictions": [l.to_dict() for l in layers],
    }


@api_bp.get("/admin/jurisdictions/overlap")
def check_overlap():
    """Preview overlapping jurisdictions at a GPS point."""
    _, _, error = _require_auth([ADMIN])
    if error:
        return error

    lat = float(request.args.get("lat", 0.0))
    lng = float(request.args.get("lng", 0.0))
    asset_type = request.args.get("asset_type", "")

    overlapping = jurisdiction_repo.find_overlapping(lat, lng, asset_type)
    return {
        "point": {"latitude": lat, "longitude": lng},
        "asset_type": asset_type,
        "overlapping_layers": [l.to_dict() for l in overlapping],
    }
