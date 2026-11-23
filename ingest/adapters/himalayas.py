"""Documented public Himalayas searches with explicit Kenya/timezone gates."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from time import sleep
from urllib.parse import urlsplit

import httpx

from ingest.classify.evidence import description_technical_context
from ingest.models import CanonicalJob, RawJob

API = "https://himalayas.app/jobs/api"
QUERIES = (
    "software engineer",
    "data",
    "devops",
    "security",
    "product manager",
    "QA engineer",
    "technical support",
    "UI UX",
)
JOB_PATH = re.compile(r"^/companies/[a-z0-9-]+/jobs/[a-z0-9-]+$")


def job_identity(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Missing Himalayas identity")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "himalayas.app"
        or parsed.query
        or parsed.fragment
        or not JOB_PATH.fullmatch(parsed.path)
    ):
        raise ValueError("Invalid Himalayas identity")
    return value


def timestamp(value: object) -> datetime:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Invalid source timestamp")
    return datetime.fromtimestamp(value, UTC)


def parse_job(record: object, *, now: datetime) -> RawJob | None:
    if not isinstance(record, Mapping):
        raise ValueError("Invalid Himalayas job")
    guid = job_identity(record.get("guid"))
    apply = record.get("applicationLink")
    parsed = urlsplit(apply) if isinstance(apply, str) else None
    if (
        not parsed
        or parsed.scheme != "https"
        or parsed.netloc != "himalayas.app"
        or parsed.path != urlsplit(guid).path
        or parsed.fragment
    ):
        raise ValueError("Invalid Himalayas application destination")
    for key in ("title", "companyName"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError("Missing vacancy metadata")
    countries = record.get("locationRestrictions")
    zones = record.get("timezoneRestrictions")
    if not isinstance(countries, list) or any(
        not isinstance(c, str) or not c.strip() for c in countries
    ):
        raise ValueError("Unknown country restrictions")
    if not isinstance(zones, list) or any(
        isinstance(z, bool)
        or not isinstance(z, (int, float))
        or not math.isfinite(z)
        or not -12 <= z <= 14
        for z in zones
    ):
        raise ValueError("Unknown timezone restrictions")
    updated = timestamp(record.get("pubDate"))
    expiry = timestamp(record.get("expiryDate"))
    if expiry <= now or (countries and "Kenya" not in countries) or (zones and 3 not in zones):
        return None
    return RawJob(
        source_id="himalayas",
        source_publisher="Himalayas",
        external_id=guid,
        title=record["title"].strip(),
        company=record["companyName"].strip(),
        location="Remote · Kenya" if countries else "Remote · Worldwide",
        source_url=guid,
        apply_url=apply,
        source_updated_at=updated,
        deadline_at=expiry,
        employment_type=record.get("employmentType"),
        technical_context=description_technical_context(record["title"], record.get("description")),
    )


class HimalayasAdapter:
    def __init__(self, client: httpx.Client | None = None, *, now: datetime | None = None):
        self._client = client or httpx.Client(
            headers={"User-Agent": "TechKaziBot/0.1", "Accept": "application/json"}
        )
        self.now = now
        self.max_pages = 16
        self.pages_per_query = 2
        self.recheck_limit = 20
        self.request_delay_seconds = 3.5
        self.search_terms = QUERIES
        self.previous_jobs: list[CanonicalJob] = []
        self.closed_job_ids: set[str] = set()
        self.checked_job_ids: set[str] = set()
        self.crawl_complete = False
        self._requests = 0

    def _get(self, url, **kwargs):
        if self._requests:
            sleep(self.request_delay_seconds)
        self._requests += 1
        try:
            return self._client.get(url, timeout=30, **kwargs)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {404, 410}:
                return exc.response
            raise

    def fetch(self) -> list[RawJob]:
        self.crawl_complete = False
        self.closed_job_ids = set()
        self.checked_job_ids = set()
        self._requests = 0
        now = self.now or datetime.now(UTC)
        found: dict[str, RawJob] = {}
        pages = 0
        for query in self.search_terms:
            previous_page = None
            for page in range(1, self.pages_per_query + 1):
                if pages >= self.max_pages:
                    raise ValueError("Configured discovery window exceeds page budget")
                response = self._get(
                    API + "/search",
                    params={"country": "KE", "q": query, "sort": "recent", "page": page},
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
                    raise ValueError("Invalid search envelope")
                jobs = payload["jobs"]
                total, limit, offset = (payload.get(k) for k in ("totalCount", "limit", "offset"))
                if (
                    any(type(v) is not int for v in (total, limit, offset))
                    or total < 0
                    or limit != 20
                    or offset != (page - 1) * limit
                    or len(jobs) > limit
                ):
                    raise ValueError("Invalid search pagination")
                if not jobs and offset < total:
                    raise ValueError("Incomplete search page")
                if len(jobs) < limit and offset + len(jobs) < total:
                    raise ValueError("Truncated search page")
                identities = tuple(job_identity(j.get("guid")) for j in jobs if isinstance(j, dict))
                if jobs and identities == previous_page:
                    raise ValueError("Repeated search page")
                previous_page = identities
                for record in jobs:
                    raw = parse_job(record, now=now)
                    if raw:
                        found[raw.external_id] = raw
                pages += 1
                if offset + len(jobs) >= total:
                    break
        # Recheck a rotating portion of accepted jobs, never crawl protected HTML.
        due = sorted(
            self.previous_jobs,
            key=lambda j: (j.last_checked_at or datetime.min.replace(tzinfo=UTC), j.job_id),
        )
        checked = 0
        for job in due:
            guid = job_identity(str(job.preferred_apply_url).split("?", 1)[0])
            if guid in found:
                continue
            if checked >= self.recheck_limit:
                break
            response = self._get(API + urlsplit(guid).path)
            checked += 1
            self.checked_job_ids.add(job.job_id)
            if response.status_code == 410:
                self.closed_job_ids.add(job.job_id)
                continue
            if response.status_code == 404:
                continue
            response.raise_for_status()
            payload = response.json()
            if (
                not isinstance(payload, dict)
                or not isinstance(payload.get("job"), dict)
                or payload["job"].get("guid") != guid
            ):
                raise ValueError("Invalid job status response")
            raw = parse_job(payload["job"], now=now)
            if raw:
                found[raw.external_id] = raw
            else:
                self.closed_job_ids.add(job.job_id)
        self.crawl_complete = True
        return list(found.values())
