import json
from pathlib import Path

import pytest

from ingest.adapters.ashby import AshbyAdapter, parse_ashby_jobs

FIXTURE = Path("tests/fixtures/m0/ashby_public_job.json")


def test_parse_listed_public_job_uses_stable_identity_and_original_urls():
    jobs = parse_ashby_jobs(json.loads(FIXTURE.read_text()))

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source_id == "ashby"
    assert job.external_id == "8a5c7ebf-02e3-4492-9efc-ce83b879757e"
    assert str(job.source_url).endswith(job.external_id)
    assert str(job.apply_url).endswith(f"{job.external_id}/application")
    assert "description" not in job.model_dump()


def test_parse_ignores_unlisted_or_incomplete_jobs():
    payload = {
        "jobs": [
            {"id": "private", "isListed": False},
            {"id": "missing-urls", "isListed": True, "title": "Engineer"},
        ]
    }

    assert parse_ashby_jobs(payload) == []


def test_adapter_rejects_an_unsafe_board_name():
    with pytest.raises(ValueError, match="board names"):
        AshbyAdapter("talentsafari/../private")
