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
        "description": "This must not be retained."
      }}]}}}}
    }}</script>'''

    jobs, next_page = parse_fuzu_listing_page(html, page_url)

    assert len(jobs) == 1
    assert jobs[0].published_date == date(2026, 9, 29)
    assert "description" not in jobs[0].model_dump()
    assert next_page is None


def test_listing_page_omits_date_when_fuzu_does_not_publish_one() -> None:
    html = '''<script type="application/ld+json">{
      "@type": "ItemList",
      "itemListElement": [{"name": "Developer", "url": "https://www.fuzu.com/kenya/jobs/developer"}]
    }</script>'''

    jobs, _ = parse_fuzu_listing_page(html, "https://www.fuzu.com/job/computers-software-development")

    assert jobs[0].published_date is None
