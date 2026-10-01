"""Persistent fetch audit and human-readable GitHub job summaries."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

EAT = ZoneInfo("Africa/Nairobi")


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def public_hash(public_files: dict) -> str:
    payload = json.dumps(public_files, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def run_identity() -> tuple[str, str | None]:
    run_id = os.environ.get("GITHUB_RUN_ID")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    repo = os.environ.get("GITHUB_REPOSITORY")
    url = f"https://github.com/{repo}/actions/runs/{run_id}" if repo and run_id else None
    return (f"{run_id}-{attempt}" if run_id else str(uuid4()), url)


def write_summary(run: dict, path: Path) -> None:
    start = datetime.fromisoformat(run["started_at"]).astimezone(EAT)
    lines = [
        f"## Fetch audit — {start:%Y-%m-%d %H:%M:%S} EAT",
        f"Outcome: **{run['outcome']}**. Public data changed: **{run['public_changed']}**.",
        "",
        "| Source | Status | Requests / pages | Raw / tech | "
        "New / updated / missing | Duration | Reason |",
        "|---|---|---|---|---|---|---|",
    ]
    for source, row in run["sources"].items():
        health = row["health"]
        lines.append(
            f"| {source} | {health['status']} | {health['requests_made']} / "
            f"{health['pages_fetched']} | {health['records_found']} / {row['technical_jobs']} | "
            f"{row['new_jobs']} / {row['updated_jobs']} / {row['missing_jobs']} | "
            f"{health['duration_seconds']:.1f}s | {health['stop_reason'] or '—'} |"
        )
    lines += ["", "Missing means not observed in this fetch; it does not confirm closure."]
    for warning in run["warnings"]:
        lines.append(f"- {warning}")
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def record_run(output_dir: Path, run: dict, write_json) -> None:
    """Store one durable record per run, including request outcomes and source timings."""
    day = datetime.fromisoformat(run["started_at"]).astimezone(UTC).date().isoformat()
    path = output_dir / "state" / "fetch-history" / f"{day}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    # This writer runs under the pipeline-wide CI lock. Individual lines carry a run ID.
    path.write_text(existing + json.dumps(run, sort_keys=True) + "\n", encoding="utf-8")
    write_json(output_dir / "state" / "last-run.json", run)
    summary = output_dir / "state" / "fetch-summary.md"
    summary.write_text("", encoding="utf-8")
    write_summary(run, summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        write_summary(run, Path(os.environ["GITHUB_STEP_SUMMARY"]))
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as handle:
            handle.write(f"publishable={str(run['publishable']).lower()}\n")
            handle.write(f"public_changed={str(run['public_changed']).lower()}\n")
            handle.write(f"needs_attention={str(run['needs_attention']).lower()}\n")
    for warning in run["warnings"]:
        print(f"::warning::{warning}")
