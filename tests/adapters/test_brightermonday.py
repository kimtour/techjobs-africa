from datetime import date

from ingest.adapters.brightermonday import (
    BrighterMondayAdapter,
    _relative_listing_day,
    parse_brightermonday_listing_page,
)


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


def _listing(title: str, slug: str, company: str, location: str) -> str:
    return f'''<div data-cy="listing-cards-components"><div>
      <a data-cy="listing-title-link" href="/listings/{slug}" title="{title}"><p>{title}</p></a>
      <p class="text-sm text-blue-700 mt-3">{company}</p>
      <span class="bg-brand-secondary-100">{location}</span>
      <p>This description must never be retained.</p>
      <div class="ml-auto"><p>6 days ago</p></div>
    </div></div>'''


def test_listing_page_keeps_minimal_metadata_and_next_page_only() -> None:
    root = "https://www.brightermonday.co.ke/jobs/software-data"
    html = _listing("Software Developer", "software-developer", "Example Co", "Nairobi") + (
        '<link rel="next" href="https://www.brightermonday.co.ke/jobs/software-data?page=2">'
    )

    jobs, next_page = parse_brightermonday_listing_page(html, root, date(2026, 9, 29))

    assert len(jobs) == 1
    assert jobs[0].external_id == "/listings/software-developer"
    assert jobs[0].company == "Example Co"
    assert jobs[0].location == "Nairobi"
    assert jobs[0].published_date == date(2026, 9, 23)
    assert "description" not in jobs[0].model_dump()
    assert next_page == f"{root}?page=2"


def test_fetch_follows_the_published_next_page_link() -> None:
    root = "https://www.brightermonday.co.ke/jobs/software-data"
    page_two = f"{root}?page=2"
    client = _PaginatedClient(
        {
            root: _listing("First role", "first", "First Co", "Nairobi")
            + f'<link rel="next" href="{page_two}">',
            page_two: _listing("Second role", "second", "Second Co", "Mombasa"),
        }
    )

    jobs = BrighterMondayAdapter(
        client=client, listing_urls=(root,), request_delay_seconds=0
    ).fetch()

    assert [job.external_id for job in jobs] == ["/listings/first", "/listings/second"]
    assert client.calls == [root, page_two]


def test_fetches_each_approved_category_page() -> None:
    engineering = "https://www.brightermonday.co.ke/jobs/engineering-technology"
    software_data = "https://www.brightermonday.co.ke/jobs/software-data"
    client = _PaginatedClient(
        {
            engineering: _listing("Software Engineer", "software-engineer", "Co", "Nairobi"),
            software_data: _listing("Data Engineer", "data-engineer", "Co", "Nairobi"),
        }
    )

    jobs = BrighterMondayAdapter(client=client, request_delay_seconds=0).fetch()

    assert [job.title for job in jobs] == ["Software Engineer", "Data Engineer"]
    assert client.calls == [engineering, software_data]


def test_engineering_category_excludes_non_software_engineering_disciplines() -> None:
    root = "https://www.brightermonday.co.ke/jobs/engineering-technology"
    html = "".join(
        (
            _listing("Software Engineer", "software-engineer", "Co", "Nairobi"),
            _listing("Mechanical Engineer", "mechanical-engineer", "Co", "Nairobi"),
            _listing("Civil Engineering Intern", "civil-engineering", "Co", "Nairobi"),
            _listing("Electrical Engineer", "electrical-engineer", "Co", "Nairobi"),
            _listing("Chemical Engineering Lead", "chemical-engineering", "Co", "Nairobi"),
            _listing("Industrial Engineer", "industrial-engineer", "Co", "Nairobi"),
        )
    )

    jobs, _ = parse_brightermonday_listing_page(html, root)

    assert [job.title for job in jobs] == ["Software Engineer"]


def test_relative_posting_day_uses_only_explicit_source_relative_dates() -> None:
    today = date(2026, 9, 29)

    assert _relative_listing_day("today", today) == today
    assert _relative_listing_day("yesterday", today) == date(2026, 9, 28)
    assert _relative_listing_day("6 days ago", today) == date(2026, 9, 23)
    assert _relative_listing_day("2 weeks ago", today) == date(2026, 9, 15)
    assert _relative_listing_day("1 month ago", today) == date(2026, 8, 29)
    assert _relative_listing_day("1 month ago", date(2026, 3, 31)) == date(2026, 2, 28)
    assert _relative_listing_day("New", today) is None
