"""Shared, validated models for the ingestion pipeline."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class EligibilityLevel(StrEnum):
    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    VERIFY = "VERIFY"
    RESTRICTED = "RESTRICTED"
    UNKNOWN = "UNKNOWN"


class JobStatus(StrEnum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


class SourceHealthStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    DISABLED = "DISABLED"
    SKIPPED = "SKIPPED"


class EligibilityDecision(BaseModel):
    level: EligibilityLevel
    evidence: str
    source: str


class RawJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    source_publisher: str | None = Field(default=None, max_length=300)
    external_id: str | None = None
    title: str = Field(min_length=1, max_length=300)
    company: str | None = Field(default=None, max_length=300)
    location: str | None = Field(default=None, max_length=2000)
    source_url: AnyHttpUrl
    apply_url: AnyHttpUrl
    published_at: datetime | None = None
    published_date: date | None = None
    deadline_at: datetime | None = None
    employment_type: str | None = Field(default=None, max_length=100)
    employer_id: str | None = None
    employer_sectors: list[str] = Field(default_factory=list)
    direct_employer: bool = False
    shared_apply_url: bool = False
    applicant_africa: bool = Field(default=False, exclude=True)
    opportunity_type: Literal["employment", "consultancy", "internship", "fellowship"] | None = None
    technical_context: (
        Literal[
            "geospatial_application_development",
            "network_service_delivery",
            "digital_product_support",
            "payments_platform_product",
            "digital_health_systems",
            "software_application_development",
            "enterprise_systems_support",
            "technical_engineering_management",
            "technical_data_analysis",
            "business_systems_analysis",
            "digital_experience_design",
            "intelligent_workflow_automation",
            "technical_documentation",
            "technology_training",
        ]
        | None
    ) = Field(default=None, exclude=True)


class SourceHealth(BaseModel):
    source_id: str
    status: SourceHealthStatus
    records_found: int = Field(ge=0)
    pages_fetched: int = Field(ge=0)
    crawl_complete: bool
    safe_to_process_absences: bool
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0
    requests_made: int = 0
    retries: int = 0
    http_status_counts: dict[str, int] = Field(default_factory=dict)
    error_type: str | None = None
    stop_reason: str | None = None
    next_allowed_at: datetime | None = None
    consecutive_failures: int = 0


class CanonicalJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    job_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=300)
    normalized_title: str = Field(min_length=1, max_length=300)
    posting_company: str | None = Field(default=None, max_length=300)
    hiring_company: str | None = Field(default=None, max_length=300)
    normalized_company: str | None = Field(default=None, max_length=300)
    is_agency_posting: bool = False
    city: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    country_code: str | None = Field(default=None, max_length=2)
    region: str | None = Field(default=None, max_length=120)
    workplace_type: str | None = Field(default=None, max_length=50)
    category: str | None = Field(default=None, max_length=80)
    secondary_categories: list[str] = Field(default_factory=list)
    category_source: str | None = Field(default=None, max_length=50)
    eligibility_level: EligibilityLevel
    eligibility_evidence: str
    eligibility_source: str
    published_at: datetime | None = None
    published_date: date | None = None
    deadline_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_checked_at: datetime | None = None
    employment_type: str | None = Field(default=None, max_length=100)
    employer_id: str | None = None
    employer_sectors: list[str] = Field(default_factory=list)
    direct_employer: bool = False
    shared_apply_url: bool = False
    opportunity_type: Literal["employment", "consultancy", "internship", "fellowship"] | None = None
    status: JobStatus = JobStatus.ACTIVE
    preferred_apply_url: AnyHttpUrl
    sources: list[str] = Field(min_length=1)
    source_publisher: str | None = Field(default=None, max_length=300)
