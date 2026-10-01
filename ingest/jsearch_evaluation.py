"""Evaluate JSearch in isolation; never modify production state or publish jobs."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import yaml
from pydantic import ValidationError

from ingest.adapters.jsearch import API_URL, FIELDS, parse_record
from ingest.adapters.jsearch import safe_url as safe_url
from ingest.dedupe.exact import canonicalize_apply_url
from ingest.main import build_jobs
from ingest.normalize.canonicalize import normalize_text


def evaluate(config: dict, baseline: dict, client: httpx.Client, key: str) -> dict:
    queries = config.get("queries")
    if (
        config.get("country") != "ke"
        or not isinstance(queries, list)
        or not 1 <= len(queries) <= 4
        or any(not isinstance(query, str) or not query.strip() for query in queries)
    ):
        raise ValueError("Evaluation requires Kenya and one to four queries.")
    existing = [
        job
        for job in baseline.get("jobs", [])
        if job.get("status") == "ACTIVE" and job.get("eligibility_level") != "RESTRICTED"
    ]
    baseline_urls = {canonicalize_apply_url(job["preferred_apply_url"]) for job in existing}
    signatures = {
        (
            normalize_text(job["title"]),
            normalize_text(job.get("hiring_company") or job.get("posting_company") or ""),
            normalize_text(job.get("city") or ""),
        )
        for job in existing
    }
    raw_jobs, searches = [], []
    links_by_id: dict[str, set[str]] = {}
    rejected: Counter = Counter()
    for query in queries:
        row = {"query": query, "status": "pending", "returned": 0, "has_more": False}
        searches.append(row)
        try:
            response = client.get(
                API_URL,
                headers={"x-api-key": key, "Accept": "application/json"},
                params={
                    "query": query,
                    "country": "ke",
                    "language": config.get("language", "en"),
                    "date_posted": config.get("date_posted", "week"),
                    "num_pages": 1,
                    "fields": FIELDS,
                },
                timeout=25,
                follow_redirects=False,
            )
            row["http_status"] = response.status_code
            if response.status_code != 200:
                row["status"] = "http_error"
                break  # Stop on errors; no retries or extra quota-consuming requests.
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            records = data.get("jobs") if isinstance(data, dict) else None
            if payload.get("status") != "OK" or not isinstance(records, list):
                raise ValueError("invalid_response")
            row.update(status="success", returned=len(records), has_more=bool(data.get("cursor")))
            for record in records:
                if not isinstance(record, dict):
                    rejected["invalid_record"] += 1
                    continue
                if str(record.get("job_country", "")).upper() not in ("KE", "KENYA"):
                    rejected["outside_or_unknown_country"] += 1
                    continue
                try:
                    raw, links = parse_record(record)
                except (ValueError, ValidationError):
                    rejected["invalid_record"] += 1
                    continue
                raw_jobs.append(raw)
                links_by_id.setdefault(f"jsearch:{raw.external_id}", set()).update(links)
        except Exception as exc:
            # Never persist response bodies, request headers, exception text, or descriptions.
            row.update(status="error", error_type=type(exc).__name__)
            break
    jobs = build_jobs(raw_jobs)
    candidates = []
    for job in jobs:
        links = sorted(links_by_id[job.job_id])
        linkedin_links = [
            url
            for url in links
            if (urlsplit(url).hostname or "").lower() == "linkedin.com"
            or (urlsplit(url).hostname or "").lower().endswith(".linkedin.com")
        ]
        exact = any(canonicalize_apply_url(url) in baseline_urls for url in links)
        signature = (
            job.normalized_title,
            normalize_text(job.hiring_company or job.posting_company or ""),
            normalize_text(job.city or ""),
        )
        candidates.append(
            {
                "job": job.model_dump(mode="json"),
                "linkedin_links": linkedin_links,
                "exact_url_overlap": exact,
                "possible_duplicate_review": not exact and signature in signatures,
            }
        )
    return {
        "schema_version": 1,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "mode": "discovery_only",
        "country": "ke",
        "searches": searches,
        "requests_made": len(searches),
        "baseline_active_roles": len(existing),
        "technical_jobs": len(candidates),
        "linkedin_linked_jobs": sum(bool(c["linkedin_links"]) for c in candidates),
        "exact_url_overlaps": sum(c["exact_url_overlap"] for c in candidates),
        "possible_duplicate_reviews": sum(c["possible_duplicate_review"] for c in candidates),
        "rejected": dict(rejected),
        "candidates": candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/jsearch-evaluation.yaml"))
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    key = os.environ.get("JSEARCH_API_KEY", "").strip()
    if not key:
        print("Set the JSEARCH_API_KEY secret before running the evaluation.")
        return 2
    baseline = json.loads(args.baseline.read_text())
    config = yaml.safe_load(args.config.read_text())
    with httpx.Client() as client:
        report = evaluate(config, baseline, client, key)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
    summary = (
        "# JSearch Kenya evaluation\n\n"
        "Discovery only: no production jobs were changed or published.\n\n"
        f"- Baseline active roles: {report['baseline_active_roles']}\n"
        f"- Requests attempted: {report['requests_made']}\n"
        f"- Unique technical jobs: {report['technical_jobs']}\n"
        f"- Jobs with LinkedIn application links: {report['linkedin_linked_jobs']}\n"
        f"- Exact application URL overlaps: {report['exact_url_overlaps']}\n"
        f"- Possible duplicates needing review: {report['possible_duplicate_reviews']}\n\n"
        "This first-page sample does not establish complete coverage or publication permission.\n"
    )
    (args.output_dir / "summary.md").write_text(summary)
    print(summary)
    return 0 if all(s["status"] == "success" for s in report["searches"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
