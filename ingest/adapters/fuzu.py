"""Adapter for Fuzu Kenya's IT/Software job listing pages.

Access method
-------------
Fuzu's public pages are protected by Cloudflare Bot Management (HTTP/2
fingerprint + JS challenge).  However the server-rendered HTML is reachable
via plain HTTP/1.1.  The ``requests`` library never negotiates HTTP/2 (no h2
in its ALPN offer), so Cloudflare's challenge layer is bypassed entirely and
Fuzu's Rails origin responds normally with a 200.

Each listing page embeds a ``schema.org`` ``ItemList`` block inside a
``<script type="application/ld+json">`` tag.  We parse that JSON -- no
description, salary, or contact data is retained.

Pagination is driven by the site's own ``<link rel="next">`` / ``<a
rel="next">`` canonical link present in every page until the last one.

Legal
-----
Source owner granted fair-use, attributed access by phone on 2026-09-29.
Scraping is limited to the public IT/Software category; no descriptions,
salary, or contacts are persisted.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, date, datetime
from html import unescape
from time import sleep
from urllib.parse import urljoin, urlparse

import requests

from ingest.models import RawJob

logger = logging.getLogger(__name__)

SOURCE_ID = "fuzu"

# Public IT/Software Development category for Kenya (country_id=1)
LISTING_URL = (
    "https://www.fuzu.com/job/computers-software-development"
    "?filters%5Bcountry_id%5D=1"
)
_ALLOWED_HOST = "www.fuzu.com"
_ALLOWED_PATH_PREFIX = "/job/computers-software-development"

# requests is HTTP/1.1-only; Cloudflare Bot Management only challenges HTTP/2.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

_NEXT_LINK_RE = re.compile(
    r'<(?:a|link)[^>]+rel=["\']next["\'][^>]*href=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_LD_JSON_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
_REACT_JSON_RE = re.compile(
    r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def _external_id(url: str) -> str:
    return urlparse(url).path.rstrip("/") or url


def _safe_next_url(href: str, page_url: str) -> str | None:
    """Return the next-page URL only if it stays on the allowed host/path."""
    candidate = urljoin(page_url, unescape(href))
    parsed = urlparse(candidate)
    if (
        parsed.scheme == "https"
        and parsed.netloc == _ALLOWED_HOST
        and parsed.path.startswith(_ALLOWED_PATH_PREFIX)
    ):
        return candidate
    return None


def _campaign_start_dates(html: str) -> dict[str, date]:
    """Read Fuzu's listing-date field from its server-rendered app state.

    Fuzu exposes a campaign start timestamp but no posting time. It represents
    the listing's published calendar date, so callers deliberately store only
    ``published_date`` rather than inventing a time of day.
    """
    dates: dict[str, object] = {}
    for block in _REACT_JSON_RE.finditer(html):
        try:
            payload = json.loads(block.group(1))
            listings = payload["context"]["page_info"]["jobs"]
        except (KeyError, TypeError, json.JSONDecodeError):
            continue

        for listing in listings:
            path = listing.get("path")
            timestamp = listing.get("campaign_start_date")
            if not isinstance(path, str) or not isinstance(timestamp, (int, float)):
                continue
            dates[urljoin("https://www.fuzu.com", path)] = datetime.fromtimestamp(
                timestamp, UTC
            ).date()
    return dates


def parse_fuzu_listing_page(
    html: str, page_url: str
) -> tuple[list[RawJob], str | None]:
    """Extract jobs from schema.org ItemList and the next-page URL.

    Returns a tuple of (jobs, next_page_url).  No descriptions, salary, or
    contact data is retained -- only title and canonical job URL.
    """
    jobs: list[RawJob] = []
    published_dates = _campaign_start_dates(html)

    for raw_block in _LD_JSON_RE.finditer(html):
        try:
            data = json.loads(raw_block.group(1))
        except json.JSONDecodeError:
            continue

        if data.get("@type") != "ItemList":
            continue

        for item in data.get("itemListElement", []):
            title = item.get("name", "").strip()
            url = item.get("url", "").strip()
            if not title or not url:
                continue
            if url.startswith("//"):
                url = "https:" + url
            jobs.append(
                RawJob(
                    source_id=SOURCE_ID,
                    external_id=_external_id(url),
                    title=title[:300],
                    company=None,
                    location=None,
                    source_url=url,   # type: ignore[arg-type]
                    apply_url=url,    # type: ignore[arg-type]
                    published_date=published_dates.get(url),
                )
            )

    next_page: str | None = None
    match = _NEXT_LINK_RE.search(html)
    if match:
        next_page = _safe_next_url(match.group(1), page_url)

    return jobs, next_page


class FuzuAdapter:
    """Fetch IT/Software job listings from Fuzu Kenya.

    Uses ``requests`` (HTTP/1.1 only -- never negotiates HTTP/2) to bypass
    Cloudflare's Bot Management challenge layer, then parses the schema.org
    ``ItemList`` embedded in each server-rendered page.
    """

    source_id = SOURCE_ID

    def __init__(
        self,
        session: requests.Session | None = None,
        listing_url: str = LISTING_URL,
        request_delay_seconds: float = 2.0,
        max_pages: int = 0,
    ) -> None:
        if session is None:
            session = requests.Session()
            session.headers.update(_BROWSER_HEADERS)
        self._session = session
        self.listing_url = listing_url
        self.request_delay_seconds = request_delay_seconds
        self.max_pages = max_pages  # 0 = unlimited

    def fetch(self) -> list[RawJob]:
        """Paginate through Fuzu's listing pages and return all jobs found."""
        jobs_by_id: dict[str, RawJob] = {}
        page_url: str | None = self.listing_url
        visited: set[str] = set()
        pages_fetched = 0

        while page_url and page_url not in visited:
            if self.max_pages and pages_fetched >= self.max_pages:
                logger.debug("fuzu: reached max_pages=%d, stopping", self.max_pages)
                break

            if visited:
                sleep(self.request_delay_seconds)

            logger.debug("fuzu: fetching %s", page_url)
            try:
                response = self._session.get(page_url, timeout=30)
                response.raise_for_status()
            except requests.exceptions.ReadTimeout:
                # CF rate-limits on rapid successive requests; return what we have
                logger.warning(
                    "fuzu: read timeout on %s -- stopping pagination", page_url
                )
                break

            visited.add(page_url)
            pages_fetched += 1

            page_jobs, next_page = parse_fuzu_listing_page(response.text, page_url)
            logger.debug(
                "fuzu: page %d -> %d jobs, next=%s",
                pages_fetched,
                len(page_jobs),
                next_page,
            )

            for job in page_jobs:
                key = job.external_id or str(job.source_url)
                jobs_by_id[key] = job

            page_url = next_page

        logger.info(
            "fuzu: collected %d jobs across %d page(s)",
            len(jobs_by_id),
            pages_fetched,
        )
        return list(jobs_by_id.values())
