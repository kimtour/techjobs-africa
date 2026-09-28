"""Create stable canonical jobs from validated source records."""

from __future__ import annotations

import re
import unicodedata

from ingest.classify.eligibility import classify_eligibility
from ingest.classify.tech import classify_technology_title
from ingest.models import CanonicalJob, RawJob

ASHBY_POSTING_COMPANY = "TalentSafari"


def normalize_text(value: str) -> str:
    """Normalize text for comparison only; never use it as a permanent identity."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", normalized)).strip()


def canonicalize_ashby_job(
    raw: RawJob, *, posting_company: str = ASHBY_POSTING_COMPANY
) -> CanonicalJob:
    """Canonicalize an Ashby job using its immutable external ID.

    TalentSafari is an agency board, so its name remains the posting company
    while a supplied company name is retained as the hiring company.
    """

    if raw.source_id != "ashby" or not raw.external_id:
        raise ValueError("Ashby canonicalization requires a RawJob with an Ashby external ID.")

    return canonicalize_raw_job(
        raw,
        posting_company=posting_company,
        hiring_company=raw.company,
        is_agency_posting=True,
    )


def _location_parts(location: str | None) -> tuple[str | None, str | None]:
    parts = [part.strip() for part in (location or "").split(",") if part.strip()]
    return (parts[0] if parts else None, parts[-1] if len(parts) > 1 else None)


def canonicalize_raw_job(
    raw: RawJob,
    *,
    posting_company: str | None = None,
    hiring_company: str | None = None,
    is_agency_posting: bool = False,
) -> CanonicalJob:
    """Canonicalize any current approved-source job with a stable external ID.

    The identifier deliberately uses only source and immutable external ID;
    mutable fields such as the title, location, and category cannot change it.
    """

    if not raw.external_id:
        raise ValueError("Canonicalization requires a RawJob external ID.")

    eligibility = classify_eligibility(location=raw.location, title=raw.title)
    category = classify_technology_title(raw.title)
    city, country = _location_parts(raw.location)
    resolved_posting_company = posting_company or raw.company
    resolved_hiring_company = hiring_company or (
        raw.company if is_agency_posting else None
    )

    return CanonicalJob(
        job_id=f"{raw.source_id}:{raw.external_id}",
        title=raw.title,
        normalized_title=normalize_text(raw.title),
        posting_company=resolved_posting_company,
        hiring_company=resolved_hiring_company,
        normalized_company=(
            normalize_text(resolved_hiring_company or resolved_posting_company)
            if resolved_hiring_company or resolved_posting_company
            else None
        ),
        is_agency_posting=is_agency_posting,
        city=city,
        country=country,
        workplace_type=None,
        category=category.category,
        secondary_categories=category.secondary_categories,
        category_source=category.source,
        eligibility_level=eligibility.level,
        eligibility_evidence=eligibility.evidence,
        eligibility_source=eligibility.source,
        published_at=raw.published_at,
        preferred_apply_url=raw.apply_url,
        sources=[raw.source_id],
    )
