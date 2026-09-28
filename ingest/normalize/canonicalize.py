"""Create stable canonical jobs from validated source records."""

from __future__ import annotations

import re
import unicodedata

from ingest.classify.eligibility import classify_eligibility
from ingest.models import CanonicalJob, RawJob

ASHBY_POSTING_COMPANY = "TalentSafari"


def normalize_text(value: str) -> str:
    """Normalize text for comparison only; never use it as a permanent identity."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", normalized)).strip()


def canonicalize_ashby_job(
    raw: RawJob, *, posting_company: str = ASHBY_POSTING_COMPANY
) -> CanonicalJob:
    """Canonicalize an Ashby job using its immutable external ID."""

    if raw.source_id != "ashby" or not raw.external_id:
        raise ValueError("Ashby canonicalization requires a RawJob with an Ashby external ID.")

    eligibility = classify_eligibility(location=raw.location, title=raw.title)
    location_parts = [part.strip() for part in (raw.location or "").split(",") if part.strip()]
    city = location_parts[0] if location_parts else None
    country = location_parts[-1] if len(location_parts) > 1 else None

    return CanonicalJob(
        job_id=f"ashby:{raw.external_id}",
        title=raw.title,
        normalized_title=normalize_text(raw.title),
        posting_company=posting_company,
        normalized_company=normalize_text(posting_company),
        is_agency_posting=True,
        city=city,
        country=country,
        workplace_type=None,
        eligibility_level=eligibility.level,
        eligibility_evidence=eligibility.evidence,
        eligibility_source=eligibility.source,
        published_at=raw.published_at,
        preferred_apply_url=raw.apply_url,
        sources=[raw.source_id],
    )
