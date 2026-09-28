import json
from pathlib import Path

from ingest.adapters.corporate_staffing import parse_corporate_staffing_jobs


def test_public_jobs_api_keeps_minimal_fields_only():
    payload = json.loads(Path("tests/fixtures/m0/corporate_staffing_job.json").read_text())
    jobs = parse_corporate_staffing_jobs(payload)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_id == "450951"
    assert job.title == "ICT Interns Job Muranga County Government"
    assert job.company == "Muranga County Government"
    assert job.published_at is not None
    assert job.published_at.tzinfo is not None
    assert "description" not in job.model_dump()


def test_recovers_explicit_company_from_title_when_source_field_is_empty() -> None:
    jobs = parse_corporate_staffing_jobs(
        [
            {
                "id": 1,
                "date_gmt": "2026-09-28T14:26:00",
                "link": "https://example.com/job/1",
                "title": {"rendered": "Senior Frontend Engineer Job HFCB Group"},
            }
        ]
    )

    assert jobs[0].company == "HFCB Group"
