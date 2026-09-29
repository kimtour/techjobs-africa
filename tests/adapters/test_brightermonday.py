from ingest.adapters.brightermonday import (
    BrighterMondayAdapter,
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
    </div></div>'''


def test_listing_page_keeps_minimal_metadata_and_next_page_only() -> None:
    root = "https://www.brightermonday.co.ke/jobs/it-telecoms"
    html = _listing("Software Developer", "software-developer", "Example Co", "Nairobi") + (
        '<link rel="next" href="https://www.brightermonday.co.ke/jobs/it-telecoms?page=2">'
    )

    jobs, next_page = parse_brightermonday_listing_page(html, root)

    assert len(jobs) == 1
    assert jobs[0].external_id == "/listings/software-developer"
    assert jobs[0].company == "Example Co"
    assert jobs[0].location == "Nairobi"
    assert "description" not in jobs[0].model_dump()
    assert next_page == f"{root}?page=2"


def test_fetch_follows_the_published_next_page_link() -> None:
    root = "https://www.brightermonday.co.ke/jobs/it-telecoms"
    page_two = f"{root}?page=2"
    client = _PaginatedClient(
        {
            root: _listing("First role", "first", "First Co", "Nairobi")
            + f'<link rel="next" href="{page_two}">',
            page_two: _listing("Second role", "second", "Second Co", "Mombasa"),
        }
    )

    jobs = BrighterMondayAdapter(
        client=client, listing_url=root, request_delay_seconds=0
    ).fetch()

    assert [job.external_id for job in jobs] == ["/listings/first", "/listings/second"]
    assert client.calls == [root, page_two]
