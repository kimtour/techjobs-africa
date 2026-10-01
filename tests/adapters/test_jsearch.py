import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from ingest.adapters.jsearch import LinkedInJSearchAdapter, linkedin_identity
from ingest.main import build_jobs, run_ingestion
from ingest.models import RawJob


def record(
    job_id="google-id",
    country="KE",
    link="https://ke.linkedin.com/jobs/view/software-engineer-at-example-123456",
):
    return {
        "job_id": job_id,
        "job_title": "Software Engineer",
        "employer_name": "Example",
        "job_city": "Nairobi",
        "job_country": country,
        "job_is_remote": True,
        "job_apply_link": link,
        "job_posted_at_datetime_utc": "2026-09-30T12:00:00Z",
        "job_description": "DESCRIPTION MUST NOT PERSIST",
    }


def test_only_linkedin_jobs_are_selected_and_identity_survives_google_id_changes(monkeypatch):
    monkeypatch.setenv("JSEARCH_API_KEY", "test-secret")
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "data": {
                    "cursor": "more",
                    "jobs": [
                        record(job_id=str(len(calls))),
                        record(link="https://careers.example.com/other"),
                        record(link="https://linkedin.com.evil.test/jobs/view/999"),
                        record(country="US"),
                    ],
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = LinkedInJSearchAdapter(client)
        jobs = adapter.fetch()
    assert len(calls) == 2
    assert all(c.url.params["num_pages"] == "1" for c in calls)
    assert all("via linkedin" in c.url.params["query"] for c in calls)
    assert len(jobs) == 1
    assert jobs[0].external_id == "123456"
    canonical = build_jobs(jobs)[0]
    assert canonical.job_id == "linkedin:123456"
    assert canonical.sources == ["linkedin"]
    assert str(canonical.preferred_apply_url) == "https://www.linkedin.com/jobs/view/123456/"
    assert "DESCRIPTION" not in canonical.model_dump_json()
    assert "test-secret" not in canonical.model_dump_json()


@pytest.mark.parametrize("status", [403, 429, 500])
def test_failure_stops_queries_without_retries(monkeypatch, status):
    monkeypatch.setenv("JSEARCH_API_KEY", "test-secret")
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(status)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        adapter = LinkedInJSearchAdapter(client)
        with pytest.raises(httpx.HTTPStatusError):
            adapter.fetch()
    assert len(calls) == 1
    assert adapter.crawl_complete is False


def test_linkedin_identity_handles_locale_urls_and_rejects_non_posting_links():
    assert linkedin_identity("https://www.linkedin.com/jobs/view/123456/?tracking=1") == "123456"
    assert linkedin_identity("https://ke.linkedin.com/jobs/view/engineer-123456") == "123456"
    assert linkedin_identity("https://linkedin.com.evil.test/jobs/view/123456/") is None
    assert linkedin_identity("https://linkedin.com/jobs/search?currentJobId=123456") is None


class SuccessfulLinkedInAdapter:
    crawl_complete = True

    def fetch(self):
        return [
            RawJob(
                source_id="linkedin",
                external_id="123456",
                title="Software Engineer",
                location="Nairobi, Kenya",
                source_url="https://www.linkedin.com/jobs/view/123456/",
                apply_url="https://www.linkedin.com/jobs/view/123456/",
            )
        ]


def test_daily_refresh_skip_keeps_saved_jobs_without_contacting_provider(tmp_path):
    run_ingestion(
        tmp_path, source_ids=["linkedin"], adapters={"linkedin": SuccessfulLinkedInAdapter}
    )
    before = (tmp_path / "public/jobs.json").read_text()

    def forbidden():
        pytest.fail("Daily cooldown must avoid API requests")

    run_ingestion(tmp_path, source_ids=["linkedin"], adapters={"linkedin": forbidden})
    assert (tmp_path / "public/jobs.json").read_text() == before
    occurrences = json.loads((tmp_path / "state/occurrences.json").read_text())
    assert occurrences["occurrences"][0]["active"] is True
    health = json.loads((tmp_path / "state/health.json").read_text())
    assert health["sources"]["linkedin"]["safe_to_process_absences"] is False


def test_monthly_budget_skips_before_contacting_provider(tmp_path):
    history = tmp_path / "state/request-history"
    history.mkdir(parents=True)
    (history / f"{datetime.now(UTC):%Y-%m-%d}.jsonl").write_text(
        "\n".join(json.dumps({"source_id": "linkedin"}) for _ in range(160)) + "\n"
    )

    def forbidden():
        pytest.fail("Monthly ceiling must avoid API requests")

    assert run_ingestion(tmp_path, source_ids=["linkedin"], adapters={"linkedin": forbidden}) == {}


def test_failed_refresh_retains_previously_published_jobs(tmp_path):
    run_ingestion(
        tmp_path, source_ids=["linkedin"], adapters={"linkedin": SuccessfulLinkedInAdapter}
    )
    before = (tmp_path / "public/jobs.json").read_text()
    path = tmp_path / "state/health.json"
    health = json.loads(path.read_text())
    health["sources"]["linkedin"]["last_attempt_at"] = (
        datetime.now(UTC) - timedelta(days=2)
    ).isoformat()
    path.write_text(json.dumps(health))

    class Failed:
        def fetch(self):
            raise RuntimeError("failure")

    run_ingestion(tmp_path, source_ids=["linkedin"], adapters={"linkedin": Failed})
    assert (tmp_path / "public/jobs.json").read_text() == before
