"""
Integration and Unit Tests for:
- HRMS Operational Fatigue Engine
- Voluntary Biometrics Telemetry
- Non-Punitive Welfare Interventions & Explainable AI (XAI)
- Local HK Neural Tensor (.hk) RAG Search
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

import main
from app.database import get_db, SessionLocal
from app.models.user import User, UserRole
from app.models.personnel import Personnel, PersonnelStatus, RiskLevel
from app.models.hrms import DutySchedule, LeaveRecord, DeploymentHistory, TransferRecord
from app.models.biometrics import BiometricReading
from app.models.intervention import WelfareIntervention
from app.ai.knowledge_base import get_knowledge_base
from app.services.hrms_engine import evaluate_hrms_stress
from app.services.risk_engine import compute_holistic_personnel_risk
from app.services.intervention_engine import generate_interventions_for_personnel
from app.auth.security import create_access_token


def test_hk_local_ai_rag_search():
    """Verify local HK Neural Tensor (.hk) format loads and searches with high relevance."""
    kb = get_knowledge_base()
    assert kb is not None
    assert len(kb.documents) > 0

    # Search for sleep/fatigue protocol
    result = kb.search("insomnia and sleep disruption")
    assert result is not None
    assert "Sleep" in result["title"] or "Fatigue" in result["title"]
    assert result["score"] >= 0.35


def test_hrms_stress_and_burnout_evaluation():
    """Verify HRMS operational stress evaluation computes fatigue, leave deprivation, and hardship."""
    db = SessionLocal()
    try:
        # Create test personnel
        test_svc = f"TEST-HRMS-{uuid.uuid4().hex[:6].upper()}"
        personnel = Personnel(
            service_number=test_svc,
            first_name="Operational",
            last_name="Test",
            rank="Constable",
            unit="201 CoBRA",
            status=PersonnelStatus.DEPLOYED,
            risk_level=RiskLevel.LOW,
            risk_score=20.0,
        )
        db.add(personnel)
        db.commit()
        db.refresh(personnel)

        # 1. Add continuous duty shifts
        now = datetime.now(timezone.utc)
        for i in range(15):
            duty = DutySchedule(
                personnel_id=personnel.id,
                date=now - timedelta(days=i),
                shift_type="NIGHT",
                hours_worked=14.0,
                consecutive_days_on_duty=i + 1,
                is_overtime=True,
            )
            db.add(duty)

        # 2. Add rejected leaves
        for j in range(2):
            leave = LeaveRecord(
                personnel_id=personnel.id,
                applied_date=now - timedelta(days=30 * (j + 1)),
                status="REJECTED",
                rejection_reason="Operational exigency",
            )
            db.add(leave)

        # 3. Add hard posting deployment
        dep = DeploymentHistory(
            personnel_id=personnel.id,
            deployment_name="Operation Green Hunt",
            terrain_type="LWE_CONFLICT",
            hard_posting=True,
            start_date=now - timedelta(days=365),
            duration_months=12.0,
            family_separation_months=12.0,
        )
        db.add(dep)
        db.commit()

        # Evaluate
        eval_res = evaluate_hrms_stress(db, personnel.id)
        assert eval_res["operational_stress_score"] > 40.0
        assert eval_res["burnout_level"] in ("HIGH", "CRITICAL")
        assert "duty_fatigue" in eval_res["contributing_factors"]
        assert len(eval_res["insights"]) > 0
        assert len(eval_res["recommendations"]) > 0

        # Evaluate holistic XAI
        holistic = compute_holistic_personnel_risk(db, personnel.id)
        assert "composite_risk_score" in holistic
        assert "xai_factor_breakdown" in holistic
        assert holistic["xai_factor_breakdown"]["operational_burnout"] > 0

        # Generate non-punitive interventions
        interventions = generate_interventions_for_personnel(
            db=db,
            personnel_id=personnel.id,
            xai_factors=eval_res["contributing_factors"],
            reason="Continuous duty with high circadian disruption",
        )
        assert len(interventions) > 0
        categories = [i.category for i in interventions]
        assert "REST_ROTATION" in categories or "LEAVE_EXPEDITE" in categories

        # Clean up
        db.query(WelfareIntervention).filter(WelfareIntervention.personnel_id == personnel.id).delete()
        db.query(DutySchedule).filter(DutySchedule.personnel_id == personnel.id).delete()
        db.query(LeaveRecord).filter(LeaveRecord.personnel_id == personnel.id).delete()
        db.query(DeploymentHistory).filter(DeploymentHistory.personnel_id == personnel.id).delete()
        db.delete(personnel)
        db.commit()
    finally:
        db.close()


def test_api_endpoints_hrms_and_interventions():
    """Verify REST API endpoints for HRMS profile and Interventions."""
    client = TestClient(main.app)

    db = SessionLocal()
    try:
        # Create test user & personnel
        admin_user = db.query(User).filter(User.role == UserRole.ADMIN).first()
        token = create_access_token(admin_user)
        headers = {"Authorization": f"Bearer {token}"}

        test_svc = f"TEST-API-{uuid.uuid4().hex[:6].upper()}"
        personnel = Personnel(
            service_number=test_svc,
            first_name="API",
            last_name="Tester",
            rank="Inspector",
            unit="Rapid Action Force",
            status=PersonnelStatus.ACTIVE,
        )
        db.add(personnel)
        db.commit()
        db.refresh(personnel)

        # 1. GET HRMS profile
        res = client.get(f"/api/personnel/{personnel.id}/hrms-profile", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["personnel_id"] == personnel.id
        assert "operational_stress_score" in data

        # 2. GET Holistic risk
        res = client.get(f"/api/personnel/{personnel.id}/holistic-risk", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "composite_risk_score" in data
        assert "xai_factor_breakdown" in data

        # 3. Log Duty Schedule
        res = client.post(
            f"/api/personnel/{personnel.id}/duty-schedule",
            headers=headers,
            json={
                "shift_type": "NIGHT",
                "hours_worked": 12.0,
                "consecutive_days_on_duty": 5,
                "is_overtime": True,
            },
        )
        assert res.status_code == 200

        # Clean up
        db.query(DutySchedule).filter(DutySchedule.personnel_id == personnel.id).delete()
        db.delete(personnel)
        db.commit()
    finally:
        db.close()
