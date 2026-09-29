"""Create stable canonical jobs from validated source records."""

from __future__ import annotations

import re
import unicodedata

from ingest.classify.eligibility import classify_eligibility
from ingest.classify.tech import classify_technology_title
from ingest.models import CanonicalJob, RawJob
from ingest.normalize.location import normalize_location

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

    category = classify_technology_title(raw.title)
    # Some approved listing cards put a structured city in their title rather
    # than in the card's location field (for example, "... – Nyeri at
    # Diageo"). Use that explicit title signal only when the source field is
    # absent; `normalize_location` still accepts only configured places.
    location = normalize_location(raw.location or raw.title)
    eligibility_location = " ".join(
        part for part in (raw.location, location.city, location.country) if part
    ) or None
    eligibility = classify_eligibility(location=eligibility_location, title=raw.title)
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
        city=location.city,
        country=location.country,
        country_code=location.country_code,
        workplace_type=location.workplace_type,
        category=category.category,
        secondary_categories=category.secondary_categories,
        category_source=category.source,
        eligibility_level=eligibility.level,
        eligibility_evidence=eligibility.evidence,
        eligibility_source=eligibility.source,
        published_at=raw.published_at,
        published_date=raw.published_date,
        preferred_apply_url=raw.apply_url,
        sources=[raw.source_id],
    )
