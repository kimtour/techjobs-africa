import json
from datetime import UTC, datetime, timedelta
from io import BytesIO

import httpx
import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

from ingest.adapters.structured_employers import StructuredEmployerAdapter
from ingest.audit import public_hash
from ingest.dedupe.exact import deduplicate_exact
from ingest.employer_state import EmployerLedger, mark_published
from ingest.http_policy import CollectionBlocked
from ingest.main import _write_json
from ingest.models import RawJob
from ingest.normalize.canonicalize import canonicalize_raw_job

EMPLOYERS = {"emp": {"id": "emp", "name": "Example Employer", "sectors": ["Banks"]}}


def source(method="html", **settings):
    return {
        "id": "employer_test",
        "platform": "custom",
        "access_method": method,
        "employer_ids": ["emp"],
        "crawl": {"max_pages": 5},
        "collection": {
            "listing_url": "https://example.test/careers",
            "detail_url_pattern": r"/job/",
            "complete_listing_verified": True,
            **settings,
        },
    }


def raw(key="one", title="Software Engineer"):
    return RawJob(
        source_id="employer_test",
        external_id=key,
        title=title,
        company="Example Employer",
        location="Nairobi, Kenya",
        direct_employer=True,
        source_url=f"https://example.test/job/{key}",
        apply_url=f"https://example.test/job/{key}",
    )


def adapter(config, handler):
    return StructuredEmployerAdapter(
        config,
        EMPLOYERS,
        httpx.Client(transport=httpx.MockTransport(handler)),
        validator=lambda url: None,
    )


def posting(title="Software Engineer"):
    return (
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "JobPosting",
                "identifier": {"value": "REQ1"},
                "title": title,
                "description": "DO NOT PERSIST THIS DESCRIPTION",
                "jobLocation": {
                    "address": {"addressLocality": "Nairobi", "addressCountry": "Kenya"}
                },
            }
        )
        + "</script>"
    )


def test_candidate_baseline_and_first_found_survive_title_edits_and_failed_publication(tmp_path):
    path = tmp_path / "state/employer-candidates.json"
    ledger = EmployerLedger(path)
    now = datetime(2026, 10, 25, 10, tzinfo=UTC)
    one = raw()
    job = canonicalize_raw_job(one)
    assert not ledger.observe(one.source_id, [one], [job], now, complete=True)
    assert ledger.source(one.source_id)["baseline_at"] == now.isoformat()
    two = raw("two")
    ready = ledger.observe(
        one.source_id,
        [one, two],
        [job, canonicalize_raw_job(two)],
        now + timedelta(days=1),
        complete=True,
    )
    assert [j.job_id for j in ready] == ["employer_test:two"]
    edited = raw("two", "Senior Software Engineer")
    refreshed = ledger.observe(
        one.source_id,
        [edited],
        [canonicalize_raw_job(edited)],
        now + timedelta(days=2),
        complete=True,
    )
    assert refreshed[0].first_seen_at == ready[0].first_seen_at
    assert refreshed[0].job_id == ready[0].job_id
    ledger.save(_write_json)
    assert ledger.source(one.source_id)["items"]["two"]["processing_status"] == "validated"
    _write_json(tmp_path / "canonical/jobs.json", {"jobs": [refreshed[0].model_dump(mode="json")]})
    mark_published(tmp_path)
    persisted = EmployerLedger(path)
    assert persisted.source(one.source_id)["items"]["two"]["processing_status"] == "published"


def test_detail_failures_remain_retryable_even_after_the_link_leaves_the_feed():
    failing = True
    listed = True

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/careers":
            return httpx.Response(
                200, text='<a href="/job/one">Vacancy</a>' if listed else "No vacancies"
            )
        return httpx.Response(503) if failing else httpx.Response(200, text=posting())

    collector = adapter(source(empty_marker="No vacancies"), handler)
    assert collector.fetch() == []
    assert not collector.crawl_complete
    queue = collector.candidate_state["items"]
    pending = next(iter(queue.values()))
    assert pending["processing_status"] == "awaiting_extraction"
    pending["next_attempt_at"] = datetime(2020, 1, 1, tzinfo=UTC).isoformat()
    failing, listed = False, False
    collector.detail_failures = 0
    jobs = collector.fetch()
    assert [j.external_id for j in jobs] == ["REQ1"]
    assert collector.crawl_complete
    assert "DO NOT PERSIST" not in json.dumps(collector.candidate_state)
    collector._client.close()


def test_robots_is_checked_for_detail_paths_not_only_listing_root():
    visited = []

    def handler(req):
        visited.append(req.url.path)
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /job/")
        return httpx.Response(200, text='<a href="/job/private">Vacancy</a>')

    collector = adapter(source(), handler)
    with pytest.raises(CollectionBlocked):
        collector.fetch()
    assert visited == ["/robots.txt", "/careers"]
    collector._client.close()


def test_conditional_details_need_validated_cache_and_preserve_identity():
    conditional = []

    def handler(req):
        if req.url.path == "/robots.txt":
            return httpx.Response(404)
        if req.url.path == "/careers":
            return httpx.Response(200, text='<a href="/job/one">Vacancy</a>')
        conditional.append(req.headers.get("If-None-Match"))
        return (
            httpx.Response(304)
            if conditional[-1]
            else httpx.Response(200, text=posting(), headers={"etag": '"1"'})
        )

    collector = adapter(source(conditional_verified=True), handler)
    first = collector.fetch()
    second = collector.fetch()
    assert first[0].external_id == second[0].external_id == "REQ1"
    assert conditional == [None, '"1"']
    collector._client.close()


def pdf_bytes():
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    stream = StreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 30 700 Td (Software Engineer|REQ1) Tj 0 -20 Td (Network Engineer|REQ2) Tj ET"
    )
    page[NameObject("/Contents")] = stream
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_multi_role_pdf_requires_durable_requisitions_and_is_not_url_merged():
    def handler(req):
        return (
            httpx.Response(404)
            if req.url.path == "/robots.txt"
            else httpx.Response(200, content=pdf_bytes())
        )

    collector = adapter(
        source(
            "pdf",
            role_pattern=r"(?P<title>[^\n|]+)\|(?P<identifier>REQ\d+)",
            location="Nairobi, Kenya",
        ),
        handler,
    )
    jobs = [canonicalize_raw_job(job) for job in collector.fetch()]
    assert len(jobs) == 2
    assert {j.job_id for j in deduplicate_exact(jobs)} == {
        "employer_test:REQ1",
        "employer_test:REQ2",
    }
    assert len({str(j.preferred_apply_url) for j in jobs}) == 1
    collector._client.close()


def test_display_hash_ignores_check_times_but_keeps_source_posting_dates():
    one = {
        "jobs.json": {
            "jobs": [
                {"job_id": "one", "published_at": "2026-10-01", "last_checked_at": "2026-10-24"}
            ]
        }
    }
    two = json.loads(json.dumps(one))
    two["jobs.json"]["jobs"][0]["last_checked_at"] = "2026-10-25"
    assert public_hash(one) == public_hash(two)
    two["jobs.json"]["jobs"][0]["published_at"] = "2026-10-02"
    assert public_hash(one) != public_hash(two)


def test_validation_failure_is_not_permanently_filtered(monkeypatch, tmp_path):
    import ingest.main as pipeline

    config = {
        **source(),
        "status": "active",
        "refresh_hours": 24,
        "reviewed_bootstrap": True,
        "crawl": {"max_pages": 1},
    }

    class Collector:
        crawl_complete = True

        def fetch(self):
            return [raw("one"), raw("two")]

    monkeypatch.setattr(
        pipeline,
        "active_factories",
        lambda *a: ({"employer_test": Collector}, {"employer_test": config}),
    )
    monkeypatch.setattr(pipeline, "source_due", lambda *a: True)
    original = pipeline.build_jobs

    def failed_validation(records, **kwargs):
        if records[0].external_id == "two":
            raise ValueError("temporary validation fault")
        return original(records, **kwargs)

    monkeypatch.setattr(pipeline, "build_jobs", failed_validation)
    pipeline.run_ingestion(tmp_path, source_ids=["employer_test"])
    path = tmp_path / "state/employer-candidates.json"
    state = json.loads(path.read_text())["sources"]["employer_test"]["items"]
    assert state["two"]["processing_status"] == "awaiting_validation"
    first_seen = state["two"]["first_seen_at"]
    monkeypatch.setattr(pipeline, "build_jobs", original)
    pipeline.run_ingestion(tmp_path, source_ids=["employer_test"])
    state = json.loads(path.read_text())["sources"]["employer_test"]["items"]
    assert state["two"]["processing_status"] == "validated"
    assert state["two"]["first_seen_at"] == first_seen


def test_pending_candidates_are_not_marked_published_until_promotion(tmp_path):
    from ingest.finalize import finalize

    data, candidate = tmp_path / "data", tmp_path / "candidate"
    for root in (data, candidate):
        _write_json(root / "canonical/jobs.json", {"schema_version": 1, "jobs": []})
        _write_json(root / "public/jobs.json", {"schema_version": 1, "jobs": []})
    ledger = EmployerLedger(candidate / "state/employer-candidates.json")
    job = canonicalize_raw_job(raw())
    ledger.observe(
        "employer_test", [raw()], [job], datetime.now(UTC), complete=True, publish_existing=True
    )
    ledger.save(_write_json)
    _write_json(
        candidate / "canonical/jobs.json",
        {"schema_version": 1, "jobs": [job.model_dump(mode="json")]},
    )
    finalize(data, candidate, promote=False, deployment={"outcome": "not_published"})
    path = data / "state/employer-candidates.json"
    assert (
        json.loads(path.read_text())["sources"]["employer_test"]["items"]["one"][
            "processing_status"
        ]
        == "validated"
    )
    finalize(data, candidate, promote=True, deployment={"outcome": "unchanged"})
    assert (
        json.loads(path.read_text())["sources"]["employer_test"]["items"]["one"][
            "processing_status"
        ]
        == "published"
    )


def test_daily_due_uses_kenya_day_and_keeps_failure_backoff():
    from ingest.registry_sources import source_due

    now = datetime(2026, 10, 26, 3, tzinfo=UTC)
    previous = datetime(2026, 10, 25, 19, tzinfo=UTC)
    assert source_due({"refresh_hours": 24}, {"last_attempt_at": previous.isoformat()}, now)
    assert not source_due(
        {"refresh_hours": 24},
        {"last_attempt_at": previous.isoformat(), "consecutive_failures": 1},
        now,
    )


def test_known_embedded_board_id_is_not_inferred_from_host_alone():
    from ingest.employer_registry import board_identity

    assert board_identity("https://boards.eu.greenhouse.io/embed/job_board/js?for=pawapay") == (
        "greenhouse",
        "pawapay",
    )
    assert board_identity("https://boards.eu.greenhouse.io/embed/job_board/js?for=other") != (
        "greenhouse",
        "pawapay",
    )
    assert board_identity("https://jobs.ashbyhq.com/M-KOPA/form/pool") == ("ashby", "M-KOPA")
    assert board_identity("https://assets-cdn.breezy.hr/script.js") is None


def test_atom_pagination_checks_every_page_and_rejects_truncation():
    visited = []

    def respond(request):
        visited.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if request.url.path == "/careers":
            return httpx.Response(
                200,
                text=(
                    '<feed xmlns="http://www.w3.org/2005/Atom">'
                    '<link rel="next" href="/page2"/></feed>'
                ),
            )
        return httpx.Response(200, text='<feed xmlns="http://www.w3.org/2005/Atom"/>')

    config = source("rss", verified_empty_feed=True)
    collector = adapter(config, respond)
    assert collector.fetch() == []
    assert collector.crawl_complete
    assert "/page2" in visited
    config["crawl"]["max_pages"] = 1
    collector = adapter(config, respond)
    assert collector.fetch() == []
    assert not collector.crawl_complete


def test_page_monitor_preserves_blocks_manual_review_and_failure_backoff():
    from ingest.employer_watch import watch_due

    now = datetime(2026, 10, 26, 3, tzinfo=UTC)
    yesterday = now - timedelta(days=1)
    for state in ("active", "manual", "blocked", "retired"):
        assert not watch_due({"status": state}, {}, now)
    assert not watch_due({"status": "pending"}, {"status": "BLOCKED"}, now)
    assert not watch_due(
        {"status": "pending"},
        {"status": "FAILED", "failures": 1, "checked_at": yesterday.isoformat()},
        now,
    )
    assert watch_due(
        {"status": "pending"}, {"status": "REACHABLE", "checked_at": yesterday.isoformat()}, now
    )


def test_coverage_does_not_treat_reachable_pages_as_vacancy_checks(tmp_path):
    from ingest.employer_state import daily_coverage
    from ingest.registry_sources import load_sources

    employers, sources = load_sources()
    sid = next(sid for sid, item in sources.items() if item["status"] == "pending")
    _write_json(
        tmp_path / "state/employer-watch.json",
        {"sources": {sid: {"status": "REACHABLE", "checked_at": datetime.now(UTC).isoformat()}}},
    )
    result = daily_coverage(tmp_path)
    assert result["employers"] == len(employers) == 758
    assert result["successfully_checked_employers"] == 0
    assert result["sources"][sid]["outcome"] in {"unsupported", "awaiting_verification"}
    assert result["sources"][sid]["verification_gaps"]


def test_daily_work_is_spread_over_existing_slots_with_late_catchup():
    from ingest.employer_watch import watch_due
    from ingest.registry_sources import daily_slot, source_due

    slots = {daily_slot({"id": f"employer_{i}"}) for i in range(100)}
    assert slots == {6, 9, 12, 15, 19}
    config = {"id": "employer_test", "status": "pending", "refresh_hours": 24}
    slot = daily_slot(config)
    before = datetime(2026, 10, 26, slot - 4, tzinfo=UTC)
    due = before + timedelta(hours=1)
    previous = {"last_attempt_at": (before - timedelta(days=1)).isoformat()}
    assert not source_due(config, previous, before)
    assert source_due(config, previous, due)
    assert not watch_due(config, {}, before)
    assert watch_due(config, {}, due)
    assert source_due(config, previous, due + timedelta(hours=2))


def test_reviewed_posting_token_survives_changed_jazzhr_title_slug():
    collector = adapter(
        source(identifier_url_pattern=r"/apply/([A-Za-z0-9]+)/"), lambda r: httpx.Response(200)
    )
    assert collector.identity("https://example.test/apply/AbC123/Old-Title") == "AbC123"
    assert collector.identity("https://example.test/apply/AbC123/New-Title") == "AbC123"
    with pytest.raises(ValueError):
        collector.identity("https://example.test/careers")


def test_reviewed_header_fields_supply_missing_job_schema_without_inventing_dates():
    config = source(
        identifier_url_pattern=r"/apply/([A-Za-z0-9]+)/",
        fields={
            "title": r"<h2>(.*?)</h2>",
            "location": r'<div title="Location">(.*?)</div>',
        },
    )
    html = '<h2>QA Automation Engineer</h2><div title="Location"><i></i>Nairobi, Kenya</div>'

    def respond(request):
        return httpx.Response(
            200, text="User-agent: *\nAllow: /" if request.url.path == "/robots.txt" else html
        )

    collector = adapter(config, respond)
    jobs = collector.detail("https://example.test/apply/Token123/QA-Automation-Engineer")
    assert len(jobs) == 1
    assert jobs[0].external_id == "Token123"
    assert jobs[0].location == "Nairobi, Kenya"
    assert jobs[0].published_at is None


def test_official_jazzhr_widget_and_direct_vacancy_identify_same_board():
    from ingest.employer_registry import board_identity

    assert board_identity("https://app.jazz.co/widgets/basic/create/branchinternational") == (
        "jazzhr",
        "branchinternational",
    )
    assert board_identity(
        "https://branchinternational.applytojob.com/apply/Token/Changed-Title"
    ) == ("jazzhr", "branchinternational")
    assert board_identity("https://app.jazz.co/unknown/branchinternational") is None


def test_targeted_refresh_keeps_cooldowns_and_failure_backoff():
    from ingest.registry_sources import source_due

    now = datetime(2026, 10, 25, 18, tzinfo=UTC)
    config = {"id": "employer_test", "refresh_hours": 24}
    health = {"last_attempt_at": (now - timedelta(hours=1)).isoformat()}
    assert not source_due(config, health, now)
    assert source_due(config, health, now, refresh=True)
    assert not source_due(
        config,
        {**health, "next_allowed_at": (now + timedelta(minutes=5)).isoformat()},
        now,
        refresh=True,
    )
    assert not source_due(config, {**health, "consecutive_failures": 1}, now, refresh=True)


def test_refresh_is_restricted_to_one_active_employer(tmp_path):
    from ingest.main import run_ingestion

    for selected in ([], ["myjobmag"], ["employer_not_active"], None):
        with pytest.raises(ValueError, match="one explicitly selected active employer"):
            run_ingestion(tmp_path, source_ids=selected, refresh_employer=True)


def test_explicit_refresh_publishes_reviewed_baseline_without_changing_health_history(
    tmp_path, monkeypatch
):
    import ingest.main as pipeline

    now = datetime.now(UTC)
    config = {
        "id": "employer_test",
        "status": "active",
        "refresh_hours": 24,
        "reviewed_bootstrap": True,
        "crawl": {"max_pages": 1},
    }

    class Collector:
        crawl_complete = True

        def fetch(self):
            return [raw()]

    monkeypatch.setattr(
        pipeline,
        "active_factories",
        lambda *a: ({"employer_test": Collector}, {"employer_test": config}),
    )
    old_attempt = (now - timedelta(minutes=30)).isoformat()
    _write_json(
        tmp_path / "state/health.json",
        {"sources": {"employer_test": {"last_attempt_at": old_attempt, "consecutive_failures": 0}}},
    )
    ledger = EmployerLedger(tmp_path / "state/employer-candidates.json")
    ledger.observe(
        "employer_test",
        [raw()],
        [canonicalize_raw_job(raw())],
        now - timedelta(minutes=30),
        complete=True,
    )
    ledger.save(_write_json)
    assert pipeline.run_ingestion(tmp_path, source_ids=["employer_test"]) == {}
    unchanged = json.loads((tmp_path / "state/health.json").read_text())
    assert unchanged["sources"]["employer_test"]["last_attempt_at"] == old_attempt
    result = pipeline.run_ingestion(tmp_path, source_ids=["employer_test"], refresh_employer=True)
    assert result["employer_test"].status == "SUCCESS"
    public = json.loads((tmp_path / "public/jobs.json").read_text())
    assert [job["job_id"] for job in public["jobs"]] == ["employer_test:one"]
