from datetime import UTC, datetime

from ingest.export.static import build_public_files
from ingest.models import CanonicalJob, EligibilityLevel


def test_public_files_are_safe_and_deterministic() -> None:
    job = CanonicalJob(
        job_id="elevolt:1",
        title="QA Automation Engineer",
        normalized_title="qa automation engineer",
        posting_company="Example Technologies",
        city="Nairobi",
        country="Kenya",
        category="QA / Testing",
        eligibility_level=EligibilityLevel.CONFIRMED,
        eligibility_evidence="Nairobi, Kenya",
        eligibility_source="title_location_rules",
        published_at=datetime(2026, 9, 28, tzinfo=UTC),
        preferred_apply_url="https://example.com/apply/1",
        sources=["elevolt"],
    )

    files = build_public_files([job])

    assert files["stats.json"] == {
        "schema_version": 1,
        "stats": {
            "total_jobs": 1,
            "by_category": {"QA / Testing": 1},
            "by_eligibility": {"CONFIRMED": 1},
        },
    }
    assert files["search-index.json"] == {
        "schema_version": 1,
        "jobs": [
            {
                "job_id": "elevolt:1",
                "title": "QA Automation Engineer",
                "company": "Example Technologies",
                "city": "Nairobi",
                "country": "Kenya",
                "category": "QA / Testing",
            }
        ],
    }
    assert "description" not in files["jobs.json"]["jobs"][0]
