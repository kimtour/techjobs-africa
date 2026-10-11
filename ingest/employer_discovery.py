"""Bounded M0 probes for screenshot employers; persist metadata only."""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from html import unescape
from pathlib import Path
from urllib.robotparser import RobotFileParser

import httpx

TARGETS = {
    "camunda": "https://api.ashbyhq.com/posting-api/job-board/camunda",
    "blacksmith": "https://api.ashbyhq.com/posting-api/job-board/Blacksmith%20Agency",
    "sdg": "https://social-discovery-ventures.breezy.hr/",
}
ASHBY_FIELDS = (
    "id",
    "title",
    "location",
    "secondaryLocations",
    "isRemote",
    "workplaceType",
    "publishedAt",
    "isListed",
    "jobUrl",
    "applyUrl",
)


def probe() -> dict:
    result = {"checked_at": datetime.now(UTC).isoformat(), "sources": {}}
    with httpx.Client(headers={"User-Agent": "TechKaziBot/0.1"}, timeout=25) as client:
        for source, url in TARGETS.items():
            host = (
                "https://social-discovery-ventures.breezy.hr"
                if source == "sdg"
                else "https://api.ashbyhq.com"
            )
            robots = client.get(host + "/robots.txt")
            rules = RobotFileParser()
            rules.parse(robots.text.replace("\\r\\n", "\n").splitlines())
            response = client.get(url)
            row = {
                "requested_url": url,
                "final_url": str(response.url),
                "http_status": response.status_code,
                "content_type": response.headers.get("content-type"),
                "bytes": len(response.content),
                "robots_http_status": robots.status_code,
                "robots_allows": rules.can_fetch("TechKaziBot/0.1", url)
                if robots.status_code == 200
                else None,
                "access_method": "public_html"
                if source == "sdg"
                else "documented_public_posting_api",
                "javascript_required": False,
            }
            response.raise_for_status()
            if source == "sdg":
                # Capture only the public card's heading/URL, never description text.
                cards = re.findall(
                    r'<li class="position-details[^\"]*">(.*?)</a>', response.text, re.S
                )
                row["jobs"] = []
                for card in cards:
                    href = re.search(r'href="(/p/[^\"]+)"', card)
                    title = re.search(r"<h2>(.*?)</h2>", card, re.S)
                    if href and title:
                        row["jobs"].append({"url": host + href[1], "title": unescape(title[1])})
                row["pagination"] = "single_public_career_page"
            else:
                payload = response.json()
                row["jobs"] = [
                    {key: job.get(key) for key in ASHBY_FIELDS} for job in payload["jobs"]
                ]
                row["pagination"] = "documented_all_published_postings"
            row["job_count"] = len(row["jobs"])
            result["sources"][source] = row
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(probe(), indent=2) + "\n")
