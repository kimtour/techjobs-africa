"""Normalize structured job locations using the maintained geography config."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_PATH = Path("config/geography.yaml")


@dataclass(frozen=True)
class LocationDecision:
    city: str | None
    country: str | None
    country_code: str | None
    workplace_type: str | None


def _contains(value: str, phrase: str) -> bool:
    return bool(re.search(rf"(?<!\w){re.escape(phrase.casefold())}(?!\w)", value.casefold()))


def normalize_location(location: str | None, config_path: Path = CONFIG_PATH) -> LocationDecision:
    """Map configured city/country phrases without guessing from unknown text."""

    if not location or not location.strip():
        return LocationDecision(None, None, None, None)
    value = location.strip()
    remote = _contains(value, "remote")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    matches: list[tuple[int, str, str, str | None]] = []
    for country in config["countries"]:
        country_name = country["name"]
        for phrase in [country_name, *country.get("aliases", [])]:
            if _contains(value, phrase):
                matches.append((len(phrase), country_name, country["code"], None))
        for city in country.get("cities", []):
            if _contains(value, city):
                matches.append((len(city), country_name, country["code"], city))

    if matches:
        _, country, country_code, city = max(matches, key=lambda match: match[0])
        return LocationDecision(city, country, country_code, "Remote" if remote else None)
    if remote:
        return LocationDecision(None, None, None, "Remote")
    return LocationDecision(None, None, None, None)
