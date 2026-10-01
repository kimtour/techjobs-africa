"""Promote a candidate only after publication; retain operational audits on failure."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

from ingest.audit import read_json


def finalize(data_dir: Path, candidate_dir: Path, *, promote: bool, deployment: dict) -> None:
    if not (candidate_dir / "state").exists():
        return
    # Copy audit state even if the candidate failed to build/deploy. Baselines are
    # tied to accepted canonical data and are only promoted with that snapshot.
    for path in (candidate_dir / "state").iterdir():
        if path.name in (
            "source-baselines.json",
            "occurrences.json",
            "last-known-good.json",
            "deployment.json",
        ):
            continue
        target = data_dir / "state" / path.name
        if path.is_dir():
            shutil.copytree(path, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    run = read_json(candidate_dir / "state/last-run.json", {})
    progress = read_json(candidate_dir / "state/fetch-progress.json", {})
    deployment["run_id"] = progress.get("run_id") or run.get("run_id")
    deployment["recorded_at"] = datetime.now(UTC).isoformat()
    deployment["promoted"] = promote
    if promote:
        for directory in ("canonical", "public"):
            shutil.copytree(candidate_dir / directory, data_dir / directory, dirs_exist_ok=True)
        for name in ("source-baselines.json", "occurrences.json"):
            snapshot = candidate_dir / "state" / name
            if snapshot.exists():
                shutil.copy2(snapshot, data_dir / "state" / name)
        (data_dir / "state/last-known-good.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": run.get("run_id"),
                    "public_hash": run.get("public_hash"),
                    "accepted_at": deployment["recorded_at"],
                },
                indent=2,
            )
            + "\n"
        )
        if deployment["outcome"] == "success":
            (data_dir / "state/deployment.json").write_text(json.dumps(deployment, indent=2) + "\n")
    day = datetime.now(UTC).date().isoformat()
    for root in (candidate_dir, data_dir):
        path = root / "state/publication-history" / f"{day}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(deployment, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    args = parser.parse_args()
    changed = os.environ.get("PUBLIC_CHANGED") == "true"
    safe = os.environ.get("PUBLISHABLE") == "true"
    fetched = os.environ.get("FETCH_OUTCOME") == "success"
    deployed = os.environ.get("DEPLOY_OUTCOME") == "success"
    finalize(
        args.data_dir,
        args.candidate_dir,
        promote=fetched and safe and (not changed or deployed),
        deployment={
            "outcome": "success"
            if deployed
            else "unchanged"
            if fetched and safe and not changed
            else "not_published",
            "deployment_url": os.environ.get("DEPLOY_URL") or None,
            "workflow_status_at_finalization": os.environ.get("WORKFLOW_STATUS"),
            "deployment_id": os.environ.get("DEPLOY_ID") or None,
        },
    )


if __name__ == "__main__":
    main()
