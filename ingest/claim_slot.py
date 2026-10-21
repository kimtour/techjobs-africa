"""Persist an at-most-once source-fetch claim under the workflow concurrency lock."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

SLOT_RE = re.compile(r"(?:test-)?\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")
UTC_HOURS = {3, 6, 9, 12, 16}


def claim_slot(data_dir: Path, slot: str, run_id: str, *, now: datetime | None = None) -> bool:
    if not slot:
        return True  # Unscheduled manual runs remain available.
    if not SLOT_RE.fullmatch(slot):
        raise ValueError("Invalid scheduler slot")
    timestamp = datetime.fromisoformat(slot.removeprefix("test-").replace("Z", "+00:00"))
    current = now or datetime.now(UTC)
    if timestamp > current + timedelta(minutes=2) or current - timestamp > timedelta(hours=1):
        raise ValueError("Scheduler slot is outside its one-hour execution window")
    if not slot.startswith("test-") and (
        timestamp.hour not in UTC_HOURS
        or timestamp.minute
        or timestamp.second
        or timestamp.microsecond
    ):
        raise ValueError("Scheduler slot is outside the configured schedule")
    # One immutable file per slot, written under the shared GitHub concurrency lock.
    path = data_dir / "state/scheduler-slots" / f"{slot.replace(':', '-')}.json"
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"slot": slot, "run_id": run_id, "claimed_at": current.isoformat()}, indent=2)
        + "\n"
    )
    return True


def git(data_dir: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(data_dir), *args], check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    slot = os.environ.get("SCHEDULER_SLOT", "")
    proceed = claim_slot(args.data_dir, slot, os.environ["GITHUB_RUN_ID"])
    if proceed and slot:
        git(args.data_dir, "config", "user.name", "github-actions[bot]")
        git(
            args.data_dir,
            "config",
            "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com",
        )
        git(args.data_dir, "add", "state/scheduler-slots")
        git(args.data_dir, "commit", "-m", f"Claim scheduled fetch {slot}")
        # A failed push stops the job before fetching any source.
        git(args.data_dir, "push", "origin", "HEAD:data")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"proceed={str(proceed).lower()}\n")
    message = (
        "Claim recorded; fetch may proceed." if proceed else "Duplicate slot; source fetch skipped."
    )
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
        summary.write(f"### Scheduler claim\n\nSlot: `{slot or 'manual'}`\n\n{message}\n")


if __name__ == "__main__":
    main()
