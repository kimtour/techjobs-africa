"""Minimal Google Jobs discovery through the documented JSearch API."""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import yaml
from pydantic import ValidationError

from ingest.models import RawJob
from ingest.normalize.location import normalize_location

API_URL = "https://api.openwebninja.com/jsearch/search-v2"


@lru_cache(maxsize=1)
def african_country_names() -> dict[str, str]:
    countries = yaml.safe_load(Path("config/geography.yaml").read_text())["countries"]
    return {item["code"]: item["name"] for item in countries}


FIELDS = ",".join(
    [
        "job_id",
        "job_title",
        "job_publisher",
        "employer_name",
        "job_city",
        "job_state",
        "job_country",
        "job_is_remote",
        "job_apply_link",
        "job_google_link",
        "apply_options",
        "job_posted_at_datetime_utc",
    ]
)


def safe_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme in ("http", "https")
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
        ):
            return value
    except ValueError:
        pass
    return None


def parse_record(record: dict) -> tuple[RawJob, list[str]]:
    """Keep minimal validated fields; ignore descriptions even if projection is ignored."""
    external_id = record.get("job_id")
    if not isinstance(external_id, str) or not external_id.strip():
        raise ValueError("missing_identity")
    options = record.get("apply_options") or []
    if not isinstance(options, list):
        raise ValueError("invalid_apply_options")
    links = [
        link
        for option in options
        if isinstance(option, dict)
        if (link := safe_url(option.get("apply_link")))
    ]
    primary = safe_url(record.get("job_apply_link"))
    direct = next(
        (
            safe_url(option.get("apply_link"))
            for option in options
            if isinstance(option, dict)
            and option.get("is_direct") is True
            and safe_url(option.get("apply_link"))
        ),
        None,
    )
    apply_url = direct or primary or next(iter(links), None)
    if not apply_url:
        raise ValueError("missing_apply_url")
    if primary:
        links.append(primary)
    published = record.get("job_posted_at_datetime_utc")
    try:
        posted_at = datetime.fromisoformat(published) if isinstance(published, str) else None
        if posted_at and (posted_at.tzinfo is None or posted_at > datetime.now(UTC)):
            posted_at = None
    except ValueError:
        posted_at = None
    location = [record.get(key) for key in ("job_location", "job_city", "job_state", "job_country")]
    if record.get("job_is_remote") is True:
        location.insert(0, "Remote")
    # Preserve explicit country evidence rather than assuming eligibility from the query.
    country_names = african_country_names()
    location = [
        country_names.get(part.upper(), part) if isinstance(part, str) else part
        for part in location
    ]
    return RawJob(
        source_id="jsearch",
        external_id=external_id,
        title=record.get("job_title"),
        company=record.get("employer_name"),
        location=" · ".join(part for part in location if isinstance(part, str) and part),
        source_url=safe_url(record.get("job_google_link")) or apply_url,
        apply_url=apply_url,
        published_at=posted_at,
    ), sorted(set(links))


def linkedin_identity(url: str) -> str | None:
    host = (urlsplit(url).hostname or "").lower()
    if host != "linkedin.com" and not host.endswith(".linkedin.com"):
        return None
    match = re.search(r"/jobs/view/(?:[^/]*-)?(\d+)/?$", urlsplit(url).path)
    return match.group(1) if match else None


class LinkedInJSearchAdapter:
    source_id = "linkedin"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client()
        self.crawl_complete = False
        self.queries = [
            "software engineer jobs in Kenya via linkedin",
            "data engineer jobs in Kenya via linkedin",
        ]

    def fetch(self) -> list[RawJob]:
        key = os.environ.get("JSEARCH_API_KEY", "").strip()
        if not key:
            raise ValueError("Missing JSearch credential")
        jobs: dict[str, RawJob] = {}
        for query in self.queries:
            response = self._client.get(
                API_URL,
                headers={"x-api-key": key, "Accept": "application/json"},
                params={
                    "query": query,
                    "country": "ke",
                    "language": "en",
                    "date_posted": "month",
                    "num_pages": 1,
                    "fields": FIELDS,
                },
                timeout=25,
                follow_redirects=False,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            records = data.get("jobs") if isinstance(data, dict) else None
            if (
                not isinstance(payload, dict)
                or payload.get("status") != "OK"
                or not isinstance(records, list)
            ):
                raise ValueError("Invalid JSearch response")
            for record in records:
                if not isinstance(record, dict) or str(
                    record.get("job_country", "")
                ).upper() not in ("KE", "KENYA"):
                    continue
                try:
                    raw, links = parse_record(record)
                except (ValueError, ValidationError):
                    continue
                for link in links:
                    external_id = linkedin_identity(link)
                    if not external_id:
                        continue
                    canonical_url = f"https://www.linkedin.com/jobs/view/{external_id}/"
                    jobs.setdefault(
                        external_id,
                        raw.model_copy(
                            update={
                                "source_id": self.source_id,
                                "external_id": external_id,
                                "source_url": canonical_url,
                                "apply_url": canonical_url,
                            }
                        ),
                    )
        # This is a bounded discovery window, never an exhaustive LinkedIn crawl.
        # Absence-based expiry is disabled regardless of successful query completion.
        self.crawl_complete = True
        return list(jobs.values())


def acceptable_destination(value: object) -> bool:
    url = safe_url(value)
    if not url:
        return False
    host = (urlsplit(url).hostname or "").casefold()
    return host != "bebee.com" and not host.endswith(".bebee.com")


class GoogleJobsJSearchAdapter:
    """Bounded Kenya and Africa-remote discovery through the documented API."""

    source_id = "jsearch"
    queries = (
        "software engineer jobs in Kenya",
        "product manager jobs in Kenya",
        "project manager jobs in Kenya",
        "remote tech jobs in Sub-Saharan Africa via linkedin",
        "remote software engineer jobs in South Africa via linkedin",
    )

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client()
        self.crawl_complete = False
        self.max_pages = 5
        self.query_countries = {}

    def fetch(self) -> list[RawJob]:
        self.crawl_complete = False
        key = os.environ.get("JSEARCH_API_KEY", "").strip()
        if not key:
            raise ValueError("Missing JSearch credential")
        jobs: dict[str, RawJob] = {}
        # Round-robin gives each configured role/location query a first page before
        # spending the remaining shared budget on continuation pages.
        pending = [(query, None) for query in self.queries]
        seen_cursors: dict[str, set[str]] = {query: set() for query in self.queries}
        for _ in range(self.max_pages):
            if not pending:
                break
            query, cursor = pending.pop(0)
            params = {
                "query": query,
                "country": self.query_countries.get(query, "za" if "Africa" in query else "ke"),
                "language": "en",
                "date_posted": "all",
                "num_pages": 1,
                "exclude_job_publishers": "beBee",
            }
            # search-v2 rejects job_location in its fields projection. Read its
            # normal response in memory so regional locations survive; parse_record
            # keeps only metadata and never retains descriptions or response bodies.
            if "remote" in query.casefold():
                params["work_from_home"] = "true"
            if cursor:
                params["cursor"] = cursor
            response = self._client.get(
                API_URL,
                headers={"x-api-key": key, "Accept": "application/json"},
                params=params,
                timeout=60,
                follow_redirects=False,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            records = data.get("jobs") if isinstance(data, dict) else None
            if (
                not isinstance(payload, dict)
                or payload.get("status") != "OK"
                or not isinstance(records, list)
            ):
                raise ValueError("Invalid JSearch response")
            for record in records:
                if not isinstance(record, dict):
                    continue
                country = str(record.get("job_country") or "").upper()
                # Keep Kenya's local roles; other geographies require explicit
                # remote AND African/worldwide location evidence from the result.
                if country not in ("KE", "KENYA"):
                    raw_location = " · ".join(
                        str(record.get(k) or "")
                        for k in ("job_location", "job_city", "job_state", "job_country")
                    )
                    geography = normalize_location(raw_location)
                    country_names = african_country_names()
                    african_country = country in country_names or country in {
                        name.upper() for name in country_names.values()
                    }
                    if record.get("job_is_remote") is not True or not (
                        african_country
                        or (
                            country
                            in ("", "WORLDWIDE", "GLOBAL", "AFRICA", "SUB-SAHARAN AFRICA", "SSA")
                            and (
                                geography.country
                                or geography.region in ("Africa", "Sub-Saharan Africa", "Worldwide")
                            )
                        )
                    ):
                        continue
                # Remove forbidden destinations before choosing a direct option.
                cleaned = dict(record)
                cleaned["apply_options"] = (
                    [
                        option
                        for option in record.get("apply_options", []) or []
                        if isinstance(option, dict)
                        and acceptable_destination(option.get("apply_link"))
                    ]
                    if isinstance(record.get("apply_options", []), list)
                    else []
                )
                if not acceptable_destination(cleaned.get("job_apply_link")):
                    cleaned["job_apply_link"] = None
                try:
                    raw, _ = parse_record(cleaned)
                except (ValueError, ValidationError):
                    continue
                publisher = record.get("job_publisher")
                publisher = publisher.strip()[:300] if isinstance(publisher, str) else None
                if not publisher or publisher.casefold() == "bebee":
                    selected = next(
                        (
                            o
                            for o in cleaned["apply_options"]
                            if o.get("apply_link") == str(raw.apply_url)
                        ),
                        {},
                    )
                    publisher = selected.get("publisher")
                    publisher = publisher.strip()[:300] if isinstance(publisher, str) else None
                    if not publisher or publisher.casefold() == "bebee":
                        publisher = urlsplit(str(raw.apply_url)).hostname
                native_linkedin_id = linkedin_identity(str(raw.apply_url))
                apply_url = (
                    f"https://www.linkedin.com/jobs/view/{native_linkedin_id}/"
                    if native_linkedin_id
                    else str(raw.apply_url)
                )
                external_id = (
                    f"linkedin-{native_linkedin_id}" if native_linkedin_id else raw.external_id
                )
                jobs.setdefault(
                    external_id,
                    raw.model_copy(
                        update={
                            "source_url": apply_url,
                            "apply_url": apply_url,
                            "external_id": external_id,
                            "source_publisher": publisher,
                        }
                    ),
                )
            cursor = data.get("cursor")
            if cursor:
                if not isinstance(cursor, str) or cursor in seen_cursors[query]:
                    raise ValueError("Invalid or repeated JSearch cursor")
                seen_cursors[query].add(cursor)
                pending.append((query, cursor))
        # Query completion is only a bounded window, never evidence of absence.
        self.crawl_complete = True
        return list(jobs.values())
