# Jobicy and Remote OK discovery — 23 November 2026

M0 completed before production adapters: both documented public JSON endpoints
returned HTTP 200 with stable numeric listing IDs, original listing links,
locations and publication dates. Both robots files permit the API paths for
TechKaziBot. Descriptions were inspected in memory only and were not saved.

References: https://jobicy.com/jobs-rss-feed and https://remoteok.com/faq,
plus Remote OK's first API entry at https://remoteok.com/api.

Both explicitly allow job aggregator use with visible source credit and original
listing links. Remote OK additionally requires followed links and forbids using
its logo without permission. Use text credit, no logos or nofollow links.
Jobicy's free API needs no credentials or wallet. No paid API is introduced.

Jobicy: traverse the documented seven-day discovery feed using count=100 and
opaque nextCursor, maximum 20 pages. Validate jobCount, hasMore and nextCursor;
fail safely if the cap is reached before completion or pages repeat. Recheck up
to 1,000 previously accepted IDs in batches of 100, oldest checked first. Only
explicit closed status removes a listing; active refreshes last_checked_at and
unknown retains it for another check. Absence from the seven-day feed never
means closure. Leave 1.2 seconds between all requests and use existing cooldown
handling on 429/503. Scheduled pipeline work already performs other source
fetches before this adapter; wait until minute 01 plus 17 seconds if invoked during minute 00, so a
standalone/manual invocation also avoids minute 00. Run at existing EAT slots.

Remote OK: fetch the documented public recent-jobs JSON feed once per run;
validate its legal metadata sentinel, record identities and original links.
The feed is a recent window, not a complete inventory. No absence expiry or
claim of authoritative closure is made. Posting dates and Last checked remain
visible so candidates can inspect freshness on the original listing.

Admission: explicit Worldwide/Anywhere, Africa or Kenya location tokens only;
unknown/missing locations and EMEA alone are excluded, as are other geographic
restrictions. Preserve location labels, stable source+numeric-ID identities and
original listing URLs. Technical classification remains independent of provider
categories/tags. Descriptions/excerpts are never persisted. Malformed responses,
403, 429 and 5xx retain previous accepted data and never close jobs.

Append Jobicy and Remote OK panels after Himalayas, keep their headers when
empty, credit each source on every card and in its header, and verify both in
All Jobs and their own feed with independent controls on desktop and mobile.
