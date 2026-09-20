"""
Pydantic schemas for all API request/response DTOs.
These define the canonical API contract shared by Android and Web clients.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.user import UserRole
from app.models.personnel import PersonnelStatus, RiskLevel
from app.models.alert import AlertSeverity, AlertStatus, AlertType
from app.models.assessment import AssessmentType


# ──────────────────────────── Auth ────────────────────────────

class LoginRequest(BaseModel):
    username: str | None = Field(None, description="User email or username")
    email: str | None = Field(None, description="User email address")
    password: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def require_identifier(self):
        if not self.email and not self.username:
            raise ValueError("Either email or username is required")
        return self

    @property
    def identifier(self) -> str:
        return self.email or self.username or ""


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    service_number: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    rank: str = Field(..., min_length=1, max_length=50)
    unit: str = Field(..., min_length=1, max_length=100)
    phone: str | None = None


# ──────────────────────────── User ────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    name: str | None = None
    role: UserRole
    is_active: bool
    onboarding_complete: bool = True
    mfa_enabled: bool = False
    permissions: list["PermissionResponse"] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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


# ──────────────────────────── AI Chat ────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = None


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime | str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessageResponse
    support_escalation: bool = False
    morale_score: int | None = None
    detected_mood: str | None = None
    risk_flag: bool = False
    safety_message: str | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────── Journals ────────────────────────────

class JournalCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    mood: str = "okay"
    status: str = "SUBMITTED"
    title: str | None = None
    client_request_id: str | None = Field(None, min_length=8, max_length=128)


class JournalItem(BaseModel):
    id: str
    mood: str
    content: str
    status: str
    created_at: str | datetime

    model_config = ConfigDict(from_attributes=True)


class JournalMobileResponse(BaseModel):
    journal: JournalItem


# ──────────────────────────── Voice ────────────────────────────

class VoiceTranscriptionResponse(BaseModel):
    id: str
    transcript: str
    requires_review: bool = True


# ──────────────────────────── Support ────────────────────────────

class SupportRequestInput(BaseModel):
    type: str = "routine"  # routine, counseling, urgent, welfare
    message: str = Field(..., min_length=1)


class SupportResponse(BaseModel):
    id: str
    status: str


class SupportRequestItem(BaseModel):
    id: str
    type: str
    message: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmergencyContactResponse(BaseModel):
    id: str
    label: str
    description: str
    contact: str

    model_config = ConfigDict(from_attributes=True)


class ResourceResponse(BaseModel):
    id: str
    title: str
    summary: str
    category: str
    body: str

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────── HRMS Operational Models ────────────────────────────

class DutyScheduleCreate(BaseModel):
    shift_type: str = "REGULAR"
    hours_worked: float = 8.0
    consecutive_days_on_duty: int = 1
    is_overtime: bool = False
    notes: str | None = None


class DutyScheduleResponse(BaseModel):
    id: str
    personnel_id: str
    date: datetime
    shift_type: str
    hours_worked: float
    consecutive_days_on_duty: int
    is_overtime: bool
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LeaveRecordCreate(BaseModel):
    leave_type: str = "CASUAL"
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str = "PENDING"
    rejection_reason: str | None = None
    days_since_last_leave: int | None = None


class LeaveRecordResponse(BaseModel):
    id: str
    personnel_id: str
    leave_type: str
    applied_date: datetime
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str
    rejection_reason: str | None = None
    days_since_last_leave: int | None = None

    model_config = ConfigDict(from_attributes=True)


class DeploymentCreate(BaseModel):
    deployment_name: str
    terrain_type: str = "STANDARD"
    hard_posting: bool = True
    start_date: datetime
    end_date: datetime | None = None
    duration_months: float | None = None
    family_separation_months: float | None = None


class DeploymentResponse(BaseModel):
    id: str
    personnel_id: str
    deployment_name: str
    terrain_type: str
    hard_posting: bool
    start_date: datetime
    end_date: datetime | None = None
    duration_months: float | None = None
    family_separation_months: float | None = None

    model_config = ConfigDict(from_attributes=True)


class HRMSProfileResponse(BaseModel):
    personnel_id: str
    operational_stress_score: float
    burnout_level: str
    contributing_factors: dict[str, float]
    metrics: dict[str, Any]
    insights: list[str]
    recommendations: list[str]


# ──────────────────────────── Biometrics / Wearable Telemetry ────────────────────────────

class BiometricIngestRequest(BaseModel):
    resting_heart_rate: float | None = None
    heart_rate_variability: float | None = None
    sleep_hours: float | None = None
    sleep_quality_score: float | None = None
    deep_sleep_minutes: int | None = None
    rem_sleep_minutes: int | None = None
    stress_index: float | None = None
    step_count: int | None = None
    device_source: str = "VOLUNTARY_WEARABLE"


class BiometricResponse(BaseModel):
    id: str
    personnel_id: str
    timestamp: datetime
    resting_heart_rate: float | None = None
    heart_rate_variability: float | None = None
    sleep_hours: float | None = None
    sleep_quality_score: float | None = None
    deep_sleep_minutes: int | None = None
    rem_sleep_minutes: int | None = None
    stress_index: float | None = None
    step_count: int | None = None
    device_source: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BiometricTrendsResponse(BaseModel):
    personnel_id: str
    readings: list[BiometricResponse]
    avg_sleep_hours: float
    avg_stress_index: float
    wearable_paired: bool


# ──────────────────────────── Welfare Interventions ────────────────────────────

class WelfareInterventionResponse(BaseModel):
    id: str
    personnel_id: str
    alert_id: str | None = None
    category: str
    title: str
    description: str
    action_plan: str
    priority: str
    status: str
    recommended_by_xai: bool
    contributing_factors: str | None = None
    outcome_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterventionStatusUpdate(BaseModel):
    status: str
    outcome_notes: str | None = None


class HolisticRiskAssessmentResponse(BaseModel):
    personnel_id: str
    composite_risk_score: float
    risk_level: str
    xai_factor_breakdown: dict[str, float]
    hrms_details: dict[str, Any]
    timestamp: str

