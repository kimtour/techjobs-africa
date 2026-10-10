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
