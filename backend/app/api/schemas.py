from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.application import ApplicationMethod, ApplicationStatus
from app.models.job_posting import PostingStatus
from app.models.paused_session import PausedReason


class ApplicationIn(BaseModel):
    company: str
    role_title: str
    location: str | None = None
    location_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    source: str | None = None
    job_url: str | None = None
    contact_person: str | None = None
    notes: str | None = None
    status: ApplicationStatus = ApplicationStatus.QUEUED
    method: ApplicationMethod = ApplicationMethod.MANUAL
    date_applied: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class ApplicationOut(ApplicationIn):
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_response_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProfileIn(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    work_authorization: str | None = None
    requires_sponsorship: bool = False
    willing_to_relocate: bool = False
    security_clearance: str | None = None
    summary: str | None = None
    standard_answers: dict[str, Any] = Field(default_factory=dict)
    eeo_answers: dict[str, Any] = Field(default_factory=dict)
    skills: dict[str, int] = Field(default_factory=dict)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    work_history: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    references: list[dict[str, Any]] = Field(default_factory=list)
    cover_letter_templates: dict[str, str] = Field(default_factory=dict)


class ProfileOut(ProfileIn):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ResumeVariantIn(BaseModel):
    name: str
    tags: list[str] = Field(default_factory=list)
    is_default: bool = False


class ResumeVariantOut(BaseModel):
    id: UUID
    profile_id: UUID
    name: str
    tags: list[str]
    pdf_path: str
    is_default: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class JobPostingOut(BaseModel):
    id: UUID
    source: str
    source_id: str | None
    ats: str | None
    company: str
    role_title: str
    location: str | None
    location_type: str | None
    salary_min: int | None
    salary_max: int | None
    requires_clearance: bool
    clearance_level: str | None
    job_url: str
    score: float | None
    score_breakdown: dict
    status: PostingStatus
    discovered_at: datetime
    last_attempted_at: datetime | None
    model_config = {"from_attributes": True}


class JobSourceIn(BaseModel):
    kind: str
    identifier: str
    enabled: bool = True
    tos_acknowledged: bool = False
    config: dict = Field(default_factory=dict)


class JobSourceOut(JobSourceIn):
    id: UUID
    last_polled_at: datetime | None = None
    last_error: str | None = None
    model_config = {"from_attributes": True}


class PausedSessionOut(BaseModel):
    id: UUID
    job_posting_id: UUID
    application_id: UUID | None
    ats: str
    reason: PausedReason
    message: str
    pending_questions: list
    screenshot_path: str | None
    resolved: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class PausedResolution(BaseModel):
    answers: dict[str, Any]
    proceed: bool = True


class AnalyticsOut(BaseModel):
    totals_by_status: dict[str, int]
    response_rate: float
    interview_conversion: float
    median_time_to_response_days: float | None
    apps_per_week: list[dict[str, Any]]
    auto_vs_manual_success: dict[str, dict[str, int]]


class AuditLogOut(BaseModel):
    id: UUID
    application_id: UUID | None
    action: str
    ats: str | None
    job_url: str | None
    answers: dict
    screenshot_paths: list[str]
    success: bool
    error: str | None
    extra: dict
    created_at: datetime
    model_config = {"from_attributes": True}


class KillSwitchOut(BaseModel):
    kill_switch: bool
    dry_run: bool
    per_job_approval: bool
