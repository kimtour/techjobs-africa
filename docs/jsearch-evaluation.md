# JSearch Kenya evaluation

This manual discovery evaluates two queries (software engineering and data engineering)
against accepted production listings. It does not add a production source, change the
saved jobs, expire listings, or deploy the website. The 1,054-role production baseline
is read from the latest accepted `data` export, not the small local example dataset.

## Set up access

1. Open https://app.openwebninja.com/api/jsearch and create your account.
2. Select the free JSearch plan and obtain an OpenWeb Ninja API key. The current
   advertised free plan provides 200 request credits per month.
3. Open https://github.com/kimtour/techjobs-africa/settings/secrets/actions and add
   a repository secret named `JSEARCH_API_KEY`. Paste the key only into the secret
   field, never into chat, source code, a committed file, or logs.
4. Run the **Evaluate JSearch Kenya** workflow from GitHub Actions. The result is
   a job summary and a seven-day `jsearch-kenya-evaluation` artifact.

This integration uses OpenWeb Ninja credentials; a RapidAPI key is not interchangeable.

## Evaluation scope

`config/jsearch-evaluation.yaml` selects Kenya (`country=ke`), English, and the past week.
The runner requests one page per query and never follows cursors, retries errors, or
requests individual job details. Two configured queries attempt at most two requests;
each first page is documented to contain up to ten jobs. This is a sample rather than
an exhaustive technology job search. Additional manual runs consume further quota.

Provider reference: https://www.openwebninja.com/api/jsearch/llms.txt
Verified on 1 October 2026: `/search-v2` returns `data.jobs` and a pagination cursor.
API authentication uses the `x-api-key` header, not a URL parameter.

The evaluation requires explicit Kenya country evidence in each returned record,
applies the existing title-level technical classifier, and retains stable upstream IDs.
It reports LinkedIn application links, exact URL overlaps with existing jobs, and
company/title/city similarities for human review. Similarity never automatically merges
jobs. A job is attributed to JSearch; a LinkedIn application link does not make JSearch
an official LinkedIn API. The evaluator prefers an application option marked direct
by the provider, but that flag alone is not proof that the destination is the employer.

Descriptions are excluded from the requested fields and are never saved even if the
provider includes them anyway. Only allowlisted job fields and aggregate results are
written. API keys, HTTP response bodies, and exception text are never logged or saved.
An HTTP error, malformed payload, or transport failure stops further requests.

## Decide whether to add a source

Review location accuracy, dated and undated listings, active application links,
technical relevance, incremental coverage, and both exact and possible duplicates.
Check provider storage and public-display permission for the intended job fields.
Record the discovery evidence before implementing or enabling a production adapter.
Direct LinkedIn scraping remains disabled. Production scheduling continues through
the existing Cloudflare scheduler; this evaluation adds no recurring schedule.

## First live evaluation — 1 October 2026

Run: https://github.com/kimtour/techjobs-africa/actions/runs/36903327217

Both configured searches succeeded (HTTP 200), using two requests. The software
query returned ten records and indicated another page; the data query returned
three records with no further cursor. Existing filtering and exact deduplication
retained nine technical listings with explicit Kenya country evidence. The accepted
production baseline contained 1,054 active, unrestricted roles.

- One listing had a LinkedIn application link: Software Engineer — Open Source
  Contributions — Remote, YO AI Labs, Mombasa (LinkedIn job ID 4471084334).
- One listing matched an existing application URL exactly: RVIBS Computer Science —
  Software Development on MyJobMag.
- The strict company/title/city review signature reported zero possible duplicates.
  Manual comparison nevertheless identified likely overlaps for Mastercard,
  Food for Education/Food4Education, Watu, and the alternate RVIBS listing. These
  are review candidates, not confirmed duplicate merges. Mastercard and Mastercard
  Foundation must not be treated as the same employer merely from similar names.
- The YO AI Labs title/company/location also appeared through another aggregator
  under a different URL and upstream ID, illustrating within-sample duplication.
- A result attributed to On used an aggregator URL containing both London and
  Nakuru. Country metadata alone therefore does not establish original location
  accuracy. Application validity, location, and employer identity need manual checks.

The nine listings are not nine proven new vacancies. The sample supports using
JSearch as a supplemental discovery source, but does not establish broad LinkedIn
coverage, complete technical coverage, stable IDs across repeated fetches, or
public-display permission. No production data or website was changed. Production
integration remains pending discovery review and provider usage-rights verification.

## LinkedIn feed — requested 1 October 2026

After reviewing the live evaluation and the usage-rights limitations, the user
explicitly requested publishing a LinkedIn feed through JSearch. The production
source retains only records with explicit Kenya evidence and actual LinkedIn
job application links. Stable identity is `linkedin:<LinkedIn job ID>` extracted
from the URL; Google/JSearch search identifiers are not used for this feed.
Titles, employers, locations, and dates remain provider metadata and are not
independently checked by scraping LinkedIn. This is not an official LinkedIn API
integration or evidence of a provider redistribution license.

Two first-page searches (software and data engineering, past month, via LinkedIn)
run at most once per 24 hours through the existing scheduler. A 160-request monthly
ceiling is enforced from durable request history before contacting the API. This
ceiling covers this production source, not separate manual evaluations or other
uses of the same account. No retries, description persistence, or absence expiry.
Provider failures retain already-published jobs. This is a limited sample feed,
not an exhaustive list of all Kenyan technology vacancies on LinkedIn.

The source is fourth including All Jobs. Source headers identify JSearch as the
provider, and the same canonical jobs appear in All Jobs without inflating totals.
The existing ingest workflow receives `JSEARCH_API_KEY` from GitHub Secrets and
has a manual `source=linkedin` option for the initial publication.


## Google Jobs feed — requested 2 October 2026

The user authorised broadening the production feed beyond LinkedIn and specified
`software engineer jobs in Kenya`, country `ke`, language `en`, the past week,
all publishers except beBee, pagination within quota, and fourth-feed placement.
Prior live discovery established non-LinkedIn results and exact application-URL
overlaps. Official `/search-v2` documentation confirms `job_publisher`,
`apply_options`, field projection, `data.cursor` and one credit per returned page.

Production source `jsearch` supersedes LinkedIn-only polling; previously accepted
LinkedIn jobs remain. Up to five cursor pages are requested once per Kenya
calendar day, normally at the 07:00 scheduler slot. Fewer requests are made when
pagination ends early. Production JSearch and historical LinkedIn requests share
a 160-credit monthly ceiling; manual evaluations/other account users are outside
this history. Same-day and budget skips are explicit in the run audit. The bounded
five-page window is not an exhaustive Google Jobs crawl; absence expiry is off.

Records require explicit Kenya country evidence and the existing title-level
technical classifier. Both the API exclusion and local application-link checks
remove beBee. If another safe application option exists it can be retained with
its actual publisher; no record is relabelled as beBee or Careerjet. Safe direct
application options take preference. Publisher labels are provider metadata,
not independent publisher verification. Missing publisher labels use the chosen
application hostname. Descriptions, secrets and response bodies are never saved.

Identifiers use the upstream job ID; a chosen LinkedIn application URL uses its
native LinkedIn ID. Exact IDs and canonical application URLs deduplicate the
new discoveries; matches to an accepted source preserve that source's identity
and add JSearch attribution. Company/title/location resemblance never auto-merges.
Failures retain accepted listings. No direct Google/LinkedIn scraping, proxy,
verification bypass, runtime backend or additional scheduler is introduced.

The homepage's fourth feed is labelled Google Jobs via JSearch. Original publisher
labels appear on its cards and in All Jobs; the two-column layout, other sources,
independent periods, pagination, mobile order and unique counts are retained.

### First Google Jobs publication

Successful run: https://github.com/kimtour/techjobs-africa/actions/runs/36988085641
Started 2026-10-02 at 12:09 EAT. Cursor exhaustion ended the crawl after two
requests. Nine valid Kenya records yielded seven classified technical listings.
Five exact application-URL overlaps gained JSearch attribution; two new jobs
raised the accepted total from 1,078 to 1,080. No previous job identity was lost.
Publishers: WhatJobs, Fuzu, MyJobMag, Corporate Staffing Services, and LinkedIn.
The fourth combined feed contains eight jobs including the retained LinkedIn
listing outside this import. All eight appear in All Jobs. beBee links are absent.

Validation: 122 Python tests, lint, six frontend behavior tests, Astro validation
and build passed. Local and production browser checks confirmed publisher labels,
feed membership, independent period/pagination controls, fixed feed heights,
fourth-feed placement, two desktop columns and mobile order without overflow.


### Coverage correction — 2 October 2026

The user's Google comparison uses "software engineer jobs near Nairobi" without
posting-date restrictions. The first import used a Kenya-wide past-week query;
it exhausted its cursor after two requests, so merely increasing pagination would
not address that mismatch. Thirteen pasted examples link through retired beBee;
those remain excluded. Some pasted jobs (GiveDirectly, Solvo and UNEP) were already
attributed to this feed. Provider indexing can still differ from browser results.

Production now queries Kenya, Nairobi, and "technology engineer jobs in Kenya via
expertini" without a posting-date restriction. A round-robin queue gives all three
queries one request before continuation pages, sharing five requests total per
refresh and the existing 160-request monthly ceiling. Scheduled refreshes remain
once per Kenya calendar day; an explicit manual refresh can bypass the daily skip,
but never the monthly ceiling. Titles now recognize mobile iOS/app development,
.NET, software internships/trainers, plural developers, hyphenated full-stack,
ML development, platform leadership, cloud infrastructure and network hardware.
Civil, mechanical and electrical engineering remain outside the technical taxonomy.

The fourth feed is Other/Google/Linkedin. Expertini is included as an indexed
publisher discovery query, not a direct scraper. Its public engineer search on
2026-10-02 returned Cloudflare's "Just a moment" verification screen locally;
robots.txt permits the requested search path but disallows /api/. No block bypass
or direct production adapter is enabled. A source-provided accessible feed or API
is required to finish direct-source discovery. Indexed listings retain the actual
publisher and original application URL and also appear in All Jobs.


Verification: commit ee3085f was successfully imported and published in
https://github.com/kimtour/techjobs-africa/actions/runs/36995778328 . The API used
five requests, returned 26 validated Kenya records, and accepted 19 technical
records. The combined fourth feed grew from 8 to 21 listings. Production has
1,098 active listings; every ID from the prior 1,080-job Google publication is
retained (other scheduled source updates also occurred between publications).
Examples now visible include Yassir Senior Mobile IOS Engineer, Scrums Mobile App
Developer, Azenia .NET Software Developer, and Adanian Software Engineering Trainer.
No Expertini-published job was returned by this first indexed discovery attempt;
Expertini direct ingestion remains blocked pending an accessible approved feed.

126 Python tests, lint, six frontend tests, Astro check and production build passed.
Production data was browser-checked locally and live: the fourth feed's load-more
expands 10 to 20 without changing other feeds; Day shows one dated listing and
Latest restores ten. At 390px the fourth feed retains its position with no horizontal
overflow. Screenshot evidence: /tmp/google-coverage-live.png. The tracked example
JSON was restored after local verification; production data remains on data branch.
