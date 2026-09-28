"""Shared, validated models for the ingestion pipeline."""

from __future__ import annotations

from datetime import datetime
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
    apply_url: AnyHttpUrl
    published_at: datetime | None = None


class SourceHealth(BaseModel):
    source_id: str
    status: SourceHealthStatus
    records_found: int = Field(ge=0)
    pages_fetched: int = Field(ge=0)
    crawl_complete: bool
    safe_to_process_absences: bool
