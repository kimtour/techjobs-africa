"""Full-registry metadata probe. Never extracts jobs or changes accepted state."""

from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from ingest.employer_onboarding import Links, write_json
from ingest.employer_registry import ROOT, platform_for, safe_url
from ingest.registry_sources import load_sources, verification_gaps


class AccessBlocked(RuntimeError):
    pass


class ProbeLimit(RuntimeError):
    pass


def public_target(url: str) -> None:
    """Do not follow workbook links or redirects into local/private services."""
    if not safe_url(url) or platform_for(url) == "social":
        raise AccessBlocked("Unsupported target")
    host = urlsplit(url).hostname
    addresses = socket.getaddrinfo(host, urlsplit(url).port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise AccessBlocked("Non-public target")


class ProbeHTTP:
    """Shared host throttles, robots cache and stop-on-block policy across workers."""

    def __init__(self, *, transport=None, validate=public_target, interval=1.0):
        self.client = httpx.Client(
            headers={"User-Agent": "TechKaziBot/0.1 (+https://techkazi.pages.dev/)"},
            transport=transport,
            follow_redirects=False,
            trust_env=False,
            timeout=10,
        )
        self.validate = validate
        self.interval = interval
        self.guard = threading.Lock()
        self.host_locks = {}
        self.robot_locks = {}
        self.last_request = {}
        self.host_delays = {}
        self.blocked_hosts = set()
        self.robots = {}
        self.requests = 0
        self.local = threading.local()

    def close(self):
        self.client.close()

    def _lock(self, mapping, key):
        with self.guard:
            return mapping.setdefault(key, threading.Lock())

    def _get(self, url):
        self.validate(url)
        if getattr(self.local, "requests", 0) >= 12:
            raise ProbeLimit("Source request budget")
        self.local.requests = getattr(self.local, "requests", 0) + 1
        host = urlsplit(url).hostname
        with self._lock(self.host_locks, host):
            if host in self.blocked_hosts:
                raise AccessBlocked("Host blocked earlier in this probe")
            delay = self.host_delays.get(host, self.interval)
            wait = delay - (time.monotonic() - self.last_request.get(host, 0))
            if wait > 0:
                time.sleep(wait)
            self.last_request[host] = time.monotonic()
            with self.guard:
                self.requests += 1
            with self.client.stream("GET", url) as response:
                # iter_bytes already decompresses the response. Do not ask
                # httpx to decode that materialized body a second time.
                headers = {
                    key: value
                    for key, value in response.headers.items()
                    if key not in {"content-encoding", "content-length", "transfer-encoding"}
                }
                if response.status_code in (401, 403, 429):
                    self.blocked_hosts.add(host)
                    raise AccessBlocked("Access limit")
                if "application/pdf" in response.headers.get("content-type", "").lower():
                    return httpx.Response(
                        response.status_code,
                        headers=headers,
                        content=b"",
                        request=response.request,
                    )
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 2_000_000:
                        raise ProbeLimit("Response exceeds probe limit")
                return httpx.Response(
                    response.status_code,
                    headers=headers,
                    content=bytes(body),
                    request=response.request,
                )

    def allowed(self, url):
        parsed = urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        with self._lock(self.robot_locks, origin):
            if origin not in self.robots:
                response = self.fetch(origin + "/robots.txt", check_robots=False)
                if response.status_code == 404:
                    parser = RobotFileParser()
                    parser.parse([])
                else:
                    response.raise_for_status()
                    parser = RobotFileParser()
                    parser.parse(response.text.splitlines())
                self.robots[origin] = parser
            parser = self.robots[origin]
        if not parser.can_fetch("TechKaziBot/0.1", url):
            raise AccessBlocked("Robots disallow")
        # Honour a published Crawl-delay where it exceeds the default host gap.
        delay = parser.crawl_delay("TechKaziBot/0.1") or parser.crawl_delay("*")
        if delay and delay > 60:
            raise AccessBlocked("Published crawl delay exceeds this probe's budget")
        host = parsed.hostname
        with self.guard:
            self.host_delays[host] = max(self.host_delays.get(host, self.interval), delay or 0)

    def fetch(self, url, *, check_robots=True):
        for _ in range(5):
            self.validate(url)
            if check_robots:
                self.allowed(url)
            response = self._get(url)
            if response.status_code not in (301, 302, 303, 307, 308):
                return response
            destination = response.headers.get("Location")
            if not destination:
                raise ProbeLimit("Missing redirect destination")
            url = urljoin(url, destination)
        raise ProbeLimit("Redirect limit")


def inspect_page(response) -> dict:
    url = str(response.url)
    content_type = response.headers.get("content-type", "").lower()
    if "rss+xml" in content_type or "atom+xml" in content_type:
        return {"method_suggestion": "feed", "feed_urls": [url], "resolved_url": url}
    if "application/pdf" in content_type or urlsplit(url).path.lower().endswith(".pdf"):
        return {"method_suggestion": "pdf", "pdf_urls": [url], "resolved_url": url}
    parser = Links()
    parser.feed(response.text)
    links = sorted({urljoin(url, link) for link in parser.links if safe_url(urljoin(url, link))})
    boards = sorted(
        {link for link in [url, *links] if platform_for(link) not in {"custom", "social"}}
    )
    feeds = sorted({urljoin(url, feed) for feed in parser.feeds if safe_url(urljoin(url, feed))})
    pdfs = [link for link in links if urlsplit(link).path.lower().endswith(".pdf")]
    vacancies = [
        link
        for link in links
        if any(
            term in urlsplit(link).path.lower()
            for term in ("/job/", "/jobs/", "/vacanc", "/position/")
        )
    ]
    method = (
        "ats_api"
        if boards
        else "structured_data"
        if parser.structured_job_count
        else "feed"
        if feeds
        else "pdf"
        if pdfs
        else "link_diff"
        if vacancies
        else "needs_review"
    )
    return {
        "method_suggestion": method,
        "resolved_url": url,
        "detected_boards": boards[:15],
        "platform_suggestions": sorted({platform_for(link) for link in boards}),
        "structured_job_count": parser.structured_job_count,
        "feed_urls": feeds[:5],
        "pdf_urls": pdfs[:15],
        "vacancy_links_sample": vacancies[:10],
        "careers_links": [
            link
            for link in links
            if any(
                term in urlsplit(link).path.lower()
                for term in ("/career", "/jobs", "/join-our-team")
            )
        ][:10],
    }


def probe_source(source, http) -> dict:
    http.local.requests = 0
    result = {
        "source_id": source["id"],
        "input_url": source.get("url"),
        "source_status": source["status"],
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "FAILED",
        "method_suggestion": "needs_review",
        "production_promoted": False,
        "collection_verified": False,
    }
    if source["status"] in {"manual", "blocked", "retired"} or source["platform"] == "social":
        result.update(status="SKIPPED", method_suggestion="manual_or_blocked")
        return result
    try:
        response = http.fetch(source["url"])
        result["http_status"] = response.status_code
        response.raise_for_status()
        result.update(inspect_page(response))
        # At most one observed same-host careers link, only if no method is visible.
        if result["method_suggestion"] == "needs_review":
            host = urlsplit(str(response.url)).hostname
            careers = [
                link
                for link in result.get("careers_links", [])
                if urlsplit(link).hostname == host and link != str(response.url)
            ]
            if careers:
                detail = http.fetch(careers[0])
                detail.raise_for_status()
                result.update(inspect_page(detail))
        result["status"] = "DISCOVERED"
    except AccessBlocked:
        result.update(status="BLOCKED", method_suggestion="manual_or_blocked")
    except ProbeLimit as exc:
        result.update(status="PARTIAL", error_type=type(exc).__name__)
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["http_status"] = getattr(getattr(exc, "response", None), "status_code", None)
    return result


def coverage(employers, sources, results):
    rows = []
    for employer in sorted(employers.values(), key=lambda e: e["id"]):
        linked = [s for s in sources.values() if employer["id"] in s["employer_ids"]]
        active = [
            s["id"]
            for s in linked
            if s["status"] == "active"
            and not verification_gaps(s)
            and all(
                s["verification"].get(k) is True for k in ("trial_review", "publication_review")
            )
        ]
        evidence = [results[s["id"]] for s in linked if s["id"] in results]
        rows.append(
            {
                "employer_id": employer["id"],
                "employer": employer["name"],
                "source_ids": [s["id"] for s in linked],
                "active_verified_sources": active,
                "daily_collection_configured": bool(active),
                "probe_outcomes": sorted({r["status"] for r in evidence}) or ["NOT_CHECKED"],
                "method_suggestions": sorted({r["method_suggestion"] for r in evidence}),
            }
        )
    return {
        "schema_version": 1,
        "checked_at": datetime.now(UTC).isoformat(),
        "mode": "discovery_only",
        "production_promoted": False,
        "employers": len(rows),
        "recruitment_sources": len(sources),
        "sources_probed": len(results),
        "daily_collection_configured": sum(r["daily_collection_configured"] for r in rows),
        "source_outcomes": dict(Counter(r["status"] for r in results.values())),
        "method_suggestions": dict(Counter(r["method_suggestion"] for r in results.values())),
        "companies": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=ROOT / "config")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8, choices=range(1, 13))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.resume:
        parser.error("Use a new output directory, or --resume for an interrupted probe")
    employers, sources = load_sources(args.config_dir)
    results = {}
    if args.resume:
        for sid in sources:
            path = args.output_dir / "sources" / f"{sid}.json"
            if path.exists():
                previous = json.loads(path.read_text())
                if (
                    previous.get("input_url") == sources[sid].get("url")
                    and previous.get("source_status") == sources[sid]["status"]
                ):
                    results[sid] = previous
    http = ProbeHTTP()
    # Resuming an interrupted assessment must not reset known access blocks.
    http.blocked_hosts.update(
        urlsplit(row["input_url"]).hostname
        for row in results.values()
        if row["status"] == "BLOCKED" and row.get("input_url")
    )
    started = time.monotonic()
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(probe_source, s, http): sid
                for sid, s in sources.items()
                if sid not in results
            }
            for future in as_completed(futures):
                sid = futures[future]
                results[sid] = future.result()
                write_json(args.output_dir / "sources" / f"{sid}.json", results[sid])
                if len(results) % 25 == 0:
                    print(f"Assessed {len(results)}/{len(sources)} recruitment sources", flush=True)
    finally:
        http.close()
        report = coverage(employers, sources, results)
        report.update(duration_seconds=round(time.monotonic() - started, 2), requests=http.requests)
        write_json(args.output_dir / "coverage.json", report)
        text = (
            "# Full-list employer coverage probe\n\n"
            "Discovery only: no vacancies published, lifecycle changes or accepted-state writes.\n"
            "Method detections are suggestions, not collection permission or job coverage.\n\n"
            f"Employers: {len(employers)}. Recruitment sources: {len(sources)}.\n"
            f"Sources assessed: {len(results)}. Employers with daily collection configured: "
            f"{report['daily_collection_configured']}.\n\n"
            "| Probe outcome | Sources |\n|---|---:|\n"
            + "".join(f"| {k} | {v} |\n" for k, v in sorted(report["source_outcomes"].items()))
            + "\n| Suggested method | Sources |\n|---|---:|\n"
            + "".join(f"| {k} | {v} |\n" for k, v in sorted(report["method_suggestions"].items()))
            + f"\nRequests: {http.requests}. Elapsed: {report['duration_seconds']} seconds.\n\n"
            "A reachable page is not a complete vacancy check. Unsupported, blocked and failed\n"
            "sources never count as having no new jobs. See coverage.json for all employers.\n"
        )
        (args.output_dir / "report.md").write_text(text)
    print(json.dumps({k: v for k, v in report.items() if k != "companies"}))


if __name__ == "__main__":
    main()
