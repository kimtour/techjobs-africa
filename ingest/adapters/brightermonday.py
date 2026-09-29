"""Adapter for BrighterMonday Kenya's owner-approved IT & Telecoms listing pages."""

from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from time import sleep
from urllib.parse import urljoin, urlparse

import httpx

from ingest.models import RawJob

SOURCE_ID = "brightermonday"
LISTING_URL = "https://www.brightermonday.co.ke/jobs/it-telecoms"
_ALLOWED_PATH = "/jobs/it-telecoms"


def _external_id(url: str) -> str:
    return urlparse(url).path.rstrip("/") or url


class _ListingPageParser(HTMLParser):
    """Read minimal card metadata and the site's published next-page link."""

    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.jobs: list[RawJob] = []
        self.next_page: str | None = None
        self._card: dict[str, object] | None = None
        self._card_div_depth = 0
        self._capture_company = False
        self._capture_badge = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "link" and attributes.get("rel") == "next":
            self._set_next_page(attributes.get("href"))
        if tag == "a" and attributes.get("rel") == "next":
            self._set_next_page(attributes.get("href"))
        if tag == "div" and attributes.get("data-cy") == "listing-cards-components":
            self._card = {"badges": []}
            self._card_div_depth = 1
            return
        if self._card is None:
            return
        if tag == "div":
            self._card_div_depth += 1
        classes = attributes.get("class", "")
        if tag == "a" and attributes.get("data-cy") == "listing-title-link":
            href = attributes.get("href")
            if href:
                self._card["url"] = urljoin(self.page_url, href)
            title = attributes.get("title")
            if title:
                self._card["title"] = title
        if tag == "p" and "text-blue-700" in classes and "mt-3" in classes:
            self._capture_company = True
        if tag == "span" and "bg-brand-secondary-100" in classes:
            self._capture_badge = True

    def handle_endtag(self, tag: str) -> None:
        if self._card is None:
            return
        if tag == "p":
            self._capture_company = False
        if tag == "span":
            self._capture_badge = False
        if tag == "div":
            self._card_div_depth -= 1
            if self._card_div_depth == 0:
                self._append_card()
                self._card = None
                self._capture_company = False
                self._capture_badge = False

    def handle_data(self, data: str) -> None:
        if self._card is None:
            return
        value = " ".join(unescape(data).split())
        if not value:
            return
        if self._capture_company:
            self._card["company"] = f"{self._card.get('company', '')} {value}".strip()
        elif self._capture_badge:
            badges = self._card["badges"]
            assert isinstance(badges, list)
            badges.append(value)

    def _set_next_page(self, href: str | None) -> None:
        if not href:
            return
        candidate = urljoin(self.page_url, href)
        parsed = urlparse(candidate)
        if parsed.scheme == "https" and parsed.netloc == "www.brightermonday.co.ke":
            if parsed.path == _ALLOWED_PATH:
                self.next_page = candidate

    def _append_card(self) -> None:
        assert self._card is not None
        title = self._card.get("title")
        link = self._card.get("url")
        if not isinstance(title, str) or not isinstance(link, str):
            return
        badges = self._card.get("badges", [])
        location = badges[0] if isinstance(badges, list) and badges else None
        company = self._card.get("company")
        self.jobs.append(
            RawJob(
                source_id=SOURCE_ID,
                external_id=_external_id(link),
                title=title[:300],
                company=company[:300] if isinstance(company, str) and company else None,
                location=location[:300] if isinstance(location, str) else None,
                source_url=link,
                apply_url=link,
            )
        )


def parse_brightermonday_listing_page(
    content: str, page_url: str
) -> tuple[list[RawJob], str | None]:
    """Parse a category page without retaining descriptions, salary, or contacts."""

    parser = _ListingPageParser(page_url)
    parser.feed(content)
    parser.close()
    return parser.jobs, parser.next_page


class BrighterMondayAdapter:
    source_id = SOURCE_ID

    def __init__(
        self,
        client: httpx.Client | None = None,
        listing_url: str = LISTING_URL,
        request_delay_seconds: float = 1.5,
    ) -> None:
        self._client = client or httpx.Client(
            headers={"Accept": "text/html", "User-Agent": "TechJobsAfricaBot/0.1"}
        )
        self.listing_url = listing_url
        self.request_delay_seconds = request_delay_seconds

    def fetch(self) -> list[RawJob]:
        jobs_by_id: dict[str, RawJob] = {}
        page_url: str | None = self.listing_url
        visited: set[str] = set()
        while page_url and page_url not in visited:
            if visited:
                sleep(self.request_delay_seconds)
            response = self._client.get(page_url, timeout=15.0)
            response.raise_for_status()
            jobs, next_page = parse_brightermonday_listing_page(response.text, page_url)
            visited.add(page_url)
            for job in jobs:
                jobs_by_id[job.external_id or str(job.source_url)] = job
            page_url = next_page
        return list(jobs_by_id.values())
