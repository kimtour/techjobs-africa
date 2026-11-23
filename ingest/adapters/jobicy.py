"""Jobicy's documented public discovery and batch-status APIs."""

from datetime import UTC, datetime
from time import sleep

import httpx

from ingest.adapters.remote_feeds import identity, listing_url, location, posted, text
from ingest.classify.evidence import description_technical_context
from ingest.models import CanonicalJob, RawJob

API = "https://jobicy.com/api/jobs"


def parse_job(record: object) -> RawJob | None:
    if not isinstance(record, dict):
        raise ValueError("Invalid Jobicy record")
    external_id = identity(record.get("id"))
    url = listing_url(record.get("url"), "jobicy.com", "/jobs/")
    if not url.split("?", 1)[0].split("/jobs/", 1)[1].startswith(external_id + "-"):
        raise ValueError("Jobicy URL/ID mismatch")
    title, company = text(record.get("jobTitle")), text(record.get("companyName"))
    published = posted(record.get("pubDate"))
    geo = location(record.get("jobGeo"))
    if not geo:
        return None
    types = record.get("jobType", [])
    if not isinstance(types, list) or any(not isinstance(t, str) for t in types):
        raise ValueError("Invalid employment types")
    return RawJob(
        source_id="jobicy",
        source_publisher="Jobicy",
        external_id=external_id,
        title=title,
        company=company,
        location=geo,
        source_url=url,
        apply_url=url,
        published_at=published,
        employment_type=", ".join(types) or None,
        technical_context=description_technical_context(title, record.get("jobDescription")),
    )


class JobicyAdapter:
    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(
            headers={"User-Agent": "TechKaziBot/0.1", "Accept": "application/json"}
        )
        self.max_pages = 20
        self.request_delay_seconds = 1.2
        self.initial_delay_seconds = 17
        self.previous_jobs: list[CanonicalJob] = []
        self.checked_job_ids: set[str] = set()
        self.closed_job_ids: set[str] = set()
        self.crawl_complete = False
        self._requests = 0

    def _get(self, **params):
        delay = self.request_delay_seconds if self._requests else 0
        if not self._requests and self.initial_delay_seconds:
            now = datetime.now(UTC)
            if now.minute == 0:
                delay = 60 - now.second + self.initial_delay_seconds
        sleep(delay)
        self._requests += 1
        path = params.pop("path", "")
        response = self._client.get(API + path, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if (
            not isinstance(payload, dict)
            or payload.get("success") is not True
            or not isinstance(payload.get("jobs"), list)
        ):
            raise ValueError("Invalid Jobicy envelope")
        return payload

    def fetch(self) -> list[RawJob]:
        self.crawl_complete = False
        self._requests = 0
        self.checked_job_ids, self.closed_job_ids = set(), set()
        found = {}
        seen_ids, cursors = set(), set()
        cursor = None
        for _ in range(self.max_pages):
            params = {"count": 100}
            if cursor:
                params["cursor"] = cursor
            payload = self._get(**params)
            rows = payload["jobs"]
            next_cursor, more = payload.get("nextCursor"), payload.get("hasMore")
            if (
                type(payload.get("jobCount")) is not int
                or payload["jobCount"] != len(rows)
                or len(rows) > 100
                or type(more) is not bool
                or (more and (not isinstance(next_cursor, str) or not next_cursor))
                or (not more and next_cursor is not None)
                or (more and not rows)
            ):
                raise ValueError("Invalid Jobicy pagination")
            for record in rows:
                if not isinstance(record, dict):
                    raise ValueError("Invalid Jobicy record")
                key = identity(record.get("id"))
                if key in seen_ids:
                    raise ValueError("Repeated Jobicy record/page")
                seen_ids.add(key)
                raw = parse_job(record)
                if raw:
                    found[key] = raw
            if not more:
                break
            if next_cursor in cursors:
                raise ValueError("Repeated Jobicy cursor")
            cursors.add(next_cursor)
            cursor = next_cursor
        else:
            raise ValueError("Jobicy discovery exceeded page budget")
        due = sorted(
            self.previous_jobs,
            key=lambda j: (j.last_checked_at or datetime.min.replace(tzinfo=UTC), j.job_id),
        )[:1000]
        for start in range(0, len(due), 100):
            batch = due[start : start + 100]
            expected = {identity(j.job_id.removeprefix("jobicy:")): j.job_id for j in batch}
            payload = self._get(path="/status", ids=",".join(expected))
            statuses = {}
            for row in payload["jobs"]:
                if not isinstance(row, dict):
                    raise ValueError("Invalid Jobicy status")
                key = identity(row.get("id"))
                if (
                    key not in expected
                    or key in statuses
                    or row.get("status") not in {"active", "closed", "unknown"}
                ):
                    raise ValueError("Invalid Jobicy status identity/value")
                statuses[key] = row["status"]
            if statuses.keys() != expected.keys() or payload.get("count") != len(expected):
                raise ValueError("Incomplete Jobicy status batch")
            for key, status in statuses.items():
                self.checked_job_ids.add(expected[key])
                if status == "closed":
                    self.closed_job_ids.add(expected[key])
                    found.pop(key, None)
        self.crawl_complete = True
        return list(found.values())
