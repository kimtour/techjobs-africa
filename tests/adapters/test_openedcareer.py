import json
from pathlib import Path

from ingest.adapters.openedcareer import parse_openedcareer_jobs


def test_parses_minimum_openedcareer_listing_metadata() -> None:
    payload = json.loads(
        (Path(__file__).parents[1] / "fixtures/m0/openedcareer_job.json").read_text()
    )

    jobs = parse_openedcareer_jobs(payload)

    assert len(jobs) == 1
    assert jobs[0].source_id == "openedcareer"
    assert jobs[0].external_id == "53866"
    assert jobs[0].title == "Security Support Assistant – All Interested Applicants"
    assert str(jobs[0].source_url) == "https://openedcareer.com/job/security-support-assistant/"
    assert jobs[0].company is None
    assert "content" not in jobs[0].model_dump()
