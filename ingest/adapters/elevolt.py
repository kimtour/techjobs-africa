"""Adapter for Elevolt’s approved public job-listing API."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from time import sleep
from typing import Any

import httpx

from ingest.models import RawJob

SOURCE_ID = "elevolt"
API_URL = "https://api.elevolt.co.ke/api/jobposts/filter"
JOB_URL_TEMPLATE = "https://jobs.elevolt.co.ke/job/{slug}"


def _date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_elevolt_jobs(payload: Mapping[str, Any]) -> list[RawJob]:
    """Parse only listing metadata; descriptions and excerpts are never read."""

    records = payload.get("data")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise ValueError("Elevolt response data must be a JSON list.")

    jobs: list[RawJob] = []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        external_id = record.get("jid")
        title = record.get("title")
        slug = record.get("slug")
        owner = record.get("owner")
        company = owner.get("name") if isinstance(owner, Mapping) else None
        location = record.get("location_display") or record.get("location")
        if not all(isinstance(value, str) and value for value in (external_id, title, slug)):
            continue
        jobs.append(
            RawJob(
                source_id=SOURCE_ID,
                external_id=external_id,
                title=title[:300],
                company=company[:300] if isinstance(company, str) else None,
                location=location[:300] if isinstance(location, str) else None,
                source_url=JOB_URL_TEMPLATE.format(slug=slug),
                apply_url=JOB_URL_TEMPLATE.format(slug=slug),
                published_at=_date(record.get("created_at")),
            )
        )
    return jobs


class ElevoltAdapter:
    source_id = SOURCE_ID

    def __init__(
        self,
        client: httpx.Client | None = None,
        max_pages: int = 5,
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
        for page in range(1, self.max_pages + 1):
            if page > 1:
                sleep(self.request_delay_seconds)
            response = self._client.post(
                API_URL, json={"skill": "software_it", "page": page}, timeout=15.0
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise ValueError("Elevolt response must be a JSON object.")
            jobs.extend(parse_elevolt_jobs(payload))
            meta = payload.get("meta")
            last_page = meta.get("last_page") if isinstance(meta, Mapping) else None
            if isinstance(last_page, int) and page >= last_page:
                self.crawl_complete = True
                break
        return jobs
