"""Read the saved fetch ledger without contacting any source."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--last", type=int, default=20)
    parser.add_argument("--source", help="Show only runs containing this source")
    args = parser.parse_args()
    runs = []
    for path in sorted((args.data_dir / "state/fetch-history").glob("*.jsonl")):
        runs.extend(json.loads(line) for line in path.read_text().splitlines() if line.strip())
    if args.source:
        runs = [run for run in runs if args.source in run["sources"]]
    if not runs:
        print("No recorded fetches. Historical workflow times are not per-source audit records.")
        return
    for run in sorted(runs, key=lambda item: item["started_at"], reverse=True)[: args.last]:
        started = datetime.fromisoformat(run["started_at"]).astimezone(ZoneInfo("Africa/Nairobi"))
        print(f"{started:%Y-%m-%d %H:%M:%S} EAT  {run['outcome']}  run {run['run_id']}")
        for source, row in run["sources"].items():
            if args.source and source != args.source:
                continue
            h = row["health"]
            print(
                f"  {source}: {h['status']} | {h['requests_made']} requests, "
                f"{h['pages_fetched']} pages, {h['records_found']} raw, "
                f"{row['technical_jobs']} tech | new {row['new_jobs']}, "
                f"updated {row['updated_jobs']}, missing {row['missing_jobs']} | "
                f"{h['duration_seconds']:.1f}s | {h['stop_reason'] or 'complete'}"
            )
        if run.get("workflow_url"):
            print(f"  Evidence: {run['workflow_url']}")


if __name__ == "__main__":
    main()
