# Screenshot employer feeds — 11 October 2026

M0 passed locally and on the GitHub runner in
https://github.com/kimtour/techjobs-africa/actions/runs/38151132401.
The `screenshot-employer-discovery` artifact contains only HTTP/robots evidence,
stable IDs, titles, locations, publication metadata and application URLs.
Descriptions and employer account/contact fields are never saved.

## Verified recurring discovery

- Camunda: `https://api.ashbyhq.com/posting-api/job-board/camunda`, HTTP 200 JSON,
  43 public postings, no pagination or JavaScript dependency. Its screenshot Data
  Layer role has native ID `b51b79c6-e2d8-428d-8cdc-0d1aae9792a9`, Remote primary
  location and EMEA/Canada secondary locations. Keep EMEA as VERIFY; the screenshot's
  Johannesburg label does not establish eligibility for every African country.
- Blacksmith Agency: `https://api.ashbyhq.com/posting-api/job-board/Blacksmith%20Agency`,
  HTTP 200 JSON, 12 public postings. The public AI Engineer posting has native ID
  `5dfccfc8-a527-44b9-b3ec-eaee25fc3f0f`, explicit Remote and South Africa among
  secondary locations. This is related coverage, not a verified identity match to
  LinkedIn's Applied AI Engineer (Remote, Randburg).
- Social Discovery Group: `https://social-discovery-ventures.breezy.hr/`, HTTP 200
  HTML, 40 unique public job URLs (130 repeated card headings), 10 currently
  recognized technical titles. All positions render without JavaScript. Robots
  allows the public board and /p/ pages; asset paths are disallowed and not fetched.
  The screenshot Product Engineer (AI-Native) has native ID `e5a41beaf52b01`.
  Its own public JobPosting JSON-LD explicitly states worldwide applicant eligibility,
  TELECOMMUTE and datePosted 2026-10-06. Detail JSON-LD is inspected only in memory.

Ashby's documented public posting API is described at
https://developers.ashbyhq.com/docs/public-job-posting-api. The API host's robots
endpoint returns 401; the explicitly documented posting endpoints return 200 without
authentication. No private API, authenticated page or access-control bypass is used.
Public metadata access does not establish a redistribution licence. Retain only
attributed minimal metadata and links to the original applications. Absence expiry
is disabled for these new feeds. Source failures retain accepted listings.

## Unavailable coverage

Expertini's approved RSS and sitemap still return HTTP 403 on 11 October. Robots
returns 200, which does not grant access through the feed block. Keep the pause
and existing listings until the publisher restores authorized access.

Cue's official About page links its jobs to LinkedIn; no public employer feed was
found. The indexed Senior Software Engineer link is
https://za.linkedin.com/jobs/view/senior-software-engineer-at-cue-4465611728.
No direct LinkedIn scraper is introduced. Indexed search cannot guarantee capture.

remoting.work has an unauthenticated candidate search, but sampled AI Developer
records have no structured geographic eligibility. The older indexed posting
4425056381 is closed; indexed posting 4436251518 is a different occurrence.
Its current native IDs cannot be equated to the screenshot's LinkedIn ID by title.
Do not fabricate a LinkedIn/native-ID match or infer African eligibility from the
search query. Do not enable a new importer without verified eligibility and identity.

## Delivery contract

These employer feeds belong in All Jobs and the existing Other/Google/Linkedin
feed, retaining employer attribution and original URLs. Do not add panels or move
neighbours. Google discovery remains within its five-request daily/160 monthly
budget. Complete LinkedIn coverage still requires an authorized comprehensive feed.

## Regional management search correction

Three daily Kenya queries remain fixed (software, product management, project
management). Two remote requests rotate over an eight-query pool every four Kenya
calendar days: product/project management in South Africa, software engineering
in South Africa, DevOps/data engineering in Sub-Saharan Africa, AI engineering in
South Africa, and product/project management in Sub-Saharan Africa. The first
rotation on 11 October selects the two South Africa management queries. The
five-request daily window and shared 160-request monthly ceiling are unchanged.

Provider remote booleans can be false on remote listings. In addition to explicit
title/location metadata, accept a narrow statement in the job's own in-memory
description (`Location: Remote` or `This role is fully remote`); reject negated
remote statements. Returned African/worldwide geographic evidence is still required.
Company-wide remote boilerplate and query wording are insufficient. Only the remote
decision and aggregate evidence count survive; descriptions never enter output.
