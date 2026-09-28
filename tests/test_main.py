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


def test_build_jobs_keeps_source_scoped_technical_listing_without_title_keyword():
    raw = RawJob(
        source_id="corporate_staffing",
        external_id="source-scoped-1",
        title="Role without a known keyword",
        source_url="https://example.com/source-scoped-1",
        apply_url="https://example.com/source-scoped-1",
    )

    jobs = build_jobs([raw])

    assert len(jobs) == 1
    assert jobs[0].category == "IT Operations"
    assert jobs[0].category_source == "source_category"


def test_build_jobs_does_not_force_a_nontechnical_myjobmag_title_into_it_operations():
    raw = RawJob(
        source_id="myjobmag",
        external_id="accounts-assistant",
        title="Accounts Assistant at Decase Chemicals Limited",
        source_url="https://example.com/accounts-assistant",
        apply_url="https://example.com/accounts-assistant",
    )

    assert build_jobs([raw]) == []
