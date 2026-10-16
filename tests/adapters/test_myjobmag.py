from datetime import date
from pathlib import Path

from ingest.adapters.myjobmag import (
    LISTING_URL,
    MyJobMagAdapter,
    _company_from_title,
    parse_myjobmag_feed,
    parse_myjobmag_listing_page,
)

FIXTURE = Path("tests/fixtures/m0/myjobmag_detailed_feed.xml")


def test_detailed_feed_keeps_minimal_job_fields_only():
    jobs = parse_myjobmag_feed(FIXTURE.read_bytes())

    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_id == "1346068"
    assert job.company == "CDL Human Resource"
    assert job.title.startswith("Domestic Assistant")
    assert str(job.apply_url) == "https://www.myjobmag.co.ke/a_fields.php?id=1346068"


class _Response:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _PaginatedClient:
    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def get(self, url: str, *, timeout: float) -> _Response:
        self.calls.append(url)
        return _Response(self.pages[url])


def _listing(
    title: str,
    slug: str,
    company: str,
    location: str,
    posted_date: str = "28 September",
) -> str:
    return f'''<li class="job-list-li"><ul>
      <li class="job-logo"><img alt="{company} logo"></li>
      <li class="job-info"><h2><a href="/job/{slug}">{title}</a></h2>
        <li class="job-desc">This description must never be retained.</li>
        <li id="job-date">{posted_date}
          <a href="/jobs-location/{location.lower()}">{location}</a>
        </li>
      </li></ul></li>'''


def test_listing_page_keeps_only_minimal_card_metadata_and_page_links() -> None:
    html = _listing("Platform Engineer", "platform-engineer", "Example Co", "Nairobi") + (
        '<ul class="setPaginate"><li><a '
        'href="/jobs-by-field/information-technology/2">2</a></li></ul>'
    )

    jobs, links = parse_myjobmag_listing_page(
        html, "https://www.myjobmag.co.ke/jobs-by-field/information-technology"
    )

    assert len(jobs) == 1
    assert jobs[0].external_id == "/job/platform-engineer"
    assert jobs[0].company == "Example Co"
    assert jobs[0].location == "Nairobi"
    assert jobs[0].published_at is None  # Source category cards do not publish a time.
    assert jobs[0].published_date is not None
    assert "description" not in jobs[0].model_dump()
    assert links == {"https://www.myjobmag.co.ke/jobs-by-field/information-technology/2"}


def test_recovers_company_from_explicit_title_when_the_card_omits_it() -> None:
    title = "Full Stack Developer at Brookfox Technologies Ltd"

    jobs, _ = parse_myjobmag_listing_page(
        _listing(title, "full-stack-developer-19", "", "Nairobi"),
        "https://www.myjobmag.co.ke/jobs-by-field/information-technology",
    )

    assert _company_from_title(title) == "Brookfox Technologies Ltd"
    assert jobs[0].company == "Brookfox Technologies Ltd"


def test_fetch_follows_discovered_pagination_without_guessing_urls() -> None:
    root = "https://www.myjobmag.co.ke/jobs-by-field/information-technology"
    page_two = f"{root}/2"
    pages = {
        root: _listing("First role", "first-role", "First Co", "Nairobi")
        + '<a href="/jobs-by-field/information-technology/2">2</a>',
        page_two: _listing("Second role", "second-role", "Second Co", "Mombasa"),
    }

    jobs = MyJobMagAdapter(
        client=_PaginatedClient(pages), listing_url=root, request_delay_seconds=0
    ).fetch()

    assert [job.external_id for job in jobs] == ["/job/first-role", "/job/second-role"]


def test_fetch_keeps_last_thirty_days_and_stops_after_an_older_page() -> None:
    root = "https://www.myjobmag.co.ke/jobs-by-field/information-technology"
    page_two = f"{root}/2"
    page_three = f"{root}/3"
    client = _PaginatedClient(
        {
            root: _listing("Recent role", "recent", "Example", "Nairobi")
            + '<a href="/jobs-by-field/information-technology/2">2</a>',
            page_two: _listing("Old role", "old", "Example", "Nairobi", posted_date="20 August")
            + '<a href="/jobs-by-field/information-technology/3">3</a>',
            page_three: _listing("Must not fetch", "never", "Example", "Nairobi"),
        }
    )

    jobs = MyJobMagAdapter(
        client=client,
        listing_url=root,
        request_delay_seconds=0,
        today=date(2026, 9, 28),
    ).fetch()

    assert [job.external_id for job in jobs] == ["/job/recent"]
    assert client.calls == [root, page_two]


def test_early_warning_requires_own_geospatial_development_evidence():
    from ingest.adapters.myjobmag import detail_technical_context
    from ingest.main import build_jobs

    body = "Geospatial application development using Python and PostGIS."
    title = "Early Warning Expert at IGAD"
    assert detail_technical_context(title, f"<aside>{body}</aside>") is None
    assert (
        detail_technical_context(title, '<div class="job-details">Monitor conflicts.</div>') is None
    )
    context = detail_technical_context(title, f'<div class="job-details">{body}</div>')
    jobs, _ = parse_myjobmag_listing_page(
        _listing(title, "early-warning", "IGAD", "Nairobi"), LISTING_URL
    )
    job = jobs[0].model_copy(update={"technical_context": context})
    assert "technical_context" not in job.model_dump()
    canonical = build_jobs([job])[0]
    assert canonical.category == "Data Engineering"
    assert canonical.category_source == "description_rule"
    assert body not in canonical.model_dump_json()


def test_multi_location_text_does_not_destroy_the_publication_date():
    from ingest.adapters.myjobmag import _ListingPageParser

    html = _listing("Network Engineer", "network", "Example", "Nairobi", "16 October")
    html = html.replace("Nairobi</a>", "Nairobi</a> and 1 other locations")
    parser = _ListingPageParser(LISTING_URL, today=date(2026, 10, 16))
    parser.feed(html)
    assert parser.jobs[0].published_date == date(2026, 10, 16)


def test_ambiguous_roles_require_technical_duties_in_their_own_detail_container():
    from ingest.adapters.myjobmag import detail_technical_context
    from ingest.main import build_jobs

    examples = [
        ("Engineer Service Delivery", "Routing and switching on a fiber network.", "Networking"),
        (
            "Senior Product Analyst, DELTA",
            "Live systems need platform testing.",
            "Application Support",
        ),
        (
            "Head of Payments and Platform",
            "Write product specifications for our API.",
            "Technical Product",
        ),
        (
            "Digital Health Systems Strengthening Officers",
            "Technical support for systems and applications.",
            "Technical Support",
        ),
    ]
    for title, evidence, category in examples:
        assert detail_technical_context(title, f"<aside>{evidence}</aside>") is None
        assert (
            detail_technical_context(title, '<div class="job-details">Office work.</div>') is None
        )
        for tag in ("script", "style", "aside"):
            assert (
                detail_technical_context(
                    title, f'<div class="job-details"><{tag}>{evidence}</{tag}></div>'
                )
                is None
            )
        context = detail_technical_context(title, f'<div class="job-details">{evidence}</div>')
        raw = parse_myjobmag_listing_page(
            _listing(title, "test-job", "Example", "Nairobi"), LISTING_URL
        )[0][0].model_copy(update={"technical_context": context})
        canonical = build_jobs([raw])[0]
        assert canonical.category == category
        assert canonical.category_source == "description_rule"
        assert "technical_context" not in raw.model_dump()
        assert evidence not in canonical.model_dump_json()


def test_fetch_collects_scoped_detail_evidence_without_fetching_every_job():
    title = "Engineer Service Delivery"
    detail_url = "https://www.myjobmag.co.ke/job/service-delivery"
    client = _PaginatedClient(
        {
            LISTING_URL: _listing(title, "service-delivery", "Example", "Nairobi")
            + _listing("Accounts Assistant", "accounts", "Example", "Nairobi"),
            detail_url: '<div class="job-details">Routing and switching on a fiber network.</div>',
        }
    )
    jobs = MyJobMagAdapter(client=client, request_delay_seconds=0).fetch()
    assert client.calls == [LISTING_URL, detail_url]
    assert jobs[0].technical_context == "network_service_delivery"
    assert jobs[1].technical_context is None
