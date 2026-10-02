import json

from ingest.main import approved_source_ids, build_jobs, run_ingestion
from ingest.models import RawJob, SourceHealthStatus


class _SuccessfulAdapter:
    crawl_complete = True

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
        "linkedin",
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


def test_build_jobs_rejects_technical_title_paired_with_non_technical_url():
    raw = RawJob(
        source_id="brightermonday",
        external_id="malformed-card",
        title="UI/UX Designer",
        source_url="https://example.com/listings/field-sales-representative",
        apply_url="https://example.com/listings/field-sales-representative",
    )

    assert build_jobs([raw]) == []


def test_failed_fetch_preserves_previous_source_and_audit(tmp_path):
    run_ingestion(tmp_path, source_ids=["elevolt"], adapters={"elevolt": _SuccessfulAdapter})
    previous = (tmp_path / "public/jobs.json").read_text()
    old_success = json.loads((tmp_path / "state/health.json").read_text())["sources"]["elevolt"][
        "last_success_at"
    ]
    health = run_ingestion(tmp_path, source_ids=["elevolt"], adapters={"elevolt": _FailingAdapter})
    assert (tmp_path / "public/jobs.json").read_text() == previous
    assert health["elevolt"].model_dump(mode="json")["last_success_at"] == old_success
    run = json.loads((tmp_path / "state/last-run.json").read_text())
    assert run["outcome"] == "BLOCKED"
    assert run["sources"]["elevolt"]["health"]["error_type"] == "RuntimeError"
    assert "temporary source outage" not in json.dumps(run)
    assert (
        len(next((tmp_path / "state/fetch-history").glob("*.jsonl")).read_text().splitlines()) == 2
    )


def test_empty_result_is_suspicious_and_does_not_erase_jobs(tmp_path):
    class Empty(_SuccessfulAdapter):
        def fetch(self):
            return []

    run_ingestion(tmp_path, source_ids=["elevolt"], adapters={"elevolt": _SuccessfulAdapter})
    health = run_ingestion(tmp_path, source_ids=["elevolt"], adapters={"elevolt": Empty})
    assert health["elevolt"].status == SourceHealthStatus.PARTIAL
    assert len(json.loads((tmp_path / "public/jobs.json").read_text())["jobs"]) == 1


def test_partial_fetch_retains_unseen_jobs(tmp_path):
    class Partial(_SuccessfulAdapter):
        crawl_complete = False

        def fetch(self):
            return [super().fetch()[0].model_copy(update={"external_id": "2"})]

    run_ingestion(tmp_path, source_ids=["elevolt"], adapters={"elevolt": _SuccessfulAdapter})

    # A second healthy source lets the mixed candidate publish safely.
    class Ashby(_SuccessfulAdapter):
        def fetch(self):
            return [super().fetch()[0].model_copy(update={"source_id": "ashby"})]

    health = run_ingestion(
        tmp_path, source_ids=["elevolt", "ashby"], adapters={"elevolt": Partial, "ashby": Ashby}
    )
    assert health["elevolt"].status == SourceHealthStatus.PARTIAL
    ids = {
        job["job_id"] for job in json.loads((tmp_path / "canonical/jobs.json").read_text())["jobs"]
    }
    assert {"elevolt:1", "elevolt:2"} <= ids
    assert not health["elevolt"].safe_to_process_absences


def test_unchanged_fetch_logs_without_requesting_deployment(tmp_path):
    for _ in range(2):
        run_ingestion(tmp_path, source_ids=["elevolt"], adapters={"elevolt": _SuccessfulAdapter})
    run = json.loads((tmp_path / "state/last-run.json").read_text())
    assert run["public_changed"] is False
    assert run["sources"]["elevolt"]["new_jobs"] == 0
    assert run["sources"]["elevolt"]["updated_jobs"] == 0


def test_cooldown_does_not_contact_source(tmp_path):
    from datetime import UTC, datetime, timedelta

    run_ingestion(tmp_path, source_ids=["elevolt"], adapters={"elevolt": _SuccessfulAdapter})
    path = tmp_path / "state/health.json"
    saved = json.loads(path.read_text())
    saved["sources"]["elevolt"]["next_allowed_at"] = (
        datetime.now(UTC) + timedelta(hours=2)
    ).isoformat()
    path.write_text(json.dumps(saved))

    def must_not_construct():
        raise AssertionError("cooldown contacted the source")

    health = run_ingestion(
        tmp_path, source_ids=["elevolt"], adapters={"elevolt": must_not_construct}
    )
    assert health["elevolt"].stop_reason == "retry_after_cooldown"
    assert health["elevolt"].error_type is None
    assert health["elevolt"].requests_made == 0


def test_supported_absence_requires_three_complete_crawls_and_never_counts_failures(tmp_path):
    class Ashby(_SuccessfulAdapter):
        remaining = 10

        def fetch(self):
            return [
                RawJob(
                    source_id="ashby",
                    external_id=str(i),
                    title=f"Product Manager {i}",
                    company="Example Technologies",
                    location="Nairobi, Kenya",
                    source_url=f"https://jobs.example.com/{i}",
                    apply_url=f"https://jobs.example.com/{i}",
                )
                for i in range(self.remaining)
            ]

    run_ingestion(tmp_path, source_ids=["ashby"], adapters={"ashby": Ashby})
    Ashby.remaining = 9
    for _ in range(2):
        health = run_ingestion(tmp_path, source_ids=["ashby"], adapters={"ashby": Ashby})
        assert health["ashby"].safe_to_process_absences
        assert len(json.loads((tmp_path / "public/jobs.json").read_text())["jobs"]) == 10
    run_ingestion(tmp_path, source_ids=["ashby"], adapters={"ashby": _FailingAdapter})
    occurrence = next(
        x
        for x in json.loads((tmp_path / "state/occurrences.json").read_text())["occurrences"]
        if x["job_id"] == "ashby:9"
    )
    assert occurrence["missed_crawls"] == 2
    run_ingestion(tmp_path, source_ids=["ashby"], adapters={"ashby": Ashby})
    assert len(json.loads((tmp_path / "public/jobs.json").read_text())["jobs"]) == 9


def test_http_metrics_are_persisted_per_source_without_descriptions(tmp_path):
    import httpx

    from ingest.adapters.ashby import AshbyAdapter

    def handler(request):
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {
                        "id": "x",
                        "isListed": True,
                        "title": "Software Engineer",
                        "location": "Nairobi",
                        "jobUrl": "https://example.com/x",
                        "applyUrl": "https://example.com/x",
                        "descriptionHtml": "private description",
                    }
                ]
            },
        )

    health = run_ingestion(
        tmp_path,
        source_ids=["ashby"],
        adapters={
            "ashby": lambda: AshbyAdapter(
                "talentsafari", httpx.Client(transport=httpx.MockTransport(handler))
            )
        },
    )
    assert health["ashby"].pages_fetched == health["ashby"].requests_made == 1
    assert health["ashby"].http_status_counts == {"200": 1}
    run = json.loads((tmp_path / "state/last-run.json").read_text())
    assert len(run["sources"]["ashby"]["requests"]) == 1
    request_log = next((tmp_path / "state/request-history").glob("*.jsonl"))
    assert json.loads(request_log.read_text())["source_id"] == "ashby"
    assert "private description" not in str(list(tmp_path.rglob("*")))
    for path in tmp_path.rglob("*.json*"):
        assert "private description" not in path.read_text()


def test_retired_bebee_removed_and_other_sources_preserved(tmp_path):
    from ingest.normalize.canonicalize import canonicalize_raw_job

    other = _SuccessfulAdapter().fetch()[0]
    retired = other.model_copy(update={"source_id": "bebee", "external_id": "retired"})
    kept = canonicalize_raw_job(other)
    kept.sources.append("bebee")
    rows = [canonicalize_raw_job(retired).model_dump(mode="json"), kept.model_dump(mode="json")]
    (tmp_path / "canonical").mkdir()
    (tmp_path / "canonical/jobs.json").write_text(json.dumps({"jobs": rows}))
    (tmp_path / "state").mkdir()
    (tmp_path / "state/health.json").write_text(json.dumps({"sources": {"bebee": {}}}))
    (tmp_path / "state/source-baselines.json").write_text(json.dumps({"bebee": [125]}))

    run_ingestion(tmp_path, source_ids=["elevolt"], adapters={"elevolt": _SuccessfulAdapter})
    jobs = json.loads((tmp_path / "public/jobs.json").read_text())["jobs"]
    assert {job["job_id"] for job in jobs} == {"elevolt:1"}
    assert jobs[0]["sources"] == ["elevolt"]
    assert "bebee" not in json.loads((tmp_path / "state/health.json").read_text())["sources"]
    assert "bebee" not in json.loads((tmp_path / "state/source-baselines.json").read_text())
