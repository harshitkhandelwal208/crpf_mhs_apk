"""
HRMS Operational Fatigue & Burnout Evaluation Engine
Analyzes duty schedules, leave patterns, continuous deployments, hard postings, and transfer frequency.
Computes an objective, explainable Operational Burnout Index (0.0 - 100.0) aligned with armed forces realities.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.models.hrms import DutySchedule, LeaveRecord, DeploymentHistory, TransferRecord


def evaluate_hrms_stress(db: Session, personnel_id: str) -> Dict[str, Any]:
    """
    Evaluates operational parameters for a given personnel.
    Returns:
        {
            "operational_stress_score": float,  # 0.0 - 100.0
            "burnout_level": str,              # LOW, MODERATE, HIGH, CRITICAL
            "contributing_factors": Dict[str, float],
            "insights": List[str],
            "recommendations": List[str]
        }
    """
    now = datetime.now(timezone.utc)
    insights: List[str] = []
    recommendations: List[str] = []
    factors: Dict[str, float] = {}

    # 1. Shift & Duty Hours (Last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    duty_records = db.scalars(
        select(DutySchedule)
        .where(DutySchedule.personnel_id == personnel_id, DutySchedule.date >= thirty_days_ago)
        .order_by(desc(DutySchedule.date))
    ).all()

    avg_hours = 8.0
    max_consecutive_days = 0
    night_shifts_count = 0
    overtime_shifts = 0

    if duty_records:
        total_hours = sum(d.hours_worked for d in duty_records)
        avg_hours = total_hours / len(duty_records)
        max_consecutive_days = max((d.consecutive_days_on_duty for d in duty_records), default=0)
        night_shifts_count = sum(1 for d in duty_records if d.shift_type in ("NIGHT", "ROTATING", "24_HR"))
        overtime_shifts = sum(1 for d in duty_records if d.is_overtime or d.hours_worked > 12.0)

    # Calculate Duty Fatigue Score (0 - 30)
    duty_fatigue_score = 0.0
    if avg_hours > 10.0:
        duty_fatigue_score += min(15.0, (avg_hours - 8.0) * 3.0)
    if max_consecutive_days >= 14:
        duty_fatigue_score += 10.0
        insights.append(f"Extended continuous duty without rest day: {max_consecutive_days} consecutive days.")
        recommendations.append("Mandatory 48-hour operational stand-down and rest cycle.")
    elif max_consecutive_days >= 7:
        duty_fatigue_score += 5.0

    if night_shifts_count >= 10:
        duty_fatigue_score += 5.0
        insights.append(f"High circadian disruption: {night_shifts_count} night/rotating shifts in past 30 days.")
    factors["duty_fatigue"] = round(duty_fatigue_score, 1)

    # 2. Leave Deprivation & Rejections
    leave_records = db.scalars(
        select(LeaveRecord)
        .where(LeaveRecord.personnel_id == personnel_id)
        .order_by(desc(LeaveRecord.applied_date))
    ).all()

    leave_score = 0.0
    latest_leave = next((l for l in leave_records if l.status == "APPROVED"), None)
    days_since_leave = 120  # baseline default
    if latest_leave and latest_leave.end_date:
        # Normalize timezone
        end = latest_leave.end_date if latest_leave.end_date.tzinfo else latest_leave.end_date.replace(tzinfo=timezone.utc)
        days_since_leave = max(0, (now - end).days)
    elif latest_leave and latest_leave.applied_date:
        applied = latest_leave.applied_date if latest_leave.applied_date.tzinfo else latest_leave.applied_date.replace(tzinfo=timezone.utc)
        days_since_leave = max(0, (now - applied).days)

    if days_since_leave > 180:
        leave_score += 18.0
        insights.append(f"Severe leave deprivation: {days_since_leave} days since last sanctioned leave.")
        recommendations.append("Expedite 14-day annual/casual home leave.")
    elif days_since_leave > 90:
        leave_score += 8.0

    rejected_leaves = sum(1 for l in leave_records if l.status == "REJECTED")
    if rejected_leaves >= 2:
        leave_score += 7.0
        insights.append(f"{rejected_leaves} leave applications rejected recently (perceived deprivation).")
        recommendations.append("Conduct supervisory review of rejected leave grounds.")
    factors["leave_deprivation"] = round(leave_score, 1)

    # 3. Hard Postings & Deployment Hardship
    deployments = db.scalars(
        select(DeploymentHistory)
        .where(DeploymentHistory.personnel_id == personnel_id)
        .order_by(desc(DeploymentHistory.start_date))
    ).all()

    deployment_score = 0.0
    active_hard_posting = any(d.hard_posting and (d.end_date is None or d.end_date > now) for d in deployments)
    if active_hard_posting:
        deployment_score += 15.0
        insights.append("Currently deployed in active operational hard posting (LWE / High Altitude / CI ops).")
    
    total_months_hard = sum(d.duration_months or 0.0 for d in deployments if d.hard_posting)
    if total_months_hard > 24:
        deployment_score += 10.0
        insights.append(f"Cumulative high-hazard service exceeds {int(total_months_hard)} months.")
        recommendations.append("Consider peaceful unit rotation upon completion of present tenure.")
    factors["deployment_hardship"] = round(deployment_score, 1)

    # 4. Frequent Transfers & Domestic Instability
    transfers = db.scalars(
        select(TransferRecord)
        .where(TransferRecord.personnel_id == personnel_id)
        .order_by(desc(TransferRecord.transfer_date))
    ).all()

    transfer_score = 0.0
    transfer_count = len(transfers)
    if transfer_count >= 3:
        transfer_score += 15.0
        insights.append(f"High familial disruption: {transfer_count} unit relocations within 3 years.")
        recommendations.append("Anchor posting stabilization request.")
    elif transfer_count >= 2:
        transfer_score += 7.0
    factors["transfer_instability"] = round(transfer_score, 1)

    # Total Operational Burnout Score (0 - 100)
    total_score = min(100.0, duty_fatigue_score + leave_score + deployment_score + transfer_score)

    if total_score >= 70.0:
        burnout_level = "CRITICAL"
    elif total_score >= 50.0:
        burnout_level = "HIGH"
    elif total_score >= 30.0:
        burnout_level = "MODERATE"
    else:
        burnout_level = "LOW"

    return {
        "operational_stress_score": round(total_score, 1),
        "burnout_level": burnout_level,
        "contributing_factors": factors,
        "metrics": {
            "avg_hours_per_day": round(avg_hours, 1),
            "max_consecutive_days": max_consecutive_days,
            "days_since_leave": days_since_leave,
            "hard_posting_active": active_hard_posting,
            "recent_transfers": transfer_count,
        },
        "insights": insights,
        "recommendations": recommendations,
    }
