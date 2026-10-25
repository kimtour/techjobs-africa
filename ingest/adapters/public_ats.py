"""Reviewed public Oracle, Workable and Workday vacancy interfaces."""

from __future__ import annotations

import re
from urllib.parse import urlencode, urljoin, urlsplit

from ingest.adapters.structured_employers import StructuredEmployerAdapter
from ingest.classify.tech import classify_technology_title, needs_detail_technical_context
from ingest.http_policy import CollectionBlocked, read_robots

API_METHODS = {"oracle", "workable", "workday"}


def label(value):
    if isinstance(value, dict):
        return value.get("descriptor") or value.get("name") or ""
    return str(value or "")


class PublicATSAdapter(StructuredEmployerAdapter):
    @staticmethod
    def _card_identity(card):
        """Read the immutable requisition suffix; never use a title slug as ID."""
        path = urlsplit(card["externalPath"]).path.rstrip("/")
        for value in card.get("bulletFields") or []:
            if (
                isinstance(value, str)
                and re.fullmatch(r"[A-Za-z]{1,12}[-_]?\d+", value)
                and path.endswith("_" + value)
            ):
                return value
        match = re.search(r"_([A-Za-z]{1,12}[-_]?\d+)$", path)
        return match.group(1) if match else None

    def fetch(self):
        self.crawl_complete = False
        return getattr(self, "_" + self.platform)()

    def _workable(self):
        response = self.get(self.endpoint + "?details=true")
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ValueError("Missing published Workable jobs array")
        grouped = {}
        for item in payload["jobs"]:
            key = item.get("shortcode")
            if not key:
                raise ValueError("Workable vacancy lacks immutable shortcode")
            row = grouped.setdefault(key, {"record": item, "places": []})
            if row["record"].get("title") != item.get("title"):
                raise ValueError("Inconsistent repeated Workable posting")
            places = item.get("locations") or [item]
            for place in places:
                if place.get("hidden"):
                    continue
                location = " · ".join(
                    dict.fromkeys(filter(None, (place.get("city"), place.get("country"))))
                )
                if location and location not in row["places"]:
                    row["places"].append(location)
        jobs = []
        for key, row in grouped.items():
            item = row["record"]
            location = " / ".join(row["places"])
            if item.get("telecommuting"):
                location = "Remote · " + location
            job = self._job(
                key,
                item.get("title"),
                location,
                item.get("url"),
                apply_url=item.get("application_url") or item.get("url"),
                published=item.get("published_on"),
                employment_type=item.get("employment_type"),
                description=item.get("description"),
            )
            if job:
                jobs.append(job)
        self.crawl_complete = True
        return jobs

    def _oracle(self):
        jobs, seen = [], set()
        offset = 0
        expected = None
        for _ in range(self.max_pages):
            query = urlencode(
                {
                    "finder": (
                        f"findReqs;siteNumber={self.settings['site']},limit=25,offset={offset}"
                    ),
                    "onlyData": "true",
                    "expand": "requisitionList",
                }
            )
            payload = self.get(self.endpoint + "?" + query).json()
            wrappers = payload.get("items") if isinstance(payload, dict) else None
            if not isinstance(wrappers, list) or len(wrappers) != 1:
                raise ValueError("Missing Oracle public requisition search")
            result = wrappers[0]
            total = result.get("TotalJobsCount")
            records = result.get("requisitionList")
            if not isinstance(total, int) or not isinstance(records, list):
                raise ValueError("Oracle search lacks total or requisitions")
            if expected is not None and expected != total:
                raise ValueError("Oracle inventory changed during pagination")
            expected = total
            for item in records:
                key = str(item.get("Id") or "")
                if not key or key in seen:
                    raise ValueError("Missing or repeated Oracle requisition ID")
                seen.add(key)
                url = self.settings["job_url_template"].format(id=key)
                description = " ".join(
                    str(item.get(field) or "")
                    for field in (
                        "ShortDescriptionStr",
                        "ExternalQualificationsStr",
                        "ExternalResponsibilitiesStr",
                    )
                )
                location = " · ".join(
                    dict.fromkeys(
                        filter(
                            None, (item.get("PrimaryLocation"), item.get("PrimaryLocationCountry"))
                        )
                    )
                )
                job = self._job(
                    key,
                    item.get("Title"),
                    location,
                    url,
                    published=item.get("PostedDate"),
                    deadline=item.get("PostingEndDate"),
                    employment_type=item.get("JobSchedule") or item.get("WorkerType"),
                    description=description,
                )
                if job:
                    # A shared group board can advertise another legal entity.
                    # Keep its public employer label instead of the registry's
                    # country-specific lead (for example KCB Kenya vs Uganda).
                    employer = label(item.get("LegalEmployer"))
                    if employer:
                        identity = " ".join(employer.split()).casefold()
                        matches = [
                            self.employers[eid]
                            for eid in self.source["employer_ids"]
                            if identity
                            in {
                                " ".join(name.split()).casefold()
                                for name in [
                                    self.employers[eid]["name"],
                                    *self.employers[eid].get("aliases", []),
                                ]
                            }
                        ]
                        matched = matches[0] if len(matches) == 1 else None
                        job = job.model_copy(
                            update={
                                "company": employer,
                                "employer_id": matched["id"] if matched else None,
                                "employer_sectors": matched["sectors"] if matched else [],
                            }
                        )
                    jobs.append(job)
            offset += len(records)
            if offset == total:
                self.crawl_complete = True
                break
            if not records or offset > total:
                raise ValueError("Oracle pagination does not match its declared total")
        return jobs

    def _post_search(self, body):
        self.target(self.endpoint)
        parsed = urlsplit(self.endpoint)
        origin = parsed.scheme + "://" + parsed.netloc
        if origin not in self.robots:
            self.robots[origin], _ = read_robots(self._client, self.endpoint, self.target)
        rules = self.robots[origin]
        if not rules.can_fetch("TechKaziBot/0.1", self.endpoint):
            raise CollectionBlocked("Workday search disallows collection")
        delay = rules.crawl_delay("TechKaziBot/0.1") or rules.crawl_delay("*") or 0
        if delay > 60:
            raise CollectionBlocked("Workday crawl delay requires separate scheduling")
        if hasattr(self._client, "policy"):
            self._client.policy["request_delay_ms"] = max(
                self._client.policy.get("request_delay_ms", 1500), delay * 1000
            )
        response = self._client.post(self.endpoint, json=body, timeout=20)
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            raise ValueError("Workday search exceeds response budget")
        return response.json()

    def _workday(self):
        cards, seen, offset, expected = [], set(), 0, None
        for _ in range(self.max_pages):
            payload = self._post_search(
                {
                    "appliedFacets": self.settings.get("facets", {}),
                    "limit": 20,
                    "offset": offset,
                    "searchText": "",
                }
            )
            total, records = payload.get("total"), payload.get("jobPostings")
            if not isinstance(total, int) or not isinstance(records, list):
                raise ValueError("Missing Workday public search result")
            if expected is not None and total not in (0, expected):
                raise ValueError("Workday inventory changed during pagination")
            # Continuation pages use zero as an omitted-total sentinel.
            if expected is None:
                expected = total
            for card in records:
                path = card.get("externalPath")
                if not path or path in seen or not path.startswith("/job/"):
                    raise ValueError("Missing or repeated Workday vacancy path")
                seen.add(path)
                cards.append(card)
            offset += len(records)
            if offset == expected:
                break
            if not records or offset > expected:
                raise ValueError("Workday pagination does not match its declared total")
        if offset != expected:
            return []  # A truncated search never looks like a complete empty board.
        jobs, ids = [], set()
        for card in cards:
            path = card["externalPath"]
            title = card.get("title")
            card_id = self._card_identity(card)
            # The same deterministic title/context rules run in the pipeline.
            # Fetch details only where they can affect technical classification;
            # this preserves full board coverage on large finance/clinical boards.
            if (
                title
                and card_id
                and not classify_technology_title(title).category
                and not needs_detail_technical_context(title)
            ):
                if card_id in ids:
                    raise ValueError("Repeated Workday requisition")
                ids.add(card_id)
                job = self._job(
                    card_id,
                    title,
                    card.get("locationsText"),
                    self.settings["public_board_url"].rstrip("/") + path,
                )
                if job:
                    jobs.append(job)
                continue
            payload = self.get(self.endpoint.removesuffix("/jobs") + path).json()
            item = payload.get("jobPostingInfo")
            if not isinstance(item, dict) or not item.get("jobReqId"):
                raise ValueError("Missing Workday individual requisition")
            key = str(item["jobReqId"])
            if card_id is not None and card_id != key:
                raise ValueError("Workday card and detail requisition IDs disagree")
            if key in ids:
                raise ValueError("Repeated Workday requisition")
            ids.add(key)
            location = " / ".join(
                dict.fromkeys(
                    filter(
                        None,
                        [label(item.get("location")), label(item.get("country"))]
                        + [label(v) for v in item.get("additionalLocations") or []],
                    )
                )
            ) or card.get("locationsText")
            url = item.get("externalUrl") or (self.settings["public_board_url"].rstrip("/") + path)
            if urlsplit(url).hostname != urlsplit(self.settings["public_board_url"]).hostname:
                raise ValueError("Unreviewed Workday application host")
            job = self._job(
                key,
                item.get("title"),
                location,
                urljoin(self.settings["public_board_url"], url),
                published=item.get("startDate"),
                deadline=item.get("endDate"),
                employment_type=label(item.get("timeType")),
                description=item.get("jobDescription"),
            )
            if job:
                jobs.append(job)
        self.crawl_complete = True
        return jobs
