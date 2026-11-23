# Himalayas discovery and collection contract — 23 November 2026

M0 completed before adapter implementation. Local checks returned HTTP 200 JSON
from the documented search API and HTTP 200 robots.txt allowing the API path.
The Kenya/software-engineer sample returned 20 records of 321 matches, with
stable guid URLs, original applicationLink values, country/timezone arrays,
update and expiry timestamps. No descriptions were saved.

Official references:
- https://himalayas.app/docs/remote-jobs-api
- https://himalayas.app/docs/data-dictionary
- https://himalayas.app/terms (API-specific clause 113)

The API permits display on our own board with visible Himalayas credit and its
supplied applicationLink, including its query parameters. Do not syndicate its
records to other boards, search engines or JobPosting structured data.

Collection is a bounded newest-results discovery window for Kenya across eight
technical searches, two 20-record pages each. Completion means this configured
window completed; it never establishes complete coverage of Himalayas. Search
pagination uses page/offset/totalCount, not the browse API's cursor. Empty country
arrays mean worldwide; nonempty arrays must include Kenya. Empty timezone arrays
mean unrestricted; nonempty arrays must include UTC+3. Unknown or malformed
restrictions are never inferred eligible. EMEA is not Kenya eligibility.

Each run also checks up to 20 previously accepted jobs, oldest checked first,
using their documented single-job API. HTTP 410 closes only the named occurrence;
HTTP 404 retains it, and 403/429/5xx never cause closure. Known expiry timestamps
also remove expired Himalayas listings. Absence expiry is disabled because
bounded discovery is not a full inventory. Descriptions are used only in memory
for scoped technical evidence. pubDate is labelled Updated, not Posted.

Collection uses the existing three daily scheduler slots and shared private
state/publication workflow, with a bounded request budget, throttling and 429
cooldowns. No new service, paid API or independent scheduler is introduced.
