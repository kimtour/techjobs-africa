# Careerjet Kenya replacement

On 2026-10-02 the user reported written permission, independently verified
freshness, and requested removal of beBee in favour of Careerjet.

## Verified access

- Public search: https://www.careerjet.co.ke/jobs?s=software+OR+engineer&l=Kenya
- Direct HTTP requests from the development environment return an unusual-traffic
  verification page. The normal browser initially showed verification, then
  completed automatically and displayed 1,426 results. A subsequent direct HTTP
  request remained blocked. No challenge was manually solved and no browser
  cookies or identity were transferred to the fetcher. HTTP 200 alone does not
  establish a successful listing fetch. Do not parse verification as an empty
  feed or evade the block.
- https://www.careerjet.co.ke/partners/publishers explicitly offers publisher
  XML feeds and an API. XML is preferred for scheduled static ingestion.
- https://www.careerjet.com/partners/api documents the v4 JSON search endpoint,
  publisher API key authentication, date sorting and bounded pagination.
  It requires the actual requesting user's IP and user agent; confirm supported
  background use with Careerjet rather than inventing user information.

## Current activation status

Careerjet is registered but disabled pending a publisher feed URL or confirmed
API access. No production adapter or synthetic listings are included before
that access and response schema are verified. The homepage reserves Careerjet
inside the existing fourth Other/Linkedin feed, also included in All Jobs when
records become available; empty Careerjet status is stated explicitly.

beBee's adapter and manual workflow option are removed. Ingestion retires its
canonical records and current operational state, and the frontend defensively
excludes old beBee exports. Historical logs and discovery remain audit evidence.
Other providers are retained with their stable identities. No source is
relabelled as Careerjet.

## Activation checks

Verify the supplied XML/API schema, stable identifiers, Kenya location evidence,
publication dates, paging and terminal completeness. Ignore descriptions and
apply title-level technical classification. Use the existing two-hour scheduler,
request audit, publication gates and failure retention; no extra scheduler.
Test valid records, nontechnical roles, duplicates, dates, malformed responses,
verification pages and blocked/rate-limited responses. Verify Careerjet cards in
Other/Linkedin and All Jobs locally and on the deployed site before declaring
the feed operational.
