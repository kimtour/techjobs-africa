# Recommendation review — 26 October 2026

## Implemented

Pending public-source monitors now establish a silent metadata baseline, then write changed vacancy/document URLs and technical title hints to the private `state/employer-review-queue.json`. Titles come only from headings or JobPosting title fields, using the existing technology taxonomy; descriptions and page/script bodies are not retained. Known tracking parameters are ignored while functional filters/IDs stay intact. Failed, partial or blocked requests preserve the previous baseline and never create a new-posting signal. A corrected source URL gets a fresh quiet baseline.

The queue is for human/agent source review, not publication. It never creates jobs, closes vacancies, approves collectors or increases verified-company counts. Pending signals are merged per source; reviewed items can be marked reviewed in private state. The existing discovery budget, host throttles, robots rules and blocked-source exclusions remain unchanged. JavaScript-only inventory still needs an approved data collector; static monitoring is not complete vacancy coverage. No employer emails/messages were sent.

## Corrections to the pasted advice

- KCB is correctly linked to its Oracle tenant. `eoin` is a tenant hostname, not an employer identity; no KCB source is removed.
- VCB is an approved direct-employer source: the official bank website links to its scoped SnapStar board, and local/hosted/trial/production evidence exists. It is not downgraded to a generic aggregator monitor.
- Absa, OldMutual, Branch, NCBA, VCB and M-Oriental already have reviewed daily collectors; do not redo their initial setup from stale advice.
- Sumac's unlinked Greenhouse URL was already replaced with its official corporate vacancies portal; do not reverse this because the unrelated/unlinked board returns zero rows.
- PDF and email application formats are not access blocks. Where fields, identity, permission and complete collection can be verified, metadata collection is possible; otherwise keep the source pending/manual with the actual reason.
- A missing policy is unconfirmed permission. Public endpoint availability alone never completes the collection-review gate.
- DNS/suspension does not prove an employer moved. KWFT's official link still points to the failing recruitment hostname; the regulator still lists Salaam's supplied domain. No replacement portal has been established.
- Branch is in scope as a fintech, but each vacancy still needs explicit African eligibility. Remote alone is insufficient. Bank sector and technical job category remain separate.
- The expansion automation is ACTIVE in the saved app configuration. Earlier subagents hit usage limits; this does not mean the main automation is paused. No duplicate automation or unsupported resume action was performed.

## Fresh portal checks

HFC's public HTML contains both a loading label and a no-open-positions placeholder. Its indexed Systems Administrator338 detail page is a candidate lead, not proof of a current vacancy. The directly fetched detail page is also a loading shell. Published assets were inspected without running them or bypassing controls; no complete approved public data collector was established.

Equity's Taleo form exposes a default no-results message and a public FacetedSearchPage module. The live result set, active/closed state and pagination remain unverified. An indexed October2026 enterprise-development program-manager posting is nontechnical; it is not evidence of an empty board or an eligible technology role. Source remains pending, with its linked employer records distinct.

This update introduces monitoring/review behaviour only; no additional employer or vacancy is claimed from it.
