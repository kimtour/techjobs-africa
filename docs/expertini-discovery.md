# Direct Expertini XML discovery — 2 October 2026

The user explicitly requested a direct source independent of JSearch.

## Verified public access (M0)

- `https://ke.expertini.com/robots.txt`: HTTP 200, text/plain, 837 bytes;
  the advertised XML sitemap paths are not disallowed. `/api/` and validation
  routes are disallowed and are never used.
- `https://ke.expertini.com/sitemapindex.xml`: HTTP 200, application/xml,
  235 bytes, one advertised job sitemap.
- `https://ke.expertini.com/job_listing1.xml`: HTTP 200, application/xml,
  297,087 bytes, 1,650 listing links.
- Verified locally and on a GitHub-hosted runner in
  https://github.com/kimtour/techjobs-africa/actions/runs/36999416837 .
  The sanitized `expertini-direct-discovery` artifact contains only URLs,
  modification timestamps and HTTP/robots evidence; no descriptions or secrets.
- Search, job-detail, terms and job-feed documentation pages return a verification
  screen. No proxy, challenge solving, cookie transfer or access-control bypass.
  Public sitemap access does not establish a redistribution licence.

## Metadata limitations and ingestion contract

This is a direct **listing-link discovery feed**, not a full structured vacancy
export. Job URLs expose a job-label prefix, locality, employer-label suffix, and
native numeric ID. Classification considers only the job prefix before the host's
locality delimiter, never employer text. Source-specific conservative checks reject
non-IT industries and generic project/QA/attachment titles lacking technical context.
Company fields stay unknown. The frontend labels Expertini titles as coming from
listing links. Do not infer publication dates from sitemap `lastmod`, last-seen
or fetch times. Dates remain unknown and appear under Latest, not dated periods.

Stable identity is `expertini:<native numeric ID>`; changing the URL title does not
create a new identity. Only HTTPS Kenya Expertini listing links are accepted, with
no credential, query, fragment, port, or foreign host. Fetch only advertised
`https://ke.expertini.com/job_listingN.xml` files (five maximum, plus one index).
Job pages are link-out destinations and are not fetched by ingestion. The redundant
Expertini-specific JSearch query is removed; Google discovery retains its Kenya and
Nairobi queries under the same shared five-request budget.

Discovery means listed in the publisher's sitemap; it does not verify that a
vacancy is still accepting applications. Absence expiry is disabled, and failures
or incomplete windows retain previous jobs. Descriptions are never requested or
persisted. Use the existing scheduler and fourth Other/Google/Linkedin feed, also
include listings in All Jobs, and retain every other source and its controls.

## Careerjet direct API investigation

The provided publisher key is valid at Careerjet's official
`https://search.api.careerjet.net/v4/query`. Basic authentication and the actual
publisher site's Referer are required. A structured 403 explicitly identified the
missing Referer; adding `https://techjobs-africa.pages.dev/` returned HTTP 200 JOBS.
The user-supplied declared IP is used for the authorized publisher request and a
truthful TechJobsAfrica publisher client identifier is used as its user agent.
Credentials are stored only in GitHub Secrets (`CAREERJET_API_KEY`,
`CAREERJET_USER_IP`), never source, data or logs.

Observed behaviour: `software OR engineer` returned 1,426 hits, 72 pages and 20
records; `software engineer` returned 208 hits, 11 pages and 20 records. The
requested page_size=100 was not honoured. Page two works. Repeating page one gives
identical titles but different opaque jobviewtrack application tokens, with no
native ID or original source URL in the documented response. Hashing those links
would create new IDs on every refresh; company/title/location cannot serve as IDs.
No production Careerjet adapter is enabled until stable native IDs or a publisher
XML export are available. Jobviewtrack returned 418 to the single redirect probe;
no deliberate block is bypassed. Official publisher XML access requires sign-in;
the inspected account page is logged out. Expertini's direct XML route avoids both
JSearch quota and these Careerjet identity limitations.


## RSS enrichment — verified following the user-supplied endpoint

`https://ke.expertini.com/jobs/feed.xml` returns HTTP 200 and valid RSS with 313
items (198,651 bytes in the inspected response). Verification also passed on the
GitHub runner: https://github.com/kimtour/techjobs-africa/actions/runs/37007784499 .
Only title/link/GUID/pubDate were saved in sanitized probe evidence; descriptions
are processed in memory and never persisted. Eight RSS titles currently pass the
technical taxonomy; total RSS count must not be represented as technical-job count.

Production combines RSS and advertised job sitemaps in up to seven requests. RSS
has genuine titles and source publication timestamps, which take precedence over
URL labels when numeric IDs coincide. GUID/link suffixes also expose stable
composite and 32- or 35-character hex IDs. Publication dates are RSS syndication dates,
not independently verified employer posting dates. No employer fields are supplied.
Only sitemap-only titles retain the listing-link label and unknown dates. Coverage
is still partial; disappearance never closes jobs. The sampled RSS-linked detail
page remained behind verification in this environment, so no job-page enrichment
or blocker bypass is enabled. Other-source attribution now survives a same-ID
refresh while current metadata updates; records are not fuzzy-merged.
