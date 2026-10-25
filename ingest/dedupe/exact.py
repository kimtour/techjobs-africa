"""Merge only proven duplicates; never fuzzy-merge job listings."""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ingest.models import CanonicalJob

TRACKING_PARAMETERS = {"fbclid", "gclid"}


def canonicalize_apply_url(url: str) -> str:
    """Remove only known tracking parameters and preserve functional ones."""

    parsed = urlsplit(url)
    retained = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_PARAMETERS and not key.casefold().startswith("utm_")
    ]
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(retained), parsed.fragment)
    )


def _merge(primary: CanonicalJob, duplicate: CanonicalJob) -> CanonicalJob:
    direct = duplicate if duplicate.direct_employer else primary
    return primary.model_copy(
        update={
            "sources": sorted(set(primary.sources).union(duplicate.sources)),
            "source_publisher": primary.source_publisher or duplicate.source_publisher,
            "preferred_apply_url": direct.preferred_apply_url
            if direct.direct_employer
            else primary.preferred_apply_url,
            "direct_employer": primary.direct_employer or duplicate.direct_employer,
            "employer_id": primary.employer_id or duplicate.employer_id,
            "employer_sectors": sorted(set(primary.employer_sectors + duplicate.employer_sectors)),
            "last_checked_at": max(
                (v for v in (primary.last_checked_at, duplicate.last_checked_at) if v is not None),
                default=None,
            ),
            "deadline_at": primary.deadline_at or duplicate.deadline_at,
            "employment_type": primary.employment_type or duplicate.employment_type,
            "opportunity_type": primary.opportunity_type or duplicate.opportunity_type,
        }
    )


def deduplicate_exact(jobs: Iterable[CanonicalJob]) -> list[CanonicalJob]:
    """Merge jobs sharing a stable ID or canonical application URL.

    Company/title/location resemblance is intentionally not used here. Those
    signals can generate review candidates later but must not auto-merge jobs.
    """

    results: list[CanonicalJob] = []
    parents: list[int] = []
    by_job_id: dict[str, int] = {}
    by_apply_url: dict[str, int] = {}

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for job in jobs:
        canonical_url = canonicalize_apply_url(str(job.preferred_apply_url))
        matches = {
            root(index)
            for index in (by_job_id.get(job.job_id), by_apply_url.get(canonical_url))
            if index is not None
        }
        if not matches:
            existing_index = len(results)
            parents.append(existing_index)
            results.append(job)
        else:
            existing_index = min(matches)
            for other in sorted(matches - {existing_index}):
                results[existing_index] = _merge(results[existing_index], results[other])
                parents[other] = existing_index
            results[existing_index] = _merge(results[existing_index], job)
        by_job_id[job.job_id] = existing_index
        by_apply_url[canonical_url] = existing_index

    return [job for index, job in enumerate(results) if root(index) == index]
