"""
Deterministic Risk Engine & Operational Alerting
Combines signals from AI chat, daily journals, voice entries, assessments, and support requests.
Updates personnel operational risk and generates alerts for authorized welfare personnel.
"""

from datetime import datetime, timezone
import json
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.personnel import Personnel, RiskLevel
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.models.audit_log import AuditLog


def score_to_level(score: float) -> str:
    if score >= 80:
        return "CRITICAL"
    elif score >= 60:
        return "HIGH"
    elif score >= 35:
        return "MODERATE"
    return "LOW"


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
    and creates alerts for welfare officers when necessary.
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

    db.flush()
    return alert_created

