"""
Welfare Intervention Recommendation Engine
Non-punitive, supportive intervention workflows for Armed Forces personnel.
Translates multi-factor Explainable AI (XAI) distress drivers into compassionate, proactive welfare solutions.
"""
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.personnel import Personnel
from app.models.alert import Alert
from app.models.intervention import WelfareIntervention


INTERVENTION_CATALOG = {
    "REST_ROTATION": {
        "title": "Operational Rest Rotation (Stand-Down)",
        "priority": "PRIORITY",
        "action_plan": (
            "1. Grant 48-hour operational stand-down from high-intensity duties.\n"
            "2. Assign to low-stress administrative or perimeter daylight shifts.\n"
            "3. Enforce 8 hours uninterrupted sleep block in protected rest quarters."
        )
    },
    "PEER_BUDDY": {
        "title": "Buddy-Pairing Support Activation",
        "priority": "ROUTINE",
        "action_plan": (
            "1. Pair personnel with a senior, trusted peer buddy trained in psychological first aid.\n"
            "2. Schedule joint off-duty recreational activities (sports, mess recreation).\n"
            "3. Daily informal check-in by peer buddy without formal reporting stigma."
        )
    },
    "FAMILY_CONNECT": {
        "title": "Family Well-Being & Communication Facilitation",
        "priority": "PRIORITY",
        "action_plan": (
            "1. Provide priority access to satellite calling facility / secure welfare tele-booth.\n"
            "2. Unit welfare officer to verify family welfare or domestic emergency if reported.\n"
            "3. Facilitate expedited leave review if family distress is verified."
        )
    },
    "COUNSELING": {
        "title": "Confidential Tele-Counseling Session",
        "priority": "URGENT",
        "action_plan": (
            "1. Schedule confidential tele-session with CRPF Medical Officer / Composite Hospital Psychologist.\n"
            "2. Ensure zero recording on service record / non-stigmatizing medical consultation.\n"
            "3. Provide self-guided digital CBT modules via Sentinel mobile app."
        )
    },
    "LEAVE_EXPEDITE": {
        "title": "Expedited Home Leave Fast-Tracking",
        "priority": "PRIORITY",
        "action_plan": (
            "1. Fast-track pending or rejected casual/earned leave application to Unit Commandant.\n"
            "2. Arrange transit pass and railway warrant expeditiously.\n"
            "3. Maintain supportive contact during home visit."
        )
    },
    "DE_ESCALATION": {
        "title": "Supportive Operational Role Reassignment",
        "priority": "URGENT",
        "action_plan": (
            "1. Temporarily reassign from high-hazard kinetic ops or armed sentry duty to support battalion role.\n"
            "2. Reassignment strictly designated as welfare support, avoiding disciplinary framing.\n"
            "3. Continuous daily psychological evaluation until stabilization."
        )
    },
}


def generate_interventions_for_personnel(
    db: Session,
    personnel_id: str,
    alert_id: Optional[str] = None,
    xai_factors: Optional[Dict[str, float]] = None,
    reason: Optional[str] = None,
) -> List[WelfareIntervention]:
    """
    Evaluates personnel risk factors and generates non-punitive welfare intervention recommendations.
    """
    personnel = db.get(Personnel, personnel_id)
    if not personnel:
        return []

    xai_factors = xai_factors or {}
    created_interventions: List[WelfareIntervention] = []

    # Determine needed interventions based on factors
    recommended_categories: List[str] = []

    if xai_factors.get("leave_deprivation", 0.0) >= 12.0:
        recommended_categories.append("LEAVE_EXPEDITE")

    if xai_factors.get("duty_fatigue", 0.0) >= 15.0 or xai_factors.get("sleep_deficit", 0.0) >= 15.0:
        recommended_categories.append("REST_ROTATION")

    if xai_factors.get("deployment_hardship", 0.0) >= 12.0 or xai_factors.get("isolation", 0.0) >= 10.0:
        recommended_categories.append("PEER_BUDDY")

    if xai_factors.get("crisis_distress", 0.0) >= 20.0 or personnel.risk_score >= 75.0:
        recommended_categories.append("COUNSELING")
        recommended_categories.append("DE_ESCALATION")
    elif personnel.risk_score >= 45.0 and "COUNSELING" not in recommended_categories:
        recommended_categories.append("COUNSELING")

    # Default fallback to Peer Buddy and Rest Rotation if no specific factor triggered
    if not recommended_categories:
        recommended_categories = ["PEER_BUDDY", "REST_ROTATION"]

    for category in recommended_categories:
        # Check if identical active intervention already exists for this personnel
        existing = db.scalar(
            select(WelfareIntervention).where(
                WelfareIntervention.personnel_id == personnel_id,
                WelfareIntervention.category == category,
                WelfareIntervention.status.in_(["RECOMMENDED", "INITIATED", "IN_PROGRESS"]),
            )
        )
        if existing:
            continue

        meta = INTERVENTION_CATALOG.get(category, INTERVENTION_CATALOG["PEER_BUDDY"])
        intervention = WelfareIntervention(
            personnel_id=personnel_id,
            alert_id=alert_id,
            category=category,
            title=meta["title"],
            description=(
                f"Explainable AI recommendation generated due to detected risk factors: "
                f"{json.dumps(xai_factors) if xai_factors else (reason or 'Multi-signal distress evaluation')}"
            ),
            action_plan=meta["action_plan"],
            priority=meta["priority"],
            status="RECOMMENDED",
            recommended_by_xai=True,
            contributing_factors=json.dumps(xai_factors),
        )
        db.add(intervention)
        created_interventions.append(intervention)

    db.flush()
    return created_interventions
