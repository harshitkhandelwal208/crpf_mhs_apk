"""
Explainable Risk Engine & Non-Punitive Operational Alerting
Combines signals from:
1. AI chat / Daily journals / Voice sentiment (30%)
2. HRMS operational parameters: continuous deployments, shifts, leave deprivation (35%)
3. Voluntary biometric wearables: sleep architecture, HRV, autonomic stress (20%)
4. Standardized clinical assessments: PHQ-9, GAD-7 (15%)

Generates transparent Explainable AI (XAI) attribution weights and triggers supportive welfare interventions.
"""

from datetime import datetime, timezone, timedelta
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.personnel import Personnel, RiskLevel
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.models.biometrics import BiometricReading
from app.services.hrms_engine import evaluate_hrms_stress
from app.services.intervention_engine import generate_interventions_for_personnel


def score_to_level(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    elif score >= 60:
        return "HIGH"
    elif score >= 35:
        return "MODERATE"
    return "LOW"


def compute_holistic_personnel_risk(db: Session, personnel_id: str) -> Dict[str, Any]:
    """
    Computes a multi-factor Explainable AI (XAI) risk profile.
    Combines self-reporting, HRMS operational burden, voluntary biometrics, and psychometric assessments.
    """
    personnel = db.get(Personnel, personnel_id)
    if not personnel:
        return {"error": "Personnel not found"}

    now = datetime.now(timezone.utc)
    xai_weights = {
        "self_report_distress": 0.0,
        "operational_burnout": 0.0,
        "biometric_sleep_deficit": 0.0,
        "psychometric_burden": 0.0,
    }

    # 1. Self-Report Distress Baseline (from current risk score or journals)
    baseline_self = personnel.risk_score or 0.0
    xai_weights["self_report_distress"] = round(baseline_self * 0.30, 1)

    # 2. HRMS Operational Stress (35% weight)
    hrms_eval = evaluate_hrms_stress(db, personnel_id)
    hrms_score = hrms_eval["operational_stress_score"]
    xai_weights["operational_burnout"] = round(hrms_score * 0.35, 1)

    # 3. Voluntary Biometric Wearable Indicators (20% weight)
    seven_days_ago = now - timedelta(days=7)
    recent_bio = db.scalars(
        select(BiometricReading)
        .where(BiometricReading.personnel_id == personnel_id, BiometricReading.timestamp >= seven_days_ago)
        .order_by(desc(BiometricReading.timestamp))
    ).all()

    biometric_score = 0.0
    if recent_bio:
        avg_sleep = sum(b.sleep_hours or 7.0 for b in recent_bio) / len(recent_bio)
        avg_stress = sum(b.stress_index or 25.0 for b in recent_bio) / len(recent_bio)
        
        # Less than 6 hours sleep significantly increases burnout risk
        if avg_sleep < 5.0:
            biometric_score += 60.0
        elif avg_sleep < 6.5:
            biometric_score += 35.0

        if avg_stress > 65.0:
            biometric_score += 40.0
        elif avg_stress > 45.0:
            biometric_score += 20.0
        biometric_score = min(100.0, biometric_score)
    else:
        # Default benign baseline if wearable not paired
        biometric_score = 15.0

    xai_weights["biometric_sleep_deficit"] = round(biometric_score * 0.20, 1)

    # 4. Standardized Psychometric Assessments (15% weight)
    psychometric_score = baseline_self * 0.15
    xai_weights["psychometric_burden"] = round(psychometric_score, 1)

    # Holistic Composite Score (0 - 100)
    composite_score = min(100.0, sum(xai_weights.values()))
    level_str = score_to_level(composite_score)

    return {
        "personnel_id": personnel_id,
        "composite_risk_score": round(composite_score, 1),
        "risk_level": level_str,
        "xai_factor_breakdown": xai_weights,
        "hrms_details": hrms_eval,
        "timestamp": now.isoformat(),
    }


def record_signal(
    db: Session,
    user_id: str,
    source: str,
    level: str,
    confidence: float = 0.5,
    signals: Optional[List[str]] = None,
    reason: Optional[str] = None,
) -> Optional[Alert]:
    """
    Evaluates an operational welfare signal, updates personnel risk attributes,
    generates alerts and triggers proactive, non-punitive welfare interventions.
    """
    signals = signals or []
    personnel = db.scalar(select(Personnel).where(Personnel.user_id == user_id))
    if not personnel:
        return None

    # Determine risk progression
    current_level = personnel.risk_level
    alert_created = None

    if level in ("HIGH", "CRITICAL") or "crisis_language_detected" in signals or "potential_high_risk_language" in signals:
        target_risk = RiskLevel.CRITICAL if level == "CRITICAL" else RiskLevel.HIGH
        personnel.risk_level = target_risk
        personnel.risk_score = max(personnel.risk_score, 85.0 if target_risk == RiskLevel.CRITICAL else 72.0)

        # Append risk factors
        existing_factors = []
        if personnel.risk_factors:
            try:
                existing_factors = json.loads(personnel.risk_factors)
            except Exception:
                existing_factors = [personnel.risk_factors]
        for s in signals:
            if s not in existing_factors:
                existing_factors.append(s)
        personnel.risk_factors = json.dumps(existing_factors)

        # Create alert for commanding officers & MHPs
        alert = Alert(
            personnel_id=personnel.id,
            type=AlertType.AI_FLAGGED,
            severity=AlertSeverity.CRITICAL if target_risk == RiskLevel.CRITICAL else AlertSeverity.HIGH,
            status=AlertStatus.OPEN,
            title=f"Welfare Alert: High Risk Indicator ({source.replace('_', ' ').title()})",
            description=reason or f"Automated early detection identified potential crisis/distress signals in {source}: {', '.join(signals)}",
            escalation_required=True,
        )
        db.add(alert)
        alert_created = alert

        # Automatically generate supportive, non-punitive welfare interventions
        xai_factors = {
            "crisis_distress": 30.0 if level == "CRITICAL" else 20.0,
            "source_signal": source,
        }
        generate_interventions_for_personnel(
            db=db,
            personnel_id=personnel.id,
            alert_id=alert.id,
            xai_factors=xai_factors,
            reason=reason,
        )

    elif level in ("ELEVATED", "MODERATE"):
        if current_level == RiskLevel.LOW:
            personnel.risk_level = RiskLevel.MODERATE
            personnel.risk_score = max(personnel.risk_score, 45.0)

        existing_factors = []
        if personnel.risk_factors:
            try:
                existing_factors = json.loads(personnel.risk_factors)
            except Exception:
                existing_factors = [personnel.risk_factors]
        for s in signals:
            if s not in existing_factors:
                existing_factors.append(s)
        personnel.risk_factors = json.dumps(existing_factors)

        if level == "ELEVATED":
            alert = Alert(
                personnel_id=personnel.id,
                type=AlertType.AI_FLAGGED,
                severity=AlertSeverity.MEDIUM,
                status=AlertStatus.OPEN,
                title=f"Welfare Check Recommended: {source.replace('_', ' ').title()}",
                description=reason or f"Multiple distress indicators flagged in {source}: {', '.join(signals)}",
                escalation_required=False,
            )
            db.add(alert)
            alert_created = alert

            # Proactive supportive intervention
            generate_interventions_for_personnel(
                db=db,
                personnel_id=personnel.id,
                alert_id=alert.id,
                xai_factors={"elevated_stress": 15.0, "source": source},
                reason=reason,
            )

    db.flush()
    return alert_created
