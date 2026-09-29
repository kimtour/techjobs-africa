"""Adapter for OpenedCareer’s approved public WordPress jobs API."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from time import sleep
from typing import Any

import httpx

from ingest.models import RawJob

SOURCE_ID = "openedcareer"
API_URL = "https://openedcareer.com/wp-json/wp/v2/job_listing"
COMPUTER_SCIENCE_CATEGORY_ID = 732


def _company_from_title(title: str) -> str | None:
    """Return an explicitly named employer from an OpenedCareer listing title.

    OpenedCareer’s public category API does not expose a company field.  Many
    of its titles do, however, use the unambiguous ``Role at Employer`` form.
    This deliberately extracts only that explicit metadata; it does not guess
    from descriptions or send listing data to a third-party AI service.
    """

    role, separator, company = title.rpartition(" at ")
    if not separator or not role.strip() or not company.strip():
        return None
    normalized = company.strip(" -–—:,")
    if normalized.casefold() in {"all interested applicants", "various employers"}:
        return None
    return normalized[:300] or None


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


def parse_openedcareer_jobs(payload: Sequence[Mapping[str, Any]]) -> list[RawJob]:
    """Parse only permitted listing metadata; never read description fields."""

    jobs: list[RawJob] = []
    for record in payload:
        external_id = record.get("id")
        link = record.get("link")
        title_value = record.get("title")
        title = (
            _plain_text(title_value.get("rendered"))
            if isinstance(title_value, Mapping)
            else None
        )
        if not isinstance(external_id, int) or not isinstance(link, str) or not title:
            continue
        date_gmt = record.get("date_gmt")
        jobs.append(
            RawJob(
                source_id=SOURCE_ID,
                external_id=str(external_id),
                title=title,
                source_url=link,
                apply_url=link,
                company=_company_from_title(title),
                published_at=(
                    datetime.fromisoformat(f"{date_gmt}+00:00")
                    if isinstance(date_gmt, str)
                    else None
                ),
            )
        )
    return jobs


class OpenedCareerAdapter:
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
        jobs: list[RawJob] = []
        page = 1
        while self.max_pages is None or page <= self.max_pages:
            if page > 1:
                sleep(self.request_delay_seconds)
            response = self._client.get(
                API_URL,
                params={
                    "job_listing_category": COMPUTER_SCIENCE_CATEGORY_ID,
                    "per_page": 100,
                    "page": page,
                },
                timeout=15.0,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("OpenedCareer response must be a JSON list.")
            jobs.extend(parse_openedcareer_jobs(payload))
            total_pages = response.headers.get("X-WP-TotalPages")
            try:
                has_next_page = page < int(total_pages) if total_pages else len(payload) == 100
            except ValueError:
                has_next_page = len(payload) == 100
            if not has_next_page:
                break
            page += 1
        return jobs
