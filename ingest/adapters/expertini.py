"""Minimal discovery from Expertini's advertised public Kenya job sitemaps."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

import httpx

from ingest.classify.tech import classify_technology_title
from ingest.models import RawJob

RSS_URL = "https://ke.expertini.com/jobs/feed.xml"
INDEX_URL = "https://ke.expertini.com/sitemapindex.xml"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
CITY_SLUGS = {
    "tatucity": "tatu-city",
    "homabay": "homa-bay",
    "eldamaravine": "eldama-ravine",
}
# Broad QA / project keywords must not admit roles explicitly in other industries.
NON_IT_CONTEXT = re.compile(
    r"\b(construction|civil|mechanical|flower|packhouse|nurse|healthcare|"
    r"food safety|pharmaceutical|agronomist|agriculture)\b",
    re.I,
)


def parse_listing_link(value: object) -> RawJob | None:
    """Use only the job-label prefix; never infer a title from employer/category text.

    XML supplies no separate title, company, posting date or active-status fields.
    Keep the employer unknown and label URL-derived titles in the frontend. Native
    numeric IDs survive changed URL titles. lastmod is deliberately never used.
    """
    if not isinstance(value, str):
        return None
    try:
        url = urlsplit(value)
        host = (url.hostname or "").lower()
        if (
            url.scheme != "https"
            or url.username is not None
            or url.password is not None
            or url.port is not None
            or not host.endswith(".ke.expertini.com")
            or url.query
            or url.fragment
        ):
            return None
        locality = host.removesuffix(".ke.expertini.com")
        if not re.fullmatch(r"[a-z]{2,40}", locality):
            return None
        match = re.fullmatch(r"/job/([a-z0-9-]+)-(\d{6,})/", unquote(url.path))
        if not match:
            return None
        label, native_id = match.groups()
        marker = f"-{CITY_SLUGS.get(locality, locality)}-"
        title_slug, separator, employer_slug = label.partition(marker)
        if not separator or not title_slug or not employer_slug:
            return None
        title = title_slug.replace("-", " ").strip()
        title = re.sub(r"\s+(in|at|for)$", "", title)
        if NON_IT_CONTEXT.search(title):
            return None
        decision = classify_technology_title(title)
        if not decision.category:
            return None
        # With only a URL label, generic project / QA / attachment phrases lack
        # enough technical context. Other providers keep their existing policy.
        if decision.category == "Technical Product" and not re.search(
            r"\b(technical|platform|software|data|ai|fintech)\b", title
        ):
            return None
        if decision.category == "QA / Testing" and not re.search(
            r"\b(qa|software|automation|sdet|test)\b", title
        ):
            return None
        if (
            decision.category == "Internship / Graduate Technology"
            and title == "volunteer worker attachment"
        ):
            return None
        title = title.title()
        for acronym in ("AI", "ICT", "IT", "QA", "SAP", "SQL", "ERP", "IOS", "RF"):
            title = re.sub(rf"\b{acronym}\b", acronym, title, flags=re.I)
        location = (
            "Kenya"
            if locality == "ke"
            else f"{CITY_SLUGS.get(locality, locality).replace('-', ' ').title()} · Kenya"
        )
        return RawJob(
            source_id="expertini",
            source_publisher="Expertini",
            external_id=native_id,
            title=title,
            location=location,
            source_url=value,
            apply_url=value,
        )
    except ValueError:
        return None


def parse_rss_item(item: ElementTree.Element) -> RawJob | None:
    """Keep genuine RSS title/publication fields, ignoring all description elements."""
    value = item.findtext("link")
    title = item.findtext("title")
    if not isinstance(value, str) or not title or len(title) > 300:
        return None
    try:
        url = urlsplit(value)
        if (
            url.scheme != "https"
            or url.hostname != "ke.expertini.com"
            or url.username is not None
            or url.password is not None
            or url.port is not None
            or url.query
            or url.fragment
        ):
            return None
        identity = re.fullmatch(
            r"/jobs/job/[a-z0-9-]+?-(?P<id>[a-f0-9]{32}(?:[a-f0-9]{3})?|\d{6,}|\d{1,8}-\d{1,12})/",
            url.path,
        )
        if (
            not identity
            or NON_IT_CONTEXT.search(title)
            or not classify_technology_title(title).category
        ):
            return None
        published = None
        date = item.findtext("pubDate")
        if date:
            try:
                candidate = parsedate_to_datetime(date)
                if candidate.tzinfo is not None and candidate <= datetime.now(UTC):
                    published = candidate.astimezone(UTC)
            except (ValueError, TypeError, OverflowError):
                pass
        return RawJob(
            source_id="expertini",
            source_publisher="Expertini RSS",
            external_id=identity["id"],
            title=title.strip(),
            location="Kenya",
            source_url=value,
            apply_url=value,
            published_at=published,
        )
    except ValueError:
        return None


class ExpertiniSitemapAdapter:
    source_id = "expertini"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client()
        self.max_pages = 5
        self.crawl_complete = False

    def _read_xml(self, url: str, expected_root: str):
        response = self._client.get(url, timeout=25, follow_redirects=False)
        response.raise_for_status()
        if len(response.content) > 20_000_000:
            raise ValueError("Expertini XML response exceeds bounded size")
        root = ElementTree.fromstring(response.content)
        expected_tag = "rss" if expected_root == "rss" else f"{{{NS['s']}}}{expected_root}"
        if root.tag != expected_tag or (expected_root == "rss" and root.find("channel") is None):
            raise ValueError("Invalid Expertini sitemap response")
        return root

    def fetch(self) -> list[RawJob]:
        self.crawl_complete = False
        rss = self._read_xml(RSS_URL, "rss")
        # RSS metadata wins when both snapshots expose the same native numeric ID.
        jobs: dict[str, RawJob] = {}
        for item in rss.findall("channel/item"):
            raw = parse_rss_item(item)
            if raw:
                jobs.setdefault(raw.external_id, raw)
        index = self._read_xml(INDEX_URL, "sitemapindex")
        pages = list(dict.fromkeys(index.findall("s:sitemap/s:loc", NS)))
        urls = list(dict.fromkeys(e.text for e in pages))
        if not urls or any(
            not isinstance(url, str)
            or not re.fullmatch(r"https://ke\.expertini\.com/job_listing\d+\.xml", url)
            for url in urls
        ):
            raise ValueError("Unrecognized Expertini listing sitemap")
        for url in urls[: self.max_pages]:
            root = self._read_xml(url, "urlset")
            entries = root.findall("s:url", NS)
            if not entries:
                raise ValueError("Empty Expertini listing sitemap")
            for entry in entries:
                raw = parse_listing_link(entry.findtext("s:loc", namespaces=NS))
                if raw:
                    jobs.setdefault(raw.external_id, raw)
        self.crawl_complete = len(urls) <= self.max_pages
        return list(jobs.values())
