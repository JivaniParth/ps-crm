"""Tests for the National Public Grievance Grid features."""

import os

os.environ["USE_IN_MEMORY_REPO"] = "true"

from app import create_app

CITIZEN_SECRET = "GrievanceTest!123"
OFFICER_SECRET = "change-officer-password"
ADMIN_SECRET = "change-admin-password"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_citizen(client, suffix="grid"):
    r = client.post(
        "/api/auth/register",
        json={
            "username": f"citizen.{suffix}@example.com",
            "password": CITIZEN_SECRET,
            "display_name": f"Test Citizen {suffix}",
            "mobile": f"900000{suffix.zfill(4)[:4]}",
        },
    )
    return r.get_json()["token"]


def _login_admin(client):
    r = client.post(
        "/api/auth/login",
        json={"username": "admin@pscrm.gov", "password": ADMIN_SECRET},
    )
    return r.get_json()["token"]


def _login_officer(client):
    r = client.post(
        "/api/auth/login",
        json={"username": "officer.ward12@pscrm.gov", "password": OFFICER_SECRET},
    )
    return r.get_json()["token"]


def _create_complaint(client, token, desc="Pothole on main road"):
    return client.post(
        "/api/complaints",
        headers=_auth_header(token),
        json={
            "description": desc,
            "location": {"latitude": 28.61, "longitude": 77.22},
            "channel": "web",
        },
    )


# ── Ticket ID Format ─────────────────────────────────────────


def test_ticket_id_format():
    """Verify tickets follow IM-YYYY-XX-XXX-XXXX pattern."""
    app = create_app()
    client = app.test_client()
    token = _register_citizen(client, "fmt1")
    r = _create_complaint(client, token)
    data = r.get_json()

    assert r.status_code == 201
    tid = data["ticket_id"]
    parts = tid.split("-")
    assert parts[0] == "IM"                  # prefix
    assert parts[1].isdigit()                # year
    assert len(parts) >= 4                   # region + hex
    assert tid.startswith("IM-")


def test_complaint_has_tier_fields():
    """New complaints carry origin_tier and current_tier."""
    app = create_app()
    client = app.test_client()
    token = _register_citizen(client, "tier1")
    r = _create_complaint(client, token)
    data = r.get_json()

    assert data["origin_tier"] == "Local"
    assert data["current_tier"] == "Local"
    assert "state_code" in data.get("location", {})
    assert "city_code" in data.get("location", {})


# ── Tier Transfer ─────────────────────────────────────────────


def test_tier_transfer_escalation():
    """Transfer a ticket from Local → State and verify audit record."""
    app = create_app()
    client = app.test_client()

    citizen_token = _register_citizen(client, "xfer1")
    officer_token = _login_officer(client)

    # Create complaint
    r = _create_complaint(client, citizen_token, "Damaged state highway bridge")
    ticket_id = r.get_json()["ticket_id"]

    # Transfer Local → State
    r = client.post(
        f"/api/complaints/{ticket_id}/transfer",
        headers=_auth_header(officer_token),
        json={
            "to_tier": "State",
            "to_department": "PWD",
            "reason": "Road reclassified as state highway",
            "transfer_type": "escalation",
        },
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["from_tier"] == "Local"
    assert data["to_tier"] == "State"
    assert data["checksum"]  # non-empty SHA-256
    assert data["audit_id"]

    # Verify complaint tier updated
    r2 = client.get(
        f"/api/complaints/{ticket_id}",
        headers=_auth_header(citizen_token),
    )
    assert r2.get_json()["current_tier"] == "State"


def test_tier_transfer_invalid_direction():
    """Escalation must move to a higher tier."""
    app = create_app()
    client = app.test_client()

    citizen_token = _register_citizen(client, "xfer2")
    officer_token = _login_officer(client)

    r = _create_complaint(client, citizen_token)
    ticket_id = r.get_json()["ticket_id"]

    # Try escalation to same tier (should fail)
    r = client.post(
        f"/api/complaints/{ticket_id}/transfer",
        headers=_auth_header(officer_token),
        json={
            "to_tier": "Local",
            "reason": "Test",
            "transfer_type": "escalation",
        },
    )
    assert r.status_code == 400


def test_audit_trail():
    """Full audit trail is retrievable after transfer."""
    app = create_app()
    client = app.test_client()

    citizen_token = _register_citizen(client, "audit1")
    officer_token = _login_officer(client)

    r = _create_complaint(client, citizen_token)
    ticket_id = r.get_json()["ticket_id"]

    # Transfer twice: Local → State → Central
    client.post(
        f"/api/complaints/{ticket_id}/transfer",
        headers=_auth_header(officer_token),
        json={"to_tier": "State", "reason": "Escalate to state", "transfer_type": "escalation"},
    )
    client.post(
        f"/api/complaints/{ticket_id}/transfer",
        headers=_auth_header(officer_token),
        json={"to_tier": "Central", "reason": "Escalate to central", "transfer_type": "escalation"},
    )

    # Get audit trail
    r = client.get(
        f"/api/complaints/{ticket_id}/audit",
        headers=_auth_header(officer_token),
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["current_tier"] == "Central"
    assert len(data["audit_trail"]) == 2


# ── Ownership ────────────────────────────────────────────────


def test_ownership_add_stake():
    """Add an ownership stake to a ticket."""
    app = create_app()
    client = app.test_client()

    citizen_token = _register_citizen(client, "own1")
    officer_token = _login_officer(client)

    r = _create_complaint(client, citizen_token)
    ticket_id = r.get_json()["ticket_id"]

    r = client.post(
        f"/api/complaints/{ticket_id}/ownership",
        headers=_auth_header(officer_token),
        json={
            "tier": "Local",
            "dept": "Roads",
            "role": "primary",
            "share": 0.6,
            "sla_owner": True,
        },
    )
    assert r.status_code == 201
    stakes = r.get_json()["ownership_stakes"]
    assert len(stakes) == 1
    assert stakes[0]["dept"] == "Roads"
    assert stakes[0]["share"] == 0.6


def test_ownership_share_exceeds_limit():
    """Total shares cannot exceed 1.0."""
    app = create_app()
    client = app.test_client()

    citizen_token = _register_citizen(client, "own2")
    officer_token = _login_officer(client)

    r = _create_complaint(client, citizen_token)
    ticket_id = r.get_json()["ticket_id"]

    # Add 70% stake
    client.post(
        f"/api/complaints/{ticket_id}/ownership",
        headers=_auth_header(officer_token),
        json={"tier": "Local", "dept": "Roads", "role": "primary", "share": 0.7},
    )

    # Try to add another 40% (total 1.1 → should fail)
    r = client.post(
        f"/api/complaints/{ticket_id}/ownership",
        headers=_auth_header(officer_token),
        json={"tier": "State", "dept": "PWD", "role": "secondary", "share": 0.4},
    )
    assert r.status_code == 400


# ── Search ────────────────────────────────────────────────────


def test_search_by_tier():
    """Search endpoint filters by governance tier."""
    app = create_app()
    client = app.test_client()

    citizen_token = _register_citizen(client, "srch1")
    _create_complaint(client, citizen_token, "Streetlights not working")

    r = client.get(
        "/api/search?tier=Local",
        headers=_auth_header(citizen_token),
    )
    assert r.status_code == 200
    assert r.get_json()["total"] >= 1


def test_search_text():
    """Full-text search across descriptions."""
    app = create_app()
    client = app.test_client()

    citizen_token = _register_citizen(client, "srch2")
    _create_complaint(client, citizen_token, "Overflowing sewage near park")

    r = client.get(
        "/api/search?q=sewage",
        headers=_auth_header(citizen_token),
    )
    assert r.status_code == 200
    # Should find at least the complaint we just created
    results = r.get_json()["results"]
    assert any("sewage" in str(res.get("description", "")).lower() for res in results)


# ── Registry Admin ────────────────────────────────────────────


def test_registry_list():
    """Admin can list registered regions."""
    app = create_app()
    client = app.test_client()
    admin_token = _login_admin(client)

    r = client.get(
        "/api/admin/registry",
        headers=_auth_header(admin_token),
    )
    assert r.status_code == 200
    regions = r.get_json()["regions"]
    assert len(regions) >= 1  # at least the dev region


def test_registry_register_and_deregister():
    """Admin can register and deregister a regional endpoint."""
    app = create_app()
    client = app.test_client()
    admin_token = _login_admin(client)

    # Register
    r = client.post(
        "/api/admin/registry",
        headers=_auth_header(admin_token),
        json={
            "region_key": "KA-BLR",
            "db_url": "sqlite:///test_blr.db",
            "tier": "Local",
            "display_name": "Bengaluru Municipal Corp",
        },
    )
    assert r.status_code == 201

    # Deregister
    r = client.delete(
        "/api/admin/registry/KA-BLR",
        headers=_auth_header(admin_token),
    )
    assert r.status_code == 200


# ── Jurisdiction Admin ────────────────────────────────────────


def test_jurisdiction_crud():
    """Admin can add and list jurisdiction layers."""
    app = create_app()
    client = app.test_client()
    admin_token = _login_admin(client)

    r = client.post(
        "/api/admin/jurisdictions",
        headers=_auth_header(admin_token),
        json={
            "tier": "Central",
            "authority_name": "NHAI",
            "department_id": "nhai-001",
            "asset_type": "road",
            "geojson": {
                "type": "Polygon",
                "coordinates": [[[77.0, 28.0], [77.5, 28.0], [77.5, 28.5], [77.0, 28.5], [77.0, 28.0]]],
            },
            "priority_weight": 30,
        },
    )
    assert r.status_code == 201
    assert r.get_json()["authority_name"] == "NHAI"

    # List
    r = client.get(
        "/api/admin/jurisdictions",
        headers=_auth_header(admin_token),
    )
    assert r.status_code == 200
    assert len(r.get_json()["jurisdictions"]) >= 1


# ── Backward Compatibility ────────────────────────────────────


def test_existing_flow_still_works():
    """The original create → track → status-update flow works."""
    app = create_app()
    client = app.test_client()

    citizen_token = _register_citizen(client, "compat1")
    officer_token = _login_officer(client)

    # Create
    r = _create_complaint(client, citizen_token, "Street light broken")
    assert r.status_code == 201
    ticket_id = r.get_json()["ticket_id"]

    # Read
    r = client.get(f"/api/complaints/{ticket_id}")
    assert r.status_code == 200

    # Timeline
    r = client.get(f"/api/complaints/{ticket_id}/timeline")
    assert r.status_code == 200

    # Status update
    r = client.patch(
        f"/api/complaints/{ticket_id}/status",
        headers=_auth_header(officer_token),
        json={"status": "In Progress"},
    )
    assert r.status_code == 200
