"""Repeatable XLSX discovery import; never activates a recruitment source."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import yaml

from ingest.dedupe.exact import canonicalize_apply_url

ROOT = Path(__file__).resolve().parents[1]
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
STATES = {"pending", "verified", "trial", "active", "manual", "blocked", "retired"}


def safe_url(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username:
            return None
        if parsed.password or any(c.isspace() for c in parsed.netloc):
            return None
        return urlunsplit(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path or "/",
                parsed.query,
                parsed.fragment,
            )
        )
    except ValueError:
        return None


def portal_url(value: str) -> str:
    url = safe_url(value)
    if not url:
        raise ValueError("Invalid recruitment URL")
    return canonicalize_apply_url(url)


def stable_id(prefix: str, key: str) -> str:
    return prefix + hashlib.sha256(key.encode()).hexdigest()[:16]


def platform_for(url: str) -> str:
    host = urlsplit(url).hostname or ""
    for suffix, name in (
        ("ashbyhq.com", "ashby"),
        ("greenhouse.io", "greenhouse"),
        ("lever.co", "lever"),
        ("breezy.hr", "breezy"),
        ("smartrecruiters.com", "smartrecruiters"),
        ("myworkdayjobs.com", "workday"),
        ("oraclecloud.com", "oracle"),
        ("taleo.net", "taleo"),
        ("workable.com", "workable"),
        ("careers-page.com", "manatal"),
        ("applytojob.com", "jazzhr"),
        ("linkedin.com", "social"),
        ("facebook.com", "social"),
    ):
        if host == suffix or host.endswith("." + suffix):
            return name
    return "custom"


def workbook_rows(path: Path):
    """Read values only, using standard XLSX XML; do not execute workbook content."""
    with ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = [
                "".join(item.itertext())
                for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("s:si", NS)
            ]
        links = {
            r.attrib["Id"]: r.attrib["Target"]
            for r in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        }
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        for sheet in workbook.findall("s:sheets/s:sheet", NS):
            target = links[sheet.attrib[f"{{{REL}}}id"]]
            target = target.lstrip("/") if target.startswith("/") else "xl/" + target
            for row in ET.fromstring(archive.read(target)).findall("s:sheetData/s:row", NS):
                cells = {}
                for cell in row.findall("s:c", NS):
                    column = re.sub(r"\d", "", cell.attrib["r"])
                    value = cell.findtext("s:v", default="", namespaces=NS)
                    if cell.attrib.get("t") == "s":
                        value = shared[int(value)] if value else ""
                    elif cell.attrib.get("t") == "inlineStr":
                        value = "".join(cell.find("s:is", NS).itertext())
                    cells[column] = value.strip()
                yield sheet.attrib["name"], int(row.attrib["r"]), cells


def read_registry(path: Path, key: str) -> dict:
    if not path.exists():
        return {"schema_version": 1, key: []}
    # Safe C parsing avoids repeatedly spending seconds on the large directories.
    return yaml.load(path.read_text(), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))


def import_workbook(path: Path, config_dir: Path, *, exclude_sheets=()) -> tuple[dict, dict]:
    employers_doc = read_registry(config_dir / "employers.yaml", "employers")
    sources_doc = read_registry(config_dir / "employer-sources.yaml", "sources")
    employers = {item["id"]: item for item in employers_doc["employers"]}
    sources = {item["id"]: item for item in sources_doc["sources"]}
    # Import keys survive reviewed renames, aliases, sector edits and URL changes.
    by_key = {key: item for item in employers.values() for key in item.get("import_keys", [])}
    by_url = {
        url: item
        for item in sources.values()
        for url in [item["url"], *item.get("import_urls", [])]
    }
    refs = []
    for sheet, row, values in workbook_rows(path):
        if sheet in {"Sources and scope", *exclude_sheets} or row < 7 or not values.get("A"):
            continue
        name, website = values["A"], safe_url(values.get("C"))
        key = (
            " ".join(name.casefold().split())
            + "|"
            + (urlsplit(website).hostname if website else "")
        )
        employer = by_key.get(key)
        if employer is None:
            employer = {
                "id": stable_id("emp_", key),
                "name": name,
                "aliases": [],
                "sectors": [],
                "website": website,
                "source_ids": [],
                "import_keys": [key],
                "references": [],
            }
            employers[employer["id"]] = by_key[key] = employer
        reference = {
            "workbook": path.name,
            "sheet": sheet,
            "row": row,
            "name": name,
            "category": values.get("B", ""),
            "notes": values.get("E", ""),
            "careers_url": values.get("D", ""),
        }
        if reference not in employer["references"]:
            employer["references"].append(reference)
        if sheet not in employer["sectors"]:
            employer["sectors"].append(sheet)
        if safe_url(values.get("D")):
            url = portal_url(values["D"])
            source = by_url.get(url)
            if source is None:
                platform = platform_for(url)
                source = {
                    "id": stable_id("employer_", url),
                    "url": url,
                    "import_urls": [url],
                    "platform": platform,
                    "status": "manual" if platform == "social" else "pending",
                    "employer_ids": [],
                    "access_method": None,
                    "country_filters": [],
                    "refresh_hours": 24,
                    "discovery_refresh_hours": 168,
                    "supports_absence_expiry": False,
                    "crawl": {
                        "max_pages": 5,
                        "max_requests_per_run": 12,
                        "request_delay_ms": 1500,
                        "timeout_seconds": 20,
                        "retry_delays_seconds": [5, 20],
                    },
                    "verification": {},
                    "suggestions": {"platform": platform},
                }
                sources[source["id"]] = by_url[url] = source
            if employer["id"] not in source["employer_ids"]:
                source["employer_ids"].append(employer["id"])
            if source["id"] not in employer["source_ids"]:
                employer["source_ids"].append(source["id"])
            notes = values.get("E", "")
            flags = source.setdefault("suggestions", {})
            for flag, pattern in {
                "needs_location_filter": (
                    r"filter (Kenya|locations?)|global (roles|board)|group portal"
                ),
                "shared_portal": r"shared|parent group|group (portal|board|recruitment)",
                "access_gap": r"fetch failed|could not be fetched|not (fully )?verified|unverified",
                "historical": r"historical|archive",
                "mixed_opportunities": r"talent.pool|volunteer|fellowship|training",
            }.items():
                if re.search(pattern, notes, re.I):
                    flags[flag] = True
        refs.append(reference)
    employers_doc.update(
        {
            "import": {
                "workbook": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "excluded_sheets": sorted(exclude_sheets),
                "directory_entries": len(refs),
            },
            "employers": sorted(employers.values(), key=lambda e: e["id"]),
        }
    )
    sources_doc["sources"] = sorted(sources.values(), key=lambda s: s["id"])
    return employers_doc, sources_doc


def public_registry(employers: dict, sources: dict) -> dict:
    portals = {s["id"]: s for s in sources["sources"]}
    if any(not safe_url(s["url"]) for s in portals.values()):
        raise ValueError("Unsafe public recruitment URL")
    if any(e.get("website") and not safe_url(e["website"]) for e in employers["employers"]):
        raise ValueError("Unsafe public employer website")
    return {
        "schema_version": 1,
        "directory_entries": employers["import"]["directory_entries"],
        "employers": [
            {
                "id": e["id"],
                "name": e["name"],
                "aliases": e["aliases"],
                "sectors": e["sectors"],
                "website": e["website"],
                "sources": [
                    {"id": sid, "url": portals[sid]["url"], "status": portals[sid]["status"]}
                    for sid in e["source_ids"]
                    if sid in portals
                ],
            }
            for e in sorted(employers["employers"], key=lambda e: e["name"].casefold())
        ],
    }


def export_registry(config_dir: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            public_registry(
                read_registry(config_dir / "employers.yaml", "employers"),
                read_registry(config_dir / "employer-sources.yaml", "sources"),
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path)
    parser.add_argument("--config-dir", type=Path, default=ROOT / "config")
    parser.add_argument("--exclude-sheet", action="append", default=[])
    parser.add_argument("--public-output", type=Path, default=ROOT / "site/src/data/employers.json")
    args = parser.parse_args()
    if args.workbook:
        employers, sources = import_workbook(
            args.workbook, args.config_dir, exclude_sheets=args.exclude_sheet
        )
        args.config_dir.mkdir(parents=True, exist_ok=True)
        for filename, doc in (("employers.yaml", employers), ("employer-sources.yaml", sources)):
            (args.config_dir / filename).write_text(
                yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
            )
    export_registry(args.config_dir, args.public_output)


if __name__ == "__main__":
    main()
