"""Focused compatibility and authorization tests for the admin console API."""
import uuid

from fastapi.testclient import TestClient

from app.config import BACKEND_DIR, ENV_FILES, PROJECT_ROOT
from app.database import SessionLocal
from app.models.audit_log import AuditLog
from app.models.journal import Journal
from main import app

client = TestClient(app)


def _headers(username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_settings_use_absolute_project_env_paths():
    assert PROJECT_ROOT == BACKEND_DIR.parent
    assert all(path.is_absolute() for path in ENV_FILES)
    assert [path.name for path in ENV_FILES] == ["env", ".env", ".env"]
    assert ENV_FILES[-1].parent == BACKEND_DIR


def test_admin_dashboard_and_personnel_shapes_on_both_prefixes():
    supervisor_headers = _headers(
        "supervisor@sentinel.mil",
        "sentinel-super-2024",
    )

    for prefix in ("/api", "/api/v1"):
        dashboard_response = client.get(
            f"{prefix}/admin/dashboard",
            headers=supervisor_headers,
        )
        assert dashboard_response.status_code == 200
        dashboard = dashboard_response.json()
        assert set(dashboard) == {"cards", "riskDistribution"}
        assert set(dashboard["cards"]) == {
            "totalPersonnel",
            "activeUsers",
            "assessmentsCompleted",
            "elevatedIndicators",
            "highIndicators",
            "criticalAlerts",
        }
        assert [item["level"] for item in dashboard["riskDistribution"]] == [
            "NORMAL",
            "LOW",
            "MODERATE",
            "ELEVATED",
            "HIGH",
            "CRITICAL",
        ]

    response = client.get(
        "/api/admin/personnel?page=1&pageSize=5",
        headers=supervisor_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"rows", "total", "page", "pageSize", "pages", "units"}
    assert data["rows"]
    assert set(data["rows"][0]) == {
        "id",
        "name",
        "serviceNumber",
        "unit",
        "role",
        "status",
        "wellbeingLevel",
        "lastCheckIn",
        "lastActivity",
    }
    assert data["rows"][0]["role"] == "USER"


def test_personnel_detail_hides_and_audits_clinical_sections():
    supervisor_headers = _headers(
        "supervisor@sentinel.mil",
        "sentinel-super-2024",
    )
    mhp_headers = _headers("mhp@sentinel.mil", "sentinel-mhp-2024")

    personnel_response = client.get(
        "/api/admin/personnel?pageSize=1",
        headers=supervisor_headers,
    )
    personnel_id = personnel_response.json()["rows"][0]["id"]

    hidden_response = client.get(
        f"/api/admin/personnel/{personnel_id}",
        headers=supervisor_headers,
    )
    assert hidden_response.status_code == 200
    hidden = hidden_response.json()
    assert set(hidden) == {
        "profile",
        "latestRisk",
        "riskTrend",
        "alerts",
        "supportRequests",
        "assessments",
        "journals",
        "conversations",
        "voiceEntries",
        "visible",
    }
    assert hidden["profile"]["id"] == personnel_id
    assert hidden["profile"]["role"] == "USER"
    assert hidden["visible"] == {
        "risk": True,
        "journals": False,
        "assessments": False,
        "conversations": False,
    }
    assert hidden["assessments"] == []
    assert hidden["journals"] == []
    assert hidden["conversations"] == []
    assert hidden["voiceEntries"] == []
    assert hidden["latestRisk"]["score"] is None

    visible_response = client.get(
        f"/api/admin/personnel/{personnel_id}",
        headers=mhp_headers,
    )
    assert visible_response.status_code == 200
    visible = visible_response.json()
    assert all(visible["visible"].values())
    assert visible["latestRisk"]["score"] is not None

    with SessionLocal() as db:
        audit_count = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == "ADMIN_PERSONNEL_DETAIL_VIEW",
                AuditLog.resource_id == personnel_id,
            )
            .count()
        )
    assert audit_count >= 2


def test_admin_alert_mapping_update_and_analytics_shapes():
    supervisor_headers = _headers(
        "supervisor@sentinel.mil",
        "sentinel-super-2024",
    )
    admin_headers = _headers("admin@sentinel.mil", "sentinel-admin-2024")

    alert_response = client.get(
        "/api/admin/alerts?pageSize=1",
        headers=supervisor_headers,
    )
    assert alert_response.status_code == 200
    alert_page = alert_response.json()
    assert set(alert_page) == {"alerts", "total", "page", "pageSize", "pages"}
    assert alert_page["alerts"]
    alert_id = alert_page["alerts"][0]["id"]

    update_response = client.put(
        f"/api/admin/alerts/{alert_id}",
        json={"status": "IN_REVIEW"},
        headers=supervisor_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "IN_REVIEW"

    filtered_response = client.get(
        "/api/admin/alerts?status=IN_REVIEW&pageSize=100",
        headers=supervisor_headers,
    )
    assert filtered_response.status_code == 200
    assert all(
        item["status"] == "IN_REVIEW"
        for item in filtered_response.json()["alerts"]
    )

    analytics_response = client.get(
        "/api/admin/analytics",
        headers=admin_headers,
    )
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert set(analytics) == {"riskDistribution", "units", "activity"}
    assert len(analytics["activity"]) == 14
    assert {
        "date",
        "journals",
        "assessments",
        "voice",
        "chats",
    } == set(analytics["activity"][0])

    audit_response = client.get(
        "/api/admin/audit-logs?pageSize=10",
        headers=admin_headers,
    )
    assert audit_response.status_code == 200
    audit_page = audit_response.json()
    assert set(audit_page) == {"logs", "total", "page", "pageSize", "pages"}
    assert audit_page["logs"]
    assert set(audit_page["logs"][0]) == {
        "id",
        "actorId",
        "actorName",
        "action",
        "targetType",
        "targetId",
        "metadata",
        "createdAt",
    }


def test_admin_can_provision_a_mobile_personnel_account():
    admin_headers = _headers("admin@sentinel.mil", "sentinel-admin-2024")
    supervisor_headers = _headers("supervisor@sentinel.mil", "sentinel-super-2024")
    suffix = uuid.uuid4().hex[:10]
    payload = {
        "email": f"personnel-{suffix}@example.invalid",
        "fullName": "Sgt. Render Deployment",
        "serviceNumber": f"crpf-{suffix}",
        "rank": "Sergeant",
        "unit": "Deployment Readiness Unit",
        "initialPassword": "Secure-Mobile-2026!",
    }

    forbidden = client.post(
        "/api/admin/personnel",
        json=payload,
        headers=supervisor_headers,
    )
    assert forbidden.status_code == 403

    weak_payload = {**payload, "initialPassword": "not-secure"}
    assert client.post(
        "/api/admin/personnel",
        json=weak_payload,
        headers=admin_headers,
    ).status_code == 422

    created = client.post(
        "/api/admin/personnel",
        json=payload,
        headers=admin_headers,
    )
    assert created.status_code == 201
    assert created.json()["serviceNumber"] == payload["serviceNumber"].upper()

    login = client.post(
        "/api/auth/login",
        json={"username": payload["email"], "password": payload["initialPassword"]},
    )
    assert login.status_code == 200
    profile = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert profile.status_code == 200
    assert profile.json()["role"] == "PERSONNEL"

    duplicate = client.post(
        "/api/admin/personnel",
        json=payload,
        headers=admin_headers,
    )
    assert duplicate.status_code == 409

    with SessionLocal() as db:
        audit = (
            db.query(AuditLog)
            .filter(AuditLog.action == "ADMIN_PERSONNEL_CREATED")
            .order_by(AuditLog.timestamp.desc())
            .first()
        )
        assert audit is not None
        assert payload["initialPassword"] not in (audit.details or "")


def test_role_enforcement_and_synthetic_monitoring_contract():
    personnel_headers = _headers(
        "personnel1@sentinel.mil",
        "sentinel-pers-2024",
    )
    supervisor_headers = _headers(
        "supervisor@sentinel.mil",
        "sentinel-super-2024",
    )

    assert client.get(
        "/api/admin/dashboard",
        headers=personnel_headers,
    ).status_code == 403
    assert client.get(
        "/api/admin/monitoring/demo",
        headers=personnel_headers,
    ).status_code == 403
    assert client.get(
        "/api/admin/analytics",
        headers=supervisor_headers,
    ).status_code == 403

    response = client.get(
        "/api/admin/monitoring/demo",
        headers=supervisor_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "demo",
        "generatedAt",
        "cameras",
        "sleep",
        "voice",
        "typing",
        "habits",
    }
    assert data["demo"] is True
    assert all(item["status"] == "DEMO_ONLY" for item in data["cameras"])
    assert all(
        item["privacy"] == "SYNTHETIC_DATA_NO_CAPTURE"
        for item in data["cameras"]
    )
    assert all("Synthetic" in item["note"] for item in data["voice"])
    assert all(isinstance(item["pitchVariance"], (int, float)) for item in data["voice"])


def test_mobile_journal_retry_is_idempotent():
    headers = _headers("personnel1@sentinel.mil", "sentinel-pers-2024")
    client_request_id = str(uuid.uuid4())
    payload = {
        "content": "Idempotency test journal entry",
        "mood": "okay",
        "status": "SUBMITTED",
        "client_request_id": client_request_id,
    }

    with SessionLocal() as db:
        before = db.query(Journal).count()

    first = client.post("/api/journals", json=payload, headers=headers)
    second = client.post("/api/journals", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["journal"]["id"] == second.json()["journal"]["id"]

    with SessionLocal() as db:
        assert db.query(Journal).count() == before + 1
