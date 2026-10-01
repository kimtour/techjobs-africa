"""Deterministic title-based technology classification."""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel

CONFIG_PATH = Path("config/categories.yaml")


class CategoryDecision(BaseModel):
    category: str | None
    secondary_categories: list[str] = []
    source: str | None


def _matches(title: str, keywords: list[str]) -> bool:
    normalized = title.casefold()
    # Seniority may appear between the domain and function (ICT Senior Analyst,
    # Cloud Lead Engineer). It changes rank, not the technical function.
    normalized = re.sub(r"\b(senior|junior|principal|lead|sr\.?|jr\.?)\s+", "", normalized)
    return any(
        re.search(rf"(?<!\w){re.escape(keyword.casefold())}(?!\w)", normalized)
        for keyword in keywords
    )


def has_non_technical_exclusion(value: str, config_path: Path = CONFIG_PATH) -> bool:
    """Return whether a title or URL label names an excluded job function."""

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return _matches(value, config.get("non_tech_exclusions", []))


def classify_technology_title(title: str, config_path: Path = CONFIG_PATH) -> CategoryDecision:
    """Return a category only when the title has deterministic technical evidence."""

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    categories = config["categories"]
    exclusions = config.get("non_tech_exclusions", [])

    # Broad technical terms can occur in non-technical commercial and support
    # roles (for example, "Sales Officer – ICT Solutions"). A job function
    # explicitly excluded by the taxonomy is never made technical by a generic
    # technology keyword elsewhere in its title.
    if _matches(title, exclusions):
        return CategoryDecision(category=None, source=None)

    matches: list[str] = []
    for category in categories:
        strong = category.get("strong_keywords", [])
        keywords = category.get("keywords", [])
        if _matches(title, strong) or _matches(title, keywords):
            matches.append(category["title"])

    if not matches:
        return CategoryDecision(category=None, source=None)

    return CategoryDecision(
        category=matches[0],
        secondary_categories=matches[1:],
        source="title_rule",
    )
