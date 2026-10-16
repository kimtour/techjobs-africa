"""Regression coverage for evidence that used to be connected only to MyJobMag."""

import json

import pytest

from ingest.adapters.ashby import parse_ashby_jobs
from ingest.adapters.corporate_staffing import parse_corporate_staffing_jobs
from ingest.adapters.elevolt import parse_elevolt_jobs
from ingest.adapters.employer_boards import SDG_URL, parse_sdg_job
from ingest.adapters.jsearch import parse_record
from ingest.adapters.openedcareer import parse_openedcareer_jobs
from ingest.main import build_jobs

TITLE = "Technical Manager"
BODY = "<p>SQL Server and API design. SYNTHETIC_BODY_SENTINEL</p>"


def parse(source):
    if source in ("corporate_staffing", "openedcareer"):
        record = {
            "id": 123,
            "title": {"rendered": TITLE},
            "link": "https://example.com/jobs/123",
            "content": {"rendered": BODY},
        }
        parser = (
            parse_corporate_staffing_jobs
            if source == "corporate_staffing"
            else parse_openedcareer_jobs
        )
        return parser([record])[0]
    if source == "elevolt":
        return parse_elevolt_jobs(
            {
                "data": [
                    {"jid": "123", "title": TITLE, "slug": "technical-manager", "description": BODY}
                ]
            }
        )[0]
    if source == "ashby":
        return parse_ashby_jobs(
            {
                "jobs": [
                    {
                        "id": "123",
                        "title": TITLE,
                        "isListed": True,
                        "jobUrl": "https://example.com/jobs/123",
                        "applyUrl": "https://example.com/jobs/123/application",
                        "descriptionHtml": BODY,
                    }
                ]
            }
        )[0]
    if source == "jsearch":
        return parse_record(
            {
                "job_id": "123",
                "job_title": TITLE,
                "job_country": "KE",
                "job_apply_link": "https://example.com/jobs/123",
                "job_description": BODY,
            }
        )[0]
    return parse_sdg_job(
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "JobPosting",
                "title": TITLE,
                "description": BODY,
                "jobLocationType": "TELECOMMUTE",
                "applicantLocationRequirements": {"name": "worldwide"},
            }
        )
        + "</script>",
        SDG_URL + "p/e5a41beaf52b01-technical-manager",
    )


@pytest.mark.parametrize(
    "source", ["corporate_staffing", "openedcareer", "elevolt", "ashby", "jsearch", "sdg"]
)
def test_each_api_uses_own_evidence_and_keeps_native_identity_without_body(source):
    raw = parse(source)
    assert raw.technical_context == "technical_engineering_management"
    job = build_jobs([raw])[0]
    assert job.job_id == f"{source}:{raw.external_id}"
    assert job.category == "Technology Leadership"
    assert job.category_source == "description_rule"
    assert str(job.preferred_apply_url) == str(raw.apply_url)
    assert "SYNTHETIC_BODY_SENTINEL" not in raw.model_dump_json()
    assert "SYNTHETIC_BODY_SENTINEL" not in job.model_dump_json()
    assert "technical_context" not in raw.model_dump()


@pytest.mark.parametrize("source", ["brightermonday", "fuzu"])
def test_html_board_fetches_pass_the_scoped_detail_evidence_to_the_pipeline(source, monkeypatch):
    import httpx

    from ingest.adapters import brightermonday, fuzu
    from ingest.models import RawJob

    host = "www.brightermonday.co.ke" if source == "brightermonday" else "www.fuzu.com"
    job_url = f"https://{host}/jobs/technical-manager"
    raw = RawJob(
        source_id=source, external_id="123", title=TITLE, source_url=job_url, apply_url=job_url
    )
    payload = (
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "JobPosting",
                "title": TITLE,
                "url": job_url,
                "description": BODY,
            }
        )
        + "</script>"
    )
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text=payload if str(request.url) == job_url else "listing")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    if source == "fuzu":
        monkeypatch.setattr(fuzu, "parse_fuzu_listing_page", lambda *args: ([raw], None))
        adapter = fuzu.FuzuAdapter(session=client, request_delay_seconds=0)
    else:
        monkeypatch.setattr(
            brightermonday, "parse_brightermonday_listing_page", lambda *args: ([raw], None)
        )
        adapter = brightermonday.BrighterMondayAdapter(
            client=client,
            listing_urls=(f"https://{host}/jobs/software-data",),
            request_delay_seconds=0,
        )
    jobs = build_jobs(adapter.fetch())
    assert jobs[0].category == "Technology Leadership"
    assert jobs[0].job_id == f"{source}:123"
    assert calls[-1] == job_url and len(calls) == 2
    assert "SYNTHETIC_BODY_SENTINEL" not in jobs[0].model_dump_json()
