import json
from pathlib import Path

from ingest.adapters.elevolt import parse_elevolt_jobs


def test_parses_minimum_elevolt_listing_metadata() -> None:
    payload = json.loads((Path(__file__).parents[1] / "fixtures/m0/elevolt_jobs.json").read_text())

    jobs = parse_elevolt_jobs(payload)

    assert len(jobs) == 1
    assert jobs[0].source_id == "elevolt"
    assert jobs[0].external_id == "27e92546-921f-49bd-a0a0-98b70b421065"
    assert jobs[0].title == "Principal Software Developer"
    assert jobs[0].company == "BRITAM"
    assert jobs[0].location == "Nairobi, Kenya"
    assert str(jobs[0].apply_url) == "https://jobs.elevolt.co.ke/job/principal-software-developer-at-britam"
    assert "description" not in jobs[0].model_dump()
