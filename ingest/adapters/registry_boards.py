"""Configuration-driven, read-only public ATS connectors for verified boards."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from ingest.classify.evidence import description_technical_context
from ingest.classify.tech import has_non_technical_exclusion
from ingest.employer_registry import safe_url
from ingest.models import RawJob

SUPPORTED = {"ashby", "greenhouse", "lever", "breezy"}


def timestamp(value):
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000, UTC)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (ValueError, OverflowError, OSError):
        return None


def board_endpoint(source: dict) -> str:
    platform, board = source["platform"], source.get("board", "")
    if platform not in SUPPORTED or not re.fullmatch(r"[A-Za-z0-9_-]+", board):
        raise ValueError("Unsupported or missing verified board")
    token = quote(board, safe="")
    if platform == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{token}"
    if platform == "greenhouse":
        # The documented public endpoint; a board that cannot be resolved stays pending.
        return f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    if platform == "lever":
        host = "api.eu.lever.co" if source.get("region") == "eu" else "api.lever.co"
        return f"https://{host}/v0/postings/{token}?mode=json"
    return f"https://{board}.breezy.hr/"


class _BreezyPage(HTMLParser):
    """Read public vacancy links and JobPosting JSON-LD, never arbitrary page text."""

    def __init__(self):
        super().__init__()
        self.links = set()
        self.jsonld = []
        self.capture = False
        self.parts = []
        self.titles = {}
        self.active_link = None
        self.heading = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and re.match(r"^/p/[^/?#]+", attrs.get("href", "")):
            self.links.add(attrs["href"])
            self.active_link = attrs["href"]
            self.titles[self.active_link] = ""
        if tag == "h2" and self.active_link:
            self.heading = True
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.capture = True
            self.parts = []

    def handle_data(self, data):
        if self.heading and self.active_link:
            self.titles[self.active_link] += data
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "h2":
            self.heading = False
        if tag == "a":
            self.active_link = None
        if tag == "script" and self.capture:
            import json

            try:
                value = json.loads("".join(self.parts))
                self.jsonld.extend(value if isinstance(value, list) else [value])
            except ValueError:
                pass
            self.capture = False


class RegistryBoardAdapter:
    """Every source retains its own identity, budget, health and expiry policy."""

    def __init__(self, source: dict, employers: dict, client=None):
        self.source = source
        self.source_id = source["id"]
        self.platform = source["platform"]
        self.endpoint = board_endpoint(source)
        self.employers = employers
        self._client = client or httpx.Client(headers={"User-Agent": "TechKaziBot/0.1"})
        self.crawl_complete = False
        self.max_pages = source.get("crawl", {}).get("max_pages", 5)
        self.invalid_records = 0

    def _job(
        self,
        external_id,
        title,
        location,
        url,
        *,
        apply_url=None,
        description=None,
        published=None,
        employment_type=None,
        deadline=None,
    ):
        if not external_id or not title or not safe_url(url) or not safe_url(apply_url or url):
            raise ValueError("Malformed public vacancy")
        # Do not turn prospect pools, training or volunteer signups into employment.
        if re.search(
            r"\b(talent (pool|community|network)|expression of interest|"
            r"general application|volunteer|training enrolment)\b",
            title,
            re.I,
        ):
            return None
        ids = self.source["employer_ids"]
        employer = self.employers[ids[0]] if len(ids) == 1 else None
        if isinstance(employment_type, list):
            employment_type = ", ".join(str(t) for t in employment_type)
        opportunity = "employment"
        if re.search(r"\b(intern|internship)\b", title, re.I):
            opportunity = "internship"
        elif re.search(r"\b(consultant|consultancy)\b", title, re.I):
            opportunity = "consultancy"
        elif re.search(r"\b(fellow|fellowship)\b", title, re.I):
            opportunity = "fellowship"
        return RawJob(
            source_id=self.source_id,
            external_id=str(external_id),
            title=title,
            company=employer["name"] if employer else None,
            location=location,
            source_url=url,
            apply_url=apply_url or url,
            source_publisher=f"{employer['name'] if employer else 'Employer board'} careers / "
            f"{self.platform.title()}",
            published_at=timestamp(published),
            deadline_at=timestamp(deadline),
            employment_type=employment_type,
            employer_id=employer["id"] if employer else None,
            employer_sectors=employer["sectors"] if employer else [],
            direct_employer=True,
            opportunity_type=opportunity,
            technical_context=description_technical_context(title, description),
        )

    def fetch(self):
        self.crawl_complete = False
        self.invalid_records = 0
        if self.platform == "breezy":
            return self._breezy()
        rows = []
        offset = 0
        for _ in range(self.max_pages):
            url = self.endpoint
            if self.platform == "lever":
                url += f"&skip={offset}&limit=100"
            response = self._client.get(url, timeout=20)
            response.raise_for_status()
            payload = response.json()
            if self.platform in {"ashby", "greenhouse"}:
                if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
                    raise ValueError("Missing public jobs array")
                records = payload["jobs"]
                if self.platform == "greenhouse":
                    total = payload.get("meta", {}).get("total")
                    if total is not None and total != len(records):
                        raise ValueError("Incomplete public jobs array")
            elif isinstance(payload, list):
                records = payload
            else:
                raise ValueError("Missing public postings array")
            for item in records:
                if not isinstance(item, dict):
                    raise ValueError("Malformed posting record")
                job = self._parse(item)
                if job:
                    rows.append(job)
            if self.platform != "lever" or len(records) < 100:
                self.crawl_complete = True
                break
            offset += len(records)
        return rows

    def _parse(self, item):
        if self.platform == "ashby":
            if item.get("isListed") is not True:
                return None
            locations = [item.get("location")]
            locations += [
                v.get("location") for v in item.get("secondaryLocations", []) if isinstance(v, dict)
            ]
            location = " · ".join(v for v in locations if v)
            if item.get("isRemote") or item.get("workplaceType") == "Remote":
                location = "Remote · " + location
            return self._job(
                item.get("id"),
                item.get("title"),
                location,
                item.get("jobUrl"),
                apply_url=item.get("applyUrl"),
                description=item.get("descriptionHtml") or item.get("descriptionPlain"),
                published=item.get("publishedAt"),
                employment_type=item.get("employmentType"),
            )
        if self.platform == "greenhouse":
            if item.get("internal_job_id") is None:
                return None  # Greenhouse prospect posts are not vacancies.
            return self._job(
                item.get("id"),
                item.get("title"),
                (item.get("location") or {}).get("name"),
                item.get("absolute_url"),
                description=item.get("content"),
            )
        categories = item.get("categories") or {}
        location = " · ".join(categories.get("allLocations") or [categories.get("location", "")])
        if item.get("workplaceType") == "remote":
            location = "Remote · " + location
        return self._job(
            item.get("id"),
            item.get("text"),
            location,
            item.get("hostedUrl"),
            apply_url=item.get("applyUrl"),
            description=item.get("descriptionPlain"),
            employment_type=categories.get("commitment"),
        )

    def _breezy(self):
        try:
            robots = self._client.get(self.endpoint + "robots.txt", timeout=20)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 404:
                raise
            robots = exc.response
        rules = RobotFileParser()
        rules.parse(robots.text.splitlines() if robots.status_code == 200 else [])
        if not rules.can_fetch("TechKaziBot/0.1", self.endpoint):
            raise ValueError("Public board disallows collection")
        response = self._client.get(self.endpoint, timeout=20)
        response.raise_for_status()
        page = _BreezyPage()
        page.feed(response.text)
        # Never accept a login/challenge/changed template as an empty board.
        if not page.links and not re.search(
            r"(no (current |open )?(positions|openings)|"
            r"%HEADER_OUR_OPENINGS%|position-list)",
            response.text,
            re.I,
        ):
            raise ValueError("Unrecognized public board")
        jobs = []
        for path in sorted(page.links):
            url = urljoin(self.endpoint, path)
            # Explicit nontechnical cards can be rejected from their own title;
            # do not fetch unrelated descriptions merely to reject a sales role.
            card_title = page.titles.get(path, "").strip()
            if card_title and has_non_technical_exclusion(card_title):
                job = self._job(
                    urlsplit(path).path.split("/")[2].split("-")[0], card_title, None, url
                )
                if job:
                    jobs.append(job)
                continue
            if not rules.can_fetch("TechKaziBot/0.1", url):
                raise ValueError("Public posting disallows collection")
            detail = self._client.get(url, timeout=20)
            detail.raise_for_status()
            parser = _BreezyPage()
            parser.feed(detail.text)
            postings = [
                p for p in parser.jsonld if isinstance(p, dict) and p.get("@type") == "JobPosting"
            ]
            if len(postings) != 1:
                raise ValueError("Missing unique job structured data")
            item = postings[0]
            locations = item.get("jobLocation") or []
            if isinstance(locations, dict):
                locations = [locations]
            labels = []
            for loc in locations:
                address = loc.get("address") or {}
                labels.extend(
                    str(address[k]) for k in ("addressLocality", "addressCountry") if address.get(k)
                )
            requirements = item.get("applicantLocationRequirements") or []
            if isinstance(requirements, dict):
                requirements = [requirements]
            for region in requirements:
                if isinstance(region, dict) and region.get("name"):
                    labels.append(region["name"])
            if item.get("jobLocationType") == "TELECOMMUTE":
                labels.insert(0, "Remote")
            job = self._job(
                urlsplit(path).path.split("/")[2].split("-")[0],
                item.get("title"),
                " · ".join(labels),
                url,
                description=item.get("description"),
                published=item.get("datePosted"),
                deadline=item.get("validThrough"),
                employment_type=item.get("employmentType"),
            )
            if job:
                jobs.append(job)
        self.crawl_complete = True
        return jobs
