import json
from datetime import UTC, datetime

import httpx
import pytest

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
    jobs = build_jobs(adapter.fetch())
    assert len(calls) == 2
    assert "cursor" not in calls[0].url.params
    assert calls[1].url.params["cursor"] == "next-page"
    assert all(r.url.params["date_posted"] == "week" for r in calls)
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
