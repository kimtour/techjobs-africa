# Employer collection activation review — 25 October 2026

The implementation owner authorized completion and deployment while retaining
verification gates. Review is based on source evidence, not on the workbook's
platform guesses or a successful workflow alone.

## Reviewed pilot sources

M-KOPA (`employer_58b8d22cf280a524`), Jumia
(`employer_6123edf0db94e3a1`), Turaco (`employer_3d2a408f9d01331a`),
Ampersand (`employer_1a047fd979fcdf88`) and Tala
(`employer_9e1960f0be135be5`) have recorded official employer linkage,
collection review, stable identities/application links, locations, date handling,
complete pagination and local/hosted accessibility. Existing evidence is in
`docs/employer-discovery/`; corrected hosted trial run 40196857729 completed all
five crawls successfully. A fresh local isolated trial of the current parser also
completed all five crawls, with two additional eligible M-KOPA backend vacancies.

The two candidates name Johannesburg, South Africa. They are African-eligible;
they do not imply Kenya eligibility. Employer application links and immutable
Ashby IDs are present. Existing source posting dates remain source dates.
Talent pools, nontechnical electrical/logistics network roles and ineligible
locations remain excluded. No descriptions are retained.

The five sources may publish reviewed current jobs on initial activation rather
than waiting for a newly created ID. `reviewed_bootstrap: true` records that
explicit review. Other newly enabled sources default to a silent initial baseline
unless their current candidates receive their own documented review. Initial
inventory is never described as newly posted, and source absence expiry remains
off. Failed or partial crawls retain previously accepted vacancies.

## Expansion and access limits

Seven additional board clues are being investigated separately: Wasoko,
GiveDirectly, Andela, pawaPay, Sama, Unlimit and LemFi. Their local evidence alone
does not grant production activation; hosted evidence and candidate review are
required. An empty Wasoko board cannot establish its current location fields.

Previously blocked Moniepoint and Busara API sources are explicitly blocked in
the registry; no automatic retries are enabled. SmartRecruiters' API robots policy
returned disallow. One discovery test request returned a posting list after that
policy result; the test was stopped, and no production SmartRecruiters API
collector is enabled. Permitted public-page methods require separate review.

This review does not claim all 758 employers have working vacancy collection.
The daily coverage report records every employer, including unsupported,
verification-pending, manual and blocked sources, separately from successful
complete vacancy checks. Page monitoring is not a substitute for those checks.

## Additional terms review

GiveDirectly, Andela, pawaPay and Unlimit remain manual: their website terms
restrict automated extraction and/or republication. Their successful ATS tests
are not collection permission. LemFi remains manual because its linked terms
returned 403 and a collection basis could not be established. Sources:

- https://www.givedirectly.org/terms-of-use
- https://www.andela.com/terms-of-use
- https://www.pawapay.io/terms-of-use
- https://www.in.unlimit.com/website-terms-of-use/
- https://www.lemfi.com/en-us/legal/terms

Sama remains pending collection review and hosted evidence. Wasoko's empty board
remains pending field verification. Kijabe's structured listing contains three
nontechnical roles but lacks per-role stable identifiers/application destinations;
no homepage is published as a job. No source-owner messages were sent.

## JazzHR expansion

Branch International, Watu and CrossBoundary completed local and hosted M0
(discovery run 40206356702) and isolated hosted trial 40206809932. Their complete
inventories contain 11, 38 and 18 records respectively. The trial yields five
additional eligible Watu roles explicitly located in Nairobi, Kenya: Data Engineer,
Tech Lead - Android Experience Engineering, QA Chapter Lead, Senior QA Automation
Engineer and QA Automation Engineer. Four omit source posting dates; preserve
that absence and display labelled First found after actual discovery. Branch's
three technical roles and CrossBoundary's technical role are overseas and excluded.

The official Branch page embeds its JazzHR widget; CrossBoundary embeds direct
posting URLs in page data. Identity matching verifies the actual board, rather
than accepting an arbitrary provider-host link. JazzHR's immutable posting token
survives changed title slugs. Watu uses both JobPosting JSON-LD and visible header
metadata; the latter supplies missing location fields and does not fabricate dates.

Collection review is limited to factual title/employer/location/date/link metadata
from public ATS pages with permitted robots paths. No descriptions, logos or
applicant information are republished. Watu's website terms explicitly distinguish
external sites; reviewed Branch terms concern banking/app services. CrossBoundary's
linked policy concerns website privacy. This review does not claim an explicit
redistribution licence. Known explicit automation restrictions are retained:
Living Goods and Umba require permission and remain manual. A subsequent broad
metadata assessment inadvertently included Umba before its manual flag was saved;
that flag is now saved and no production collector is enabled for it.
