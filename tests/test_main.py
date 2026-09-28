import json

from ingest.main import approved_source_ids, run_ingestion
from ingest.models import RawJob, SourceHealthStatus


class _SuccessfulAdapter:
    def fetch(self) -> list[RawJob]:
        return [
            RawJob(
                source_id="elevolt",
                external_id="1",
                title="Product Manager",
                company="Example Technologies",
                location="Nairobi, Kenya",
                source_url="https://jobs.example.com/1",
                apply_url="https://jobs.example.com/1",
            )
        ]


class _FailingAdapter:
    def fetch(self) -> list[RawJob]:
        raise RuntimeError("temporary source outage")


def test_approved_sources_exclude_discovery_and_disabled_sources():
    assert approved_source_ids() == [
        "myjobmag",
        "corporate_staffing",
        "openedcareer",
        "elevolt",
        "ashby",
    ]


def test_run_isolates_a_failed_source_and_writes_static_output(tmp_path):
    health = run_ingestion(
        tmp_path,
        source_ids=["elevolt", "ashby"],
        adapters={"elevolt": _SuccessfulAdapter, "ashby": _FailingAdapter},
    )

    assert health["elevolt"].status == SourceHealthStatus.SUCCESS
    assert health["ashby"].status == SourceHealthStatus.FAILED
    public_jobs = json.loads((tmp_path / "public/jobs.json").read_text())
    assert public_jobs["jobs"][0]["category"] == "Technical Product"
    assert "description" not in public_jobs["jobs"][0]
