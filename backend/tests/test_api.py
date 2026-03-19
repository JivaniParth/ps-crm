from app import create_app

CITIZEN_TEST_SECRET = "CitizenTest!890"
OFFICER_TEST_SECRET = "change-officer-password"
MAYOR_TEST_SECRET = "change-mayor-password"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint():
    app = create_app()
    client = app.test_client()

    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_classification_endpoint():
    app = create_app()
    client = app.test_client()

    response = client.post("/api/classify", json={"text": "There is sewage overflow near my house"})
    payload = response.get_json()

    assert response.status_code == 200
    assert "department" in payload
    assert "confidence" in payload


def test_ticket_creation_flow():
    app = create_app()
    client = app.test_client()

    register = client.post(
        "/api/auth/register",
        json={
            "username": "citizen.one@example.com",
            "password": CITIZEN_TEST_SECRET,
            "display_name": "Aarav Mehta",
            "mobile": "9876543210",
        },
    )
    citizen_token = register.get_json()["token"]

    response = client.post(
        "/api/complaints",
        headers=_auth_header(citizen_token),
        json={
            "description": "Streetlights are not working for 3 days",
            "location": {"latitude": 28.61, "longitude": 77.22},
            "channel": "web",
        },
    )

    payload = response.get_json()
    assert response.status_code == 201
    assert payload["ticket_id"].startswith("IM-")
    assert payload["ward"].startswith("Ward-")


def test_officer_dashboard_access_control():
    app = create_app()
    client = app.test_client()

    register = client.post(
        "/api/auth/register",
        json={
            "username": "citizen.two@example.com",
            "password": CITIZEN_TEST_SECRET,
            "display_name": "Nisha Rao",
            "mobile": "9990001112",
        },
    )
    citizen_token = register.get_json()["token"]

    forbidden = client.get("/api/dashboard/officer", headers=_auth_header(citizen_token))
    assert forbidden.status_code == 403

    officer_login = client.post(
        "/api/auth/login",
        json={
            "username": "officer.ward12@pscrm.gov",
            "password": OFFICER_TEST_SECRET,
        },
    )
    officer_token = officer_login.get_json()["token"]

    ok = client.get("/api/dashboard/officer", headers=_auth_header(officer_token))
    assert ok.status_code == 200


def test_mayor_dashboard_access_control():
    app = create_app()
    client = app.test_client()

    register = client.post(
        "/api/auth/register",
        json={
            "username": "citizen.three@example.com",
            "password": CITIZEN_TEST_SECRET,
            "display_name": "Ritu Jain",
            "mobile": "9011112233",
        },
    )
    citizen_token = register.get_json()["token"]

    forbidden = client.get("/api/dashboard/mayor", headers=_auth_header(citizen_token))
    assert forbidden.status_code == 403

    mayor_login = client.post(
        "/api/auth/login",
        json={
            "username": "mayor@pscrm.gov",
            "password": MAYOR_TEST_SECRET,
        },
    )
    mayor_token = mayor_login.get_json()["token"]

    ok = client.get("/api/dashboard/mayor", headers=_auth_header(mayor_token))
    payload = ok.get_json()

    assert ok.status_code == 200
    assert "analytics" in payload
