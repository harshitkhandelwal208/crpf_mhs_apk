"""
Pydantic schemas for all API request/response DTOs.
These define the canonical API contract shared by Android and Web clients.
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole
from app.models.personnel import PersonnelStatus, RiskLevel
from app.models.alert import AlertSeverity, AlertStatus, AlertType
from app.models.assessment import AssessmentType


# ──────────────────────────── Auth ────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., description="User email address")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ──────────────────────────── User ────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    permissions: list["PermissionResponse"] = []
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.PERSONNEL


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    role: UserRole | None = None


# ──────────────────────────── Permission ────────────────────────────

class PermissionResponse(BaseModel):
    id: str
    resource: str
    action: str
    granted: bool
    granted_at: datetime

    class Config:
        from_attributes = True


class PermissionGrantRequest(BaseModel):
    resource: str = Field(
        ...,
        description="e.g. clinical:journals, clinical:assessments, clinical:ai_conversations, clinical:transcripts"
    )
    action: str = Field(..., description="e.g. read, write")


# ──────────────────────────── Personnel ────────────────────────────

class PersonnelResponse(BaseModel):
    id: str
    service_number: str
    first_name: str
    last_name: str
    rank: str
    unit: str
    status: PersonnelStatus
    risk_level: RiskLevel
    last_check_in: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class PersonnelDetailResponse(PersonnelResponse):
    """Extended detail - risk_score only visible to authorized roles."""
    risk_score: float | None = None
    risk_factors: str | None = None
    phone: str | None = None
    notes: str | None = None
    alert_count: int = 0


class PersonnelUpdateRequest(BaseModel):
    rank: str | None = None
    unit: str | None = None
    status: PersonnelStatus | None = None
    phone: str | None = None
    notes: str | None = None


class PersonnelListResponse(BaseModel):
    items: list[PersonnelResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ──────────────────────────── Alert ────────────────────────────

class AlertResponse(BaseModel):
    id: str
    personnel_id: str
    personnel_name: str | None = None
    type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str | None = None
    assigned_to: str | None = None
    assignee_name: str | None = None
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    resolution_notes: str | None = None
    resolved_at: datetime | None = None
    escalation_required: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class AlertCreateRequest(BaseModel):
    personnel_id: str
    type: AlertType
    severity: AlertSeverity
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    escalation_required: bool = False


class AlertAcknowledgeRequest(BaseModel):
    pass  # Acknowledging user comes from auth context


class AlertAssignRequest(BaseModel):
    assigned_to: str = Field(..., description="User ID to assign to")


class AlertStatusChangeRequest(BaseModel):
    status: AlertStatus


class AlertResolveRequest(BaseModel):
    resolution_notes: str = Field(..., min_length=1)


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ──────────────────────────── Risk Dashboard ────────────────────────────

class RiskDistribution(BaseModel):
    low: int
    moderate: int
    high: int
    critical: int


class RiskDashboardResponse(BaseModel):
    total_personnel: int
    distribution: RiskDistribution
    high_risk_personnel: list[PersonnelResponse]
    recent_risk_changes: list[AlertResponse]
    units_summary: list[dict]


class PersonnelRiskResponse(BaseModel):
    """Risk details for a single personnel member.
    raw risk_score is only included for authorized viewers."""
    personnel_id: str
    risk_level: RiskLevel
    risk_score: float | None = None  # None for unauthorized
    risk_factors: list[str] = []
    recent_alerts: list[AlertResponse] = []
    trend: str = "STABLE"  # IMPROVING, STABLE, DECLINING


# ──────────────────────────── Analytics ────────────────────────────

class AnalyticsOverview(BaseModel):
    total_personnel: int
    active_personnel: int
    total_alerts: int
    open_alerts: int
    resolved_alerts: int
    avg_resolution_hours: float
    risk_distribution: RiskDistribution


class AnalyticsTrend(BaseModel):
    date: str
    alert_count: int
    risk_score_avg: float


class AnalyticsTrendsResponse(BaseModel):
    trends: list[AnalyticsTrend]
    period: str


# ──────────────────────────── Audit Log ────────────────────────────

class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None = None
    user_email: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    ip_address: str | None = None
    details: str | None = None
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ──────────────────────────── Clinical (Permission-Gated) ────────────────────────────

class JournalResponse(BaseModel):
    id: str
    personnel_id: str
    title: str
    content: str
    sentiment_score: float | None = None
    sentiment_label: str | None = None
    is_flagged: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class JournalListResponse(BaseModel):
    items: list[JournalResponse]
    total: int


class AssessmentResponse(BaseModel):
    id: str
    personnel_id: str
    type: AssessmentType
    score: float
    max_score: float
    risk_indicators: str | None = None
    notes: str | None = None
    assessed_by: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AssessmentListResponse(BaseModel):
    items: list[AssessmentResponse]
    total: int


# ──────────────────────────── Settings ────────────────────────────

class EnvironmentInfo(BaseModel):
    app_name: str
    app_version: str
    environment: str
    database_type: str
    total_users: int
    total_personnel: int
    total_alerts: int


# ──────────────────────────── Generic ────────────────────────────

class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str | dict
