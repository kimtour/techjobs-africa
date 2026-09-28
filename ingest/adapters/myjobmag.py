"""Adapter for MyJobMag Kenya's approved detailed XML feed."""

from __future__ import annotations

from collections.abc import Sequence
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree

import httpx

from ingest.models import RawJob

SOURCE_ID = "myjobmag"
DEFAULT_FEED_URL = "https://www.myjobmag.co.ke/jobsxml_by_categories.xml"


def _text(item: ElementTree.Element, name: str, *, max_length: int | None = 300) -> str | None:
    value = item.findtext(name)
    if not value or not value.strip():
        return None
    normalized = value.strip()
    return normalized[:max_length] if max_length else normalized


def _external_id(url: str) -> str:
    query_id = parse_qs(urlparse(url).query).get("id", [])
    return query_id[0] if query_id else url


def parse_myjobmag_feed(content: bytes) -> list[RawJob]:
    """Parse minimal fields from the approved feed and ignore descriptions."""

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


class MyJobMagAdapter:
    source_id = SOURCE_ID

    def __init__(
        self, client: httpx.Client | None = None, feed_url: str = DEFAULT_FEED_URL
    ) -> None:
        self._client = client or httpx.Client(
            headers={"Accept": "application/xml", "User-Agent": "TechJobsAfricaBot/0.1"}
        )
        self.feed_url = feed_url

    def fetch(self) -> list[RawJob]:
        response = self._client.get(self.feed_url, timeout=15.0)
        response.raise_for_status()
        return parse_myjobmag_feed(response.content)
