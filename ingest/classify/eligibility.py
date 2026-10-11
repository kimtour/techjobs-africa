"""Deterministic eligibility decisions; descriptions are never persisted."""

from __future__ import annotations

import re

from ingest.models import EligibilityDecision, EligibilityLevel
from ingest.normalize.location import normalize_location

AFRICAN_TERMS = (
    "africa",
    "kenya",
    "nairobi",
    "nigeria",
    "lagos",
    "ghana",
    "accra",
    "south africa",
    "cape town",
    "egypt",
    "cairo",
)
NON_AFRICAN_RESIDENCY = (
    "united states",
    "usa",
    "canada",
    "united kingdom",
    "uk",
)
APPLICANT_AFRICA_PATTERN = re.compile(
    r"\b(open to|candidates? (?:based )?in|applicants? (?:based )?in|apply from) africa\b",
    re.IGNORECASE,
)


def _contains_term(value: str, terms: tuple[str, ...]) -> str | None:
    folded = value.casefold()
    return next((term for term in terms if re.search(rf"\b{re.escape(term)}\b", folded)), None)


def classify_eligibility(
    *,
    location: str | None = None,
    title: str | None = None,
    description: str | None = None,
) -> EligibilityDecision:
    """Classify whether African candidates are eligible using conservative rules."""

    structured = " ".join(part for part in (location, title) if part).strip()
    structured_lower = structured.casefold()

    geography = normalize_location(structured)
    if normalize_location(location).region == "Worldwide" or re.search(
        r"\bworldwide\b", title or "", re.I
    ):
        return EligibilityDecision(
            level=EligibilityLevel.CONFIRMED,
            evidence="Structured location states worldwide.",
            source="structured_location",
        )

    restricted = _contains_term(structured, NON_AFRICAN_RESIDENCY)
    has_residency_requirement = re.search(
        r"\b(must reside|residency|authorized to work)\b", structured_lower
    )
    if restricted and has_residency_requirement:
        return EligibilityDecision(
            level=EligibilityLevel.RESTRICTED,
            evidence=f"Structured residency requirement names {restricted}.",
            source="structured_location",
        )

    african = geography.country.casefold() if geography.country else None
    if not african and geography.region in ("Africa", "Sub-Saharan Africa"):
        african = geography.region.casefold()
    if not african and geography.region != "EMEA":
        african = _contains_term(structured, AFRICAN_TERMS)
    if african:
        return EligibilityDecision(
            level=EligibilityLevel.CONFIRMED,
            evidence=f"Structured location/title names {african}.",
            source="structured_location",
        )

    if geography.region == "EMEA":
        return EligibilityDecision(
            level=EligibilityLevel.VERIFY,
            evidence="Structured location is EMEA without country eligibility.",
            source="structured_location",
        )

    if description and APPLICANT_AFRICA_PATTERN.search(description):
        return EligibilityDecision(
            level=EligibilityLevel.LIKELY,
            evidence="Description directly addresses candidates in Africa.",
            source="description",
        )

    return EligibilityDecision(
        level=EligibilityLevel.UNKNOWN,
        evidence="No reliable African eligibility signal found.",
        source="none",
    )
