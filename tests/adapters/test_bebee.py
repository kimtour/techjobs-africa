import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from ingest.adapters.bebee import BeBeeAdapter, listing_links, parse_job
from ingest.main import build_jobs

URL = "https://bebee.com/ke/jobs/data-scientist-britam-nairobi--fj-1234"


def metadata(**updates):
    record = {
        "@type": "JobPosting",
        "title": "Data Scientist",
        "identifier": {"value": "fj-1234"},
        "hiringOrganization": {"name": "Britam"},
        "jobLocation": {"address": {"addressCountry": "KE", "addressLocality": "Nairobi"}},
        "datePosted": "2026-09-30",
        "description": "Do not retain this description",
    }
    record.update(updates)
    return '<script type="application/ld+json">' + json.dumps(record) + "</script>"


def test_minimal_metadata_stable_identity_and_technical_classification():
    row = parse_job(metadata(), URL)
    assert row.external_id == "fj-1234"
    assert row.company == "Britam"
    assert row.location == "Nairobi · Kenya"
    assert "description" not in row.model_dump()
    jobs = build_jobs([row])
    assert jobs[0].job_id == "bebee:fj-1234"
    assert jobs[0].country == "Kenya"


@pytest.mark.parametrize("title", ["Line Chef", "Debt Collector", "Software Sales Executive"])
def test_nontechnical_jobs_rejected(title):
    assert parse_job(metadata(title=title), URL) is None
    assert listing_links(f'<h3><a href="{URL}">{title}</a></h3>') == []


def test_foreign_missing_location_expired_and_mutable_identity_rejected():
    assert parse_job(metadata(jobLocation={"address": {"addressCountry": "GB"}}), URL) is None
    assert parse_job(metadata(jobLocation={}), URL) is None
    assert parse_job(metadata(identifier={"value": "different"}), URL) is None
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()
    assert parse_job(metadata(validThrough=yesterday), URL) is None


def test_discovery_accepts_only_bebee_technical_detail_links():
    html = f'<h3><a href="{URL}">Data Scientist</a></h3>'
    html += '<h3><a href="https://evil.example/ke/jobs/test--123">Data Scientist</a></h3>'
    assert listing_links(html) == [URL]


@pytest.mark.parametrize("status", [403, 429, 500])
def test_deliberate_and_transient_failures_stop_without_completion(status):
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status)))
    adapter = BeBeeAdapter(client)
    with pytest.raises(httpx.HTTPStatusError):
        adapter.fetch()
    assert not adapter.crawl_complete


def test_bounded_pages_are_deduped_and_detail_country_is_verified():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path.endswith("technology"):
            return httpx.Response(200, text=f'<h3><a href="{URL}">Data Scientist</a></h3>')
        return httpx.Response(200, text=metadata())

    adapter = BeBeeAdapter(httpx.Client(transport=httpx.MockTransport(handler)))
    adapter.max_pages = 2
    assert len(adapter.fetch()) == 1
    assert len(calls) == 3
    assert adapter.crawl_complete
