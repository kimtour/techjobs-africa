"""Robots and redirect policy shared by employer discovery and collectors."""

from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from ingest.employer_registry import safe_url


class CollectionBlocked(RuntimeError):
    pass


def read_robots(client, url: str, validator=None):
    parsed = urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = origin + "/robots.txt"
    for _ in range(4):
        if validator:
            validator(robots_url)
        try:
            response = client.get(robots_url)
        except httpx.HTTPStatusError as exc:
            response = exc.response
            if response.status_code not in (301, 302, 303, 307, 308, 404):
                raise
        if response.status_code not in (301, 302, 303, 307, 308):
            break
        robots_url = urljoin(robots_url, response.headers.get("Location", ""))
        if not safe_url(robots_url):
            raise ValueError("Unsafe robots redirect")
    else:
        raise ValueError("Too many robots redirects")
    # A genuine missing robots file has no disallow rules; transport/403/429 do.
    if response.status_code != 404:
        response.raise_for_status()
    parser = RobotFileParser()
    parser.parse(response.text.splitlines() if response.status_code != 404 else [])
    return parser, response.status_code


def robots_allowed(client, url: str, validator=None) -> dict:
    parsed = urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    parser, status = read_robots(client, url, validator)
    return {
        "status": status,
        "allowed": parser.can_fetch("TechKaziBot/0.1", url),
        "url": origin + "/robots.txt",
    }


def checked_get(client, url, validator=None, **kwargs):
    """Follow redirects after checking the destination's robots rules."""
    for _ in range(4):
        if validator:
            validator(url)
        try:
            response = client.get(url, **kwargs)
            if response.status_code == 304:
                return response
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            response = exc.response
            if response.status_code == 304:
                return response
            if response.status_code not in (301, 302, 303, 307, 308):
                raise
            url = urljoin(url, response.headers.get("Location", ""))
            if not safe_url(url) or not robots_allowed(client, url, validator)["allowed"]:
                raise CollectionBlocked("Redirect destination disallows collection") from None
    raise ValueError("Too many public redirects")
