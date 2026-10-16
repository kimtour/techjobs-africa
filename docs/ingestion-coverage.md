# Ingestion coverage and filtered jobs

On 16 October 2026, the MyJobMag category page contained clear technical jobs
that the title taxonomy rejected, including Software Architect, Systems Support
Analyst, ICT Security Manager, and Head of Artificial Intelligence. Scheduled
fetches were succeeding; filtering caused the omissions. Multi-location cards
also appended location text to their date, causing the publication date to be lost.

The taxonomy now covers the audited IT, networking, security, architecture,
enterprise software, data, and technical leadership variants. Employer names
are excluded from classification evidence. A shared vacancy advert can qualify
through an explicit technical vacancy, but its title and application URL must
agree; the original listing and stable source identity are retained.

Ambiguous service delivery, product analysis, payments platform, digital health,
software delivery, and enterprise support titles require technical evidence in
their own job-details container. Recommendations, scripts, and unrelated page
content do not qualify. Descriptions remain in memory only. Detail requests use
the existing source request budget, delay, retry, and block policy.

Each completed classification writes the current filtered IDs, titles, and
reasons to `data:state/classification/<source>.json`, also included in the fetch
audit artifact. Run history retains filter counts and reason totals rather than
repeating the full title list. `unclassified_title_or_unverified_context` means
a title needs review or did not supply enough scoped detail evidence;
`non_technical_function` identifies an excluded job function. A category page
alone still does not make an HR, finance, clerical, or programme administration
vacancy technical.

Use the ingestion workflow's `myjobmag` source option for a targeted refresh.
Keep scheduled polling unless the source provides an official webhook or event
API. A webhook can trigger ingestion sooner, but it cannot repair classification
or pagination gaps. The existing Cloudflare scheduler already dispatches the
GitHub workflow; another trigger is unnecessary for this defect.

## All-board coverage

The follow-up audit runs the shared taxonomy across Corporate Staffing,
BrighterMonday, Fuzu, OpenedCareer, Elevolt, TalentSafari, the verified employer
boards, and Google Jobs. Domain/function patterns cover IT/ICT roles, software
stacks, architecture, networking, data, technical education and enterprise
applications. Broad IT patterns are fallbacks so specific support, security,
product and software categories retain priority. Explicit employer suffixes in
both titles and URL slugs do not supply job-function evidence.

Corporate Staffing, OpenedCareer, Elevolt, Ashby (including employer boards),
Google Jobs and Breezy inspect only the current record's own description in
memory. BrighterMonday and Fuzu can enrich scoped ambiguous titles from a
matching JobPosting record on the discovered same-source detail URL. They never
use unrelated page text or recommendations; unknown or unavailable evidence
remains visible in the classification audit. Shared adverts are accepted only
when the source title and URL agree, regardless of publisher.
Fuzu can also use its public `context.job_details` record when the title and path
match; expired records and `similar_jobs` never supply evidence.

Use the workflow's `all` option when deploying a shared coverage change. A
source-specific refresh leaves other boards' backlogs untouched. Google's daily
and monthly quotas still apply; a manual refresh must remain within the saved
monthly request ceiling. Expertini remains paused until authorized feed access
is restored; Careerjet and unconfigured Greenhouse boards cannot supply jobs
without verified access/board configuration.
