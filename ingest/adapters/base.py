"""Adapter contracts shared by source implementations."""

from __future__ import annotations

from typing import Protocol

from ingest.models import RawJob


class SourceAdapter(Protocol):
    source_id: str

    def fetch(self) -> list[RawJob]:
        """Return only active source records from one healthy source run."""
