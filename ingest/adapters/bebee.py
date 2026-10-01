"""Authorized beBee public HTML discovery; metadata only, no internal APIs."""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from ingest.classify.tech import classify_technology_title
from ingest.models import RawJob

LISTING_URL = "https://bebee.com/ke/jobs/industry/technology"


def is_technical_title(title: str) -> bool:
    """Require a technical function, not merely a tech industry or generic QA."""
    if re.search(
        r"\b(recruitment|recruiter|sales|business development|chef|debt collector)\b",
        title,
        re.IGNORECASE,
    ):
        return False
    decision = classify_technology_title(title)
    if decision.category == "QA / Testing" and not re.search(
        r"\b(software|automation|automated|selenium|sdet|qa engineer|test engineer)\b",
        title,
        re.IGNORECASE,
    ):
        return False
    return decision.category is not None


class _MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_heading = False
        self.link = None
        self.title_parts = []
        self.cards = []
        self.in_json = False
        self.json_parts = []
        self.records = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h3":
            self.in_heading = True
            self.title_parts = []
            self.link = None
        if tag == "a" and self.in_heading:
            self.link = attrs.get("href")
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.in_json = True
            self.json_parts = []

    def handle_data(self, data):
        if self.in_heading:
            self.title_parts.append(data)
        if self.in_json:
            self.json_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "h3":
            if self.link:
                self.cards.append((self.link, " ".join("".join(self.title_parts).split())))
            self.in_heading = False
        if tag == "script" and self.in_json:
            self.in_json = False
            try:
                payload = json.loads("".join(self.json_parts))
                self.records.extend(payload if isinstance(payload, list) else [payload])
            except (ValueError, TypeError):
                pass


def listing_links(html: str) -> list[str]:
    parser = _MetadataParser()
    parser.feed(html)
    links = []
    for href, title in parser.cards:
        url = urljoin(LISTING_URL, href)
        parsed = urlsplit(url)
        if (
            parsed.hostname == "bebee.com"
            and parsed.path.startswith("/ke/jobs/")
            and "--" in parsed.path
            and is_technical_title(title)
        ):
            links.append(url)
    return list(dict.fromkeys(links))


def parse_job(html: str, url: str) -> RawJob | None:
    parser = _MetadataParser()
    parser.feed(html)
    for record in parser.records:
        if not isinstance(record, dict) or record.get("@type") != "JobPosting":
            continue
        title = record.get("title")
        if not isinstance(title, str) or not is_technical_title(title):
            continue
        identifier = record.get("identifier", {})
        external_id = identifier.get("value") if isinstance(identifier, dict) else None
        suffix = urlsplit(url).path.rsplit("--", 1)[-1]
        if not isinstance(external_id, str) or external_id != suffix:
            continue
        if not re.fullmatch(r"[a-zA-Z0-9-]+", external_id):
            continue
        place = record.get("jobLocation", {})
        address = place.get("address", {}) if isinstance(place, dict) else {}
        if not isinstance(address, dict) or str(address.get("addressCountry", "")).upper() not in (
            "KE",
            "KENYA",
        ):
            continue
        today = datetime.now(UTC).date()
        try:
            valid = date.fromisoformat(str(record.get("validThrough", ""))[:10])
            if valid < today:
                continue
        except ValueError:
            pass
        try:
            published = date.fromisoformat(str(record.get("datePosted", ""))[:10])
            if published > today:
                published = None
        except ValueError:
            published = None
        company = record.get("hiringOrganization", {})
        company = company.get("name") if isinstance(company, dict) else None
        city = address.get("addressLocality")
        location = f"{city} · Kenya" if isinstance(city, str) and city else "Kenya"
        return RawJob(
            source_id="bebee",
            external_id=external_id,
            title=title[:300],
            company=company[:300] if isinstance(company, str) else None,
            location=location[:300],
            published_date=published,
            source_url=url,
            apply_url=url,
        )
    return None


class BeBeeAdapter:
    source_id = "bebee"

    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(headers={"User-Agent": "TechJobsAfricaBot/0.1"})
        self.max_pages = 10
        self.crawl_complete = False

    def fetch(self) -> list[RawJob]:
        self.crawl_complete = False
        seen = set()
        jobs = []
        for page in range(self.max_pages):
            response = self._client.get(
                LISTING_URL, params={"page": page} if page else {}, follow_redirects=True
            )
            response.raise_for_status()
            if "<h3" not in response.text:
                raise ValueError("Missing beBee listing cards")
            for url in listing_links(response.text):
                if url in seen:
                    continue
                seen.add(url)
                detail = self._client.get(url, follow_redirects=True)
                detail.raise_for_status()
                job = parse_job(detail.text, url)
                if job:
                    jobs.append(job)
        # Bounded discovery does not justify closing absent jobs.
        self.crawl_complete = True
        return jobs
