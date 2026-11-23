"""Remote OK's public recent-jobs feed, with original followed listing links."""

import httpx

from ingest.adapters.remote_feeds import identity, listing_url, location, posted, text
from ingest.classify.evidence import description_technical_context
from ingest.models import RawJob

API = "https://remoteok.com/api"


def parse_job(record: object) -> RawJob | None:
    if not isinstance(record, dict):
        raise ValueError("Invalid Remote OK record")
    external_id = identity(record.get("id"))
    url = listing_url(record.get("url"), "remoteok.com", "/remote-jobs/")
    if not url.split("?", 1)[0].endswith("-" + external_id):
        raise ValueError("Remote OK URL/ID mismatch")
    title, company = text(record.get("position")), text(record.get("company"))
    published = posted(record.get("date"))
    geo = location(record.get("location"))
    if not geo:
        return None
    return RawJob(
        source_id="remoteok",
        source_publisher="Remote OK",
        external_id=external_id,
        title=title,
        company=company,
        location=geo,
        source_url=url,
        apply_url=url,
        published_at=published,
        technical_context=description_technical_context(title, record.get("description")),
    )


class RemoteOKAdapter:
    def __init__(self, client: httpx.Client | None = None):
        self._client = client or httpx.Client(
            headers={"User-Agent": "TechKaziBot/0.1", "Accept": "application/json"}
        )
        self.crawl_complete = False

    def fetch(self) -> list[RawJob]:
        self.crawl_complete = False
        response = self._client.get(API, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if (
            not isinstance(payload, list)
            or not payload
            or not isinstance(payload[0], dict)
            or not isinstance(payload[0].get("legal"), str)
            or "Remote OK" not in payload[0]["legal"]
            or "last_updated" not in payload[0]
        ):
            raise ValueError("Missing Remote OK feed metadata")
        jobs, seen = [], set()
        for row in payload[1:]:
            raw = parse_job(row)
            key = identity(row.get("id"))
            if key in seen:
                raise ValueError("Repeated Remote OK identity")
            seen.add(key)
            if raw:
                jobs.append(raw)
        self.crawl_complete = True
        return jobs
