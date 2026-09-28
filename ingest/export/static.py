"""Create deterministic public JSON without source descriptions or contacts."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from ingest.models import CanonicalJob

SCHEMA_VERSION = 1


def _sort_key(job: CanonicalJob) -> tuple[str, str]:
    """Sort newest dated jobs first; place undated records afterwards."""

    published = job.published_at.isoformat() if job.published_at else ""
    return (published, job.job_id)


def build_public_files(jobs: Iterable[CanonicalJob]) -> dict[str, object]:
    """Return deterministic, publishable files from canonical technical jobs."""

    dated = sorted((job for job in jobs if job.published_at), key=_sort_key, reverse=True)
    undated = sorted((job for job in jobs if not job.published_at), key=_sort_key)
    ordered = dated + undated
    serialized_jobs = [job.model_dump(mode="json") for job in ordered]
    categories = Counter(job.category for job in ordered if job.category)
    countries = Counter(job.country for job in ordered if job.country)
    eligibility = Counter(job.eligibility_level.value for job in ordered)

    return {
        "jobs.json": {"schema_version": SCHEMA_VERSION, "jobs": serialized_jobs},
        "search-index.json": {
            "schema_version": SCHEMA_VERSION,
            "jobs": [
                {
                    "job_id": job.job_id,
                    "title": job.title,
                    "company": job.hiring_company or job.posting_company,
                    "city": job.city,
                    "country": job.country,
                    "category": job.category,
                }
                for job in ordered
            ],
        },
        "categories.json": {
            "schema_version": SCHEMA_VERSION,
            "categories": [
                {"name": name, "job_count": count} for name, count in sorted(categories.items())
            ],
        },
        "countries.json": {
            "schema_version": SCHEMA_VERSION,
            "countries": [
                {"name": name, "job_count": count} for name, count in sorted(countries.items())
            ],
        },
        "stats.json": {
            "schema_version": SCHEMA_VERSION,
            "stats": {
                "total_jobs": len(ordered),
                "by_category": dict(sorted(categories.items())),
                "by_eligibility": dict(sorted(eligibility.items())),
            },
        },
    }
