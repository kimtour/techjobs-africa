"""Adapter for Ashby's documented public Job Postings API."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

import httpx

from ingest.models import RawJob

SOURCE_ID = "ashby"
API_URL_TEMPLATE = "https://api.ashbyhq.com/posting-api/job-board/{board}"
BOARD_PATTERN = re.compile(r"^[a-z0-9-]+$")


def _as_optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def parse_ashby_jobs(payload: Mapping[str, Any]) -> list[RawJob]:
    """Convert listed public Ashby postings into minimal RawJob records.

    Description fields in the public API response are intentionally ignored.
    """

    jobs = payload.get("jobs")
    if not isinstance(jobs, Sequence) or isinstance(jobs, (str, bytes)):
        raise ValueError("Ashby response does not contain a jobs list.")

    parsed: list[RawJob] = []
    for job in jobs:
        if not isinstance(job, Mapping) or job.get("isListed") is not True:
            continue

        external_id = _as_optional_text(job.get("id"))
        title = _as_optional_text(job.get("title"))
        source_url = _as_optional_text(job.get("jobUrl"))
        apply_url = _as_optional_text(job.get("applyUrl"))
        if not all((external_id, title, source_url, apply_url)):
            continue

        published_at = _as_optional_text(job.get("publishedAt"))
        parsed.append(
            RawJob(
                source_id=SOURCE_ID,
                external_id=external_id,
                title=title,
                company=None,
                location=_as_optional_text(job.get("location")),
                source_url=source_url,
                apply_url=apply_url,
                published_at=datetime.fromisoformat(published_at) if published_at else None,
            )
        )
    return parsed


class AshbyAdapter:
    source_id = SOURCE_ID

    def __init__(self, board: str, client: httpx.Client | None = None) -> None:
        if not BOARD_PATTERN.fullmatch(board):
            raise ValueError(
                "Ashby board names may contain only lowercase letters, digits, and hyphens."
            )
        self.board = board
        self._client = client or httpx.Client(
            headers={"Accept": "application/json", "User-Agent": "TechKaziBot/0.1"}
        )

    @property
    def api_url(self) -> str:
        return API_URL_TEMPLATE.format(board=self.board)

    def fetch(self) -> list[RawJob]:
        self.crawl_complete = False
        response = self._client.get(self.api_url, timeout=15.0)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise ValueError("Ashby response must be a JSON object.")
        jobs = parse_ashby_jobs(payload)
        self.crawl_complete = True
        return jobs
