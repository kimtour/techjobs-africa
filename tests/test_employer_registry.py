import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

import httpx
import pytest
import yaml

from ingest.adapters.registry_boards import RegistryBoardAdapter
from ingest.dedupe.exact import deduplicate_exact
from ingest.employer_onboarding import discover, trial
from ingest.employer_registry import import_workbook, platform_for, portal_url, public_registry
from ingest.main import build_jobs
from ingest.registry_sources import CHECKS, active_factories, source_due, verification_gaps


def xlsx(path, sheets):
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{ns}" xmlns:r="{rel}"><sheets>'
            + "".join(
                f'<sheet name="{name}" sheetId="{i}" r:id="r{i}"/>'
                for i, name in enumerate(sheets, 1)
            )
            + "</sheets></workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            "<Relationships>"
            + "".join(
                f'<Relationship Id="r{i}" Target="worksheets/sheet{i}.xml"/>'
                for i in range(1, len(sheets) + 1)
            )
            + "</Relationships>",
        )
        for i, rows in enumerate(sheets.values(), 1):
            content = ""
            for number, values in enumerate(rows, 7):
                cells = "".join(
                    f'<c r="{column}{number}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
                    for column, value in zip("ABCDE", values, strict=True)
                )
                content += f'<row r="{number}">{cells}</row>'
            archive.writestr(
                f"xl/worksheets/sheet{i}.xml",
                f'<worksheet xmlns="{ns}"><sheetData>{content}</sheetData></worksheet>',
            )


def save_registry(root, employers, sources):
    root.mkdir(exist_ok=True)
    (root / "employers.yaml").write_text(yaml.safe_dump(employers))
    (root / "employer-sources.yaml").write_text(yaml.safe_dump(sources))


def test_import_preserves_shared_boards_distinct_employers_and_reviewed_edits(tmp_path):
    path = tmp_path / "directory.xlsx"
    first = (
        "First Employer",
        "Banking",
        "https://first.example/",
        "https://jobs.lever.co/group?country=KE&utm_source=sheet",
        "A caveat",
    )
    second = (
        "Second Employer",
        "Insurance",
        "https://second.example/",
        "https://jobs.lever.co/group?country=KE",
        "Shared board, different employer",
    )
    xlsx(
        path, {"Banks": [first, second], "Energy": [first], "Ministries and departments": [second]}
    )
    employers, sources = import_workbook(
        path, tmp_path, exclude_sheets=["Ministries and departments"]
    )
    assert employers["import"]["directory_entries"] == 3
    assert len(employers["employers"]) == 2
    assert len(sources["sources"]) == 1
    assert len(sources["sources"][0]["employer_ids"]) == 2
    original_ids = [e["id"] for e in employers["employers"]]
    employers["employers"][0]["name"] = "Reviewed name"
    employers["employers"][0]["aliases"] = ["Original name"]
    sources["sources"][0]["status"] = "verified"
    sources["sources"][0]["verification"] = {"collection_review": True}
    save_registry(tmp_path, employers, sources)
    again, again_sources = import_workbook(
        path, tmp_path, exclude_sheets=["Ministries and departments"]
    )
    assert again == employers
    assert again_sources == sources
    assert [e["id"] for e in again["employers"]] == original_ids
    exported = json.dumps(public_registry(again, again_sources))
    assert "A caveat" not in exported and "import_keys" not in exported
    assert all(
        r["sheet"] != "Ministries and departments"
        for e in again["employers"]
        for r in e["references"]
    )


def test_url_normalization_keeps_functional_parameters_and_rejects_unsafe_urls():
    assert portal_url("https://jobs.example/board?country=KE&job=1&utm_campaign=x") == (
        "https://jobs.example/board?country=KE&job=1"
    )
    for url in ["javascript:alert(1)", "https://user:secret@example.com", "file:///tmp/jobs"]:
        with pytest.raises(ValueError):
            portal_url(url)
    assert platform_for("https://jobs.lever.co.evil.example/board") == "custom"


def board(platform="ashby"):
    return {
        "id": "employer_test",
        "platform": platform,
        "board": "Example-Board",
        "url": "https://jobs.ashbyhq.com/Example-Board",
        "status": "trial",
        "employer_ids": ["example"],
        "refresh_hours": 24,
        "supports_absence_expiry": False,
        "official_careers_url": "https://example.com/careers",
        "crawl": {
            "max_pages": 2,
            "max_requests_per_run": 8,
            "request_delay_ms": 0,
            "retry_delays_seconds": [],
            "timeout_seconds": 2,
        },
        "verification": {
            **dict.fromkeys(CHECKS, True),
            "collection_basis": "Reviewed test fixture",
            "evidence_paths": ["local.json", "runner.json"],
        },
    }


EMPLOYERS = {"example": {"id": "example", "name": "Example", "sectors": ["Banking"]}}


def payload():
    return {
        "jobs": [
            {
                "id": "immutable-1",
                "isListed": True,
                "title": "Software Engineer",
                "location": "Nairobi, Kenya",
                "jobUrl": "https://jobs.example/immutable-1",
                "applyUrl": "https://jobs.example/apply/immutable-1",
                "descriptionPlain": "SECRET_DESCRIPTION",
                "employmentType": "FullTime",
            }
        ]
    }


def test_adapter_identity_empty_shape_and_description_exclusion():
    data = payload()
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=data)))
    adapter = RegistryBoardAdapter(board(), EMPLOYERS, client)
    raw = adapter.fetch()
    assert adapter.crawl_complete and raw[0].source_id == "employer_test"
    assert raw[0].employer_id == "example"
    assert "SECRET_DESCRIPTION" not in raw[0].model_dump_json()
    data["jobs"][0]["title"] = "Talent pool"
    assert adapter.fetch() == []
    data["jobs"] = []
    assert adapter.fetch() == [] and adapter.crawl_complete
    del data["jobs"]
    with pytest.raises(ValueError):
        adapter.fetch()
    assert not adapter.crawl_complete


def test_trial_does_not_write_production_state_or_publish_unverified_sources(tmp_path):
    accepted = tmp_path / "production.json"
    accepted.write_text('{"schema_version":1,"jobs":[]}')
    before = accepted.read_bytes()
    factories = []

    def factory(source, employers):
        factories.append(source["id"])
        return RegistryBoardAdapter(
            source,
            employers,
            httpx.Client(
                transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload()))
            ),
        )

    unverified = {**board(), "id": "unverified", "verification": {}}
    report = trial(
        [board(), unverified], EMPLOYERS, tmp_path / "trial", accepted=accepted, factory=factory
    )
    assert accepted.read_bytes() == before
    assert report["candidate_jobs"] == report["additional_unique_jobs"] == 1
    assert factories == ["employer_test"]
    assert report["sources"][1]["status"] == "NOT_VERIFIED"
    assert not (tmp_path / "trial/state").exists()
    assert "SECRET_DESCRIPTION" not in "".join(
        p.read_text() for p in (tmp_path / "trial").rglob("*.json")
    )
    with pytest.raises(ValueError):
        trial([board()], EMPLOYERS, tmp_path / "trial", factory=factory)


def test_activation_requires_evidence_and_due_policy_respects_backoff(tmp_path):
    source = board()
    source["status"] = "active"
    source["verification"] = {}
    save_registry(tmp_path, {"employers": list(EMPLOYERS.values())}, {"sources": [source]})
    with pytest.raises(ValueError):
        active_factories(tmp_path)
    assert verification_gaps(source)
    now = datetime(2026, 10, 25, 16, tzinfo=UTC)
    assert source_due(source, {}, now)
    health = {"last_attempt_at": (now - timedelta(hours=25)).isoformat(), "consecutive_failures": 1}
    assert not source_due(source, health, now)
    health["consecutive_failures"] = 0
    assert source_due(source, health, now)
    health["next_allowed_at"] = (now + timedelta(hours=1)).isoformat()
    assert not source_due(source, health, now)


def test_discovery_does_not_fetch_disallowed_page_or_change_lifecycle():
    requests = []

    def handler(req):
        requests.append(str(req.url))
        return httpx.Response(200, text="User-agent: *\nDisallow: /careers")

    source = board()
    report = discover(source, EMPLOYERS, httpx.Client(transport=httpx.MockTransport(handler)))
    assert report["status"] == "BLOCKED"
    assert requests == ["https://example.com/robots.txt"]
    assert source["status"] == "trial"


def test_repository_registry_excludes_ministries_and_activates_only_reviewed_sources():
    employers = yaml.safe_load(Path("config/employers.yaml").read_text())
    assert employers["import"]["directory_entries"] == 796
    assert employers["import"]["excluded_sheets"] == ["Ministries and departments"]
    factories, sources = active_factories()
    assert factories
    assert all(
        not verification_gaps(s)
        and s["verification"]["trial_review"]
        and s["verification"]["publication_review"]
        for s in sources.values()
    )


def test_exact_duplicate_bridge_keeps_identity_attribution_and_direct_metadata():
    adapter = RegistryBoardAdapter(
        board(),
        EMPLOYERS,
        httpx.Client(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload()))
        ),
    )
    direct = build_jobs(adapter.fetch())[0]
    first = direct.model_copy(
        update={
            "job_id": "aggregator:1",
            "sources": ["aggregator"],
            "direct_employer": False,
            "employer_id": None,
            "employer_sectors": [],
        }
    )
    second = direct.model_copy(
        update={
            "job_id": "other:2",
            "sources": ["other"],
            "preferred_apply_url": "https://jobs.example/second",
        }
    )
    bridge = direct.model_copy(
        update={"job_id": "aggregator:1", "preferred_apply_url": "https://jobs.example/second"}
    )
    merged = deduplicate_exact([first, second, bridge])
    assert len(merged) == 1
    assert merged[0].job_id == "aggregator:1"
    assert set(merged[0].sources) == {"aggregator", "other", "employer_test"}
    assert merged[0].direct_employer and merged[0].employer_id == "example"


def test_breezy_repeated_apply_link_keeps_title_and_skips_nontechnical_detail():
    requested = []
    listing = (
        '<a href="/p/sales-sales-executive"><h2>Sales Executive</h2></a>'
        '<a href="/p/sales-sales-executive">Apply</a>'
        '<a href="/p/tech-software-engineer"><h2>Software Engineer</h2></a>'
    )
    detail = (
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "JobPosting",
                "title": "Software Engineer",
                "description": "SECRET_DESCRIPTION",
                "jobLocation": {
                    "address": {"addressLocality": "Nairobi", "addressCountry": "Kenya"}
                },
                "employmentType": ["FULL_TIME"],
            }
        )
        + "</script>"
    )

    def handler(req):
        requested.append(req.url.path)
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        return httpx.Response(200, text=listing if req.url.path == "/" else detail)

    adapter = RegistryBoardAdapter(
        board("breezy"), EMPLOYERS, httpx.Client(transport=httpx.MockTransport(handler))
    )
    raw = adapter.fetch()
    assert adapter.crawl_complete and len(raw) == 2
    assert "/p/sales-sales-executive" not in requested
    assert len(build_jobs(raw)) == 1
    assert "SECRET_DESCRIPTION" not in "".join(r.model_dump_json() for r in raw)


@pytest.mark.parametrize("redirects", [True, False])
def test_official_redirect_proves_link_but_board_itself_does_not(monkeypatch, redirects):
    source = board()
    if not redirects:
        source["official_careers_url"] = source["url"]

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"Location": source["url"]})
        return httpx.Response(200, text="<html>Public careers board</html>")

    class EmptyAdapter:
        crawl_complete = True

        def __init__(self):
            self._client = httpx.Client()

        def fetch(self):
            return []

    monkeypatch.setattr("ingest.employer_onboarding.make_adapter", lambda *args: EmptyAdapter())
    report = discover(source, EMPLOYERS, httpx.Client(transport=httpx.MockTransport(handler)))
    assert report["status"] == "SUCCESS"
    assert report["checks"]["official_link"] is redirects
    assert source["status"] == "trial"


@pytest.mark.parametrize(
    "platform,empty_schema,expected",
    [("ashby", False, False), ("ashby", True, True), ("custom", True, False)],
)
def test_independent_board_check_requires_official_evidence_and_never_visits_employer(
    monkeypatch, platform, empty_schema, expected
):
    from ingest.employer_onboarding import verify_board_access

    source = board()
    source["platform"] = platform
    source["verified_empty_schema"] = empty_schema
    source["verification"]["local_access"] = False
    with pytest.raises(ValueError, match="reviewed official linkage"):
        verify_board_access(source, EMPLOYERS)
    source["verification"]["local_access"] = True

    class Adapter:
        crawl_complete = True

        def __init__(self):
            self._client = httpx.Client(transport=httpx.MockTransport(handler))

        def fetch(self):
            response = self._client.get("https://jobs.ashbyhq.com/Example-Board")
            response.raise_for_status()
            return []

    def handler(request):
        assert request.url.host == "jobs.ashbyhq.com"
        return httpx.Response(200)

    monkeypatch.setattr("ingest.employer_onboarding.make_adapter", lambda *args: Adapter())
    report = verify_board_access(source, EMPLOYERS)
    assert report["status"] == "SUCCESS"
    assert not report["official_link_checked_this_run"]
    assert report["checks"]["locations"] is expected
    assert report["prior_official_evidence"] == source["verification"]["evidence_paths"]
    assert "official_link" not in report["checks"]
    assert source["status"] == "trial"


def test_discovery_candidate_summary_ranks_real_roles_without_publication():
    from ingest.employer_onboarding import candidate_summary
    from ingest.models import RawJob

    records = [
        RawJob(
            source_id="example",
            external_id=str(i),
            title=title,
            location=location,
            source_url=f"https://example.com/jobs/{i}",
            apply_url=f"https://example.com/jobs/{i}",
        )
        for i, (title, location) in enumerate(
            [
                ("Software Engineer", "Nairobi, Kenya"),
                ("Software Engineer", "Seattle, United States"),
                ("Clinical Nurse", "Nairobi, Kenya"),
            ]
        )
    ]
    summary = candidate_summary(records)
    assert summary["technical_jobs"] == 2
    assert summary["eligible_jobs"] == 1
    assert summary["candidate_metadata"][0]["job_id"] == "example:0"
    assert summary["candidate_metadata"][0]["country"] == "Kenya"
    assert not summary["publication_approved"]
    assert candidate_summary([])["eligible_jobs"] == 0
    assert "description" not in json.dumps(summary)
