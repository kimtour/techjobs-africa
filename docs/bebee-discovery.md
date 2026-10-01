# beBee Kenya discovery

Inspected 2026-10-01 at the user's request as a possible supplemental source
for the fourth (LinkedIn) feed. Production integration authorized later in the same session.

## Evidence

- https://bebee.com/ke/jobs/industry/technology displayed 4,988 offers and
  250 pages. This is a category total, not a verified Kenya technical-role total:
  the first page also included Line Chef, Debt Collector, recruitment, and sales
  listings, plus a London Central location.
- Inspected public detail:
  https://bebee.com/ke/jobs/data-scientist-1-year-fixed-term-contract-britam-nairobi--fj-2391724440
  showed a Nairobi data science role. Apply now redirected to account registration;
  no public LinkedIn application link was exposed in the inspected UI. This sample
  does not establish that all beBee postings lack LinkedIn links.
- https://bebee.com/ke/terms section 9 describes multiple sources and disclaims
  accuracy/currency/completeness. Section 10.2 prohibits "scraping without
  authorization, using automated bots or scripts". Section 11.1 prohibits
  reproduction/exploitation without authorization.
- https://bebee.com/robots.txt allows general public paths but disallows `/api/`,
  authentication paths, and query parameters including `page`, `q`, `sort`,
  `location`, `fuente`, and `postedWithin`. Do not crawl blocked pagination or
  use internal APIs or registration to bypass restrictions.

## Decision

The user subsequently reported obtaining beBee authorization by phone on
2026-10-01 and explicitly requested adding its technical listings under the
renamed fourth feed, "Other/Linkedin". Record this as user-reported owner
permission; no written authorization was supplied. This instruction supersedes
this source's general no-scraping restriction for the requested public category
and bounded category pagination. Internal APIs and authentication remain unused.

Production fetches up to ten public category pages daily (an explicit manual
`source=bebee` refresh bypasses the daily interval), then fetches details
only for titles matching the technical taxonomy with additional source-specific exclusions
for recruitment, sales, and generic quality-assurance roles lacking software/test
automation evidence. These exclusions also apply to previously saved beBee records. Structured JobPosting
metadata supplies stable identifiers, employer, date, validity, and explicit Kenya
country evidence. Expired and nontechnical postings are rejected; descriptions
are never retained. Missing crawl results never close saved jobs. HTTP blocks
stop the fetch; there is no proxy, evasion, or credential access.

Listings are attributed to beBee inside Other/Linkedin and All Jobs. They are
not assigned LinkedIn IDs or claimed to originate from LinkedIn. Existing JSearch
LinkedIn listings retain their source labels and share the fourth feed.

The existing two-result LinkedIn feed is a bounded JSearch sample: two first-page
queries (software engineer and data engineer), last-month window, explicit Kenya
metadata, and validated LinkedIn application URLs. It is not an exhaustive count
of LinkedIn technology vacancies in Kenya. Broader role queries and documented
pagination are separate ways to improve JSearch coverage within the API budget.
