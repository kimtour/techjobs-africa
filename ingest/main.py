"""Run approved-source ingestion and write deterministic static data files."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml

from ingest.adapters.ashby import AshbyAdapter
from ingest.adapters.corporate_staffing import CorporateStaffingAdapter
from ingest.adapters.elevolt import ElevoltAdapter
from ingest.adapters.myjobmag import MyJobMagAdapter
from ingest.adapters.openedcareer import OpenedCareerAdapter
from ingest.dedupe.exact import deduplicate_exact
from ingest.export.static import build_public_files
from ingest.models import CanonicalJob, RawJob, SourceHealth, SourceHealthStatus
from ingest.normalize.canonicalize import canonicalize_raw_job

CONFIG_PATH = Path("config/sources.yaml")
AdapterFactory = Callable[[], object]
ADAPTERS: Mapping[str, AdapterFactory] = {
    "ashby": lambda: AshbyAdapter("talentsafari"),
    "myjobmag": MyJobMagAdapter,
    "corporate_staffing": CorporateStaffingAdapter,
    "openedcareer": OpenedCareerAdapter,
    "elevolt": ElevoltAdapter,
}
# These endpoints are explicitly scoped by their sources to IT/software listings.
# A missing title keyword must not discard a listing from that verified category.
SOURCE_SCOPED_TECH_SOURCES = frozenset(
    {"corporate_staffing", "elevolt", "myjobmag", "openedcareer"}
)


def approved_source_ids(config_path: Path = CONFIG_PATH) -> list[str]:
    """Return enabled sources that have an implemented production method."""

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return [
        source["id"]
        for source in config["sources"]
        if source.get("enabled") and source.get("production_method") and source["id"] in ADAPTERS
    ]


def build_jobs(raw_jobs: Sequence[RawJob]) -> list[CanonicalJob]:
    """Canonicalize and retain only roles with a deterministic technical match."""

    technical_jobs = []
    for raw in raw_jobs:
        job = canonicalize_raw_job(raw)
        if not job.category and raw.source_id in SOURCE_SCOPED_TECH_SOURCES:
            job = job.model_copy(
                update={"category": "IT Operations", "category_source": "source_category"}
            )
        if job.category:
            technical_jobs.append(job)
    return deduplicate_exact(technical_jobs)


def _write_json(path: Path, content: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary.write(json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def run_ingestion(
    output_dir: Path,
    *,
    source_ids: Sequence[str] | None = None,
    adapters: Mapping[str, object] = ADAPTERS,
) -> dict[str, SourceHealth]:
    """Fetch each source independently and write safe static files on success."""

    selected_ids = list(source_ids or approved_source_ids())
    raw_jobs: list[RawJob] = []
    health: dict[str, SourceHealth] = {}
    for source_id in selected_ids:
        adapter_factory = adapters.get(source_id)
        if adapter_factory is None:
            raise ValueError(f"No adapter is registered for {source_id!r}.")
        try:
            fetched = adapter_factory().fetch()
        except Exception:  # Source failures are isolated and recorded below.
            health[source_id] = SourceHealth(
                source_id=source_id,
                status=SourceHealthStatus.FAILED,
                records_found=0,
                pages_fetched=0,
                crawl_complete=False,
                safe_to_process_absences=False,
            )
            continue
        raw_jobs.extend(fetched)
        health[source_id] = SourceHealth(
            source_id=source_id,
            status=SourceHealthStatus.SUCCESS,
            records_found=len(fetched),
            pages_fetched=1,
            crawl_complete=True,
            safe_to_process_absences=True,
        )

    jobs = build_jobs(raw_jobs)
    for filename, content in build_public_files(jobs).items():
        _write_json(output_dir / "public" / filename, content)
    _write_json(
        output_dir / "canonical" / "jobs.json",
        {"schema_version": 1, "jobs": [job.model_dump(mode="json") for job in jobs]},
    )
    _write_json(
        output_dir / "state" / "health.json",
        {
            "schema_version": 1,
            "sources": {key: value.model_dump() for key, value in health.items()},
        },
    )
    return health


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source", action="append", dest="sources")
    args = parser.parse_args()
    health = run_ingestion(args.output_dir, source_ids=args.sources)
    summary = ", ".join(f"{key}={value.status}" for key, value in health.items())
    print("Ingestion complete: " + summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
