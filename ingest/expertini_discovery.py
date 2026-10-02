"""Read only Expertini's advertised public XML; never job descriptions or challenges."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

import httpx

INDEX_URL = "https://ke.expertini.com/sitemapindex.xml"
LIST_URL = "https://ke.expertini.com/job_listing1.xml"
RSS_URL = "https://ke.expertini.com/jobs/feed.xml"
ROBOTS_URL = "https://ke.expertini.com/robots.txt"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def probe(output: Path) -> None:
    evidence = {"checked_at": datetime.now(UTC).isoformat(), "requests": [], "jobs": []}
    with httpx.Client(follow_redirects=False) as client:
        for url in (ROBOTS_URL, INDEX_URL, LIST_URL, RSS_URL):
            response = client.get(url, timeout=25)
            evidence["requests"].append(
                {
                    "url": url,
                    "http_status": response.status_code,
                    "content_type": response.headers.get("content-type"),
                    "bytes": len(response.content),
                }
            )
            response.raise_for_status()
            if url == ROBOTS_URL:
                evidence["robots"] = response.text
            else:
                root = ElementTree.fromstring(response.content)
                if url == RSS_URL:
                    if root.tag != "rss":
                        raise ValueError("Expertini RSS response is not RSS")
                    evidence["rss"] = [
                        {key: e.findtext(key) for key in ("title", "link", "guid", "pubDate")}
                        for e in root.findall("channel/item")
                    ]
                elif url == INDEX_URL:
                    evidence["advertised_sitemaps"] = [
                        e.text for e in root.findall("s:sitemap/s:loc", NS)
                    ]
                else:
                    evidence["jobs"] = [
                        {
                            "url": e.findtext("s:loc", namespaces=NS),
                            "modified_at": e.findtext("s:lastmod", namespaces=NS),
                        }
                        for e in root.findall("s:url", NS)
                    ]
    if LIST_URL not in evidence["advertised_sitemaps"] or not evidence["jobs"]:
        raise ValueError("No advertised Expertini listing sitemap")
    output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(
        f"Verified public Expertini XML: {len(evidence['jobs'])} sitemap links, "
        f"{len(evidence['rss'])} RSS items; no descriptions."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    probe(parser.parse_args().output)


if __name__ == "__main__":
    main()
