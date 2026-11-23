"""Validation shared by the explicitly licensed public remote-job APIs."""

from datetime import UTC, datetime
from html import unescape
from urllib.parse import urlsplit


def text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing source metadata")
    return unescape(value).strip()


def identity(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Invalid source identity")
    result = str(value)
    if not result.isascii() or not result.isdecimal() or int(result) <= 0:
        raise ValueError("Invalid source identity")
    return result


def listing_url(value: object, host: str, prefix: str) -> str:
    value = text(value)
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != host
        or not parsed.path.startswith(prefix)
        or len(parsed.path) <= len(prefix)
        or parsed.fragment
    ):
        raise ValueError("Unsafe source listing URL")
    return value


def location(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    tokens = {part.strip().casefold() for part in value.split(",")}
    # Exact structured tokens only: EMEA is never an African eligibility signal.
    if tokens & {"anywhere", "worldwide"}:
        return "Remote · Worldwide"
    if "kenya" in tokens:
        return "Remote · Kenya"
    if "africa" in tokens:
        return "Remote · Africa"
    return None


def posted(value: object) -> datetime:
    result = datetime.fromisoformat(text(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Publication timestamp must include timezone")
    return result.astimezone(UTC)
