# Missing-employer careers-source review — 25 October 2026

This review covers the original **99 employer records without linked recruitment sources**. It is discovery and vacancy metadata evidence, not production activation. The original dirty checkout was preserved. No shared registry, adapter, deployment or private-state writer was changed.

## Exact coverage

- All 99 original employer records have an initial outcome and review row.
- 31 employers now have careers-source candidates: 24 original observed links plus seven recovered from link labels or official indexed recruitment pages.
- 68 employers still have no usable observed recruitment source. They are unresolved, not healthy zero-vacancy collectors.
- Zero new collectors have passed every production verification gate in this review. Homepage availability is never counted as vacancy collection.
- Initial homepage outcomes were 24 discovered, 50 no-careers-link, 19 failed and six access-limited. The label-aware follow-up examined all 50 no-link employers and found two real additional career pages.

The proposal is `discovery-output/overnight-missing/registry-proposal.json` and `/tmp/techkazi-overnight-missing-patch.json`. Each employer retains its own identity, including the two REREC employer records sharing one fetch URL. No employer merge is proposed.

## Recovered sources and next action

| Employer | Observed source | Evidence/result | Next action |
|---|---|---|---|
| Kwara | https://kwara.com/about#careers → https://kwara.zohorecruit.com/jobs/Careers | Official About page links both Join the team and See Open Roles to the Zoho board; board reachable but dynamic, no server-rendered vacancy inventory | Review public Zoho collection interface and complete pagination; no guessed private API |
| Decathlon Kenya | https://www.decathlon.co.ke/content/128-careers | Marketing Manager and official Google Form Apply Today link; no JobPosting data | Nontechnical role: exclude from technical feed; review page changes as discovery |
| CUEA | https://recruitment.cuea.edu/ | Official subdomain, reachable recruitment table with header only; homepage cross-link not verified | Review collection terms and table implementation before treating as a verified empty board |
| DeKUT | https://recruitment.dkut.ac.ke/vacancies/admin | Recruitment homepage links Vacancies to this list; list reachable | Confirm explicit empty state, public detail IDs and complete pagination; main-site notices can differ |
| KEMSA | https://swifthr.kemsa.go.ke/resume/PublicJobList.aspx | Official subdomain public vacancy list reachable; search cache says No Job Vacancies | Validate live empty marker and official careers cross-link before empty-collector acceptance |
| KEBS | https://careers.kebs.org | Official recruitment PDF references this URL; local connection timed out | Backoff and access review, no claim of collection |
| Kenya Law | https://kenyalaw.org/kl/index.php?id=10133 | Official legacy vacancy page indexed; local read timed out | Establish current-maintained source, no claim of collection |

Official provenance for KEBS: https://www.kebs.org/wp-content/uploads/2023/12/External-Advert-Senior-Positions.pdf. This archived PDF establishes a source lead, not current jobs. Official source searches did not turn Africa Data Centres' third-party staging `adc.chisenga.com` into a trusted employer source.

## Actual vacancy inventories

Pezesha's official index listed **10 individual vacancy links**, all 10 detail pages responded. An unrelated news link was excluded. Five clearly technical role titles were observed: Junior Data Scientist, Senior Data Scientist, QA Engineer Intern, Software Engineer Intern and Senior Software Engineer. Junior and Senior Data Scientist explicitly give Nairobi, Kenya with hybrid/remote options. Other role locations need review. The Software Engineer Intern URL contains spaces; the exact observed link succeeds with percent encoding, so it should not be silently replaced with a guessed slug.

The separate Full-Time Consultant – Senior Data & Risk Manager page explicitly closes **30 November 2025**. It is expired and must not be newly published just because it remains on the careers index. No immutable requisition IDs or posting dates were found. A collector needs the pipeline's persistent URL-to-ID state, reviewed field extraction, verified application path, source terms and hosted trial before acceptance. Do not derive identity from the title.

Dolcepay lists four individual positions, including **Fullstack Developer**. It has an application mailbox and Remote / Full-time label. Geographic eligibility is not proven; do not infer worldwide or Kenya remote eligibility from that label. No requisition ID or structured dates were found.

AVA links Maintenance Mechanic and Assembly Technician; these titles do not establish technical jobs under the site's software/IT taxonomy. Occidental's 2025 PDFs are old/nontechnical leads. Decathlon's Marketing Manager is excluded. Individual metadata exports are in `discovery-output/overnight-missing/roles/`.

## Blocks, empty states and rejected false positives

- Medic's official page links `medic.pinpointhq.com/en` and `medicmobile.pinpointhq.com/`. Both requests were blocked. No alternate endpoint, proxy or evasion was attempted.
- Churpy's Freshteam page responds without extracted jobs or useful visible inventory. It is an unresolved/possibly retired shell, not a proven healthy-empty result.
- Yellow Card's BambooHR page is a dynamic careers shell. Public JavaScript did not establish a public inventory interface. BambooHR's authenticated applicant-tracking API requires hiring credentials and is not a substitute public endpoint.
- PAIX and Kwara expose Zoho Recruit shells; public reachability does not validate parsing or pagination.
- Kenya Coast Guard explicitly says No Open Vacancies. East African Portland explicitly says No openings. Both are useful empty-template candidates, still requiring source and hosted checks.
- Isuzu, Tausi and JamboPay have Careers links pointing only to `#`; Zanifu's homepage fragment is likewise not a careers source.
- CUEA's career-guidance news article and Kenya Law's Employment and Labour Relations Court link were rejected as hiring-source false positives.
- REREC supplier-manual PDFs were not treated as vacancy advertisements.
- Existing access limits and deliberate blocks remain gates. No login, LinkedIn/Facebook collection, description storage, expiry or production baselines were introduced.

## Complete employer review

An empty source column below means no usable careers candidate was recovered. The initial status is preserved so a later source link cannot erase the original access failure.

| Employer | Initial outcome | Proposed source URLs | Review |
|---|---|---|---|
| Adrian Kenya | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Africa Data Centres Kenya | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Africa's Talking | ACCESS_LIMIT | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Afrinet Global & Company | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Ahadi Corporation / Ahadi Wireless / SasaKonnect | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| APA / Apollo Group | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Ariya Finergy | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Asilimia | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Associated Vehicle Assemblers | DISCOVERED | https://ava.co.ke/careers/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Bandwidth and Cloud Services / BCS Group | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Capex Life Assurance | DISCOVERED | https://capexlifeassurance.co.ke/careers/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Catholic University of Eastern Africa | NO_CAREERS_LINK | https://recruitment.cuea.edu/ | Additional official careers candidate recovered; not activated. |
| Chumz / Moneto Ventures | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Churpy | DISCOVERED | https://churpy-team.freshteam.com/jobs | Freshteam public jobs page responds but has no extracted vacancy data; shell or retired board, not healthy-empty. |
| Credrails | DISCOVERED | https://www.credrails.com/new-website-2-0/career-page-updated | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Daproim Africa | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Decathlon Kenya | NO_CAREERS_LINK | https://www.decathlon.co.ke/content/128-careers | Additional official careers candidate recovered; not activated. |
| Dedan Kimathi University of Technology | FAILED | https://recruitment.dkut.ac.ke/vacancies/admin | Additional official careers candidate recovered; not activated. |
| Direct Pay / DPO Pay / Network | ACCESS_LIMIT | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Directline Assurance | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Dolcepay Kenya | DISCOVERED | https://dpkenya.com/career | Four individual roles, including Fullstack Developer. No immutable ID/structured location/date; remote label alone does not prove eligibility. |
| East Africa Reinsurance | DISCOVERED | https://eastafricare.com/careers/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| East African Portland Cement | DISCOVERED | https://eastafricanportland.com/careers | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Egypro East Africa | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Fingo Payments Services | DISCOVERED | https://www.fingopay.io/careers | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Fireside Group | DISCOVERED | https://fireside.co.ke/careers/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Freight In Time | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Geminia General Insurance | DISCOVERED | https://geminia.co.ke/careers/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Gjenge Makers | ACCESS_LIMIT | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Gladys Technologies | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| GOMYCODE Kenya | ACCESS_LIMIT | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Guardian Bank | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| HealthX Africa | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Hela Apparel Holdings Kenya | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Hisa | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Horizon Contact Centers | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Intersat Africa | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Intra Africa Assurance | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Isuzu East Africa | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Kansai Plascon East Africa | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Kasha | ACCESS_LIMIT | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Kashia Services / Cashia | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| KenCall EPZ | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Kenya Airports Parking Services (KAPS) | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Kenya Bureau of Standards | FAILED | https://careers.kebs.org | Additional official careers candidate recovered; not activated. |
| Kenya Coast Guard Service | DISCOVERED | https://www.kcgs.go.ke/vacancies<br>https://www.kcgs.go.ke/vacancies/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Kenya Law / National Council for Law Reporting | NO_CAREERS_LINK | https://kenyalaw.org/kl/index.php?id=10133 | Additional official careers candidate recovered; not activated. |
| Kenya Medical Supplies Authority | FAILED | https://swifthr.kemsa.go.ke/resume/PublicJobList.aspx | Additional official careers candidate recovered; not activated. |
| Kotani Pay | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Kukua | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Kwara | NO_CAREERS_LINK | https://kwara.com/about#careers | Additional official careers candidate recovered; not activated. |
| M-Shule | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Maasai Mara University | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Mamlaka Hub and Spoke | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Medic | DISCOVERED | https://medic.org/careers/ | Official careers links observed to medic.pinpointhq.com and medicmobile.pinpointhq.com; both deliberately blocked. No retry/evasion or activation. |
| Monarch Insurance | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| MyISP | DISCOVERED | https://myisp.co.ke/job-openings/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| National Computer and Cybercrimes Coordination Committee / NC4 | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| National Intelligence Service | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| National Transport and Safety Authority | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| National Youth Service | DISCOVERED | https://www.nys.go.ke/jobs | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Ndovu | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Occidental Insurance | DISCOVERED | https://www.occidental-ins.com/careers/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| On It Microfinance Bank | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| PAIX Data Centres Kenya | DISCOVERED | https://careers.paix.io/jobs/Careers | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| PathCare Kenya | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Pesaflow | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Pesawise Services | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Pezesha | DISCOVERED | https://pezesha.com/careers/ | 10 individual vacancy links; news link excluded. Technical candidates need location/date/application and persistent URL identity review; software-intern link has malformed spaces. |
| Pwani Oil Products | DISCOVERED | https://hrmis.pwani.net/recruitmentportal/files/html/login.html?tenantId=fc71989e-c3a6-40ba-bf4d-05f71d3490c9 | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Raha Pay | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| REREC | DISCOVERED | https://rerec.co.ke/career/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Rural Electrification and Renewable Energy Corporation | DISCOVERED | https://rerec.co.ke/career/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Sky World | DISCOVERED | https://skyworld.co.ke/careers/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Soliton Telmec | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Star Discover Insurance / Star Discover Life | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Takaful Insurance of Africa | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Tanda Agent | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Tausi Assurance | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Teachers Service Commission | DISCOVERED | https://www.tsc.go.ke/index.php/services/teacher-management/recruitment-and-selection | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Technology Service Providers of Kenya / TESPOK | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Tetranet Services | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Text Book Centre | ACCESS_LIMIT | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| TIBU Health | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Tononoka Group | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Umsuka Capital | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Unwired Communications | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| V-Squared Networks | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Viewtech / SasaPay | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Vilcom Networks | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Wakandi Kenya | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Wananchi Group / Zuku | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Wavelink Networks | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| WaveX Internet Service Provider | DISCOVERED | https://wavex.co.ke/careers/ | Observed official careers candidate; collection, complete inventory and hosted trial gates remain. |
| Web Tribe / JamboPay | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Yellow Card | DISCOVERED | https://yellowcard.bamboohr.com/careers | BambooHR public careers shell reachable; authenticated applicant-tracking API is not a public collection fallback. |
| Zamupay | FAILED | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| Zanifu | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |
| ZTE Kenya | NO_CAREERS_LINK | Unresolved | No verified employer vacancy source discovered; not a healthy zero-vacancy crawl. |

## Verification limits

All fetches used the shared robots-aware `ProbeHTTP` policy with host throttling and request budgets. Only factual vacancy/source metadata, link labels, template headings and empty-state evidence were retained. Page bodies and job descriptions were processed in memory only. This report does not claim legal permission solely because an endpoint is accessible. Remaining gates include relevant terms review, precise identity, complete inventory, local and GitHub-hosted access, trial quality checks and publication review.
