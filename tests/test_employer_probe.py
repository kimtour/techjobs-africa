import socket
from types import SimpleNamespace

import httpx
import pytest

from ingest.employer_probe import (
    AccessBlocked,
    ProbeHTTP,
    coverage,
    inspect_page,
    probe_source,
    public_target,
)


def test_public_target_rejects_private_dns_and_social_redirects(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(AccessBlocked):
        public_target("https://careers.example/")
    with pytest.raises(AccessBlocked):
        public_target("https://www.linkedin.com/jobs/")


def test_robots_disallow_and_shared_host_block_are_never_retried():
    seen = []

    def request(req):
        seen.append(str(req.url))
        return httpx.Response(200, text="User-agent: *\nDisallow: /careers")

    http = ProbeHTTP(transport=httpx.MockTransport(request), validate=lambda url: None, interval=0)
    source = {
        "id": "s",
        "platform": "custom",
        "status": "pending",
        "url": "https://a.example/careers",
    }
    try:
        assert probe_source(source, http)["status"] == "BLOCKED"
        assert seen == ["https://a.example/robots.txt"]
    finally:
        http.close()

    seen.clear()

    def limited(req):
        seen.append(str(req.url))
        return httpx.Response(429)

    http = ProbeHTTP(transport=httpx.MockTransport(limited), validate=lambda url: None, interval=0)
    try:
        assert probe_source(source, http)["status"] == "BLOCKED"
        assert (
            probe_source({**source, "url": "https://a.example/jobs"}, http)["status"] == "BLOCKED"
        )
        assert len(seen) == 1
    finally:
        http.close()


def test_probe_discovers_careers_feed_without_storing_descriptions_or_promoting():
    def request(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/":
            return httpx.Response(200, text='<a href="/careers">Jobs</a>')
        return httpx.Response(
            200, text='<link type="application/rss+xml" href="/openings.rss">SECRET BODY'
        )

    http = ProbeHTTP(transport=httpx.MockTransport(request), validate=lambda url: None, interval=0)
    source = {"id": "s", "platform": "custom", "status": "pending", "url": "https://a.example/"}
    try:
        result = probe_source(source, http)
        assert result["status"] == "DISCOVERED"
        assert result["method_suggestion"] == "feed"
        assert result["feed_urls"] == ["https://a.example/openings.rss"]
        assert "SECRET BODY" not in str(result)
        assert source["status"] == "pending"
        assert result["production_promoted"] is False
        assert http.requests == 3
    finally:
        http.close()


def test_methods_and_coverage_do_not_equate_reachability_with_vacancy_coverage():
    response = httpx.Response(
        200,
        text='<iframe src="https://jobs.lever.co/group"></iframe>',
        request=httpx.Request("GET", "https://a.example/careers"),
    )
    assert inspect_page(response)["platform_suggestions"] == ["lever"]
    pdf = httpx.Response(
        200,
        headers={"content-type": "application/pdf"},
        request=httpx.Request("GET", "https://a.example/advert.pdf"),
    )
    assert inspect_page(pdf)["method_suggestion"] == "pdf"
    employers = {e: {"id": e, "name": e} for e in ("a", "b", "c")}
    sources = {"shared": {"id": "shared", "employer_ids": ["a", "b"], "status": "trial"}}
    result = coverage(
        employers, sources, {"shared": {"status": "DISCOVERED", "method_suggestion": "ats_api"}}
    )
    assert len(result["companies"]) == 3
    assert result["sources_probed"] == 1
    assert result["daily_collection_configured"] == 0
    assert result["companies"][2]["probe_outcomes"] == ["NOT_CHECKED"]
    assert "no new jobs" not in str(result)


def test_manual_sites_are_not_requested():
    result = probe_source(
        {"id": "s", "status": "manual", "platform": "social"},
        SimpleNamespace(local=SimpleNamespace()),
    )
    assert result["status"] == "SKIPPED"


def test_redirect_checks_destination_robots_and_large_pages_are_partial():
    visited = []

    def redirected(req):
        visited.append(str(req.url))
        if req.url.host == "b.example":
            return httpx.Response(200, text="User-agent: *\nDisallow: /")
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "https://b.example/jobs"})

    source = {"id": "s", "platform": "custom", "status": "pending", "url": "https://a.example/"}
    http = ProbeHTTP(
        transport=httpx.MockTransport(redirected), validate=lambda url: None, interval=0
    )
    try:
        assert probe_source(source, http)["status"] == "BLOCKED"
        assert visited == [
            "https://a.example/robots.txt",
            "https://a.example/",
            "https://b.example/robots.txt",
        ]
    finally:
        http.close()

    def oversized(req):
        return (
            httpx.Response(404)
            if req.url.path == "/robots.txt"
            else httpx.Response(200, content=b"x" * 2_000_001)
        )

    http = ProbeHTTP(
        transport=httpx.MockTransport(oversized), validate=lambda url: None, interval=0
    )
    try:
        result = probe_source(source, http)
        assert result["status"] == "PARTIAL"
        assert result["error_type"] == "ProbeLimit"
    finally:
        http.close()


def test_compressed_responses_are_decoded_once():
    import gzip

    def compressed(req):
        text = (
            "User-agent: *\nAllow: /"
            if req.url.path == "/robots.txt"
            else '<a href="https://jobs.lever.co/board">Openings</a>'
        )
        return httpx.Response(
            200, headers={"content-encoding": "gzip"}, content=gzip.compress(text.encode())
        )

    http = ProbeHTTP(
        transport=httpx.MockTransport(compressed), validate=lambda url: None, interval=0
    )
    source = {
        "id": "s",
        "platform": "custom",
        "status": "pending",
        "url": "https://a.example/careers",
    }
    try:
        result = probe_source(source, http)
        assert result["status"] == "DISCOVERED"
        assert result["platform_suggestions"] == ["lever"]
    finally:
        http.close()


@pytest.mark.parametrize(
    "html,expected",
    [
        ("<h1>Careers</h1><p>We currently do not have open positions</p>", "EMPTY"),
        ("<h1>Careers</h1><p>New opportunities coming soon</p>", "REVIEW_REQUIRED"),
        (
            '<p>We currently do not have open positions</p><a href="/jobs/123">Engineer</a>',
            "REVIEW_REQUIRED",
        ),
        (
            '<p>We currently do not have open positions</p><a href="/new-advert.pdf">Advert</a>',
            "REVIEW_REQUIRED",
        ),
    ],
)
def test_reviewed_empty_state_never_promotes_or_hides_new_vacancies(html, expected):
    def respond(request):
        return (
            httpx.Response(404)
            if request.url.path == "/robots.txt"
            else httpx.Response(200, text=html)
        )

    http = ProbeHTTP(transport=httpx.MockTransport(respond), validate=lambda url: None, interval=0)
    source = {
        "id": "s",
        "url": "https://a.example/careers",
        "status": "pending",
        "platform": "custom",
        "reviewed_empty_marker": "We currently do not have open positions",
    }
    try:
        result = probe_source(source, http)
        assert result["vacancy_state"] == expected
        assert result["collection_verified"] is False
        assert result["production_promoted"] is False
        assert source["status"] == "pending"
    finally:
        http.close()


def test_shared_board_requires_evidenced_employer_coverage_without_merging_records():
    from ingest.registry_sources import CHECKS

    employers = {e: {"id": e, "name": e} for e in ("bank", "insurer")}
    source = {
        "id": "shared",
        "status": "active",
        "platform": "lever",
        "board": "group",
        "employer_ids": ["bank", "insurer"],
        "verified_employer_ids": ["bank"],
        "verification": {
            **dict.fromkeys(CHECKS, True),
            "trial_review": True,
            "publication_review": True,
            "evidence_paths": ["review.json"],
            "collection_basis": "Reviewed public board",
        },
    }
    result = coverage(employers, {"shared": source}, {})
    rows = {x["employer_id"]: x for x in result["companies"]}
    assert result["daily_collection_configured"] == 1
    assert rows["bank"]["active_verified_sources"] == ["shared"]
    assert rows["insurer"]["active_verified_sources"] == []
    assert rows["insurer"]["source_ids"] == ["shared"]
    assert result["recruitment_sources"] == 1


def test_discovery_hints_are_titles_only_and_keep_functional_job_links():
    import json

    html = (
        "<h3>Software Engineer</h3><p>DO NOT PERSIST DESCRIPTION: Data Engineer duties</p>"
        "<script>Software Engineer secret body</script>"
        '<a href="/careers/338?country=KE&utm_source=mail">View role</a>'
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "JobPosting",
                "title": "Cyber Security Analyst",
                "description": "DO NOT PERSIST JSON DESCRIPTION",
            }
        )
        + "</script>"
    )
    result = inspect_page(
        httpx.Response(200, text=html, request=httpx.Request("GET", "https://example.test/careers"))
    )
    assert result["technical_title_hints"] == ["Cyber Security Analyst", "Software Engineer"]
    assert result["observed_vacancy_links"] == [
        "https://example.test/careers/338?country=KE&utm_source=mail"
    ]
    assert "DO NOT PERSIST" not in json.dumps(result)
