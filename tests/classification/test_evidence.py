"""Description evidence must refer to the job, regardless of its publisher."""

import json

import httpx
import pytest

from ingest.classify.evidence import (
    description_technical_context,
    enrich_listing_jobs,
    structured_technical_context,
)
from ingest.fetch import ObservedClient
from ingest.models import RawJob


@pytest.mark.parametrize(
    "title,body,expected",
    [
        (
            "Information Management Assistant",
            "Hardware and IT support.",
            "enterprise_systems_support",
        ),
        ("Technical Manager", "SQL Server and API design.", "technical_engineering_management"),
        ("Senior Product Analyst", "Platform testing for live systems.", "digital_product_support"),
        (
            "Engineer Service Delivery",
            "Routing and switching on a fiber network.",
            "network_service_delivery",
        ),
    ],
)
def test_description_evidence_requires_both_scoped_title_and_own_duties(title, body, expected):
    assert description_technical_context(title, body) == expected
    assert description_technical_context(title, "Office administration.") is None
    assert description_technical_context("Accounts Assistant", body) is None
    assert description_technical_context(title, f"<aside>{body}</aside>") is None
    assert description_technical_context(title, f"<script>{body}</script>") is None


def structured(title="Technical Manager", url="https://jobs.example/1"):
    return (
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@graph": [
                    {
                        "@type": "JobPosting",
                        "title": title,
                        "url": url,
                        "description": "<p>SQL Server and API design.</p>",
                    }
                ]
            }
        )
        + "</script>"
    )


def test_structured_evidence_matches_title_and_destination_not_recommendations():
    url = "https://jobs.example/1"
    assert structured_technical_context("Technical Manager", structured(), url)
    assert (
        structured_technical_context("Technical Manager", structured(url=url + "/other"), url)
        is None
    )
    assert structured_technical_context("Senior Product Analyst", structured(), url) is None
    assert (
        structured_technical_context("Technical Manager", "<p>SQL Server and API design.</p>", url)
        is None
    )


def raw(title="Technical Manager", url="https://jobs.example/1"):
    return RawJob(source_id="fuzu", external_id="1", title=title, source_url=url, apply_url=url)


def test_detail_evidence_is_bounded_to_discovered_source_urls_and_excludes_text():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text=structured())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    observed = ObservedClient(client, {"max_requests_per_run": 1}, sleeper=lambda _: None)
    jobs = enrich_listing_jobs(
        [
            raw(),
            raw(url="https://other.example/2"),
            raw(url="https://jobs.example/3"),
            raw(title="Software Engineer"),
        ],
        observed,
        allowed_hosts={"jobs.example"},
    )
    assert calls == ["https://jobs.example/1"]
    assert jobs[0].technical_context == "technical_engineering_management"
    assert all(j.technical_context is None for j in jobs[1:])
    assert all(
        "description" not in j.model_dump_json() and "SQL Server" not in j.model_dump_json()
        for j in jobs
    )


@pytest.mark.parametrize("status", [403, 429, 500])
def test_detail_blocks_and_failures_are_not_bypassed(status):
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(status)))
    observed = ObservedClient(client, {"retry_delays_seconds": []}, sleeper=lambda _: None)
    with pytest.raises(httpx.HTTPStatusError):
        enrich_listing_jobs([raw()], observed, allowed_hosts={"jobs.example"})
    assert observed.requests == 1


def test_optional_404_keeps_the_listing_without_inventing_evidence_or_expiry():
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(404)))
    observed = ObservedClient(client, {}, sleeper=lambda _: None)
    original = raw()
    assert enrich_listing_jobs([original], observed, allowed_hosts={"jobs.example"}) == [original]
