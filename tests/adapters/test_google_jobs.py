import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import yaml

from ingest.adapters.jsearch import GoogleJobsJSearchAdapter
from ingest.main import build_jobs, run_ingestion
from ingest.models import RawJob
from ingest.normalize.canonicalize import canonicalize_raw_job


def record(job_id="google-1", **updates):
    item = {
        "job_id": job_id,
        "job_title": "Software Engineer",
        "employer_name": "Example",
        "job_country": "KE",
        "job_city": "Nairobi",
        "job_publisher": "Indeed",
        "job_apply_link": f"https://careers.example.com/{job_id}",
        "job_posted_at_datetime_utc": "2026-10-01T10:00:00Z",
        "job_description": "NEVER PERSIST DESCRIPTION",
    }
    item.update(updates)
    return item


def test_cursor_pagination_all_publishers_kenya_filter_and_no_descriptions(monkeypatch):
    monkeypatch.setenv("JSEARCH_API_KEY", "test-secret")
    calls = []

    def respond(request):
        calls.append(request)
        records = [
            record(),
            record("foreign", job_country="US"),
            record("hr", job_title="HR Officer"),
        ]
        if len(calls) == 2:
            records = [record(), record("google-2", job_publisher="MyJobMag")]
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "data": {
                    "jobs": records,
                    "cursor": "next-page" if len(calls) == 1 else None,
                },
            },
        )

    adapter = GoogleJobsJSearchAdapter(httpx.Client(transport=httpx.MockTransport(respond)))
    adapter.queries = ("software engineer jobs in Kenya",)
    jobs = build_jobs(adapter.fetch())
    assert len(calls) == 2
    assert "cursor" not in calls[0].url.params
    assert calls[1].url.params["cursor"] == "next-page"
    assert all(r.url.params["date_posted"] == "all" for r in calls)
    assert all(r.url.params["query"] == "software engineer jobs in Kenya" for r in calls)
    assert all(r.url.params["exclude_job_publishers"] == "beBee" for r in calls)
    assert {j.job_id for j in jobs} == {"jsearch:google-1", "jsearch:google-2"}
    assert {j.source_publisher for j in jobs} == {"Indeed", "MyJobMag"}
    assert "DESCRIPTION" not in json.dumps([j.model_dump(mode="json") for j in jobs])
    assert "test-secret" not in json.dumps([j.model_dump(mode="json") for j in jobs])
    assert adapter.crawl_complete


def test_bebee_destination_removed_before_direct_link_selection(monkeypatch):
    monkeypatch.setenv("JSEARCH_API_KEY", "test-secret")
    records = [
        record(
            job_publisher="beBee",
            job_apply_link="https://bebee.com/ke/jobs/1",
            apply_options=[
                {
                    "publisher": "beBee",
                    "is_direct": True,
                    "apply_link": "https://ke.bebee.com/ke/jobs/1",
                },
                {"publisher": "Employer", "apply_link": "https://careers.example.com/original"},
            ],
        ),
        record("only-bebee", job_apply_link="https://bebee.com/ke/jobs/2"),
    ]
    adapter = GoogleJobsJSearchAdapter(
        httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, json={"status": "OK", "data": {"jobs": records}})
            )
        )
    )
    jobs = adapter.fetch()
    assert len(jobs) == 1
    assert str(jobs[0].apply_url) == "https://careers.example.com/original"
    assert jobs[0].source_publisher == "Employer"


def test_pagination_cannot_exceed_five_request_budget(monkeypatch):
    monkeypatch.setenv("JSEARCH_API_KEY", "test-secret")
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "data": {
                    "jobs": [record()],
                    "cursor": f"cursor-{len(calls)}",
                },
            },
        )

    adapter = GoogleJobsJSearchAdapter(httpx.Client(transport=httpx.MockTransport(respond)))
    assert len(adapter.fetch()) == 1
    assert len(calls) == 5


@pytest.mark.parametrize("status", [403, 429, 500])
def test_later_page_failure_never_reports_success(monkeypatch, status):
    monkeypatch.setenv("JSEARCH_API_KEY", "test-secret")
    calls = []

    def respond(request):
        calls.append(request)
        return (
            httpx.Response(
                200, json={"status": "OK", "data": {"jobs": [record()], "cursor": "next"}}
            )
            if len(calls) == 1
            else httpx.Response(status)
        )

    adapter = GoogleJobsJSearchAdapter(httpx.Client(transport=httpx.MockTransport(respond)))
    with pytest.raises(httpx.HTTPStatusError):
        adapter.fetch()
    assert len(calls) == 2
    assert not adapter.crawl_complete


def test_exact_existing_url_preserves_original_identity_and_adds_google_attribution(tmp_path):
    old = canonicalize_raw_job(
        RawJob(
            source_id="myjobmag",
            external_id="keep",
            title="Software Engineer",
            location="Kenya",
            source_url="https://careers.example.com/original",
            apply_url="https://careers.example.com/original",
        )
    )
    (tmp_path / "canonical").mkdir()
    (tmp_path / "canonical/jobs.json").write_text(
        json.dumps({"jobs": [old.model_dump(mode="json")]})
    )

    class Adapter:
        crawl_complete = True

        def fetch(self):
            return [
                RawJob(
                    source_id="jsearch",
                    external_id="google-new",
                    source_publisher="MyJobMag",
                    title="Software Engineer",
                    location="Kenya",
                    source_url="https://careers.example.com/original",
                    apply_url="https://careers.example.com/original?utm_source=google",
                )
            ]

    run_ingestion(tmp_path, source_ids=["jsearch"], adapters={"jsearch": Adapter})
    jobs = json.loads((tmp_path / "public/jobs.json").read_text())["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "myjobmag:keep"
    assert set(jobs[0]["sources"]) == {"myjobmag", "jsearch"}
    assert jobs[0]["source_publisher"] == "MyJobMag"


def test_google_and_historical_linkedin_requests_share_monthly_ceiling(tmp_path):
    history = tmp_path / "state/request-history"
    history.mkdir(parents=True)
    (history / f"{datetime.now(UTC):%Y-%m-%d}.jsonl").write_text(
        "\n".join(json.dumps({"source_id": "linkedin" if i % 2 else "jsearch"}) for i in range(156))
        + "\n"
    )

    def forbidden():
        pytest.fail("Shared account quota must be checked before requests")

    assert run_ingestion(tmp_path, source_ids=["jsearch"], adapters={"jsearch": forbidden}) == {}


def test_next_kenya_calendar_day_can_refresh_before_24_hours(tmp_path, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 3, 4, tzinfo=UTC).astimezone(tz or UTC)

    monkeypatch.setattr("ingest.main.datetime", Clock)

    class Adapter:
        crawl_complete = True

        def fetch(self):
            return [
                RawJob(
                    source_id="jsearch",
                    external_id="1",
                    title="Software Engineer",
                    location="Kenya",
                    source_url="https://careers.example.com/1",
                    apply_url="https://careers.example.com/1",
                )
            ]

    run_ingestion(tmp_path, source_ids=["jsearch"], adapters={"jsearch": Adapter})
    path = tmp_path / "state/health.json"
    health = json.loads(path.read_text())
    health["sources"]["jsearch"]["last_attempt_at"] = "2026-10-02T17:00:00Z"
    path.write_text(json.dumps(health))
    assert "jsearch" in run_ingestion(
        tmp_path, source_ids=["jsearch"], adapters={"jsearch": Adapter}
    )


def test_google_linkedin_identity_uses_native_id_instead_of_changing_search_id(monkeypatch):
    monkeypatch.setenv("JSEARCH_API_KEY", "test-secret")
    link = "https://ke.linkedin.com/jobs/view/software-engineer-123456"
    adapter = GoogleJobsJSearchAdapter(
        httpx.Client(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(
                    200,
                    json={
                        "status": "OK",
                        "data": {
                            "jobs": [
                                record("first", job_apply_link=link, job_publisher="LinkedIn"),
                                record("changed", job_apply_link=link, job_publisher="LinkedIn"),
                            ]
                        },
                    },
                )
            )
        )
    )
    jobs = adapter.fetch()
    assert len(jobs) == 1
    assert jobs[0].external_id == "linkedin-123456"
    assert str(jobs[0].apply_url) == "https://www.linkedin.com/jobs/view/123456/"


def test_queries_share_budget_and_expertini_keeps_publisher(monkeypatch):
    monkeypatch.setenv("JSEARCH_API_KEY", "test-secret")
    calls = []

    def respond(request):
        calls.append(request)
        publisher = "Expertini" if "Nairobi" in request.url.params["query"] else "LinkedIn"
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "data": {
                    "jobs": [
                        record(
                            publisher,
                            job_publisher=publisher,
                            job_apply_link=f"https://ke.expertini.com/jobs/{publisher}/",
                        )
                    ],
                    "cursor": f"next-{len(calls)}",
                },
            },
        )

    adapter = GoogleJobsJSearchAdapter(httpx.Client(transport=httpx.MockTransport(respond)))
    adapter.queries = ("software engineer jobs in Kenya", "software engineer jobs near Nairobi")
    jobs = adapter.fetch()
    assert len(calls) == 5
    assert [r.url.params["query"] for r in calls[: len(adapter.queries)]] == list(adapter.queries)
    assert all("cursor" not in r.url.params for r in calls[: len(adapter.queries)])
    assert calls[len(adapter.queries)].url.params["cursor"] == "next-1"
    assert any(j.source_publisher == "Expertini" for j in jobs)


def test_explicit_refresh_bypasses_today_skip_but_not_quota(tmp_path):
    class Adapter:
        crawl_complete = True

        def fetch(self):
            return [
                RawJob(
                    source_id="jsearch",
                    external_id="1",
                    title="Software Engineer",
                    location="Kenya",
                    source_url="https://example.com/1",
                    apply_url="https://example.com/1",
                )
            ]

    run_ingestion(tmp_path, source_ids=["jsearch"], adapters={"jsearch": Adapter})
    assert run_ingestion(tmp_path, source_ids=["jsearch"], adapters={"jsearch": Adapter}) == {}
    assert "jsearch" in run_ingestion(
        tmp_path, source_ids=["jsearch"], adapters={"jsearch": Adapter}, refresh_jsearch=True
    )
    history = tmp_path / "state/request-history"
    history.mkdir(parents=True, exist_ok=True)
    (history / f"{datetime.now(UTC):%Y-%m-%d}.jsonl").write_text(
        "\n".join(json.dumps({"source_id": "jsearch"}) for _ in range(160)) + "\n"
    )
    assert (
        run_ingestion(
            tmp_path, source_ids=["jsearch"], adapters={"jsearch": Adapter}, refresh_jsearch=True
        )
        == {}
    )


def test_production_uses_configured_role_queries_with_shared_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("JSEARCH_API_KEY", "test-secret")
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"status": "OK", "data": {"jobs": [record()]}})

    adapter = GoogleJobsJSearchAdapter(httpx.Client(transport=httpx.MockTransport(respond)))
    adapter.queries = ("obsolete query",)
    run_ingestion(tmp_path, source_ids=["jsearch"], adapters={"jsearch": lambda: adapter})
    config = yaml.safe_load(Path("config/sources.yaml").read_text())
    queries = next(s for s in config["sources"] if s["id"] == "jsearch")["crawl"]["queries"]
    assert [request.url.params["query"] for request in calls] == queries
    assert len(calls) <= 5


def test_linkedin_manager_queries_capture_roles_and_require_kenya_evidence(monkeypatch):
    monkeypatch.setenv("JSEARCH_API_KEY", "test-secret")
    queries = []

    def respond(request):
        query = request.url.params["query"]
        queries.append(query)
        title = "Product Manager" if query.startswith("product") else "Project Manager"
        manager = query.startswith(("product", "project"))
        job_id = "123456" if title == "Product Manager" else "789012"
        records = (
            [
                record(
                    job_id,
                    job_title=title,
                    job_publisher="LinkedIn",
                    job_apply_link=f"https://www.linkedin.com/jobs/view/{job_id}/",
                ),
                record("foreign", job_title=title, job_country="US"),
            ]
            if manager
            else []
        )
        return httpx.Response(200, json={"status": "OK", "data": {"jobs": records}})

    adapter = GoogleJobsJSearchAdapter(httpx.Client(transport=httpx.MockTransport(respond)))
    jobs = build_jobs(adapter.fetch())
    assert {job.title for job in jobs} == {"Product Manager", "Project Manager"}
    assert {job.job_id for job in jobs} == {"jsearch:linkedin-123456", "jsearch:linkedin-789012"}
    assert all(job.category == "Technical Product" for job in jobs)
    assert all(job.source_publisher == "LinkedIn" and job.country_code == "KE" for job in jobs)
    assert "product manager jobs in Kenya" in queries
    assert "project manager jobs in Kenya" in queries


@pytest.mark.parametrize("empty", [False, True])
def test_bounded_google_sample_preserves_accumulated_jobs_and_keeps_empty_guard(tmp_path, empty):
    old_jobs = [
        canonicalize_raw_job(
            RawJob(
                source_id="jsearch",
                external_id=f"old-{i}",
                title="Software Engineer",
                location="Kenya",
                source_url=f"https://example.com/old-{i}",
                apply_url=f"https://example.com/old-{i}",
            )
        )
        for i in range(3)
    ]
    (tmp_path / "canonical").mkdir()
    (tmp_path / "canonical/jobs.json").write_text(
        json.dumps({"jobs": [job.model_dump(mode="json") for job in old_jobs]})
    )
    (tmp_path / "state").mkdir()
    (tmp_path / "state/source-baselines.json").write_text(json.dumps({"jsearch": [100] * 7}))
    (tmp_path / "public").mkdir()
    (tmp_path / "public/jobs.json").write_text(
        json.dumps({"schema_version": 1, "jobs": [job.model_dump(mode="json") for job in old_jobs]})
    )

    class Adapter:
        crawl_complete = True

        def fetch(self):
            return (
                []
                if empty
                else [
                    RawJob(
                        source_id="jsearch",
                        external_id="new-manager",
                        title="Product Manager",
                        location="Kenya",
                        source_url="https://example.com/new-manager",
                        apply_url="https://example.com/new-manager",
                    )
                ]
            )

    health = run_ingestion(tmp_path, source_ids=["jsearch"], adapters={"jsearch": Adapter})
    assert health["jsearch"].status == ("PARTIAL" if empty else "SUCCESS")
    assert not health["jsearch"].safe_to_process_absences
    jobs = json.loads((tmp_path / "public/jobs.json").read_text())["jobs"]
    assert {job.job_id for job in old_jobs} <= {job["job_id"] for job in jobs}
    assert ("jsearch:new-manager" in {job["job_id"] for job in jobs}) == (not empty)


def test_remote_africa_and_worldwide_results_keep_real_geography(monkeypatch):
    monkeypatch.setenv("JSEARCH_API_KEY", "test-secret")
    records = [
        record("za", job_country="ZA", job_city="Johannesburg", job_is_remote=True),
        record("ug", job_country="UG", job_city="Kampala", job_is_remote=True),
        record(
            "ssa",
            job_country=None,
            job_city=None,
            job_location="Sub-Saharan Africa",
            job_is_remote=True,
            job_title="AI Developer",
        ),
        record(
            "global",
            job_country=None,
            job_city=None,
            job_location="Worldwide",
            job_is_remote=True,
            job_title="Product Engineer (AI-Native)",
        ),
        record("on-site", job_country="ZA", job_is_remote=False),
        record("us", job_country="US", job_is_remote=True),
        record(
            "unknown", job_country=None, job_city=None, job_location="Remote", job_is_remote=True
        ),
        record("emea", job_country=None, job_city=None, job_location="EMEA", job_is_remote=True),
    ]
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"status": "OK", "data": {"jobs": records}})

    adapter = GoogleJobsJSearchAdapter(httpx.Client(transport=httpx.MockTransport(respond)))
    adapter.queries = ("remote tech jobs in Sub-Saharan Africa",)
    jobs = {j.job_id: j for j in build_jobs(adapter.fetch())}
    assert set(jobs) == {"jsearch:za", "jsearch:ug", "jsearch:ssa", "jsearch:global"}
    assert jobs["jsearch:za"].country == "South Africa"
    assert jobs["jsearch:ug"].country == "Uganda"
    assert jobs["jsearch:ssa"].region == "Sub-Saharan Africa"
    assert jobs["jsearch:ssa"].country is None
    assert jobs["jsearch:global"].region == "Worldwide"
    assert all(j.eligibility_level == "CONFIRMED" for j in jobs.values())
    assert calls[0].url.params["country"] == "za"
    assert calls[0].url.params["work_from_home"] == "true"
    assert "job_location" in calls[0].url.params["fields"]
