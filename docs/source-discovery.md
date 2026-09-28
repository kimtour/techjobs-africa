# M0 Source Discovery

Generated: 2026-09-28T08:57:53.082250+00:00
Environment: local

> This is a technical probe only. Terms of Service review still requires manual confirmation.

## Current M0 decisions

- **LinkedIn:** disabled. LinkedIn's User Agreement prohibits scraping, bots, and copying or distributing Service content without consent. The supplied job-search URL will not be probed or ingested. Its Job Posting API is partner-only and designed to post/manage an employer's jobs, not to retrieve general search results.
- **OpenedCareer:** disabled. Its Terms and Conditions prohibit collecting content in bulk, directly or through third parties, without consent. Written permission is required before reconsidering this source.
- **Elevolt:** not approved for production ingestion. Its Terms grant personal use and require written consent for downloading or modification. Obtain written permission before enabling an automated adapter.
- **Greenhouse:** the configured generic search URL redirected to a MyGreenhouse sign-in page. It remains a discovery aid only; production ingestion must use verified company Job Board API boards.
- **MyJobMag:** approved by the source owner for minimal, attributed link-out aggregation through its advertised detailed XML feed. Do not persist descriptions.
- **Corporate Staffing:** approved by the source owner for fair-use, attributed access through its public WordPress jobs API. Do not persist descriptions.
- **Ashby:** use the official public API confirmed below instead of HTML collection; the GitHub Actions probe also confirmed its board page is reachable.

### GitHub Actions confirmation

The required hosted-runner probe completed successfully on 2026-09-28 in [run 36403117088](https://github.com/kimtour/techjobs-africa/actions/runs/36403117088).

- **MyJobMag, Corporate Staffing, Greenhouse, and Ashby:** HTTP 200, `ACCESSIBLE`, and allowed by their current `robots.txt` paths.
- **LinkedIn, OpenedCareer, and Elevolt:** `SKIPPED` because they are disabled in `config/sources.yaml`; the probe made no request to them.
- The GitHub result matches the local technical baseline for every active source.

### Official API confirmation

The TalentSafari Ashby board is available through Ashby's documented public Job Postings API:

- Endpoint: `https://api.ashbyhq.com/posting-api/job-board/talentsafari`
- Local M0 API check: HTTP 200, JSON, API version 1, 19 listed public postings.
- Confirmed useful fields: stable `id`, `title`, `location`, `workplaceType`, `isRemote`, `employmentType`, `publishedAt`, `applyUrl`, and `jobUrl`.
- Production rule: request and publish listed public postings only; do not store the response descriptions.

### Corporate Staffing public-feed confirmation

- RSS: `https://www.corporatestaffing.co.ke/category/it-jobs-in-kenya/feed/` returned HTTP 200, `application/rss+xml`, and 40 entries.
- Public JSON: `https://www.corporatestaffing.co.ke/wp-json/wp/v2/job?categories=10` is a standard WordPress jobs endpoint. A one-record check returned HTTP 200 and pagination headers (`X-WP-Total: 1986`, `X-WP-TotalPages: 1986`).
- Confirmed useful fields: stable `id`, `date_gmt`, `link`, rendered `title`, `employment_type`, and `hiring_organizations`.
- Status: approved by the source owner for fair-use, attributed access. Use the public WordPress jobs endpoint; do not persist descriptions.

### MyJobMag public-feed confirmation

The `/feeds/` page is HTML, but it explicitly publishes XML feed URLs.

- Summary feed: `https://www.myjobmag.co.ke/jobsxml.xml` returned HTTP 200, `application/xml`, and 100 entries.
- Detailed feed: `https://www.myjobmag.co.ke/jobsxml_by_categories.xml` returned HTTP 200, `application/xml`, and 100 entries.
- Confirmed useful detailed-feed fields: `title`, `company`, `location`, `industry`, `position`, `pubDate`, `expiryDate`, and `link`.
- Status: approved by the source owner for minimal, attributed link-out aggregation. Use the detailed XML feed; do not persist descriptions.

| Source | HTTP | Access | Format | Redirects | Robots allowed? | Bytes |
|---|---:|---|---|---:|---|---:|
| myjobmag | 200 | ACCESSIBLE | html | 0 | True | 125213 |
| corporate_staffing | 200 | ACCESSIBLE | html | 0 | True | 339411 |
| openedcareer | 200 | ACCESSIBLE | html | 0 | True | 267197 |
| elevolt | 200 | ACCESSIBLE | html | 0 | True | 326071 |
| greenhouse | 200 | ACCESSIBLE | html | 2 | True | 7292 |
| ashby | 200 | ACCESSIBLE | html | 0 | True | 20783 |

## Per-source details

### myjobmag

- Requested URL: `https://www.myjobmag.co.ke/jobs-by-field/information-technology`
- Final URL: `https://www.myjobmag.co.ke/jobs-by-field/information-technology`
- Access: `ACCESSIBLE`
- HTTP: `200`
- Content-Type: `text/html; charset=UTF-8`
- Format hypothesis: `html`
- Redirects: `0`
- Retry-After: `None`
- robots.txt: `https://www.myjobmag.co.ke/robots.txt`
- robots HTTP: `200`
- robots allowed for configured agent/path: `True`
- Response bytes: `125213`
- Clues: `{"has_job_schema": false, "has_next_data": false, "has_pagination_words": false, "mentions_rss": false, "mentions_wp_json": false}`
- Error: `None`

Sanitized first 500 chars:

```text
<!doctype html> <html> <head> <meta http-equiv="Content-Type" content="text/html; charset=utf-8" /> <meta http-equiv="Content-Language" Content="en" /> <base href="https://www.myjobmag.co.ke/" /> <title>ICT / Computer Jobs in Kenya 2026 - ICT / Computer Vacancies in Kenya | MyJobMag</title> <meta name="description" content="See all latest ICT / Computer jobs in Kenya today. Check latest and verified vacancies in Kenya. Jobs for ICT / Computer professionals and jobseekers." /> <link rel
```

Manual ToS / permission review: **REVIEWED — public feed found; automation permission is not explicit**

### corporate_staffing

- Requested URL: `https://www.corporatestaffing.co.ke/category/it-jobs-in-kenya/`
- Final URL: `https://www.corporatestaffing.co.ke/category/it-jobs-in-kenya/`
- Access: `ACCESSIBLE`
- HTTP: `200`
- Content-Type: `text/html; charset=UTF-8`
- Format hypothesis: `html`
- Redirects: `0`
- Retry-After: `None`
- robots.txt: `https://www.corporatestaffing.co.ke/robots.txt`
- robots HTTP: `200`
- robots allowed for configured agent/path: `True`
- Response bytes: `339411`
- Clues: `{"has_job_schema": false, "has_next_data": false, "has_pagination_words": true, "mentions_rss": true, "mentions_wp_json": true}`
- Error: `None`

Sanitized first 500 chars:

```text
<!doctype html><html lang="en-US" prefix="og: https://ogp.me/ns#" class="no-js" ><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1, minimum-scale=1"><title>IT Jobs In Kenya 2026 | Latest Vacancies</title><meta name="description" content="Browse the latest IT Jobs In Kenya. Explore today&#039;s job vacancies. Over 50 IT Jobs In Kenya posted this week. Find your next job here."/><meta name="robots" content="follow, index, max-snippet:-1, max-video-previ
```

Manual ToS / permission review: **PENDING**

### openedcareer

- Requested URL: `https://openedcareer.com/job-category/computer-science/`
- Final URL: `https://openedcareer.com/job-category/computer-science/`
- Access: `ACCESSIBLE`
- HTTP: `200`
- Content-Type: `text/html; charset=UTF-8`
- Format hypothesis: `html`
- Redirects: `0`
- Retry-After: `None`
- robots.txt: `https://openedcareer.com/robots.txt`
- robots HTTP: `200`
- robots allowed for configured agent/path: `True`
- Response bytes: `267197`
- Clues: `{"has_job_schema": false, "has_next_data": false, "has_pagination_words": true, "mentions_rss": true, "mentions_wp_json": true}`
- Error: `None`

Sanitized first 500 chars:

```text
<!DOCTYPE html> <html lang="en-US" prefix="og: https://ogp.me/ns#" class="no-js"> <head> <meta charset="UTF-8"> <meta name="viewport" content="width=device-width"> <link rel="profile" href="//gmpg.org/xfn/11"> <!-- Google tag (gtag.js) consent mode dataLayer added by Site Kit --> <script id="google_gtagjs-js-consent-mode-data-layer"> window.dataLayer = window.dataLayer || [];function gtag(){dataLayer.push(arguments);} gtag('consent', 'default', {"ad_personalization":"denied","ad_sto
```

Manual ToS / permission review: **PENDING**

### elevolt

- Requested URL: `https://jobs.elevolt.co.ke/jobs/category/software-it?page=1&location=&type=&qualification=&search=`
- Final URL: `https://jobs.elevolt.co.ke/jobs/category/software-it?page=1&location=&type=&qualification=&search=`
- Access: `ACCESSIBLE`
- HTTP: `200`
- Content-Type: `text/html; charset=utf-8`
- Format hypothesis: `html`
- Redirects: `0`
- Retry-After: `None`
- robots.txt: `https://jobs.elevolt.co.ke/robots.txt`
- robots HTTP: `200`
- robots allowed for configured agent/path: `True`
- Response bytes: `326071`
- Clues: `{"has_job_schema": true, "has_next_data": true, "has_pagination_words": true, "mentions_rss": false, "mentions_wp_json": false}`
- Error: `None`

Sanitized first 500 chars:

```text
<!DOCTYPE html><html class="min-h-full w-full" lang="en-ke"><head><meta charSet="utf-8"/><meta content="IE=edge" http-equiv="X-UA-Compatible"/><meta content="width=device-width,initial-scale=1,minimum-scale=1,maximum-scale=1,user-scalable=no" name="viewport"/><meta content="#034C9D" name="theme-color"/><meta content="h3bj4cl0tszs6nmbyjxgoyjo7s4ng9" name="facebook-domain-verification"/><title>Jobs in Software It | Latest Software It Vacancies | Elevolt</title><meta name="robots" content="index,fo
```

Manual ToS / permission review: **PENDING**

### greenhouse

- Requested URL: `https://my.greenhouse.io/jobs/search?location=Kenya&lat=0.554064&lon=37.903148&location_type=country&country_short_name=KE&work_type[]=remote`
- Final URL: `https://my.greenhouse.io/users/sign_in`
- Access: `ACCESSIBLE`
- HTTP: `200`
- Content-Type: `text/html; charset=utf-8`
- Format hypothesis: `html`
- Redirects: `2`
- Retry-After: `None`
- robots.txt: `https://my.greenhouse.io/robots.txt`
- robots HTTP: `200`
- robots allowed for configured agent/path: `True`
- Response bytes: `7292`
- Clues: `{"has_job_schema": false, "has_next_data": false, "has_pagination_words": true, "mentions_rss": false, "mentions_wp_json": false}`
- Error: `None`

Sanitized first 500 chars:

```text
<!DOCTYPE html> <html lang="en"> <head> <title>MyGreenhouse</title> <meta name="viewport" content="width=device-width,initial-scale=1"> <meta name="description" content="Take control of your job hunt by autofilling applications and getting new roles delivered to your inbox." /> <link rel="icon" type="image/x-icon" href="https://job-seekers.cdn.greenhouse.io/assets/favicon-db928f695ac699a6677db69398dccbdf12615243618f00e5a9d6e94b0c6fdd0f.ico" /> <meta name
```

Manual ToS / permission review: **PENDING**

### ashby

- Requested URL: `https://jobs.ashbyhq.com/talentsafari`
- Final URL: `https://jobs.ashbyhq.com/talentsafari`
- Access: `ACCESSIBLE`
- HTTP: `200`
- Content-Type: `text/html; charset=utf-8`
- Format hypothesis: `html`
- Redirects: `0`
- Retry-After: `None`
- robots.txt: `https://jobs.ashbyhq.com/robots.txt`
- robots HTTP: `200`
- robots allowed for configured agent/path: `True`
- Response bytes: `20783`
- Clues: `{"has_job_schema": true, "has_next_data": false, "has_pagination_words": false, "mentions_rss": false, "mentions_wp_json": false}`
- Error: `None`

Sanitized first 500 chars:

```text
<!DOCTYPE html> <html lang="en"> <head> <meta charset="utf-8"> <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no"> <meta name="theme-color" content="#473BCE"> <meta name="csp-nonce" id="csp-nonce" content="boVnUABfXMfgvsGrowyKrOGID4xTJx_-s9FyxA5JYXE"> <link rel="icon" type="image/svg+xml" href="https://cdn.ashbyprd.com/cdn_assets/7e7e1a70a20f742343268feefb33d210a6dbda67/favicon.svg"> <link rel="icon" type="image/png" href="https://cdn.
```

Manual ToS / permission review: **PENDING**
