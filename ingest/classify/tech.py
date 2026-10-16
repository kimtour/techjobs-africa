"""Deterministic title-based technology classification."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

CONFIG_PATH = Path("config/categories.yaml")


@lru_cache(maxsize=8)
def _load_config(config_path: Path) -> dict:
    """The taxonomy is immutable within one ingestion run."""
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def _role_title(title: str) -> str:
    # Employer names are attribution, never evidence of the vacancy's function.
    role = title.rsplit(" at ", 1)[0]
    role = re.sub(r"\bI\.C\.T\.?(?=\W|$)", "ICT", role, flags=re.I)
    return re.sub(r"\bI\.T\.?(?=\W|$)", "IT", role, flags=re.I)


def classification_title(title: str, company: str | None = None) -> str:
    """Remove an explicit employer suffix without altering the stored source title."""
    role = _role_title(title)
    if company and role.casefold().endswith(" " + company.casefold()):
        role = role[: -(len(company) + 1)].rstrip(" -–—")
        role = re.sub(r"\s+(?:NGO\s+)?Job$", "", role, flags=re.I)
    return role


def mixed_technology_roles(title: str, config_path: Path = CONFIG_PATH) -> list[str]:
    """Find explicit technical vacancies in a comma-separated multi-role advert."""
    role = _role_title(title)
    if "," not in role or not has_non_technical_exclusion(role, config_path):
        return []
    parts = re.split(r",\s*|\s+and\s+", role)
    return [part.strip() for part in parts if classify_technology_title(part, config_path).category]


def needs_detail_technical_context(title: str, config_path: Path = CONFIG_PATH) -> bool:
    config = _load_config(config_path)
    return any(
        re.search(rule["title_pattern"], _role_title(title), re.I)
        for rule in config.get("context_rules", [])
    )


def listing_technical_context(title: str, body: str, config_path: Path = CONFIG_PATH) -> str | None:
    """Require both a scoped title and technical duties in the listing's own body."""
    config = _load_config(config_path)
    for rule in config.get("context_rules", []):
        if re.search(rule["title_pattern"], _role_title(title), re.I) and all(
            re.search(pattern, body, re.I) for pattern in rule["required_evidence"]
        ):
            return rule["key"]
    return None


def category_from_technical_context(
    context: str | None, config_path: Path = CONFIG_PATH
) -> CategoryDecision:
    config = _load_config(config_path)
    for rule in config.get("context_rules", []):
        if context == rule["key"]:
            return CategoryDecision(category=rule["category"], source="description_rule")
    return CategoryDecision(category=None, source=None)


def geospatial_technical_context(title: str, body: str) -> str | None:
    """Require development evidence in this ambiguous role's own in-memory body."""
    if not _matches(title, ["early warning expert"]):
        return None
    return listing_technical_context(title, body)


class CategoryDecision(BaseModel):
    category: str | None
    secondary_categories: list[str] = []
    source: str | None


@lru_cache(maxsize=128)
def _keyword_pattern(keywords: tuple[str, ...]) -> re.Pattern | None:
    if not keywords:
        return None
    phrases = [
        re.escape(re.sub(r"\s+", " ", re.sub(r"[-–—,/:()]", " ", keyword.casefold())).strip())
        for keyword in keywords
    ]
    return re.compile(r"(?<!\w)(?:" + "|".join(phrases) + r")(?!\w)")


def _matches(title: str, keywords: list[str]) -> bool:
    pattern = _keyword_pattern(tuple(keywords))
    if pattern is None:
        return False
    normalized = title.casefold()
    normalized = re.sub(r"[-–—]", " ", normalized)
    normalized = re.sub(r"[,/:()]", " ", normalized)
    normalized = re.sub(r"\bsuport\b", "support", normalized)
    normalized = re.sub(r"\b(front|back)\s+end\b", r"\1end", normalized)
    normalized = re.sub(
        r"\b(engineers|developers|interns|labelers)\b", lambda m: m[0][:-1], normalized
    )
    normalized = re.sub(r"\s+", " ", normalized)
    # Seniority may appear between the domain and function (ICT Senior Analyst,
    # Cloud Lead Engineer). It changes rank, not the technical function.
    normalized = re.sub(
        r"\b(senior|junior|principal|lead|sr\.?|jr\.?)\s+"
        r"(?=(?:engineer|developer|analyst|architect|specialist|officer|administrator|"
        r"consultant|manager|technician|scientist)\b)",
        "",
        normalized,
    )
    return pattern.search(normalized) is not None


def has_non_technical_exclusion(value: str, config_path: Path = CONFIG_PATH) -> bool:
    """Return whether a title or URL label names an excluded job function."""

    config = _load_config(config_path)
    return _matches(_role_title(value), config.get("non_tech_exclusions", []))


def classify_technology_title(title: str, config_path: Path = CONFIG_PATH) -> CategoryDecision:
    """Return a category only when the title has deterministic technical evidence."""

    config = _load_config(config_path)
    title = _role_title(title)
    categories = config["categories"]
    exclusions = config.get("non_tech_exclusions", [])

    # Broad technical terms can occur in non-technical commercial and support
    # roles (for example, "Sales Officer – ICT Solutions"). A job function
    # explicitly excluded by the taxonomy is never made technical by a generic
    # technology keyword elsewhere in its title.
    if _matches(title, exclusions):
        roles = mixed_technology_roles(title, config_path)
        if roles:
            decision = classify_technology_title(roles[0], config_path)
            return decision.model_copy(update={"source": "mixed_title_rule"})
        return CategoryDecision(category=None, source=None)

    matches: list[str] = []
    fallbacks: list[str] = []
    for category in categories:
        strong = category.get("strong_keywords", [])
        keywords = category.get("keywords", [])
        if (
            _matches(title, strong)
            or _matches(title, keywords)
            or any(
                re.search(pattern, title, re.I) for pattern in category.get("title_patterns", [])
            )
        ):
            matches.append(category["title"])
        elif any(
            re.search(pattern, title, re.I)
            for pattern in category.get("fallback_title_patterns", [])
        ):
            fallbacks.append(category["title"])

    if not matches:
        matches = fallbacks

    if not matches:
        return CategoryDecision(category=None, source=None)

    return CategoryDecision(
        category=matches[0],
        secondary_categories=matches[1:],
        source="title_rule",
    )
