import json
from datetime import UTC, datetime

import httpx
import pytest

from ingest.adapters.expertini import ExpertiniSitemapAdapter, parse_listing_link
from ingest.main import run_ingestion
from ingest.normalize.canonicalize import canonicalize_raw_job

HOST = "https://ke.expertini.com"
JOB = (
    "https://nairobi.ke.expertini.com/job/senior-backend-engineer-nairobi-umba-636490169546311236/"
)
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def index(urls=None):
    urls = urls or [f"{HOST}/job_listing1.xml"]
    return (
        f'<sitemapindex xmlns="{NS}">'
        + "".join(f"<sitemap><loc>{u}</loc></sitemap>" for u in urls)
        + "</sitemapindex>"
    )


def listing(urls=None):
    return (
        f'<urlset xmlns="{NS}">'
        + "".join(
            f"<url><loc>{u}</loc><lastmod>{datetime.now(UTC).isoformat()}</lastmod></url>"
            for u in urls or [JOB]
        )
        + "</urlset>"
    )


def test_native_identity_survives_changed_slug_and_dates_remain_unknown():
    first = parse_listing_link(JOB)
    changed = parse_listing_link(
        JOB.replace("senior-backend-engineer", "principal-backend-engineer")
    )
    assert first.external_id == changed.external_id == "636490169546311236"
    assert first.title == "Senior Backend Engineer"
    assert first.company is None
    assert first.published_at is None and first.published_date is None
    assert str(first.apply_url) == JOB
    assert canonicalize_raw_job(first).country_code == "KE"


@pytest.mark.parametrize(
    "url",
    [
        JOB.replace("https:", "http:"),
        JOB.replace("nairobi.ke.expertini.com", "ke.expertini.com.evil.example"),
        JOB.replace("nairobi.ke.expertini.com", "nairobi.ng.expertini.com"),
        JOB.replace("636490169546311236", "missing-id"),
        JOB + "?token=secret",
        JOB.replace("nairobi-umba", "company-only"),
        JOB.replace("senior-backend-engineer", "hr-officer"),
        JOB.replace("senior-backend-engineer", "quality-assurance-flower-packhouse"),
        JOB.replace("senior-backend-engineer", "project-manager-construction"),
        JOB.replace("senior-backend-engineer", "project-manager"),
        JOB.replace("senior-backend-engineer", "volunteer-worker-attachment"),
        JOB.replace(
            "senior-backend-engineer-nairobi-umba", "account-manager-nairobi-software-engineer"
        ),
    ],
)
def test_untrusted_or_nontechnical_listing_labels_are_rejected(url):
    assert parse_listing_link(url) is None


def test_advertised_xml_pagination_deduplication_and_no_date_invention():
    calls = []

    def respond(request):
        calls.append(str(request.url))
        content = index([f"{HOST}/job_listing1.xml", f"{HOST}/job_listing2.xml"])
        if request.url.path.endswith("feed.xml"):
            content = "<rss><channel/></rss>"
        if "job_listing" in request.url.path:
            content = listing(
                [JOB, JOB.replace("senior-backend-engineer", "principal-backend-engineer")]
            )
        return httpx.Response(200, text=content)

    adapter = ExpertiniSitemapAdapter(httpx.Client(transport=httpx.MockTransport(respond)))
    jobs = adapter.fetch()
    assert len(calls) == 4 and len(jobs) == 1
    assert adapter.crawl_complete
    assert jobs[0].published_at is None and jobs[0].published_date is None
    assert "description" not in jobs[0].model_dump()


@pytest.mark.parametrize(
    "payload",
    [
        "<html>Verification</html>",
        "broken XML",
        index(["https://evil.example/internal.xml"]),
        listing(),
    ],
)
def test_malformed_challenge_or_foreign_index_never_reports_success(payload):
    adapter = ExpertiniSitemapAdapter(
        httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text=payload)))
    )
    with pytest.raises(Exception):
        adapter.fetch()
    assert not adapter.crawl_complete


@pytest.mark.parametrize("code", [403, 429, 500])
def test_blocked_refresh_preserves_prior_jobs(tmp_path, code):
    old = canonicalize_raw_job(parse_listing_link(JOB))
    (tmp_path / "canonical").mkdir()
    (tmp_path / "canonical/jobs.json").write_text(
        json.dumps({"jobs": [old.model_dump(mode="json")]})
    )
    adapter = ExpertiniSitemapAdapter(
        httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(code)))
    )
    run_ingestion(tmp_path, source_ids=["expertini"], adapters={"expertini": lambda: adapter})
    jobs = json.loads((tmp_path / "canonical/jobs.json").read_text())["jobs"]
    assert jobs[0]["job_id"] == old.job_id and jobs[0]["status"] == "ACTIVE"


def test_bounded_sitemap_window_is_partial():
    def respond(request):
        if request.url.path.endswith("feed.xml"):
            return httpx.Response(200, text="<rss><channel/></rss>")
        return httpx.Response(
            200,
            text=index([f"{HOST}/job_listing1.xml", f"{HOST}/job_listing2.xml"])
            if request.url.path.endswith("sitemapindex.xml")
            else listing(),
        )

    adapter = ExpertiniSitemapAdapter(httpx.Client(transport=httpx.MockTransport(respond)))
    adapter.max_pages = 1
    assert len(adapter.fetch()) == 1
    assert not adapter.crawl_complete


def test_rss_metadata_overrides_url_label_for_same_native_id_without_descriptions():
    rss = """<rss><channel><item>
    <title>Senior Backend Engineer (AI)</title>
    <link>https://ke.expertini.com/jobs/job/senior-backend-engineer-nairobi-umba-636490169546311236/</link>
    <pubDate>Thu, 01 Oct 2026 04:45:06 +0100</pubDate>
    <description>NEVER STORE THIS DESCRIPTION</description>
    </item></channel></rss>"""

    def respond(request):
        if request.url.path.endswith("feed.xml"):
            return httpx.Response(200, text=rss)
        return httpx.Response(
            200, text=index() if "sitemapindex" in request.url.path else listing()
        )

    adapter = ExpertiniSitemapAdapter(httpx.Client(transport=httpx.MockTransport(respond)))
    jobs = adapter.fetch()
    assert len(jobs) == 1
    assert jobs[0].external_id == "636490169546311236"
    assert jobs[0].title == "Senior Backend Engineer (AI)"
    assert jobs[0].source_publisher == "Expertini RSS"
    assert jobs[0].published_at == datetime(2026, 10, 1, 3, 45, 6, tzinfo=UTC)
    assert "DESCRIPTION" not in json.dumps([j.model_dump(mode="json") for j in jobs])


@pytest.mark.parametrize(
    "native_id", ["3597-2032", "26f571cadf4942d39f9874579a67b7da105", "636490169546311236"]
)
def test_rss_ids_are_native_and_missing_or_bad_dates_stay_unknown(native_id):
    from xml.etree import ElementTree

    from ingest.adapters.expertini import parse_rss_item

    item = ElementTree.fromstring(f"""<item><title>Software Engineer</title>
        <link>https://ke.expertini.com/jobs/job/software-engineer-kenya-example-{native_id}/</link>
        <pubDate>not a date</pubDate></item>""")
    job = parse_rss_item(item)
    assert job.external_id == native_id
    assert job.company is None
    assert job.published_at is None


def test_refresh_keeps_other_source_attributions_while_updating_real_metadata(tmp_path):
    old = canonicalize_raw_job(parse_listing_link(JOB))
    old.sources = ["expertini", "jsearch"]
    (tmp_path / "canonical").mkdir()
    (tmp_path / "canonical/jobs.json").write_text(
        json.dumps({"jobs": [old.model_dump(mode="json")]})
    )

    class Adapter:
        crawl_complete = True

        def fetch(self):
            return [
                parse_listing_link(
                    JOB.replace("senior-backend-engineer", "principal-backend-engineer")
                )
            ]

    run_ingestion(tmp_path, source_ids=["expertini"], adapters={"expertini": Adapter})
    jobs = json.loads((tmp_path / "public/jobs.json").read_text())["jobs"]
    assert jobs[0]["job_id"] == old.job_id
    assert set(jobs[0]["sources"]) == {"expertini", "jsearch"}
    assert jobs[0]["title"] == "Principal Backend Engineer"
