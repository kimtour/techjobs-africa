"""Adapter for MyJobMag Kenya's approved, attributed IT listing pages."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from time import sleep
from urllib.parse import parse_qs, urljoin, urlparse
from xml.etree import ElementTree

import httpx

from ingest.models import RawJob

SOURCE_ID = "myjobmag"
DEFAULT_FEED_URL = "https://www.myjobmag.co.ke/jobsxml_by_categories.xml"
LISTING_URL = "https://www.myjobmag.co.ke/jobs-by-field/information-technology"
_ALLOWED_LISTING_PATH = "/jobs-by-field/information-technology"


def _text(item: ElementTree.Element, name: str, *, max_length: int | None = 300) -> str | None:
    value = item.findtext(name)
    if not value or not value.strip():
        return None
    normalized = value.strip()
    return normalized[:max_length] if max_length else normalized


def _external_id(url: str) -> str:
    query_id = parse_qs(urlparse(url).query).get("id", [])
    if query_id:
        return query_id[0]
    return urlparse(url).path.rstrip("/") or url


def parse_myjobmag_feed(content: bytes) -> list[RawJob]:
    """Parse minimal XML fields; production uses the complete category pages."""

    root = ElementTree.fromstring(content)
    items: Sequence[ElementTree.Element] = root.findall(".//item")
    jobs: list[RawJob] = []
    for item in items:
        title = _text(item, "position") or _text(item, "title")
        link = _text(item, "link", max_length=None)
        if not title or not link:
            continue
        published_text = _text(item, "pubDate")
        jobs.append(
            RawJob(
                source_id=SOURCE_ID,
                external_id=_external_id(link),
                title=title,
                company=_text(item, "company"),
                location=_text(item, "location"),
                source_url=link,
                apply_url=link,
                published_at=parsedate_to_datetime(published_text) if published_text else None,
            )
        )
    return jobs


class _ListingPageParser(HTMLParser):
    """Read listing metadata and pagination links, never descriptions or excerpts."""

    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.jobs: list[RawJob] = []
        self.jobs_with_days: list[tuple[RawJob, date | None]] = []
        self.page_links: set[str] = set()
        self._card: dict[str, str] | None = None
        self._card_li_depth = 0
        self._in_heading = False
        self._in_date = False
        self._date_li_depth: int | None = None
        self._in_location_link = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if (
            tag == "li"
            and "job-list-li" in attributes.get("class", "").split()
            and self._card is None
        ):
            self._card = {}
            self._card_li_depth = 1
            return
        if self._card is not None and tag == "li":
            self._card_li_depth += 1
            if attributes.get("id") == "job-date":
                self._in_date = True
                self._date_li_depth = self._card_li_depth
        if self._card is not None and tag == "h2":
            self._in_heading = True
        if self._card is not None and tag == "img":
            alt = attributes.get("alt", "")
            if alt.lower().endswith(" logo"):
                self._card["company"] = alt[:-5].strip()
        if tag != "a":
            return
        href = attributes.get("href")
        if self._card is not None and self._in_heading and href:
            self._card["url"] = urljoin(self.page_url, href)
        if self._card is not None and href and "/jobs-location/" in href:
            self._in_location_link = True
        if not href:
            return
        candidate = urljoin(self.page_url, href)
        parsed = urlparse(candidate)
        if (
            parsed.scheme == "https"
            and parsed.netloc == "www.myjobmag.co.ke"
            and (
                parsed.path == _ALLOWED_LISTING_PATH
                or parsed.path.startswith(_ALLOWED_LISTING_PATH + "/")
            )
        ):
            self.page_links.add(candidate)

    def handle_endtag(self, tag: str) -> None:
        if self._card is not None and tag == "h2":
            self._in_heading = False
        if self._card is not None and tag == "a":
            self._in_location_link = False
        if self._card is not None and tag == "li":
            if self._date_li_depth == self._card_li_depth:
                self._in_date = False
                self._date_li_depth = None
            self._card_li_depth -= 1
            if self._card_li_depth == 0:
                self._append_card()
                self._card = None
                self._in_heading = False
                self._in_date = False
                self._date_li_depth = None
                self._in_location_link = False

    def handle_data(self, data: str) -> None:
        if self._card is None:
            return
        value = " ".join(unescape(data).split())
        if not value:
            return
        if self._in_heading:
            self._card["title"] = f"{self._card.get('title', '')} {value}".strip()
        elif self._in_location_link:
            self._card["location"] = f"{self._card.get('location', '')} {value}".strip()
        elif self._in_date:
            self._card["date"] = f"{self._card.get('date', '')} {value}".strip()

    def _append_card(self) -> None:
        assert self._card is not None
        title = self._card.get("title")
        link = self._card.get("url")
        if not title or not link:
            return
        job = RawJob(
            source_id=SOURCE_ID,
            external_id=_external_id(link),
            title=title[:300],
            company=self._card.get("company") or None,
            location=self._card.get("location") or None,
            source_url=link,
            apply_url=link,
        )
        self.jobs.append(job)
        self.jobs_with_days.append((job, _listing_day(self._card.get("date"))))


def _listing_day(value: str | None, today: date | None = None) -> date | None:
    """Parse the day MyJobMag exposes without inventing a posting time."""

    if not value:
        return None
    reference_day = today or date.today()
    normalized = " ".join(value.split())
    for fmt in ("%d %B", "%d %b"):
        try:
            parsed = datetime.strptime(
                f"{normalized} {reference_day.year}", f"{fmt} %Y"
            ).date()
        except ValueError:
            continue
        return parsed.replace(year=parsed.year - 1) if parsed > reference_day else parsed
    return None


def parse_myjobmag_listing_page(content: str, page_url: str) -> tuple[list[RawJob], set[str]]:
    """Parse a category page without retaining job descriptions or excerpts."""

    parser = _ListingPageParser(page_url)
    parser.feed(content)
    parser.close()
    return parser.jobs, parser.page_links


class MyJobMagAdapter:
    source_id = SOURCE_ID

    def __init__(
        self,
        client: httpx.Client | None = None,
        listing_url: str = LISTING_URL,
        max_pages: int | None = None,
        request_delay_seconds: float = 1.5,
        lookback_days: int = 30,
        today: date | None = None,
    ) -> None:
        self._client = client or httpx.Client(
            headers={"Accept": "text/html", "User-Agent": "TechJobsAfricaBot/0.1"}
        )
        self.listing_url = listing_url
        self.max_pages = max_pages
        self.request_delay_seconds = request_delay_seconds
        self.lookback_days = lookback_days
        self.today = today

    def fetch(self) -> list[RawJob]:
        """Follow only pagination links published by the IT category pages."""

        pending = [self.listing_url]
        visited: set[str] = set()
        jobs_by_id: dict[str, RawJob] = {}
        cutoff = (self.today or date.today()) - timedelta(days=self.lookback_days)
        while pending and (self.max_pages is None or len(visited) < self.max_pages):
            page_url = pending.pop(0)
            if page_url in visited:
                continue
            if visited:
                sleep(self.request_delay_seconds)
            response = self._client.get(page_url, timeout=15.0)
            response.raise_for_status()
            parser = _ListingPageParser(page_url)
            parser.feed(response.text)
            parser.close()
            visited.add(page_url)
            dated_jobs = parser.jobs_with_days
            for job, listing_day in dated_jobs:
                if listing_day is not None and listing_day < cutoff:
                    continue
                jobs_by_id[job.external_id or str(job.source_url)] = job
            page_days = [listing_day for _, listing_day in dated_jobs if listing_day is not None]
            if page_days and max(page_days) < cutoff:
                break
            pending.extend(sorted(parser.page_links - visited - set(pending)))
        return list(jobs_by_id.values())
