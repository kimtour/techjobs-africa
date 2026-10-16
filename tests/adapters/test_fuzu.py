from datetime import date

from ingest.adapters.fuzu import parse_fuzu_listing_page


def test_listing_page_uses_fuzu_campaign_start_as_published_date() -> None:
    page_url = "https://www.fuzu.com/job/computers-software-development?filters%5Bcountry_id%5D=1"
    job_url = "https://www.fuzu.com/kenya/jobs/data-engineer-example"
    html = f'''<script type="application/ld+json">{{
      "@type": "ItemList",
      "itemListElement": [{{"name": "Data Engineer", "url": "{job_url}"}}]
    }}</script>
    <script type="application/json">{{
      "context": {{"page_info": {{"jobs": [{{
        "path": "/kenya/jobs/data-engineer-example",
        "campaign_start_date": 1790640000,
        "company_name": "Example Engineering Ltd",
        "description": "This must not be retained."
      }}]}}}}
    }}</script>'''

    jobs, next_page = parse_fuzu_listing_page(html, page_url)

    assert len(jobs) == 1
    assert jobs[0].published_date == date(2026, 9, 29)
    assert jobs[0].company == "Example Engineering Ltd"
    assert "description" not in jobs[0].model_dump()
    assert next_page is None


def test_listing_page_omits_date_when_fuzu_does_not_publish_one() -> None:
    html = """<script type="application/ld+json">{
      "@type": "ItemList",
      "itemListElement": [{"name": "Developer", "url": "https://www.fuzu.com/kenya/jobs/developer"}]
    }</script>"""

    jobs, _ = parse_fuzu_listing_page(
        html, "https://www.fuzu.com/job/computers-software-development"
    )

    assert jobs[0].published_date is None


def test_timeout_is_not_reported_as_a_complete_crawl():
    import pytest
    import requests

    from ingest.adapters.fuzu import FuzuAdapter

    class TimedOutSession:
        def get(self, *args, **kwargs):
            raise requests.exceptions.ReadTimeout()

    adapter = FuzuAdapter(session=TimedOutSession())
    with pytest.raises(requests.exceptions.ReadTimeout):
        adapter.fetch()
    assert adapter.crawl_complete is False


def test_detail_uses_only_matching_job_record_and_excludes_recommendations_and_expired_jobs():
    import json

    from ingest.adapters.fuzu import detail_technical_context

    url = "https://www.fuzu.com/kenya/jobs/group-systems-manager"
    record = {
        "title": "Group Systems Manager",
        "path": "/kenya/jobs/group-systems-manager",
        "description": "ERP configuration and technical support.",
        "expired": False,
    }

    def body(own):
        return (
            '<script type="application/json">'
            + json.dumps(
                {
                    "context": {
                        "job_details": own,
                        "similar_jobs": [record],
                    }
                }
            )
            + "</script>"
        )

    assert (
        detail_technical_context(record["title"], body(record), url) == "enterprise_systems_support"
    )
    for change in [
        {"title": "Other vacancy"},
        {"path": "/kenya/jobs/other"},
        {"expired": True},
        {"description": "Office administration."},
    ]:
        assert detail_technical_context(record["title"], body({**record, **change}), url) is None
    assert detail_technical_context(record["title"], body({}), url) is None
