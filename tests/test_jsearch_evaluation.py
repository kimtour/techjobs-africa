import json

import httpx
import pytest
import yaml

from ingest.jsearch_evaluation import evaluate, parse_record

CONFIG = {"country": "ke", "queries": ["software engineer jobs in Kenya", "data jobs in Kenya"]}


def record(**updates):
    return {
        "job_id": "stable-id",
        "job_title": "Software Engineer",
        "employer_name": "Example",
        "job_city": "Nairobi",
        "job_country": "KE",
        "job_posted_at_datetime_utc": "2026-09-30T12:00:00Z",
        "job_apply_link": "https://www.linkedin.com/jobs/view/123?utm_source=google",
        "apply_options": [
            {"apply_link": "https://careers.example.com/job/123", "is_direct": True},
        ],
        "job_description": "PRIVATE DESCRIPTION MUST NOT BE PERSISTED",
        **updates,
    }


def test_current_v2_schema_country_filter_tech_filter_and_baseline_overlap():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "status": "OK",
                "data": {
                    "cursor": "more-pages",
                    "jobs": [
                        record(),
                        record(job_id="hr", job_title="HR Manager"),
                        record(job_id="us", job_country="US"),
                        record(job_id="unknown", job_country=None),
                        record(job_id="unsafe", job_apply_link="javascript:bad", apply_options=[]),
                    ],
                },
            },
        )

    baseline = {
        "jobs": [
            {
                "status": "ACTIVE",
                "eligibility_level": "CONFIRMED",
                "title": "Software Engineer",
                "posting_company": "Example",
                "city": "Nairobi",
                "preferred_apply_url": "https://careers.example.com/job/123?utm_source=other",
            }
        ]
    }
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        report = evaluate(CONFIG, baseline, client, "secret-test-key")
    assert len(requests) == 2
    assert all(r.url.path.endswith("/search-v2") for r in requests)
    assert all(
        r.url.params["country"] == "ke" and r.url.params["num_pages"] == "1" for r in requests
    )
    assert all("job_description" not in r.url.params["fields"] for r in requests)
    assert all(r.headers["x-api-key"] == "secret-test-key" for r in requests)
    assert report["technical_jobs"] == report["linkedin_linked_jobs"] == 1
    assert report["exact_url_overlaps"] == 1
    assert report["baseline_active_roles"] == 1
    assert report["rejected"]["outside_or_unknown_country"] == 4
    assert report["searches"][0]["has_more"] is True
    job = report["candidates"][0]["job"]
    assert job["job_id"] == "jsearch:stable-id"
    assert job["country"] == "Kenya"
    assert job["preferred_apply_url"] == "https://careers.example.com/job/123"
    assert "PRIVATE DESCRIPTION" not in json.dumps(report)
    assert "secret-test-key" not in json.dumps(report)


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_http_failure_stops_without_retries_or_modifying_baseline(status):
    requests = []
    baseline = {"jobs": []}

    def respond(request):
        requests.append(request)
        return httpx.Response(status, text="secret-test-key response body")

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        report = evaluate(CONFIG, baseline, client, "secret-test-key")
    assert len(requests) == report["requests_made"] == 1
    assert report["searches"][0]["status"] == "http_error"
    assert report["candidates"] == []
    assert baseline == {"jobs": []}
    assert "secret-test-key" not in json.dumps(report)


def test_identity_survives_title_edits_and_invalid_dates_stay_unknown():
    first, _ = parse_record(record())
    second, _ = parse_record(
        record(job_title="Senior Software Engineer", job_posted_at_datetime_utc="invalid")
    )
    assert first.external_id == second.external_id
    assert second.published_at is None
    with pytest.raises(ValueError, match="missing_identity"):
        parse_record(record(job_id=None))


def test_excess_queries_rejected_before_any_request():
    def respond(request):
        pytest.fail("No request should be made for an invalid budget")

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ValueError, match="one to four"):
            evaluate({"country": "ke", "queries": ["engineer"] * 5}, {}, client, "key")


def test_workflow_is_manual_and_cannot_publish_or_write_production_state():
    from pathlib import Path

    workflow = yaml.load(
        Path(".github/workflows/evaluate-jsearch.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert list(workflow["on"]) == ["workflow_dispatch"]
    assert workflow["permissions"] == {"contents": "read"}
    steps = workflow["jobs"]["evaluate"]["steps"]
    assert not any("wrangler" in str(s) or "git push" in str(s) for s in steps)


def test_application_urls_reject_embedded_credentials_and_non_web_schemes():
    from ingest.jsearch_evaluation import safe_url

    assert safe_url("https://:password@example.com/job") is None
    assert safe_url("https://user:password@example.com/job") is None
    assert safe_url("javascript:alert(1)") is None
    assert safe_url("https://careers.example.com/job/123") is not None
