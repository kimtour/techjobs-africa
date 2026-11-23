import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from ingest.adapters.himalayas import API, HimalayasAdapter, parse_job
from ingest.main import build_jobs, run_ingestion
from ingest.models import SourceHealthStatus

NOW = datetime(2026, 11, 23, 9, tzinfo=UTC)
GUID = "https://himalayas.app/companies/example/jobs/software-engineer-123"


def record(**updates):
    return {
        "guid": GUID,
        "title": "Software Engineer",
        "companyName": "Example",
        "applicationLink": GUID + "?utm_source=api",
        "locationRestrictions": [],
        "timezoneRestrictions": [],
        "pubDate": NOW.timestamp() - 86400,
        "expiryDate": NOW.timestamp() + 86400 * 30,
        "employmentType": "Full Time",
        "description": "PRIVATE_DESCRIPTION_SENTINEL",
        **updates,
    }


def page(jobs, *, total=None, offset=0):
    return {
        "jobs": jobs,
        "totalCount": len(jobs) if total is None else total,
        "offset": offset,
        "limit": 20,
    }


def adapter(handler, **kwargs):
    a = HimalayasAdapter(httpx.Client(transport=httpx.MockTransport(handler)), now=NOW, **kwargs)
    a.request_delay_seconds = 0
    a.search_terms = ("software engineer",)
    return a


def test_identity_links_update_dates_and_description_minimization():
    raw = parse_job(record(), now=NOW)
    job = build_jobs([raw])[0]
    changed = build_jobs([parse_job(record(title="Senior Software Engineer"), now=NOW)])[0]
    assert job.job_id == changed.job_id == "himalayas:" + GUID
    assert str(job.preferred_apply_url) == record()["applicationLink"]
    assert job.published_at is None and job.source_updated_at == NOW - timedelta(days=1)
    assert job.deadline_at == NOW + timedelta(days=30)
    assert (job.region, job.workplace_type, job.eligibility_level) == (
        "Worldwide",
        "Remote",
        "CONFIRMED",
    )
    assert "PRIVATE_DESCRIPTION_SENTINEL" not in raw.model_dump_json() + job.model_dump_json()


@pytest.mark.parametrize(
    "countries,zones,accepted",
    [
        ([], [], True),
        (["Kenya"], [3], True),
        (["Kenya", "United States"], [2, 3], True),
        (["United States"], [], False),
        (["EMEA"], [3], False),
        ([], [-8, -7], False),
    ],
)
def test_country_and_timezone_restrictions(countries, zones, accepted):
    raw = parse_job(record(locationRestrictions=countries, timezoneRestrictions=zones), now=NOW)
    assert (raw is not None) == accepted
    if raw and countries:
        assert raw.location == "Remote · Kenya"


@pytest.mark.parametrize(
    "updates",
    [
        {"locationRestrictions": None},
        {"timezoneRestrictions": None},
        {"timezoneRestrictions": ["3"]},
        {"timezoneRestrictions": [True]},
        {"expiryDate": None},
        {"pubDate": "invalid"},
        {"guid": "https://evil.example/jobs/software-engineer"},
        {"applicationLink": "https://himalayas.app@evil.example/job"},
        {"applicationLink": "https://himalayas.app/companies/other/jobs/other"},
    ],
)
def test_unknown_metadata_or_unsafe_identity_fails_closed(updates):
    with pytest.raises(ValueError):
        parse_job(record(**updates), now=NOW)


def test_expired_and_nontech_records_do_not_publish():
    assert parse_job(record(expiryDate=NOW.timestamp()), now=NOW) is None
    assert build_jobs([parse_job(record(title="HR Manager"), now=NOW)]) == []


def test_pagination_deduplicates_searches_and_bounds_the_discovery_window():
    calls = []

    def handler(request):
        calls.append(dict(request.url.params))
        n = int(request.url.params["page"])
        jobs = [
            record(guid=GUID + f"-{i}", applicationLink=GUID + f"-{i}?utm_source=api")
            for i in range((n - 1) * 20, n * 20)
        ]
        return httpx.Response(200, json=page(jobs, total=321, offset=(n - 1) * 20))

    a = adapter(handler)
    a.search_terms = ("software", "engineer")
    jobs = a.fetch()
    assert len(jobs) == 40 and len(calls) == 4 and a.crawl_complete
    assert all(c["country"] == "KE" and c["sort"] == "recent" for c in calls)


@pytest.mark.parametrize(
    "payload",
    [{}, {"jobs": []}, page([], total=30), page([record()], total=30), page([record()], offset=20)],
)
def test_malformed_or_incomplete_search_does_not_claim_completion(payload):
    a = adapter(lambda request: httpx.Response(200, json=payload))
    with pytest.raises(ValueError):
        a.fetch()
    assert not a.crawl_complete


def test_empty_search_is_valid_and_never_implies_absence_closure():
    a = adapter(lambda request: httpx.Response(200, json=page([])))
    assert a.fetch() == [] and a.crawl_complete and not a.closed_job_ids


@pytest.mark.parametrize("status,expected", [(410, 0), (404, 1), (403, 1), (429, 1), (503, 1)])
def test_real_pipeline_status_checks_close_only_authoritative_closed_jobs(
    tmp_path, status, expected, monkeypatch
):
    # No waiting or network in this regression; the real observer and state writer run.
    monkeypatch.setattr("ingest.fetch.time.sleep", lambda _: None)
    monkeypatch.setattr("ingest.adapters.himalayas.sleep", lambda _: None)
    current = datetime.now(UTC)
    initial = record(pubDate=current.timestamp() - 30, expiryDate=current.timestamp() + 86400)
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=page([initial])))
    )

    def factory():
        a = HimalayasAdapter(client)
        a.search_terms = ("software engineer",)
        return a

    run_ingestion(tmp_path, source_ids=["himalayas"], adapters={"himalayas": factory})
    # Keep an unrelated provider in the snapshot so the independent total-drop
    # safety gate is not triggered by a one-job synthetic catalogue.
    saved_path = tmp_path / "canonical/jobs.json"
    saved = json.loads(saved_path.read_text())
    other = {
        **saved["jobs"][0],
        "job_id": "elevolt:other",
        "sources": ["elevolt"],
        "preferred_apply_url": "https://example.com/other",
        "deadline_at": None,
    }
    saved["jobs"].append(other)
    saved_path.write_text(json.dumps(saved))
    (tmp_path / "public/jobs.json").write_text(json.dumps(saved))

    def handler(request):
        if request.url.path == "/jobs/api/search":
            return httpx.Response(200, json=page([]))
        assert str(request.url) == API + "/companies/example/jobs/software-engineer-123"
        return httpx.Response(status, headers={"Retry-After": "60"} if status == 429 else {})

    def refreshed():
        a = adapter(handler)
        a.now = current
        return a

    health = run_ingestion(tmp_path, source_ids=["himalayas"], adapters={"himalayas": refreshed})
    jobs = json.loads((tmp_path / "public/jobs.json").read_text())["jobs"]
    assert len([job for job in jobs if "himalayas" in job["sources"]]) == expected
    assert any(job["job_id"] == "elevolt:other" for job in jobs)
    assert not health["himalayas"].safe_to_process_absences
    if status in {403, 429, 503}:
        assert health["himalayas"].status != SourceHealthStatus.SUCCESS
    for path in tmp_path.rglob("*.json*"):
        assert "PRIVATE_DESCRIPTION_SENTINEL" not in path.read_text()


def test_exact_dedupe_keeps_required_himalayas_apply_link():
    h = build_jobs([parse_job(record(), now=NOW)])[0]
    other = h.model_copy(
        update={"job_id": "other:123", "sources": ["other"], "preferred_apply_url": GUID}
    )
    from ingest.dedupe.exact import deduplicate_exact

    result = deduplicate_exact([other, h])
    assert len(result) == 1 and result[0].job_id == "other:123"
    assert str(result[0].preferred_apply_url) == record()["applicationLink"]
