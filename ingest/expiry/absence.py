"""Reconcile source occurrences without expiring jobs after bad crawls."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ingest.models import CanonicalJob, SourceHealth


class JobOccurrence(BaseModel):
    """Minimal persistent state for one source's occurrence of a job."""

    model_config = ConfigDict(extra="forbid")

    occurrence_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    first_seen_at: datetime
    last_seen_at: datetime
    missed_crawls: int = Field(default=0, ge=0)
    active: bool = True
    closure_reason: str | None = None


def reconcile_occurrences(
    existing: list[JobOccurrence],
    present: list[CanonicalJob],
    health: SourceHealth,
    *,
    observed_at: datetime,
    closure_threshold: int = 2,
) -> list[JobOccurrence]:
    """Refresh present jobs and process absences only when the crawl is safe."""

    if closure_threshold < 1:
        raise ValueError("closure_threshold must be at least one.")
    source_id = health.source_id
    present_for_source = {job.job_id: job for job in present if source_id in job.sources}
    reconciled: list[JobOccurrence] = []
    seen_ids: set[str] = set()

    for occurrence in existing:
        if occurrence.source_id != source_id:
            reconciled.append(occurrence)
            continue
        seen_ids.add(occurrence.job_id)
        if occurrence.job_id in present_for_source:
            reconciled.append(
                occurrence.model_copy(
                    update={
                        "last_seen_at": observed_at,
                        "missed_crawls": 0,
                        "active": True,
                        "closure_reason": None,
                    }
                )
            )
            continue
        if not health.safe_to_process_absences:
            reconciled.append(occurrence)
            continue
        missed_crawls = occurrence.missed_crawls + 1
        reconciled.append(
            occurrence.model_copy(
                update={
                    "missed_crawls": missed_crawls,
                    "active": missed_crawls < closure_threshold,
                    "closure_reason": (
                        "missing_from_complete_crawl"
                        if missed_crawls >= closure_threshold
                        else None
                    ),
                }
            )
        )

    for job_id in sorted(set(present_for_source).difference(seen_ids)):
        reconciled.append(
            JobOccurrence(
                occurrence_id=f"{source_id}:{job_id}",
                job_id=job_id,
                source_id=source_id,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
            )
        )
    return reconciled
