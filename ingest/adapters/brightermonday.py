"""Adapter for BrighterMonday Kenya's owner-approved technology listing pages."""

from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, timedelta
from html import unescape
from html.parser import HTMLParser
from time import sleep
from urllib.parse import urljoin, urlparse

import httpx

from ingest.classify.evidence import enrich_listing_jobs
from ingest.models import RawJob

SOURCE_ID = "brightermonday"
LISTING_URLS = (
    "https://www.brightermonday.co.ke/jobs/engineering-technology",
    "https://www.brightermonday.co.ke/jobs/software-data",
)
_ENGINEERING_TECHNOLOGY_PATH = "/jobs/engineering-technology"
_ALLOWED_PATHS = frozenset({_ENGINEERING_TECHNOLOGY_PATH, "/jobs/software-data"})
_NON_SOFTWARE_ENGINEERING_TITLES = (
    "mechanical engineer",
    "mechanical engineering",
    "civil engineer",
    "civil engineering",
    "electrical engineer",
    "electrical engineering",
    "chemical engineer",
    "chemical engineering",
    "industrial engineer",
    "industrial engineering",
)


def _external_id(url: str) -> str:
    return urlparse(url).path.rstrip("/") or url


class _ListingPageParser(HTMLParser):
    """Read minimal card metadata and the site's published next-page link."""

    def __init__(self, page_url: str, today: date | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.today = today
        self.jobs: list[RawJob] = []
        self.next_page: str | None = None
        self._card: dict[str, object] | None = None
        self._card_div_depth = 0
        self._capture_company = False
        self._capture_badge = False
        self._relative_date_div_depth: int | None = None

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
            if "ml-auto" in attributes.get("class", ""):
                self._relative_date_div_depth = self._card_div_depth
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
            if self._relative_date_div_depth == self._card_div_depth:
                self._relative_date_div_depth = None
            self._card_div_depth -= 1
            if self._card_div_depth == 0:
                self._append_card()
                self._card = None
                self._capture_company = False
                self._capture_badge = False
                self._relative_date_div_depth = None

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
        elif self._relative_date_div_depth is not None:
            self._card["relative_date"] = f"{self._card.get('relative_date', '')} {value}".strip()

    def _set_next_page(self, href: str | None) -> None:
        if not href:
            return
        candidate = urljoin(self.page_url, href)
        parsed = urlparse(candidate)
        if parsed.scheme == "https" and parsed.netloc == "www.brightermonday.co.ke":
            if parsed.path in _ALLOWED_PATHS:
                self.next_page = candidate

    def _append_card(self) -> None:
        assert self._card is not None
        title = self._card.get("title")
        link = self._card.get("url")
        if not isinstance(title, str) or not isinstance(link, str):
            return
        if urlparse(
            self.page_url
        ).path == _ENGINEERING_TECHNOLOGY_PATH and _is_non_software_engineering_title(title):
            return
        badges = self._card.get("badges", [])
        location = badges[0] if isinstance(badges, list) and badges else None
        company = self._card.get("company")
        published_date = _relative_listing_day(self._card.get("relative_date"), self.today)
        self.jobs.append(
            RawJob(
                source_id=SOURCE_ID,
                external_id=_external_id(link),
                title=title[:300],
                company=company[:300] if isinstance(company, str) and company else None,
                location=location[:300] if isinstance(location, str) else None,
                source_url=link,
                apply_url=link,
                published_date=published_date,
            )
        )


def _is_non_software_engineering_title(title: str) -> bool:
    normalized = " ".join(title.lower().split())
    return any(term in normalized for term in _NON_SOFTWARE_ENGINEERING_TITLES)


def _relative_listing_day(value: object, today: date | None = None) -> date | None:
    """Convert an explicit source-relative day into a date without inventing a time."""

    if not isinstance(value, str):
        return None
    reference_day = today or date.today()
    normalized = " ".join(value.lower().split())
    if normalized == "today":
        return reference_day
    if normalized == "yesterday":
        return reference_day - timedelta(days=1)
    match = re.fullmatch(r"(\d+) days? ago", normalized)
    if match:
        return reference_day - timedelta(days=int(match.group(1)))
    match = re.fullmatch(r"(\d+) weeks? ago", normalized)
    if match:
        return reference_day - timedelta(weeks=int(match.group(1)))
    match = re.fullmatch(r"(\d+) months? ago", normalized)
    if match:
        months_ago = int(match.group(1))
        month_index = reference_day.year * 12 + reference_day.month - 1 - months_ago
        year, month_index = divmod(month_index, 12)
        month = month_index + 1
        return date(year, month, min(reference_day.day, monthrange(year, month)[1]))
    return None


def parse_brightermonday_listing_page(
    content: str, page_url: str, today: date | None = None
) -> tuple[list[RawJob], str | None]:
    """Parse a category page without retaining descriptions, salary, or contacts."""

    parser = _ListingPageParser(page_url, today)
    parser.feed(content)
    parser.close()
    return parser.jobs, parser.next_page


class BrighterMondayAdapter:
    source_id = SOURCE_ID

    def __init__(
        self,
        client: httpx.Client | None = None,
        listing_urls: tuple[str, ...] = LISTING_URLS,
        request_delay_seconds: float = 1.5,
        today: date | None = None,
        max_pages: int = 40,
    ) -> None:
        self._client = client or httpx.Client(
            headers={"Accept": "text/html", "User-Agent": "TechKaziBot/0.1"}
        )
        self.listing_urls = listing_urls
        self.request_delay_seconds = request_delay_seconds
        self.today = today
        self.max_pages = max_pages

    def fetch(self) -> list[RawJob]:
        self.crawl_complete = False
        jobs_by_id: dict[str, RawJob] = {}
        visited: set[str] = set()
        request_count = 0
        for listing_url in self.listing_urls:
            page_url: str | None = listing_url
            while page_url and page_url not in visited:
                if request_count >= self.max_pages:
                    return list(jobs_by_id.values())
                if request_count:
                    sleep(self.request_delay_seconds)
                response = self._client.get(page_url, timeout=15.0)
                response.raise_for_status()
                jobs, next_page = parse_brightermonday_listing_page(
                    response.text, page_url, self.today
                )
                visited.add(page_url)
                request_count += 1
                for job in jobs:
                    jobs_by_id[job.external_id or str(job.source_url)] = job
                if next_page in visited:
                    return list(jobs_by_id.values())
                page_url = next_page
        self.crawl_complete = True
        return enrich_listing_jobs(
            list(jobs_by_id.values()), self._client, allowed_hosts={"www.brightermonday.co.ke"}
        )
