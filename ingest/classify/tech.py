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
    return any(
        re.search(rf"(?<!\w){re.escape(keyword.casefold())}(?!\w)", normalized)
        for keyword in keywords
    )


def classify_technology_title(title: str, config_path: Path = CONFIG_PATH) -> CategoryDecision:
    """Return a category only when the title has deterministic technical evidence."""

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    categories = config["categories"]
    exclusions = config.get("non_tech_exclusions", [])

    matches: list[str] = []
    for category in categories:
        strong = category.get("strong_keywords", [])
        keywords = category.get("keywords", [])
        if _matches(title, strong) or _matches(title, keywords):
            matches.append(category["title"])

    if not matches and _matches(title, exclusions):
        return CategoryDecision(category=None, source=None)
    if not matches:
        return CategoryDecision(category=None, source=None)

    return CategoryDecision(
        category=matches[0],
        secondary_categories=matches[1:],
        source="title_rule",
    )
