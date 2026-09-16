"""
Seed script - creates development test data.
Gated behind ENV=development. Not accessible in production.
"""
import sys
import os
from datetime import datetime, timedelta, timezone
import random

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.user import User, UserRole
from app.models.personnel import Personnel, PersonnelStatus, RiskLevel
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.journal import Journal
from app.models.assessment import Assessment, AssessmentType
from app.models.permission import Permission
from app.auth.security import hash_password


def seed():
    if settings.ENV != "development":
        print("ERROR: Seed script can only run in development environment.")
        print("Set SENTINEL_ENV=development to enable seeding.")
        sys.exit(1)

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(User).first()
        if existing:
            print("Database already has data. Skipping seed.")
            return

        print("Seeding users...")

        # ── Users ────────────────────────────────────────────
        users = [
            User(
                email="superadmin@sentinel.mil",
                full_name="Col. Sarah Mitchell",
                hashed_password=hash_password("sentinel-super-2024"),
                role=UserRole.SUPER_ADMIN,
            ),
            User(
                email="admin@sentinel.mil",
                full_name="Maj. David Chen",
                hashed_password=hash_password("sentinel-admin-2024"),
                role=UserRole.ADMIN,
            ),
            User(
                email="mhp@sentinel.mil",
                full_name="Dr. Emily Rodriguez",
                hashed_password=hash_password("sentinel-mhp-2024"),
                role=UserRole.MENTAL_HEALTH_PROFESSIONAL,
            ),
            User(
                email="supervisor@sentinel.mil",
                full_name="Capt. James Walker",
                hashed_password=hash_password("sentinel-super-2024"),
                role=UserRole.SUPERVISOR,
            ),
            User(
                email="personnel1@sentinel.mil",
                full_name="Sgt. Mike Johnson",
                hashed_password=hash_password("sentinel-pers-2024"),
                role=UserRole.PERSONNEL,
            ),
        ]
        for u in users:
            db.add(u)
        db.flush()

        # Grant clinical permissions to MHP (not to ADMIN!)
        mhp_user = db.query(User).filter(User.email == "mhp@sentinel.mil").first()
        superadmin_user = db.query(User).filter(User.email == "superadmin@sentinel.mil").first()

        clinical_permissions = [
            Permission(user_id=mhp_user.id, resource="clinical:journals", action="read", granted=True, granted_by=superadmin_user.id),
            Permission(user_id=mhp_user.id, resource="clinical:assessments", action="read", granted=True, granted_by=superadmin_user.id),
            Permission(user_id=mhp_user.id, resource="clinical:ai_conversations", action="read", granted=True, granted_by=superadmin_user.id),
            Permission(user_id=mhp_user.id, resource="clinical:transcripts", action="read", granted=True, granted_by=superadmin_user.id),
            # SUPER_ADMIN also gets clinical access
            Permission(user_id=superadmin_user.id, resource="clinical:journals", action="read", granted=True, granted_by=superadmin_user.id),
            Permission(user_id=superadmin_user.id, resource="clinical:assessments", action="read", granted=True, granted_by=superadmin_user.id),
        ]
        for p in clinical_permissions:
            db.add(p)

        print("Seeding personnel...")

        # ── Personnel ────────────────────────────────────────
        ranks = ["Pvt.", "PFC", "Cpl.", "Sgt.", "SSgt.", "SFC", "MSG", "1SG", "SGM"]
        units = ["Alpha Company, 1st Battalion", "Bravo Company, 2nd Battalion",
                 "Charlie Company, 3rd Battalion", "Delta Company, 1st Battalion",
                 "Echo Company, Support Battalion", "HQ Company"]
        first_names = ["James", "John", "Robert", "Michael", "William", "David",
                       "Richard", "Joseph", "Thomas", "Charles", "Maria", "Jennifer",
                       "Patricia", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica",
                       "Sarah", "Karen", "Daniel", "Matthew", "Anthony", "Mark", "Donald"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
                      "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez",
                      "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore",
                      "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris"]

        personnel_list = []
        now = datetime.now(timezone.utc)

        for i in range(50):
            risk_level = random.choices(
                [RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.CRITICAL],
                weights=[50, 30, 15, 5],
            )[0]
            risk_score = {
                RiskLevel.LOW: random.uniform(0, 25),
                RiskLevel.MODERATE: random.uniform(25, 50),
                RiskLevel.HIGH: random.uniform(50, 75),
                RiskLevel.CRITICAL: random.uniform(75, 100),
            }[risk_level]

            status = random.choices(
                list(PersonnelStatus),
                weights=[60, 15, 15, 8, 2],
            )[0]

            risk_factors = []
            if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                possible_factors = ["sleep_disruption", "isolation", "missed_check_ins",
                                    "mood_decline", "substance_concern", "relationship_stress",
                                    "performance_decline"]
                risk_factors = random.sample(possible_factors, k=random.randint(1, 3))

            p = Personnel(
                service_number=f"SN-{10000 + i:05d}",
                first_name=random.choice(first_names),
                last_name=random.choice(last_names),
                rank=random.choice(ranks),
                unit=random.choice(units),
                status=status,
                risk_level=risk_level,
                risk_score=round(risk_score, 1),
                risk_factors=",".join(risk_factors) if risk_factors else None,
                last_check_in=now - timedelta(hours=random.randint(1, 72)),
                phone=f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            )
            db.add(p)
            personnel_list.append(p)

        db.flush()

        print("Seeding alerts...")

        # ── Alerts ────────────────────────────────────────
        alert_titles = {
            AlertType.BEHAVIORAL: ["Unusual behavior pattern detected", "Behavioral concern reported by peer",
                                   "Mood shift detected in recent interactions"],
            AlertType.CHECK_IN_MISSED: ["Missed scheduled check-in", "48hr check-in overdue",
                                        "Multiple consecutive check-ins missed"],
            AlertType.RISK_SCORE_CHANGE: ["Risk score increased significantly", "Risk level elevated to HIGH",
                                          "Rapid risk score change detected"],
            AlertType.ASSESSMENT_DUE: ["PHQ-9 assessment overdue", "Quarterly assessment due",
                                       "Follow-up assessment required"],
            AlertType.AI_FLAGGED: ["AI detected concerning language patterns", "Automated sentiment analysis flag",
                                   "AI risk model escalation"],
            AlertType.MANUAL: ["Supervisor concern noted", "Peer support request",
                              "Command-directed evaluation needed"],
            AlertType.SYSTEM: ["System health check failed", "Data sync issue detected",
                              "Automated monitoring alert"],
        }

        supervisor_user = db.query(User).filter(User.email == "supervisor@sentinel.mil").first()

        for i in range(80):
            alert_type = random.choice(list(AlertType))
            severity = random.choices(
                list(AlertSeverity),
                weights=[30, 35, 25, 10],
            )[0]
            status = random.choices(
                list(AlertStatus),
                weights=[25, 15, 15, 10, 25, 10],
            )[0]

            created_at = now - timedelta(hours=random.randint(1, 720))

            alert = Alert(
                personnel_id=random.choice(personnel_list).id,
                type=alert_type,
                severity=severity,
                status=status,
                title=random.choice(alert_titles[alert_type]),
                description=f"Auto-generated alert for development testing. Severity: {severity.value}.",
                assigned_to=supervisor_user.id if status in (AlertStatus.ASSIGNED, AlertStatus.IN_PROGRESS) else None,
                acknowledged_by=supervisor_user.id if status != AlertStatus.OPEN else None,
                acknowledged_at=created_at + timedelta(minutes=random.randint(5, 120)) if status != AlertStatus.OPEN else None,
                resolution_notes="Resolved during routine monitoring." if status == AlertStatus.RESOLVED else None,
                resolved_at=created_at + timedelta(hours=random.randint(1, 48)) if status == AlertStatus.RESOLVED else None,
                escalation_required=severity == AlertSeverity.CRITICAL,
                created_at=created_at,
            )
            db.add(alert)

        db.flush()

        print("Seeding clinical data...")

        # ── Journals (Clinical - Permission-Gated) ────────────────
        journal_titles = [
            "Daily reflection", "Weekly check-in notes", "Post-exercise debrief",
            "Personal goals update", "Stress management progress",
            "Sleep pattern observations", "Team dynamics reflection",
        ]
        sentiments = ["positive", "neutral", "negative", "mixed"]

        for person in random.sample(personnel_list, 20):
            for j in range(random.randint(1, 5)):
                journal = Journal(
                    personnel_id=person.id,
                    title=random.choice(journal_titles),
                    content="[Clinical content - this represents a journal entry that requires explicit permission to view.]",
                    sentiment_score=random.uniform(-1, 1),
                    sentiment_label=random.choice(sentiments),
                    is_flagged=random.random() < 0.15,
                    created_at=now - timedelta(days=random.randint(1, 90)),
                )
                db.add(journal)

        # ── Assessments (Clinical - Permission-Gated) ────────────
        for person in random.sample(personnel_list, 25):
            for a_type in random.sample(list(AssessmentType), k=random.randint(1, 3)):
                max_scores = {
                    AssessmentType.PHQ9: 27, AssessmentType.GAD7: 21,
                    AssessmentType.PCL5: 80, AssessmentType.AUDIT_C: 12,
                    AssessmentType.COLUMBIA: 6, AssessmentType.CUSTOM: 100,
                }
                max_score = max_scores[a_type]
                score = random.uniform(0, max_score)

                assessment = Assessment(
                    personnel_id=person.id,
                    type=a_type,
                    score=round(score, 1),
                    max_score=max_score,
                    risk_indicators="elevated" if score > max_score * 0.6 else None,
                    assessed_by=mhp_user.id,
                    created_at=now - timedelta(days=random.randint(1, 180)),
                )
                db.add(assessment)

        db.commit()
        print(f"Seed complete! Created:")
        print(f"  - {len(users)} users")
        print(f"  - {len(clinical_permissions)} clinical permissions")
        print(f"  - {len(personnel_list)} personnel")
        print(f"  - 80 alerts")
        print(f"  - Journals and assessments for selected personnel")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
