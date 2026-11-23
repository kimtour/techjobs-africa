import json

import httpx
import pytest

from ingest.adapters.jobicy import JobicyAdapter
from ingest.adapters.jobicy import parse_job as jobicy_job
from ingest.adapters.remoteok import RemoteOKAdapter
from ingest.adapters.remoteok import parse_job as remoteok_job
from ingest.main import build_jobs, run_ingestion


def jobicy(**updates):
    return {
        "id": 123,
        "url": "https://jobicy.com/jobs/123-software-engineer?u=test",
        "jobTitle": "Software Engineer",
        "companyName": "Example",
        "jobGeo": "Anywhere",
        "pubDate": "2026-11-22T12:00:00+00:00",
        "jobType": ["Full-Time"],
        "jobDescription": "PRIVATE_DESCRIPTION_SENTINEL",
        **updates,
    }


def remoteok(**updates):
    return {
        "id": "456",
        "url": "https://remoteOK.com/remote-jobs/remote-software-engineer-example-456",
        "position": "Software Engineer",
        "company": "Example",
        "location": "Worldwide",
        "date": "2026-11-22T12:00:00+00:00",
        "description": "PRIVATE_DESCRIPTION_SENTINEL",
        **updates,
    }


def page(jobs, cursor=None):
    return {
        "jobs": jobs,
        "jobCount": len(jobs),
        "nextCursor": cursor,
        "hasMore": bool(cursor),
        "success": True,
    }


def make_adapter(cls, handler):
    a = cls(httpx.Client(transport=httpx.MockTransport(handler)))
    if isinstance(a, JobicyAdapter):
        a.request_delay_seconds = a.initial_delay_seconds = 0
    return a


@pytest.mark.parametrize(
    "record,parse,source", [(jobicy, jobicy_job, "jobicy"), (remoteok, remoteok_job, "remoteok")]
)
def test_identity_links_dates_eligibility_and_no_description(record, parse, source):
    raw = parse(record())
    job = build_jobs([raw])[0]
    changed = (
        record(jobTitle="Senior Software Engineer")
        if source == "jobicy"
        else record(position="Senior Software Engineer")
    )
    assert build_jobs([parse(changed)])[0].job_id == job.job_id
    assert str(raw.apply_url) == str(job.preferred_apply_url)
    assert job.job_id == source + ":" + str(record()["id"])
    assert job.published_at.isoformat() == "2026-11-22T12:00:00+00:00"
    assert job.eligibility_level == "CONFIRMED" and job.region == "Worldwide"
    assert "PRIVATE_DESCRIPTION_SENTINEL" not in raw.model_dump_json() + job.model_dump_json()
    nontech = record(jobTitle="HR Manager") if source == "jobicy" else record(position="HR Manager")
    assert not build_jobs([parse(nontech)])


@pytest.mark.parametrize(
    "geo,accepted",
    [
        ("Anywhere", True),
        ("Worldwide", True),
        ("Africa", True),
        ("Kenya", True),
        ("Kenya, USA", True),
        ("EMEA", False),
        ("EMEA, USA", False),
        ("Europe", False),
        ("US Only", False),
        ("", False),
        (None, False),
        ("Worldwide except Africa", False),
    ],
)
def test_explicit_geographic_admission(geo, accepted):
    assert bool(jobicy_job(jobicy(jobGeo=geo))) == accepted
    assert bool(remoteok_job(remoteok(location=geo))) == accepted


@pytest.mark.parametrize("parse,record", [(jobicy_job, jobicy), (remoteok_job, remoteok)])
@pytest.mark.parametrize(
    "updates",
    [
        {"id": True},
        {"id": "../123"},
        {"id": 0},
        {"url": "https://evil.example/jobs/123"},
        {"url": "https://jobicy.com@evil.example/jobs/123"},
    ],
)
def test_malformed_identity_or_unsafe_link_rejected(parse, record, updates):
    with pytest.raises(ValueError):
        parse(record(**updates))


def test_remoteok_metadata_and_duplicate_validation():
    metadata = {"legal": "Credit Remote OK", "last_updated": 123}
    for payload in [[], {}, [remoteok()], [metadata, remoteok(), remoteok()]]:
        a = make_adapter(RemoteOKAdapter, lambda request: httpx.Response(200, json=payload))
        with pytest.raises(ValueError):
            a.fetch()
        assert not a.crawl_complete
    a = make_adapter(
        RemoteOKAdapter, lambda request: httpx.Response(200, json=[metadata, remoteok()])
    )
    assert len(a.fetch()) == 1 and a.crawl_complete


def test_jobicy_cursor_traversal_and_request_parameters():
    calls = []

    def handler(request):
        calls.append(dict(request.url.params))
        return httpx.Response(
            200,
            json=page(
                [jobicy(id=124, url="https://jobicy.com/jobs/124-engineer")]
                if request.url.params.get("cursor")
                else [jobicy()],
                None if request.url.params.get("cursor") else "opaque+/=",
            ),
        )

    a = make_adapter(JobicyAdapter, handler)
    assert len(a.fetch()) == 2 and a.crawl_complete
    assert calls == [{"count": "100"}, {"count": "100", "cursor": "opaque+/="}]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {**page([]), "success": False},
        {**page([]), "hasMore": True},
        {**page([jobicy()]), "jobCount": 0},
        {**page([]), "nextCursor": "unexpected"},
    ],
)
def test_jobicy_invalid_pagination(payload):
    a = make_adapter(JobicyAdapter, lambda request: httpx.Response(200, json=payload))
    with pytest.raises(ValueError):
        a.fetch()
    assert not a.crawl_complete


def test_jobicy_repeated_page_and_page_budget_fail_safely():
    a = make_adapter(
        JobicyAdapter, lambda request: httpx.Response(200, json=page([jobicy()], "repeat"))
    )
    with pytest.raises(ValueError):
        a.fetch()
    a.max_pages = 1
    with pytest.raises(ValueError):
        a.fetch()
    assert not a.crawl_complete


@pytest.mark.parametrize(
    "result,retained",
    [
        ("closed", False),
        ("active", True),
        ("unknown", True),
        (403, True),
        (404, True),
        (429, True),
        (503, True),
        ("missing", True),
    ],
)
def test_jobicy_real_pipeline_closes_only_explicit_closed(tmp_path, monkeypatch, result, retained):
    monkeypatch.setattr("ingest.fetch.time.sleep", lambda _: None)
    monkeypatch.setattr("ingest.adapters.jobicy.sleep", lambda _: None)

    def initial():
        return make_adapter(
            JobicyAdapter, lambda request: httpx.Response(200, json=page([jobicy()]))
        )

    run_ingestion(tmp_path, source_ids=["jobicy"], adapters={"jobicy": initial})
    saved_path = tmp_path / "canonical/jobs.json"
    saved = json.loads(saved_path.read_text())
    saved["jobs"].append(
        {
            **saved["jobs"][0],
            "job_id": "elevolt:other",
            "sources": ["elevolt"],
            "preferred_apply_url": "https://example.com/other",
        }
    )
    saved_path.write_text(json.dumps(saved))
    (tmp_path / "public/jobs.json").write_text(json.dumps(saved))

    def handler(request):
        if request.url.path == "/api/jobs":
            return httpx.Response(200, json=page([]))
        assert request.url.path == "/api/jobs/status" and request.url.params["ids"] == "123"
        if isinstance(result, int):
            return httpx.Response(result, headers={"Retry-After": "60"})
        return httpx.Response(
            200,
            json={
                "success": True,
                "count": 0 if result == "missing" else 1,
                "jobs": [] if result == "missing" else [{"id": 123, "status": result}],
            },
        )

    health = run_ingestion(
        tmp_path,
        source_ids=["jobicy"],
        adapters={"jobicy": lambda: make_adapter(JobicyAdapter, handler)},
    )
    jobs = json.loads((tmp_path / "public/jobs.json").read_text())["jobs"]
    assert any(j["job_id"] == "jobicy:123" for j in jobs) == retained
    assert any(j["job_id"] == "elevolt:other" for j in jobs)
    assert not health["jobicy"].safe_to_process_absences
    for path in tmp_path.rglob("*.json*"):
        assert "PRIVATE_DESCRIPTION_SENTINEL" not in path.read_text()


@pytest.mark.parametrize("status", [403, 404, 429, 503, 200])
def test_remoteok_failed_or_empty_refresh_retains_jobs(tmp_path, monkeypatch, status):
    monkeypatch.setattr("ingest.fetch.time.sleep", lambda _: None)
    metadata = {"legal": "Credit Remote OK", "last_updated": 123}

    def factory():
        return make_adapter(
            RemoteOKAdapter, lambda request: httpx.Response(200, json=[metadata, remoteok()])
        )

    run_ingestion(tmp_path, source_ids=["remoteok"], adapters={"remoteok": factory})

    def failed():
        return make_adapter(
            RemoteOKAdapter, lambda request: httpx.Response(status, json=[metadata])
        )

    health = run_ingestion(tmp_path, source_ids=["remoteok"], adapters={"remoteok": failed})
    jobs = json.loads((tmp_path / "public/jobs.json").read_text())["jobs"]
    assert len(jobs) == 1 and jobs[0]["job_id"] == "remoteok:456"
    assert not health["remoteok"].safe_to_process_absences
