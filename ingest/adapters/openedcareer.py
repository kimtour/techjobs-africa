"""Adapter for OpenedCareer’s approved public WordPress jobs API."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any

import httpx

from ingest.models import RawJob

SOURCE_ID = "openedcareer"
API_URL = "https://openedcareer.com/wp-json/wp/v2/job_listing"


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
                published_at=(
                    datetime.fromisoformat(date_gmt) if isinstance(date_gmt, str) else None
                ),
            )
        )
    return jobs


class OpenedCareerAdapter:
    source_id = SOURCE_ID

    def __init__(self, client: httpx.Client | None = None, max_pages: int = 5) -> None:
        self._client = client or httpx.Client(
            headers={"Accept": "application/json", "User-Agent": "TechJobsAfricaBot/0.1"}
        )
        self.max_pages = max_pages

    def fetch(self) -> list[RawJob]:
        jobs: list[RawJob] = []
        for page in range(1, self.max_pages + 1):
            response = self._client.get(
                API_URL, params={"per_page": 100, "page": page}, timeout=15.0
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("OpenedCareer response must be a JSON list.")
            jobs.extend(parse_openedcareer_jobs(payload))
            if len(payload) < 100:
                break
        return jobs
