"""Activation gates and daily due policy for registry-backed sources."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from functools import partial
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from ingest.adapters.public_ats import API_METHODS, PublicATSAdapter
from ingest.adapters.registry_boards import SUPPORTED, RegistryBoardAdapter
from ingest.adapters.structured_employers import METHODS, StructuredEmployerAdapter
from ingest.employer_registry import ROOT, STATES, read_registry

CHECKS = (
    "official_link",
    "collection_review",
    "local_access",
    "runner_access",
    "stable_ids",
    "application_links",
    "locations",
    "dates_reviewed",
    "complete",
)


def load_sources(config_dir: Path = ROOT / "config") -> tuple[dict, dict]:
    employers = {
        e["id"]: e for e in read_registry(config_dir / "employers.yaml", "employers")["employers"]
    }
    sources = {
        s["id"]: s
        for s in read_registry(config_dir / "employer-sources.yaml", "sources")["sources"]
    }
    for source in sources.values():
        if source["status"] not in STATES:
            raise ValueError("Unknown source lifecycle status")
        if not source["employer_ids"] or any(e not in employers for e in source["employer_ids"]):
            raise ValueError("Unresolved employer-source link")
        if source.get("refresh_hours", 0) < 24:
            raise ValueError("Employer boards must not run more than daily")
        if source.get("supports_absence_expiry"):
            raise ValueError("New employer sources require separate absence-policy verification")
    return employers, sources


def verification_gaps(source: dict) -> list[str]:
    evidence = source.get("verification", {})
    gaps = [name for name in CHECKS if evidence.get(name) is not True]
    if not evidence.get("evidence_paths"):
        gaps.append("evidence_paths")
    if not evidence.get("collection_basis"):
        gaps.append("collection_basis")
    if not collector_supported(source):
        gaps.append("supported_board")
    return gaps


def collector_supported(source):
    return (source["platform"] in SUPPORTED and bool(source.get("board"))) or (
        source.get("access_method") in METHODS | API_METHODS
        and bool(source.get("collection", {}).get("listing_url"))
    )


def make_adapter(source, employers):
    if source.get("access_method") in API_METHODS:
        return PublicATSAdapter(source, employers)
    if source.get("access_method") in METHODS:
        return StructuredEmployerAdapter(source, employers)
    return RegistryBoardAdapter(source, employers)


def active_factories(config_dir: Path = ROOT / "config") -> tuple[dict, dict]:
    employers, sources = load_sources(config_dir)
    factories, config = {}, {}
    boards = set()
    for sid, source in sources.items():
        if source["status"] != "active":
            continue
        if verification_gaps(source):
            raise ValueError(f"Active employer source lacks verification: {sid}")
        if not all(
            source["verification"].get(check) is True
            for check in ("trial_review", "publication_review")
        ):
            raise ValueError(f"Active employer source requires trial and publication review: {sid}")
        key = (
            source.get("access_method") or source["platform"],
            source.get("board") or source["collection"]["listing_url"],
            source.get("region"),
        )
        if key in boards:
            raise ValueError("Shared recruitment board must have one active collection source")
        boards.add(key)
        factories[sid] = partial(make_adapter, source, employers)
        config[sid] = {
            **source,
            "enabled": True,
            "production_method": source["platform"],
            "allow_verified_empty": True,
        }
    return factories, config


def daily_slot(source: dict) -> int:
    """Spread collection across the five existing EAT slots, with late catch-up."""
    slots = (6, 9, 12, 15, 19)
    identity = source.get("id")
    return slots[int(sha256(identity.encode()).hexdigest()[:8], 16) % len(slots)] if identity else 6


def source_due(source: dict, health: dict, now: datetime) -> bool:
    last = health.get("last_attempt_at")
    if not last:
        return True
    last = datetime.fromisoformat(last).astimezone(UTC)
    failures = min(health.get("consecutive_failures", 0), 4)
    hours = min(source["refresh_hours"] * 2**failures, 168)
    cooldown = health.get("next_allowed_at")
    # A healthy daily board is due on the next EAT calendar day, avoiding drift.
    if not failures and source["refresh_hours"] == 24:
        due = (
            now.astimezone(ZoneInfo("Africa/Nairobi")).date()
            > last.astimezone(ZoneInfo("Africa/Nairobi")).date()
        ) and now.astimezone(ZoneInfo("Africa/Nairobi")).hour >= daily_slot(source)
    else:
        due = now >= last + timedelta(hours=hours)
    return due and (not cooldown or now >= datetime.fromisoformat(cooldown).astimezone(UTC))
