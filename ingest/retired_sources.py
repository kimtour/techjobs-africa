"""Migrate accepted snapshots when a source is explicitly retired."""

RETIRED_FIELDS = {"employer_id", "employer_sectors", "direct_employer"}


def is_retired_source(source: str) -> bool:
    return source == "bebee" or source.startswith("employer_")


def retained_job(job: dict) -> dict | None:
    """Drop retired identities; preserve other providers and their stable IDs."""
    if is_retired_source(job["job_id"].split(":", 1)[0]):
        return None
    sources = [source for source in job["sources"] if not is_retired_source(source)]
    if not sources:
        return None
    retained = {key: value for key, value in job.items() if key not in RETIRED_FIELDS}
    retained["sources"] = sources
    if job.get("direct_employer") and sources != job["sources"]:
        retained["source_publisher"] = None
    return retained
