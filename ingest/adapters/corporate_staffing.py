"""Adapter for Corporate Staffing's approved public WordPress jobs API."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from time import sleep
from typing import Any

import httpx

from ingest.models import RawJob
from ingest.normalize.location import normalize_location

SOURCE_ID = "corporate_staffing"
API_URL = "https://www.corporatestaffing.co.ke/wp-json/wp/v2/job"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _plain_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    parser = _TextExtractor()
    parser.feed(value)
    normalized = " ".join(unescape("".join(parser.parts)).split())
    return normalized[:300] if normalized else None


def _title(record: Mapping[str, Any]) -> str | None:
    title = record.get("title")
    return _plain_text(title.get("rendered")) if isinstance(title, Mapping) else None


def _company_from_title(title: str) -> str | None:
    """Recover an explicitly named employer from this source's title convention.

    Corporate Staffing commonly publishes titles such as ``Role Job HFCB Group``
    while leaving its structured employer field empty.  This uses only the public
    title, and deliberately rejects location/preposition tails such as ``Job in
    Nairobi`` rather than guessing an employer.
    """

    match = re.search(r"\s+Job\s+(?P<company>.+)$", title, flags=re.IGNORECASE)
    if not match:
        return None
    company = match.group("company").strip(" -–—")
    if not company or re.match(r"^(in|at|for|with|near)\b", company, flags=re.IGNORECASE):
        return None
    return company


def _location_from_listing(*values: object) -> str:
    """Resolve title, URL, and in-memory body signals to a safe display location."""

    parser = _TextExtractor()
    for value in values:
        if isinstance(value, str):
            parser.feed(value)
    text = " ".join(unescape(" ".join(parser.parts)).split())
    location = normalize_location(text)
    if location.city:
        return f"{location.city}, {location.country}"
    if location.workplace_type:
        return location.workplace_type
    if location.country:
        return location.country
    return "Kenya"


def parse_corporate_staffing_jobs(payload: Sequence[Mapping[str, Any]]) -> list[RawJob]:
    """Parse minimum permitted fields; descriptions and excerpts are never read."""

    jobs: list[RawJob] = []
    for record in payload:
        external_id = record.get("id")
        link = record.get("link")
        title = _title(record)
        if not isinstance(external_id, int) or not isinstance(link, str) or not title:
            continue
        date_gmt = record.get("date_gmt")
        content = record.get("content")
        location = _location_from_listing(
            title,
            link,
            content.get("rendered") if isinstance(content, Mapping) else None,
        )
        jobs.append(
            RawJob(
                source_id=SOURCE_ID,
                external_id=str(external_id),
                title=title,
                company=_company_from_title(title),
                location=location,
                source_url=link,
                apply_url=link,
                published_at=(
                    datetime.fromisoformat(f"{date_gmt}+00:00")
                    if isinstance(date_gmt, str)
                    else None
                ),
            )
        )
    return jobs


class CorporateStaffingAdapter:
    source_id = SOURCE_ID

    def __init__(
        self,
        client: httpx.Client | None = None,
        max_pages: int | None = None,
        request_delay_seconds: float = 1.5,
    ) -> None:
        self._client = client or httpx.Client(
            headers={"Accept": "application/json", "User-Agent": "TechJobsAfricaBot/0.1"}
        )
        self.max_pages = max_pages
        self.request_delay_seconds = request_delay_seconds

    def fetch(self) -> list[RawJob]:
        self.crawl_complete = False
        jobs: list[RawJob] = []
        page = 1
        while self.max_pages is None or page <= self.max_pages:
            if page > 1:
                sleep(self.request_delay_seconds)
            response = self._client.get(
                API_URL,
                params={"categories": 10, "per_page": 100, "page": page},
                timeout=15.0,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("Corporate Staffing response must be a JSON list.")
            page_jobs = parse_corporate_staffing_jobs(payload)
            jobs.extend(page_jobs)
            total_pages = response.headers.get("X-WP-TotalPages")
            try:
                has_next_page = page < int(total_pages) if total_pages else len(payload) == 100
            except ValueError:
                has_next_page = len(payload) == 100
            if not has_next_page:
                self.crawl_complete = True
                break
            page += 1
        return jobs
