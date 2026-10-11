# LinkedIn product/project management coverage — 10 October 2026

The user clarified that the screenshot illustrates missing kinds of jobs,
particularly Product Manager and Project Manager vacancies posted on LinkedIn.
M-KOPA backend jobs already appear in the accepted feed; an additional employer
source is outside this correction.

Both Product Manager and Project Manager already classify as Technical Product.
The actual coverage gap is discovery: production only queried software engineering
in Kenya and Nairobi. Those queries are not an exhaustive LinkedIn tech-job feed.

Production now shares its existing five-request window across four queries:

- software engineer jobs in Kenya
- software engineer jobs near Nairobi
- product manager jobs in Kenya
- project manager jobs in Kenya

Each query receives its first page before continuations. Configuration now drives
the executed queries, preventing the YAML and adapter from silently diverging.
The once-per-Kenya-calendar-day policy, 160-request monthly ceiling, explicit Kenya
country evidence, stable identifiers, deduplication and beBee exclusion remain.
JSearch discovers indexed vacancies; it cannot guarantee every LinkedIn posting
or the same results/ranking as LinkedIn's own search. No direct LinkedIn scraping
or access-control bypass is introduced. Original application links and publisher
labels are preserved; descriptions are never persisted.

Two precise screenshot title variants were also confirmed to fail classification:
GCP Cloud Platform Administrator and Manager,Technology. Add the cloud-platform
administration phrase and reversed management phrase, normalizing title and
keyword punctuation consistently. Technical Project Manager and generic Project
Manager remain included. Sales and non-technical engineering exclusions remain.

Manager records use the existing Other/Google/Linkedin and All Jobs feeds; no new
employer source or panel is enabled. Source order, periods, pagination, scrolling
and unique counts remain unchanged.

The first refresh (run 38035913226) passed all 169 Python tests but the provider
returned a read timeout on the third request, the new product-management query.
The existing feed was retained. Increase this source's request timeout from 25 to
60 seconds for uncached searches without adding retries or extra budget.

Audit also showed two earlier refreshes rejected as `suspicious_count_drop`:
accepted JSearch jobs accumulate, while each fresh five-page ranked sample can
be much smaller. Do not compare a bounded sample to the accumulated inventory or
use sample count variation as evidence of missing jobs. Positive validated JSearch
samples may add/refresh records; empty results, malformed responses and request
failures retain the previous feed. Absence expiry remains disabled. Other sources'
count-drop gates are unchanged.

The refresh in run 38036233518 successfully published three new IDs, retaining
all 1,329 prior IDs. LinkedIn-qualified management searches returned only one
accepted project-management listing, attributed to Jobweb Kenya, and no Product
Manager listing. Management queries now search across indexed publishers without
the restrictive `via linkedin` qualifier, preserving actual LinkedIn links and
publisher attribution whenever returned. This remains indexed discovery, not an
exhaustive LinkedIn inventory.

## Delivery verification

Published implementation: commit `f106b1e`, successful production refresh
https://github.com/kimtour/techjobs-africa/actions/runs/38036492059 . Published
code passed 171 Python tests, lint/format checks, six frontend behavior tests,
Astro validation and the production build.

Local browser verification used the accepted 1,361-job export: Product Manager
search showed eight matching entries in the combined feed and 67 in All Jobs.
On 11 October, the live site had 1,371 roles after the next scheduled updates;
Product Manager search showed 11 combined-feed entries and 70 in All Jobs.
Live Project Manager load-more expanded the combined feed from 10 to 20 rows,
leaving every other feed's visible count, header position and 416px body height
unchanged. Publisher labels and original links were verified in both feeds.

The optional construction-function exclusion was not published. Automatic
approval review rejected that additional removal as outside the user's request.
It is preserved only on local branch `codex/optional-construction-exclusion`;
production and main retain the existing inclusion rules. No M-KOPA employer
source or additional source panel was enabled by this work.

## Sub-Saharan Africa coverage and source failure repair — 2026-10-11

The screenshot includes South Africa remote, Sub-Saharan Africa remote and worldwide
remote technology jobs. The previous JSearch adapter discarded every non-Kenya
result and omitted the provider's `job_location` field. Five daily requests now
cover Kenya software engineering, product management and project management,
plus Sub-Saharan Africa and South Africa remote tech discovery across publishers,
including LinkedIn when supplied by the provider.
The regional queries use the documented South Africa (`za`) search locale;
Sub-Saharan Africa is not a country code. Query wording never establishes eligibility.
Remote queries also use the provider's documented `work_from_home=true` filter.
Other-country results require explicit remote plus African/worldwide location
evidence. Countries retain their names/codes, and regional locations have a separate
`region` field; generic remote and EMEA alone remain insufficient. This is a bounded
provider sample, not a complete export of LinkedIn's signed-in search results.

All seven reported MyJobMag/Corporate Staffing listings were publicly reachable
and already present in the approved IT discovery surfaces. Their own title variants
were unrecognized. Add Machine Learning Expert, Geospatial Systems, Systems
Integration Coordinator, AI Developer and AI-native Product Engineer variants.
Early Warning Expert is ambiguous: include only when its own in-memory detail body
contains geospatial, programming and application-development evidence. MyJobMag
reads only its job-details container, excluding recommendations; Corporate Staffing
uses the existing job payload. Persist only the category decision, never the body.

The 14:00 UTC audit (`38145429534`) shows all other attempted sources succeeding;
Expertini has 29 consecutive HTTP 403 failures, reproduced locally on the public RSS.
Pause those requests pending restored authorized feed access, retain accepted jobs
and historical blocked health, and report the policy skip in each audit. Do not
change scheduler failure detection, bypass the block, expire those jobs or suppress
new failures from other sources. Scheduler alert workflows deliberately fail to
notify of a failed ingestion; the Worker itself was operating correctly.

Remote discovery remains across publishers: LinkedIn-only regional queries returned
no eligible remote records in the verified sample. Keep original LinkedIn links and
labels whenever returned, and do not imply the provider reproduces LinkedIn search.
The provider rejected `job_location` in a field projection with HTTP 400; use its
normal response in memory, retaining only minimal fields. Added aggregate window
counts distinguish empty provider coverage from geographic filtering without logging
queries, response bodies, descriptions or credentials.
