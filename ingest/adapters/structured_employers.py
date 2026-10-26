"""Reviewed structured-data, feed, listing and multi-role PDF employer collectors."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
from datetime import UTC, datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import parse_qs, urljoin, urlsplit
from uuid import uuid4
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import httpx

from ingest.adapters.registry_boards import RegistryBoardAdapter
from ingest.dedupe.exact import canonicalize_apply_url
from ingest.employer_registry import safe_url
from ingest.http_policy import CollectionBlocked, checked_get, read_robots
from ingest.models import RawJob

METHODS = {"jsonld", "rss", "html", "pdf"}


def public_target(url):
    if not safe_url(url):
        raise ValueError("Unsafe vacancy URL")
    host = urlsplit(url).hostname
    if host and any(
        host == domain or host.endswith("." + domain)
        for domain in ("linkedin.com", "facebook.com", "fb.com")
    ):
        raise ValueError("Social-network collection is not permitted")
    addresses = socket.getaddrinfo(host, urlsplit(url).port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Vacancy URL must resolve publicly")


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.postings, self.links = [], []
        self.next_url = None
        self.capture = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"a", "link"} and attrs.get("href"):
            self.links.append(attrs["href"])
            if "next" in attrs.get("rel", "").split():
                self.next_url = attrs["href"]
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.capture, self.parts = True, []

    def handle_data(self, text):
        if self.capture:
            self.parts.append(text)

    def handle_endtag(self, tag):
        if tag != "script" or not self.capture:
            return
        self.capture = False
        try:
            value = json.loads("".join(self.parts))
        except ValueError:
            return
        pending = value if isinstance(value, list) else [value]
        while pending:
            node = pending.pop()
            if not isinstance(node, dict):
                continue
            kinds = node.get("@type", [])
            if "JobPosting" in ([kinds] if isinstance(kinds, str) else kinds):
                self.postings.append(node)
            pending.extend(node.get("@graph", []))
            pending.extend(node.get("itemListElement", []))
            if isinstance(node.get("item"), dict):
                pending.append(node["item"])


def place_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " · ".join(filter(None, (place_text(item) for item in value)))
    if isinstance(value, dict):
        if value.get("address"):
            return place_text(value["address"])
        return " · ".join(
            filter(
                None,
                (
                    place_text(value.get(k))
                    for k in ("addressLocality", "addressRegion", "addressCountry", "name")
                ),
            )
        )
    return ""


class StructuredEmployerAdapter:
    _job = RegistryBoardAdapter._job

    def __init__(self, source, employers, client=None, validator=public_target):
        self.source, self.employers = source, employers
        self.source_id = source["id"]
        self.platform = source["access_method"]
        self.settings = source["collection"]
        self.endpoint = self.settings["listing_url"]
        self._client = client or httpx.Client(headers={"User-Agent": "TechKaziBot/0.1"})
        self.validator = validator
        self.candidate_state = {"items": {}}
        self.crawl_complete = False
        self.max_pages = source["crawl"]["max_pages"]
        self.robots = {}
        self.detail_failures = 0

    def target(self, url):
        self.validator(url)
        allowed = set(self.settings.get("allowed_hosts", [])) | {urlsplit(self.endpoint).hostname}
        if urlsplit(url).hostname not in allowed:
            raise ValueError("Unreviewed vacancy host")

    def get(self, url, **kwargs):
        self.target(url)
        origin = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}"
        if origin not in self.robots:
            self.robots[origin], _ = read_robots(self._client, url, self.target)
        rules = self.robots[origin]
        if not rules.can_fetch("TechKaziBot/0.1", url):
            raise CollectionBlocked("Employer source disallows collection")
        delay = rules.crawl_delay("TechKaziBot/0.1") or rules.crawl_delay("*") or 0
        if delay > 60:
            raise ValueError("Crawl delay requires manual scheduling")
        if hasattr(self._client, "policy"):
            self._client.policy["request_delay_ms"] = max(
                self._client.policy.get("request_delay_ms", 1500), delay * 1000
            )
        response = checked_get(self._client, url, self.target, **kwargs)
        limit = min(self.settings.get("max_response_bytes", 2_000_000), 5_000_000)
        if len(response.content) > limit:
            raise ValueError("Employer response exceeds budget")
        return response

    def identity(self, url, identifier=None):
        if isinstance(identifier, dict):
            identifier = identifier.get("value")
        if identifier:
            return str(identifier)
        query_key = self.settings.get("identifier_query_parameter")
        if query_key:
            values = parse_qs(urlsplit(url).query).get(query_key, [])
            if len(values) != 1 or not values[0].strip():
                raise ValueError("Vacancy URL lacks its reviewed query identifier")
            return values[0]
        pattern = self.settings.get("identifier_url_pattern")
        if pattern:
            match = re.search(pattern, urlsplit(url).path)
            if not match:
                raise ValueError("Vacancy URL lacks the reviewed immutable posting ID")
            return match.group(1)
        identities = self.candidate_state.setdefault("url_identities", {})
        for original_url, identity in self.settings.get("initial_url_identities", {}).items():
            key = canonicalize_apply_url(original_url)
            if key in identities and identities[key] != identity:
                raise ValueError("Reviewed URL identity conflicts with persistent identity")
            identities[key] = identity
        return identities.setdefault(canonicalize_apply_url(url), str(uuid4()))

    def json_job(self, item, detail_url):
        if (
            detail_url == self.endpoint
            and not item.get("url")
            and not self.settings.get("listing_is_single_vacancy")
        ):
            raise ValueError("Listing record has no individual vacancy destination")
        url = urljoin(detail_url, item.get("url") or detail_url)
        identifier = self.identity(url, item.get("identifier"))
        location = place_text(item.get("jobLocation"))
        if item.get("jobLocationType") == "TELECOMMUTE":
            location = "Remote · " + place_text(
                item.get("applicantLocationRequirements") or location
            )
        return self._job(
            identifier,
            item.get("title"),
            location,
            url,
            description=item.get("description"),
            published=item.get("datePosted"),
            deadline=item.get("validThrough"),
            employment_type=item.get("employmentType"),
        )

    def detail(self, url):
        key = self.identity(url)
        now = datetime.now(UTC)
        row = self.candidate_state["items"].setdefault(
            key,
            {
                "external_id": key,
                "detail_url": url,
                "first_seen_at": now.isoformat(),
                "processing_status": "awaiting_extraction",
                "attempts": 0,
            },
        )
        if row.get("next_attempt_at") and now < datetime.fromisoformat(row["next_attempt_at"]):
            self.detail_failures += 1
            return []
        try:
            headers = {}
            if self.settings.get("conditional_verified") and row.get("parsed_metadata"):
                if row.get("etag"):
                    headers["If-None-Match"] = row["etag"]
                elif row.get("last_modified"):
                    headers["If-Modified-Since"] = row["last_modified"]
            response = self.get(url, headers=headers)
            if response.status_code == 304 and not row.get("parsed_metadata"):
                raise ValueError("Not-modified response without validated cached metadata")
            fingerprint = (
                row.get("content_hash")
                if response.status_code == 304
                else hashlib.sha256(response.content).hexdigest()
            )
            # The detail body was actually fetched; reuse only its parsed compact fields.
            if (response.status_code == 304 or row.get("content_hash") == fingerprint) and row.get(
                "parsed_metadata"
            ):
                jobs = [RawJob.model_validate(item) for item in row["parsed_metadata"]]
            else:
                parser = Page()
                parser.feed(response.text)
                fields = {}
                for name, pattern in self.settings.get("fields", {}).items():
                    match = re.search(pattern, response.text, re.I | re.S)
                    if match:
                        fields[name] = unescape(re.sub(r"<[^>]+>", " ", match.group(1))).strip()
                for name, date_format in self.settings.get("field_date_formats", {}).items():
                    if not fields.get(name):
                        continue
                    value = re.sub(r"(?<=\d)(st|nd|rd|th)\b", "", fields[name], flags=re.I)
                    value = " ".join(value.replace(",", " ").split())
                    parsed = datetime.strptime(value, date_format).replace(
                        tzinfo=ZoneInfo(self.settings.get("date_timezone", "UTC"))
                    )
                    if name == "deadline" and not any(
                        token in date_format for token in ("%H", "%I")
                    ):
                        parsed = parsed.replace(hour=23, minute=59, second=59)
                    fields[name] = parsed.isoformat()
                jobs = [
                    self.json_job(
                        {**item, "identifier": item.get("identifier") or fields.get("identifier")},
                        str(response.url),
                    )
                    for item in parser.postings
                ]
                if not parser.postings and self.settings.get("fields"):
                    jobs = [
                        self._job(
                            self.identity(url, fields.get("identifier")),
                            fields.get("title"),
                            fields.get("location"),
                            url,
                            description=fields.get("description"),
                            published=fields.get("published"),
                            deadline=fields.get("deadline"),
                            employment_type=fields.get("employment_type"),
                        )
                    ]
                jobs = [
                    job.model_copy(update={"location": fields["location"]})
                    if job and not job.location and fields.get("location")
                    else job
                    for job in jobs
                ]
                jobs = [job for job in jobs if job]
                if not jobs and parser.postings:
                    row.update(processing_status="filtered", attempts=0, next_attempt_at=None)
                    return []  # Recognized talent pools/internal posts are deliberate exclusions.
                if not jobs:
                    raise ValueError("No individual vacancy data")
            row.update(
                etag=response.headers.get("etag") or row.get("etag"),
                last_modified=response.headers.get("last-modified") or row.get("last_modified"),
                content_hash=fingerprint,
                processing_status="extracted",
                attempts=0,
                next_attempt_at=None,
                parsed_metadata=[
                    {
                        **job.model_dump(mode="json"),
                        "technical_context": job.technical_context,
                        "applicant_africa": job.applicant_africa,
                    }
                    for job in jobs
                ],
            )
            for job in jobs:
                self.candidate_state["items"].setdefault(
                    str(job.external_id),
                    {
                        "external_id": job.external_id,
                        "first_seen_at": row["first_seen_at"],
                        "processing_status": "seen",
                    },
                )
            return jobs
        except Exception as exc:
            row["attempts"] += 1
            row.update(
                processing_status="awaiting_extraction",
                error_type=type(exc).__name__,
                next_attempt_at=(now + timedelta(hours=min(2 ** row["attempts"], 48))).isoformat(),
            )
            self.detail_failures += 1
            if isinstance(exc, CollectionBlocked) or getattr(
                getattr(exc, "response", None), "status_code", None
            ) in (401, 403, 429):
                raise
            return []

    def pdf(self, response):
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(response.content))
        if reader.is_encrypted or len(reader.pages) > 30:
            raise ValueError("PDF requires manual review")
        text = ""
        for page in reader.pages:
            stream = page.get_contents()
            if stream and len(stream.get_data()) > 2_000_000:
                raise ValueError("PDF text stream exceeds budget")
            text += (page.extract_text() or "") + "\n"
        if not text.strip():
            raise ValueError("Scanned PDF requires reviewed OCR")
        pattern = self.settings.get("role_pattern")
        if not pattern:
            raise ValueError("PDF needs a reviewed requisition extraction rule")
        jobs = []
        for match in re.finditer(pattern, text, re.M):
            fields = match.groupdict()
            if not fields.get("identifier"):
                raise ValueError("PDF role lacks a durable identifier")
            job = self._job(
                fields["identifier"],
                fields.get("title"),
                fields.get("location") or self.settings.get("location"),
                str(response.url),
                description=match.group(),
                deadline=fields.get("deadline") or self.settings.get("deadline"),
            )
            if job:
                jobs.append(job.model_copy(update={"shared_apply_url": True}))
        if not jobs:
            raise ValueError("PDF has no verified individual vacancy matches")
        return jobs

    def fetch(self):
        self.crawl_complete = False
        self.detail_failures = 0
        jobs, seen_pages, seen_links = [], set(), set()
        expected_links = None
        url = self.endpoint
        for _ in range(self.max_pages):
            if url in seen_pages:
                raise ValueError("Listing pagination cycle")
            seen_pages.add(url)
            response = self.get(url)
            if self.platform == "pdf":
                jobs.extend(self.pdf(response))
                self.crawl_complete = self.settings.get("complete_listing_verified", False)
                break
            if self.platform == "rss":
                root = ET.fromstring(response.content)
                entries = root.findall(".//item") + root.findall(
                    "{http://www.w3.org/2005/Atom}entry"
                )
                if not entries and not self.settings.get("verified_empty_feed"):
                    raise ValueError("Unrecognized or empty vacancy feed")
                links = []
                for entry in entries:
                    link = entry.findtext("link")
                    if not link:
                        node = entry.find("{http://www.w3.org/2005/Atom}link")
                        link = node.get("href") if node is not None else None
                    if link:
                        links.append(urljoin(url, link))
                next_nodes = root.findall("{http://www.w3.org/2005/Atom}link")
                next_nodes += root.findall("{http://www.w3.org/2005/Atom}link[@rel='next']")
                next_url = next(
                    (
                        urljoin(str(response.url), node.get("href"))
                        for node in next_nodes
                        if node.get("rel") == "next" and node.get("href")
                    ),
                    None,
                )
                # Feeds are discovery endpoints; vacancy fields must come from details.
                page_postings = []
            else:
                parser = Page()
                parser.feed(response.text)
                if len(seen_pages) == 1 and self.settings.get("declared_count_pattern"):
                    text = unescape(re.sub(r"<[^>]+>", " ", response.text))
                    matches = re.findall(self.settings["declared_count_pattern"], text, re.I)
                    if not matches:
                        raise ValueError("Listing no longer supplies its reviewed vacancy total")
                    counts = [int(value) for value in matches]
                    expected_links = (
                        sum(counts) if self.settings.get("sum_declared_counts") else counts[0]
                    )
                page_postings = (
                    [] if self.settings.get("ignore_listing_postings") else parser.postings
                )
                pattern = self.settings.get("detail_url_pattern")
                links = [
                    urljoin(str(response.url), link)
                    for link in parser.links
                    if pattern and re.search(pattern, urljoin(str(response.url), link))
                ]
                embedded = self.settings.get("embedded_detail_url_pattern")
                if embedded:
                    links.extend(
                        unescape(match.group(0)) for match in re.finditer(embedded, response.text)
                    )
                next_url = urljoin(str(response.url), parser.next_url) if parser.next_url else None
                pagination = self.settings.get("pagination_url_pattern")
                if pagination and not next_url:
                    candidates = {
                        urljoin(str(response.url), link)
                        for link in parser.links
                        if re.search(pagination, urljoin(str(response.url), link))
                    }
                    unseen = candidates - seen_pages
                    if len(unseen) > 1:
                        raise ValueError("Ambiguous listing pagination")
                    if candidates and not unseen:
                        raise ValueError("Listing pagination cycle")
                    next_url = next(iter(unseen), None)
                if (
                    not page_postings
                    and not links
                    and not re.search(
                        self.settings.get("empty_marker", r"(?!)"), response.text, re.I
                    )
                ):
                    raise ValueError("Unrecognized vacancy listing")
            jobs.extend(
                job for item in page_postings if (job := self.json_job(item, str(response.url)))
            )
            for link in sorted(set(links) - seen_links):
                seen_links.add(link)
                jobs.extend(self.detail(link))
            if not next_url:
                self.crawl_complete = not self.detail_failures and self.settings.get(
                    "complete_listing_verified", False
                )
                break
            url = next_url
        # Retry discovered details even if they disappear from a bounded feed.
        for row in list(self.candidate_state["items"].values()):
            link = row.get("detail_url")
            if (
                row.get("processing_status") == "awaiting_extraction"
                and link
                and link not in seen_links
            ):
                jobs.extend(self.detail(link))
        if self.detail_failures:
            self.crawl_complete = False
        if expected_links is not None and len(seen_links) != expected_links:
            self.crawl_complete = False
        return jobs
