"""Verify a public employer board without persisting response descriptions."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from ingest.adapters.ashby import AshbyAdapter
from ingest.m0_probe import robots_info


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    adapter = AshbyAdapter(args.board)
    robots = robots_info(adapter._client, adapter.api_url)
    if robots["robots_allowed"] is False:
        raise ValueError("Public API path disallowed by robots.txt")
    jobs = adapter.fetch()
    report = {
        "schema_version": 1,
        "checked_at": datetime.now(UTC).isoformat(),
        "environment": os.environ.get("M0_ENV", "local"),
        "api_url": adapter.api_url,
        "crawl_complete": adapter.crawl_complete,
        "listed_jobs": len(jobs),
        "robots_status": robots["robots_status"],
        "robots_allowed": robots["robots_allowed"],
        "jobs": [job.model_dump(mode="json") for job in jobs],
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "jobs"}))


if __name__ == "__main__":
    main()
