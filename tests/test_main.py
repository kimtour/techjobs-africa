import json

from ingest.main import approved_source_ids, build_jobs, run_ingestion
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
        "brightermonday",
        "fuzu",
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


def test_build_jobs_rejects_unclassified_job_from_a_technical_source_page():
    raw = RawJob(
        source_id="corporate_staffing",
        external_id="source-scoped-1",
        title="Role without a known keyword",
        source_url="https://example.com/source-scoped-1",
        apply_url="https://example.com/source-scoped-1",
    )

    jobs = build_jobs([raw])

    assert jobs == []


def test_build_jobs_rejects_non_technical_brightermonday_listing():
    raw = RawJob(
        source_id="brightermonday",
        external_id="human-resources-business-partner",
        title="Human Resources Business Partner",
        source_url="https://example.com/human-resources-business-partner",
        apply_url="https://example.com/human-resources-business-partner",
    )

    assert build_jobs([raw]) == []
