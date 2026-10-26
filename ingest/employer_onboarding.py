"""Bounded discovery and isolated employer trials; never promotes production state."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from ingest.adapters.public_ats import API_METHODS
from ingest.adapters.registry_boards import SUPPORTED, board_endpoint
from ingest.adapters.structured_employers import METHODS
from ingest.audit import read_json
from ingest.dedupe.exact import canonicalize_apply_url, deduplicate_exact
from ingest.employer_registry import ROOT, board_identity, platform_for, safe_url
from ingest.export.static import build_public_files
from ingest.fetch import ObservedClient
from ingest.http_policy import checked_get, robots_allowed
from ingest.main import build_jobs
from ingest.models import CanonicalJob
from ingest.registry_sources import (
    collector_supported,
    load_sources,
    make_adapter,
    verification_gaps,
)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.feeds = []
        self.structured_job_count = 0
        self.capture = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("type") in {"application/rss+xml", "application/atom+xml"}:
            self.feeds.append(attrs.get("href", ""))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.capture = True
            self.parts = []
        for key in ("href", "src"):
            if key in attrs and tag in ("a", "iframe", "script"):
                self.links.append(attrs[key])

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != "script" or not self.capture:
            return
        self.capture = False
        try:
            payload = json.loads("".join(self.parts))
        except ValueError:
            return
        nodes = payload if isinstance(payload, list) else [payload]
        while nodes:
            item = nodes.pop()
            if not isinstance(item, dict):
                continue
            if item.get("@type") == "JobPosting":
                self.structured_job_count += 1
            nodes.extend(item.get("@graph", []))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def candidate_summary(records) -> dict:
    """Rank existing fetched records; never fetch more pages or approve publication."""
    parsed = build_jobs(records)
    eligible = [
        job
        for job in parsed
        if job.eligibility_level in {"CONFIRMED", "LIKELY"}
        and (job.deadline_at is None or job.deadline_at > datetime.now(UTC))
    ]
    return {
        "technical_jobs": len(parsed),
        "eligible_jobs": len(eligible),
        "publication_approved": False,
        "candidate_metadata": [
            {
                "job_id": job.job_id,
                "title": job.title,
                "employer": job.posting_company,
                "country": job.country,
                "application_url": str(job.preferred_apply_url),
            }
            for job in eligible
        ],
    }


def discover(source: dict, employers: dict, client=None, *, request_budget=8) -> dict:
    """Collect metadata only. Discoverability never changes lifecycle or permission."""
    result = {
        "source_id": source["id"],
        "checked_at": datetime.now(UTC).isoformat(),
        "environment": "github" if os.environ.get("GITHUB_ACTIONS") else "local",
        "status": "FAILED",
        "checks": {},
        "requests": [],
    }
    raw_client = client or httpx.Client(headers={"User-Agent": "TechKaziBot/0.1"})
    policy = {**source["crawl"], "max_requests_per_run": request_budget, "retry_delays_seconds": []}
    observed = ObservedClient(raw_client, policy)
    try:
        if source["platform"] == "social" or source["status"] in {"blocked", "retired", "manual"}:
            result["status"] = "SKIPPED"
            return result
        official = source.get("official_careers_url")
        if not official:
            owner = employers[source["employer_ids"][0]]
            official = owner.get("website")
        if not safe_url(official):
            raise ValueError("Missing official employer website")
        result["official_url"] = official
        rule = robots_allowed(observed, official)
        result["official_robots"] = rule
        if not rule["allowed"]:
            result["status"] = "BLOCKED"
            return result
        response = checked_get(observed, official)
        response.raise_for_status()
        links = Links()
        links.feed(response.text)
        urls = [urljoin(str(response.url), link) for link in links.links]
        if urlsplit(str(response.url)).hostname != urlsplit(official).hostname:
            # An official employer careers redirect is itself a board link.
            result["official_redirect"] = str(response.url)
            urls.append(str(response.url))
        # Some official careers pages embed job links in their page data.
        urls += re.findall(
            r'https?://[A-Za-z0-9-]+\.applytojob\.com/apply/[^\s<>"\x27]+', response.text
        )
        if not any(platform_for(url) in SUPPORTED for url in urls if safe_url(url)):
            # Follow one observed employer careers link, never guessed URL variants.
            careers = [
                url
                for url in urls
                if safe_url(url)
                and (urlsplit(url).hostname or "").removeprefix("www.")
                == (urlsplit(str(response.url)).hostname or "").removeprefix("www.")
                and urlsplit(url).path != urlsplit(str(response.url)).path
                and any(
                    term in urlsplit(url).path.casefold()
                    for term in ("/career", "/jobs", "/join-our-team", "/vacanc", "/work-with-us")
                )
            ]
            if careers:
                career_url = careers[0]
                if not robots_allowed(observed, career_url)["allowed"]:
                    result["status"] = "BLOCKED"
                    return result
                career_response = checked_get(observed, career_url)
                career_links = Links()
                career_links.feed(career_response.text)
                result["careers_page"] = str(career_response.url)
                urls += [urljoin(str(career_response.url), link) for link in career_links.links]
        result["structured_job_count"] = links.structured_job_count
        result["feed_urls"] = [
            urljoin(str(response.url), feed)
            for feed in links.feeds
            if safe_url(urljoin(str(response.url), feed))
        ][:5]
        detected = sorted(
            {
                url
                for url in urls
                if safe_url(url)
                and platform_for(url) in SUPPORTED | {"smartrecruiters", "workable"}
            }
        )
        # Keep only board discovery links, never page bodies, descriptions or forms.
        result["detected_boards"] = detected[:15]
        candidate = source.get("board_url") or source["url"]
        board = urlsplit(candidate)
        if source.get("board") and board_identity(candidate):
            result["checks"]["official_link"] = any(
                board_identity(url) == (source["platform"], source["board"]) for url in urls
            )
        else:
            result["checks"]["official_link"] = any(
                urlsplit(url).hostname == board.hostname
                and urlsplit(url).path.rstrip("/") == board.path.rstrip("/")
                for url in urls
            )
        if collector_supported(source):
            endpoint = (
                source["collection"]["listing_url"]
                if source.get("access_method") in METHODS | API_METHODS
                else board_endpoint(source)
            )
            result["endpoint"] = endpoint
            try:
                result["board_robots"] = robots_allowed(observed, endpoint)
            except httpx.HTTPStatusError as exc:
                # Ashby's /robots.txt is an authenticated, non-posting route. An
                # explicitly reviewed public API may still be checked once; a
                # block on the posting endpoint itself is never bypassed/retried.
                if (
                    source["platform"] == "ashby"
                    and exc.response.status_code == 401
                    and source.get("robots_unavailable_basis")
                    == "https://developers.ashbyhq.com/docs/public-job-posting-api"
                ):
                    result["board_robots"] = {
                        "status": 401,
                        "allowed": None,
                        "basis": source["robots_unavailable_basis"],
                    }
                else:
                    raise
            if result["board_robots"]["allowed"] is False:
                result["status"] = "BLOCKED"
                return result
            adapter = make_adapter(source, employers)
            adapter._client.close()
            adapter._client = observed
            records = adapter.fetch()
            result["records_found"] = len(records)
            result.update(candidate_summary(records))
            result["checks"].update(
                {
                    "stable_ids": all(r.external_id for r in records),
                    "application_links": all(safe_url(str(r.apply_url)) for r in records),
                    "locations": any(r.location for r in records)
                    or (not records and source["platform"] in {"ashby", "greenhouse", "lever"}),
                    "dates_reviewed": True,
                    "complete": adapter.crawl_complete,
                }
            )
            result["sample"] = [
                {
                    "id": r.external_id,
                    "title": r.title,
                    "location": r.location,
                    "application_url": str(r.apply_url),
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                }
                for r in records[:5]
            ]
            if not records:
                result["empty_board"] = True
                result["field_evidence"] = "Documented provider schema; no current vacancy sample"
            result["status"] = "SUCCESS" if adapter.crawl_complete else "PARTIAL"
        else:
            result["status"] = "DISCOVERED"
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        code = getattr(getattr(exc, "response", None), "status_code", None)
        if code in (401, 403, 429):
            result["status"] = "BLOCKED"
        result["http_status"] = code
    finally:
        result["requests"] = observed.events
        if client is None:
            raw_client.close()
    return result


def verify_board_access(source: dict, employers: dict) -> dict:
    """Check the public board independently after an evidenced official-link review."""
    prior = source.get("verification", {})
    if (
        source["status"] in {"manual", "blocked", "retired"}
        or not all(
            prior.get(key) is True for key in ("official_link", "collection_review", "local_access")
        )
        or not prior.get("evidence_paths")
        or not prior.get("collection_basis")
    ):
        raise ValueError("Board access check requires reviewed official linkage and local evidence")
    report = {
        "source_id": source["id"],
        "checked_at": datetime.now(UTC).isoformat(),
        "environment": "github" if os.environ.get("GITHUB_ACTIONS") else "local",
        "official_link_checked_this_run": False,
        "prior_official_evidence": prior["evidence_paths"],
        "status": "FAILED",
        "checks": {},
    }
    adapter = make_adapter(source, employers)
    observed = ObservedClient(adapter._client, source["crawl"])
    adapter._client = observed
    try:
        raw = adapter.fetch()  # Adapter enforces board-specific robots and access restrictions.
        report["records_found"] = len(raw)
        report.update(candidate_summary(raw))
        report["checks"] = {
            "stable_ids": all(job.external_id for job in raw),
            "application_links": all(safe_url(str(job.apply_url)) for job in raw),
            "locations": any(job.location for job in raw)
            or (
                not raw
                and source["platform"] in SUPPORTED
                and source.get("verified_empty_schema") is True
            ),
            "dates_reviewed": True,
            "complete": adapter.crawl_complete,
        }
        report["status"] = "SUCCESS" if adapter.crawl_complete else "PARTIAL"
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        code = getattr(getattr(exc, "response", None), "status_code", None)
        report["http_status"] = code
        if code in (401, 403, 429) or type(exc).__name__ == "CollectionBlocked":
            report["status"] = "BLOCKED"
    finally:
        report["requests"] = observed.events
        observed.client.close()
    return report


def trial(
    sources: list[dict],
    employers: dict,
    output_dir: Path,
    *,
    accepted: Path | None = None,
    factory=make_adapter,
) -> dict:
    """Always start an empty candidate; accepted input is read only for comparisons."""
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Trial output must be new or empty")
    if accepted is not None and not accepted.is_file():
        raise ValueError("Accepted baseline file is missing")
    baseline = (
        [CanonicalJob.model_validate(j) for j in read_json(accepted, {"jobs": []})["jobs"]]
        if accepted
        else []
    )
    baseline_urls = {canonicalize_apply_url(str(j.preferred_apply_url)) for j in baseline}
    report = {
        "schema_version": 1,
        "mode": "trial",
        "production_promoted": False,
        "checked_at": datetime.now(UTC).isoformat(),
        "baseline_supplied": accepted is not None,
        "sources": [],
    }
    jobs = []
    for source in sources:
        gaps = verification_gaps(source)
        row = {"source_id": source["id"], "verification_gaps": gaps}
        if gaps or source["status"] not in {"verified", "trial", "active"}:
            row["status"] = "NOT_VERIFIED"
            report["sources"].append(row)
            continue
        adapter = factory(source, employers)
        observer = ObservedClient(adapter._client, source["crawl"])
        adapter._client = observer
        try:
            raw = adapter.fetch()
            rejected = []
            parsed = build_jobs(raw, rejections=rejected)
            accepted_jobs = [
                j
                for j in parsed
                if j.eligibility_level in {"CONFIRMED", "LIKELY"}
                and (j.deadline_at is None or j.deadline_at > datetime.now(UTC))
            ]
            row.update(
                {
                    "status": "SUCCESS" if adapter.crawl_complete else "PARTIAL",
                    "raw_jobs": len(raw),
                    "technical_jobs": len(parsed),
                    "eligible_jobs": len(accepted_jobs),
                    "filtered_jobs": rejected,
                    "eligibility_review": [
                        {"job_id": j.job_id, "level": j.eligibility_level}
                        for j in parsed
                        if j not in accepted_jobs
                    ],
                    "complete": adapter.crawl_complete,
                    "duplicates_in_accepted": sum(
                        canonicalize_apply_url(str(j.preferred_apply_url)) in baseline_urls
                        for j in accepted_jobs
                    ),
                }
            )
            if adapter.crawl_complete:
                jobs.extend(
                    j.model_copy(update={"last_checked_at": datetime.now(UTC)})
                    for j in accepted_jobs
                )
        except Exception as exc:
            row.update({"status": "FAILED", "error_type": type(exc).__name__})
        finally:
            row["requests"] = observer.events
            observer.client.close()
        report["sources"].append(row)
    jobs = deduplicate_exact(jobs)
    report["candidate_jobs"] = len(jobs)
    report["outcome"] = (
        "SUCCESS"
        if report["sources"] and all(r["status"] == "SUCCESS" for r in report["sources"])
        else "INCOMPLETE"
    )
    report["additional_unique_jobs"] = (
        sum(canonicalize_apply_url(str(j.preferred_apply_url)) not in baseline_urls for j in jobs)
        if accepted
        else None
    )
    for name, payload in build_public_files(jobs).items():
        write_json(output_dir / "candidate" / name, payload)
    write_json(output_dir / "audit.json", report)
    lines = [
        "# Employer trial",
        "",
        "Production state was not modified.",
        "",
        "| Source | Status | Raw | Technical | Eligible |",
        "|---|---|---|---|---|",
    ]
    for row in report["sources"]:
        lines.append(
            f"| {row['source_id']} | {row['status']} | {row.get('raw_jobs', '—')} | "
            f"{row.get('technical_jobs', '—')} | {row.get('eligible_jobs', '—')} |"
        )
    lines += [
        "",
        f"Candidate jobs: {len(jobs)}.",
        f"Additional unique jobs: {report['additional_unique_jobs']} (null = no baseline).",
    ]
    (output_dir / "report.md").write_text("\n".join(lines) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["discover", "access", "trial"])
    parser.add_argument("--config-dir", type=Path, default=ROOT / "config")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--accepted", type=Path)
    parser.add_argument("--due", action="store_true")
    args = parser.parse_args()
    if args.mode == "access" and not args.source:
        parser.error("Board access checks require explicit --source selection")
    employers, registry = load_sources(args.config_dir)
    sources = (
        [registry[sid] for sid in args.source]
        if args.source
        else sorted(
            [
                s
                for s in registry.values()
                if (args.mode == "trial" and s["status"] in {"verified", "trial", "active"})
                or (args.mode == "discover" and (s.get("pilot_rank") or s.get("discovery_enabled")))
            ],
            key=lambda s: (s.get("pilot_rank", 1000), s["id"]),
        )
    )
    if args.mode == "trial":
        report = trial(sources, employers, args.output_dir, accepted=args.accepted)
        print(
            json.dumps(
                {
                    "candidate_jobs": report["candidate_jobs"],
                    "statuses": {r["source_id"]: r["status"] for r in report["sources"]},
                }
            )
        )
    else:
        count = 0
        for source in sources:
            path = args.output_dir / f"{source['id']}.json"
            old = read_json(path, {})
            if args.due:
                if old.get("status") == "BLOCKED":
                    continue  # A deliberate block needs review, not weekly retries.
                last = old.get("checked_at")
                if last and datetime.now(UTC) < datetime.fromisoformat(last) + timedelta(
                    hours=source.get("discovery_refresh_hours", 168)
                ):
                    continue
                if count >= 2:
                    break  # At most 16 discovery HTTP requests per pipeline slot.
            result = (
                verify_board_access(source, employers)
                if args.mode == "access"
                else discover(
                    source,
                    employers,
                    request_budget=8 if args.due else source["crawl"]["max_requests_per_run"],
                )
            )
            write_json(path, result)
            print(json.dumps({"source_id": source["id"], "status": result["status"]}))
            count += 1


if __name__ == "__main__":
    main()
