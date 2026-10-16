"""Inspect a job's own description in memory; retain only a rule identifier."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from urllib.parse import urldefrag, urlsplit

import httpx
import requests

from ingest.classify.tech import (
    classify_technology_title,
    listing_technical_context,
    needs_detail_technical_context,
)
from ingest.models import RawJob


class _BodyText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "aside", "nav"):
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "aside", "nav"):
            self.ignored = max(0, self.ignored - 1)

    def handle_data(self, value):
        if not self.ignored:
            self.parts.append(value)


def description_technical_context(title: str, description: object) -> str | None:
    if (
        not isinstance(title, str)
        or not isinstance(description, str)
        or not needs_detail_technical_context(title)
    ):
        return None
    parser = _BodyText()
    parser.feed(description)
    parser.close()
    return listing_technical_context(title, " ".join(parser.parts))


class _StructuredDescriptions(HTMLParser):
    def __init__(self, title: str, url: str):
        super().__init__(convert_charrefs=True)
        self.title = " ".join(title.rsplit(" at ", 1)[0].casefold().split())
        self.url = urldefrag(url)[0].rstrip("/")
        self.in_json = False
        self.parts: list[str] = []
        self.contexts: list[str | None] = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self.in_json = True
            self.parts = []

    def handle_data(self, value):
        if self.in_json:
            self.parts.append(value)

    def handle_endtag(self, tag):
        if tag == "script" and self.in_json:
            self.in_json = False
            try:
                self._read(json.loads("".join(self.parts)))
            except (TypeError, ValueError):
                pass
            self.parts = []

    def _read(self, item):
        if isinstance(item, list):
            for child in item:
                self._read(child)
        elif isinstance(item, dict):
            if "@graph" in item:
                self._read(item["@graph"])
            kind = item.get("@type")
            if kind != "JobPosting" and not (isinstance(kind, list) and "JobPosting" in kind):
                return
            title = item.get("title")
            if not isinstance(title, str):
                return
            if " ".join(title.rsplit(" at ", 1)[0].casefold().split()) != self.title:
                return
            # A same-title recommendation must not supply this job's evidence.
            url = item.get("url") or item.get("@id")
            if isinstance(url, str) and urldefrag(url)[0].rstrip("/") != self.url:
                return
            self.contexts.append(description_technical_context(title, item.get("description")))


def structured_technical_context(title: str, html: str, url: str) -> str | None:
    parser = _StructuredDescriptions(title, url)
    parser.feed(html)
    parser.close()
    contexts = set(parser.contexts)
    return contexts.pop() if len(contexts) == 1 else None


def enrich_listing_jobs(
    jobs: list[RawJob],
    client,
    *,
    allowed_hosts: set[str],
    detail_parser=structured_technical_context,
) -> list[RawJob]:
    """Read only discovered, same-source detail URLs for scoped ambiguous roles."""
    enriched = []
    for job in jobs:
        if classify_technology_title(job.title).category or not needs_detail_technical_context(
            job.title
        ):
            enriched.append(job)
            continue
        url = str(job.source_url)
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
            enriched.append(job)
            continue
        policy = getattr(client, "policy", {})
        if getattr(client, "requests", 0) >= policy.get("max_requests_per_run", float("inf")):
            enriched.append(job)
            continue
        try:
            response = client.get(url, timeout=15)
            response.raise_for_status()
        except (httpx.HTTPStatusError, requests.HTTPError) as exc:
            if exc.response.status_code not in (404, 410):
                raise
            # Missing optional evidence never expires a listing or loses the crawl.
            enriched.append(job)
            continue
        context = detail_parser(job.title, response.text, url)
        enriched.append(job.model_copy(update={"technical_context": context}))
    return enriched
