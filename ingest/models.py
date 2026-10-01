"""Shared, validated models for the ingestion pipeline."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

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


class EligibilityDecision(BaseModel):
    level: EligibilityLevel
    evidence: str
    source: str


class RawJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    external_id: str | None = None
    title: str = Field(min_length=1, max_length=300)
    company: str | None = Field(default=None, max_length=300)
    location: str | None = Field(default=None, max_length=300)
    source_url: AnyHttpUrl
    apply_url: AnyHttpUrl
    published_at: datetime | None = None
    published_date: date | None = None


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
    workplace_type: str | None = Field(default=None, max_length=50)
    category: str | None = Field(default=None, max_length=80)
    secondary_categories: list[str] = Field(default_factory=list)
    category_source: str | None = Field(default=None, max_length=50)
    eligibility_level: EligibilityLevel
    eligibility_evidence: str
    eligibility_source: str
    published_at: datetime | None = None
    published_date: date | None = None
    status: JobStatus = JobStatus.ACTIVE
    preferred_apply_url: AnyHttpUrl
    sources: list[str] = Field(min_length=1)
