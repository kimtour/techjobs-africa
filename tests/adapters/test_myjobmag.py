from datetime import date
from pathlib import Path

from ingest.adapters.myjobmag import (
    MyJobMagAdapter,
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
    assert "description" not in jobs[0].model_dump()
    assert links == {"https://www.myjobmag.co.ke/jobs-by-field/information-technology/2"}


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
            page_two: _listing(
                "Old role", "old", "Example", "Nairobi", posted_date="20 August"
            )
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
