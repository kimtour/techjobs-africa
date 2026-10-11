from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import yaml

CONFIG_PATH = Path("config/sources.yaml")
MARKDOWN_OUTPUT = Path("docs/source-discovery.md")
JSON_OUTPUT = Path("m0-results.json")

CONTACT_URL = os.getenv("CRAWLER_CONTACT_URL", "").strip()
CONTACT_EMAIL = os.getenv("CRAWLER_CONTACT_EMAIL", "").strip()
RUN_ENVIRONMENT = os.getenv("M0_ENV", "local").strip() or "local"

contact = CONTACT_URL or CONTACT_EMAIL or "contact-not-configured"
USER_AGENT = f"TechKaziBot/0.1 (+{contact})"

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/json,application/xml;q=0.9,*/*;q=0.8",
}


def load_sources() -> list[dict]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"{CONFIG_PATH} is missing.")

    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return data.get("sources", [])


def robots_info(client: httpx.Client, target_url: str) -> dict:
    parsed = urlparse(target_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    result = {
        "robots_url": robots_url,
        "robots_status": None,
        "robots_allowed": None,
        "robots_error": None,
    }

    try:
        response = client.get(robots_url, timeout=10.0)
        result["robots_status"] = response.status_code

        if response.status_code != 200:
            return result

        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        result["robots_allowed"] = parser.can_fetch(USER_AGENT, target_url)
    except Exception as exc:
        result["robots_error"] = str(exc)

    return result


def classify_format(content_type: str, text_sample: str) -> str:
    ctype = (content_type or "").lower()
    sample = (text_sample or "").lstrip().lower()

    if "application/json" in ctype or sample.startswith("{") or sample.startswith("["):
        return "json"
    if "xml" in ctype or "rss" in ctype or sample.startswith("<?xml"):
        return "xml/rss"
    if "text/html" in ctype or "<html" in sample or "<!doctype html" in sample:
        return "html"
    return "unknown"


def extract_clues(text: str) -> dict:
    lower = text.lower()

    return {
        "has_next_data": "__next_data__" in lower,
        "mentions_wp_json": "/wp-json/" in lower,
        "mentions_rss": "application/rss+xml" in lower or "application/atom+xml" in lower,
        "has_pagination_words": any(
            token in lower for token in ["next page", "pagination", "page="]
        ),
        "has_job_schema": '"jobposting"' in lower or "jobposting" in lower,
    }


def status_class(status_code: int | None, error: str | None) -> str:
    if error:
        if "timeout" in error.lower():
            return "TIMEOUT"
        return "NETWORK_ERROR"

    if status_code is None:
        return "UNKNOWN"
    if status_code in (403,):
        return "BLOCKED"
    if status_code in (429,):
        return "RATE_LIMITED"
    if 500 <= status_code <= 599:
        return "SERVER_ERROR"
    if 200 <= status_code <= 399:
        return "ACCESSIBLE"
    return "HTTP_ERROR"


def probe_source(client: httpx.Client, source: dict) -> dict:
    source_id = source["id"]
    target_url = source.get("discovery_url")

    if source.get("enabled") is False:
        return {
            "source_id": source_id,
            "requested_url": target_url,
            "status_class": "SKIPPED",
            "error": "Source is disabled in config/sources.yaml; no request made.",
        }

    if not target_url:
        return {
            "source_id": source_id,
            "status_class": "SKIPPED",
            "error": "No discovery_url configured",
        }

    robots = robots_info(client, target_url)

    result = {
        "source_id": source_id,
        "requested_url": target_url,
        "final_url": None,
        "status_code": None,
        "status_class": None,
        "content_type": None,
        "response_bytes": 0,
        "redirect_count": 0,
        "retry_after": None,
        "format": None,
        "sample": None,
        "clues": {},
        "error": None,
        **robots,
    }

    try:
        response = client.get(
            target_url,
            follow_redirects=True,
            timeout=float(source.get("crawl", {}).get("timeout_seconds", 15)),
        )

        text = response.text
        sample = " ".join(text[:500].split())

        result.update(
            {
                "final_url": str(response.url),
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "response_bytes": len(response.content),
                "redirect_count": len(response.history),
                "retry_after": response.headers.get("retry-after"),
                "format": classify_format(
                    response.headers.get("content-type", ""),
                    text[:1000],
                ),
                "sample": sample,
                "clues": extract_clues(text[:250000]),
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["status_class"] = status_class(
        result["status_code"],
        result["error"],
    )

    return result


def write_markdown(results: list[dict]) -> None:
    MARKDOWN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# M0 Source Discovery",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Environment: {RUN_ENVIRONMENT}",
        "",
        "> This is a technical probe only. Terms of Service review still requires manual "
        "confirmation.",
        "",
        "| Source | HTTP | Access | Format | Redirects | Robots allowed? | Bytes |",
        "|---|---:|---|---|---:|---|---:|",
    ]

    for r in results:
        lines.append(
            "| {source} | {status} | {access} | {fmt} | {redirects} | {robots} | {size} |".format(
                source=r.get("source_id", ""),
                status=r.get("status_code", "N/A"),
                access=r.get("status_class", "N/A"),
                fmt=r.get("format", "N/A"),
                redirects=r.get("redirect_count", 0),
                robots=r.get("robots_allowed", "unknown"),
                size=r.get("response_bytes", 0),
            )
        )

    lines.extend(["", "## Per-source details", ""])

    for r in results:
        lines.extend(
            [
                f"### {r.get('source_id')}",
                "",
                f"- Requested URL: `{r.get('requested_url')}`",
                f"- Final URL: `{r.get('final_url')}`",
                f"- Access: `{r.get('status_class')}`",
                f"- HTTP: `{r.get('status_code')}`",
                f"- Content-Type: `{r.get('content_type')}`",
                f"- Format hypothesis: `{r.get('format')}`",
                f"- Redirects: `{r.get('redirect_count')}`",
                f"- Retry-After: `{r.get('retry_after')}`",
                f"- robots.txt: `{r.get('robots_url')}`",
                f"- robots HTTP: `{r.get('robots_status')}`",
                f"- robots allowed for configured agent/path: `{r.get('robots_allowed')}`",
                f"- Response bytes: `{r.get('response_bytes')}`",
                f"- Clues: `{json.dumps(r.get('clues', {}), sort_keys=True)}`",
                f"- Error: `{r.get('error')}`",
                "",
                "Sanitized first 500 chars:",
                "",
                "```text",
                r.get("sample") or "",
                "```",
                "",
                "Manual ToS / permission review: **PENDING**",
                "",
            ]
        )

    MARKDOWN_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    sources = load_sources()
    results: list[dict] = []

    with httpx.Client(headers=HEADERS) as client:
        for source in sources:
            print(f"Probing {source['id']}...")
            results.append(probe_source(client, source))
            delay_ms = source.get("crawl", {}).get("request_delay_ms", 0) or 0
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)

    write_markdown(results)
    JSON_OUTPUT.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": datetime.now(UTC).isoformat(),
                "user_agent": USER_AGENT,
                "environment": RUN_ENVIRONMENT,
                "results": results,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print(f"Markdown: {MARKDOWN_OUTPUT}")
    print(f"JSON: {JSON_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
