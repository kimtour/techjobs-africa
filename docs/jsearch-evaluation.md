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

Live evaluation is pending until the API key is configured. Mocked regression tests
verify parsing and safeguards, but do not establish live coverage or publication rights.
