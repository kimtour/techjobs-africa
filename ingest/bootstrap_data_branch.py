"""Create the versioned directory structure used by the private data branch.

Run this only against a checked-out data branch, for example:
    python ingest/bootstrap_data_branch.py --data-dir ../techjobs-africa-data
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA_VERSION = 1

FILES: dict[str, object] = {
    "schema_version.json": {"schema_version": SCHEMA_VERSION},
    "canonical/jobs.json": {"schema_version": SCHEMA_VERSION, "jobs": []},
    "state/occurrences.json": {"schema_version": SCHEMA_VERSION, "occurrences": []},
    "state/health.json": {"schema_version": SCHEMA_VERSION, "sources": {}},
    "state/duplicate-review.json": {"schema_version": SCHEMA_VERSION, "reviews": []},
    "state/last-run.json": {"schema_version": SCHEMA_VERSION, "runs": {}},
    "state/last-known-good.json": {"schema_version": SCHEMA_VERSION, "snapshot": None},
    "state/deployment.json": {"schema_version": SCHEMA_VERSION, "deployment": None},
    "public/jobs.json": {"schema_version": SCHEMA_VERSION, "jobs": []},
    "public/search-index.json": {"schema_version": SCHEMA_VERSION, "jobs": []},
    "public/categories.json": {"schema_version": SCHEMA_VERSION, "categories": []},
    "public/countries.json": {"schema_version": SCHEMA_VERSION, "countries": []},
    "public/stats.json": {"schema_version": SCHEMA_VERSION, "stats": {}},
}


def write_json(path: Path, content: object, overwrite: bool) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument(
        "--force", action="store_true", help="replace existing bootstrap JSON files"
    )
    args = parser.parse_args()

    root = args.data_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "sources").mkdir(exist_ok=True)
    (root / "snapshots/last_known_good").mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0
    for relative_path, content in FILES.items():
        if write_json(root / relative_path, content, args.force):
            created += 1
        else:
            skipped += 1

    print(f"Bootstrap complete: {created} written, {skipped} unchanged at {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
