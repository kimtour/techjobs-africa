from datetime import UTC, datetime, timedelta

from ingest.expiry.absence import JobOccurrence, reconcile_occurrences
from ingest.models import CanonicalJob, EligibilityLevel, SourceHealth, SourceHealthStatus

NOW = datetime(2026, 9, 28, tzinfo=UTC)


def job(job_id: str = "elevolt:1") -> CanonicalJob:
    return CanonicalJob(
        job_id=job_id,
        title="QA Engineer",
        normalized_title="qa engineer",
        eligibility_level=EligibilityLevel.UNKNOWN,
        eligibility_evidence="No reliable African eligibility signal found.",
        eligibility_source="none",
        preferred_apply_url="https://example.com/apply/1",
        sources=["elevolt"],
    )


def occurrence(missed_crawls: int = 0) -> JobOccurrence:
    return JobOccurrence(
        occurrence_id="elevolt:elevolt:1",
        job_id="elevolt:1",
        source_id="elevolt",
        first_seen_at=NOW - timedelta(days=1),
        last_seen_at=NOW - timedelta(days=1),
        missed_crawls=missed_crawls,
    )


def health(*, safe: bool) -> SourceHealth:
    return SourceHealth(
        source_id="elevolt",
        status=SourceHealthStatus.SUCCESS if safe else SourceHealthStatus.FAILED,
        records_found=0,
        pages_fetched=0,
        crawl_complete=safe,
        safe_to_process_absences=safe,
    )


def test_failed_crawl_leaves_absence_counters_untouched():
    results = reconcile_occurrences([occurrence(1)], [], health(safe=False), observed_at=NOW)

    assert results[0].missed_crawls == 1
    assert results[0].active is True


def test_two_complete_crawl_absences_close_a_listing():
    results = reconcile_occurrences([occurrence(1)], [], health(safe=True), observed_at=NOW)

    assert results[0].missed_crawls == 2
    assert results[0].active is False
    assert results[0].closure_reason == "missing_from_complete_crawl"


def test_present_jobs_refresh_even_when_absence_processing_is_gated():
    results = reconcile_occurrences([occurrence(1)], [job()], health(safe=False), observed_at=NOW)

    assert results[0].last_seen_at == NOW
    assert results[0].missed_crawls == 0
    assert results[0].active is True
