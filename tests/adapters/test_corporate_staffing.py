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
    assert "description" not in job.model_dump()
