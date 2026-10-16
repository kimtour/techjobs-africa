"""Verified public employer feeds for Africa/worldwide remote technology jobs."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit

import httpx

from ingest.adapters.ashby import parse_ashby_jobs
from ingest.classify.evidence import description_technical_context
from ingest.classify.tech import classify_technology_title, needs_detail_technical_context
from ingest.models import RawJob
from ingest.normalize.location import normalize_location

ASHBY_EMPLOYERS = {
    "camunda": ("camunda", "Camunda"),
    "blacksmith": ("Blacksmith Agency", "Blacksmith Agency"),
}
SDG_URL = "https://social-discovery-ventures.breezy.hr/"


def _eligible_remote_location(values: list[str], remote: bool) -> str | None:
    if not remote:
        return None
    # Prefer explicit African countries, then wider regions; never infer a
    # country from EMEA, a search query, company boilerplate or timezone.
    for value in values:
        location = normalize_location(value)
        if location.country:
            return f"Remote · {value}"
    for value in values:
        if normalize_location(value).region in (
            "Worldwide",
            "Africa",
            "Sub-Saharan Africa",
            "EMEA",
        ):
            return f"Remote · {value}"
    return None


def parse_employer_ashby(payload: Mapping, source_id: str) -> list[RawJob]:
    board, company = ASHBY_EMPLOYERS[source_id]
    metadata = {job.get("id"): job for job in payload.get("jobs", []) if isinstance(job, Mapping)}
    jobs = []
    for raw in parse_ashby_jobs(payload):
        job = metadata[raw.external_id]
        values = [job.get("location")]
        for secondary in job.get("secondaryLocations") or []:
            if isinstance(secondary, Mapping):
                values.append(secondary.get("location"))
        values = [value.strip() for value in values if isinstance(value, str) and value.strip()]
        remote = (
            job.get("isRemote") is True
            or job.get("workplaceType") == "Remote"
            or any(normalize_location(value).workplace_type == "Remote" for value in values)
        )
        location = _eligible_remote_location(values, remote)
        expected_path = f"/{quote(board, safe='')}/{raw.external_id}"
        if not location or any(
            urlsplit(str(url)).scheme != "https"
            or urlsplit(str(url)).username is not None
            or urlsplit(str(url)).hostname != "jobs.ashbyhq.com"
            or urlsplit(str(url)).path not in (expected_path, expected_path + "/application")
            for url in (raw.source_url, raw.apply_url)
        ):
            continue
        jobs.append(
            raw.model_copy(
                update={
                    "source_id": source_id,
                    "company": company,
                    "location": location,
                    "source_publisher": f"{company} careers / Ashby",
                }
            )
        )
    return jobs


class AshbyEmployerAdapter:
    def __init__(self, source_id: str, client: httpx.Client | None = None) -> None:
        board, _ = ASHBY_EMPLOYERS[source_id]
        self.source_id = source_id
        self.api_url = f"https://api.ashbyhq.com/posting-api/job-board/{quote(board, safe='')}"
        self._client = client or httpx.Client(headers={"User-Agent": "TechKaziBot/0.1"})
        self.crawl_complete = False

    def fetch(self) -> list[RawJob]:
        self.crawl_complete = False
        response = self._client.get(self.api_url, timeout=25)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise ValueError("Employer board must return an object")
        jobs = parse_employer_ashby(payload, self.source_id)
        self.crawl_complete = True
        return jobs


class _BreezyCards(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.heading = False
        self.card = None
        self.cards = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "li":
            if self.depth:
                self.depth += 1
            elif "position-details" in attrs.get("class", "").split():
                self.depth = 1
                self.card = {"title": "", "url": None}
        if self.depth:
            if tag == "h2":
                self.heading = True
            if tag == "a" and not self.card["url"]:
                self.card["url"] = urljoin(SDG_URL, attrs.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "h2":
            self.heading = False
        if tag == "li" and self.depth:
            self.depth -= 1
            if not self.depth:
                url = self.card["url"]
                if url and self.card["title"].strip():
                    self.cards[url] = self.card["title"].strip()
                self.card = None

    def handle_data(self, value):
        if self.depth and self.heading:
            self.card["title"] += value


class _JobPosting(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_json = False
        self.parts = []
        self.jobs = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self.in_json = True
            self.parts = []

    def handle_data(self, value):
        if self.in_json:
            self.parts.append(value)

    def handle_endtag(self, tag):
        if tag == "script" and self.in_json:
            self.in_json = False
            try:
                payload = json.loads("".join(self.parts))
            except ValueError:
                return
            for item in payload if isinstance(payload, list) else [payload]:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    # Whitelist immediately: the description never leaves memory.
                    self.jobs.append(
                        {
                            "technical_context": description_technical_context(
                                item.get("title") or "", item.get("description")
                            ),
                            **{
                                key: item.get(key)
                                for key in (
                                    "title",
                                    "datePosted",
                                    "jobLocationType",
                                    "applicantLocationRequirements",
                                )
                            },
                        }
                    )


def parse_sdg_job(body: str, url: str) -> RawJob | None:
    match = re.fullmatch(r"/p/([a-f0-9]{14})-[a-z0-9-]+", urlsplit(url).path)
    if urlsplit(url).hostname != urlsplit(SDG_URL).hostname or not match:
        return None
    parser = _JobPosting()
    parser.feed(body)
    if len(parser.jobs) != 1:
        raise ValueError("Expected one structured job posting")
    item = parser.jobs[0]
    applicants = item["applicantLocationRequirements"]
    applicants = applicants if isinstance(applicants, list) else [applicants]
    values = [
        entry["name"]
        for entry in applicants
        if isinstance(entry, dict) and isinstance(entry.get("name"), str)
    ]
    location = _eligible_remote_location(values, item["jobLocationType"] == "TELECOMMUTE")
    if not location:
        return None
    try:
        published_date = date.fromisoformat(item["datePosted"])
    except (TypeError, ValueError):
        published_date = None
    return RawJob(
        source_id="sdg",
        source_publisher="Social Discovery Group careers / Breezy",
        external_id=match[1],
        title=item["title"],
        technical_context=item["technical_context"],
        company="Social Discovery Group",
        location=location,
        source_url=url,
        apply_url=url,
        published_date=published_date,
    )


class SocialDiscoveryAdapter:
    source_id = "sdg"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(headers={"User-Agent": "TechKaziBot/0.1"})
        self.crawl_complete = False

    def fetch(self) -> list[RawJob]:
        self.crawl_complete = False
        response = self._client.get(SDG_URL, timeout=25)
        response.raise_for_status()
        parser = _BreezyCards()
        parser.feed(response.text)
        if not parser.cards:
            raise ValueError("Public career board has no job cards")
        jobs = []
        for url, title in parser.cards.items():
            if not classify_technology_title(title).category and not needs_detail_technical_context(
                title
            ):
                continue
            if urlsplit(url).hostname != urlsplit(SDG_URL).hostname:
                continue
            response = self._client.get(url, timeout=25)
            response.raise_for_status()
            job = parse_sdg_job(response.text, url)
            if job:
                jobs.append(job)
        self.crawl_complete = True
        return jobs
