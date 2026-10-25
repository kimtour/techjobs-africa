# Employer pilot results — 25 October 2026

The workbook import contains 796 rows, 758 employer records and 633 distinct
recruitment URL strings. Fourteen portals were assessed; five passed the recorded
local and hosted checks for isolated trial. This is not daily coverage of all
employers. New sources remain trial; production was not promoted.

## Latest local trial

Checked at 13:15 UTC, against the accepted job baseline. All five complete fetches
succeeded. Descriptions were used only in memory and were not persisted.

| Employer portal | Raw listings | Technical | Eligible candidates |
|---|---:|---:|---:|
| M-KOPA | 54 | 4 | 2 |
| Jumia | 29 | 0 | 0 |
| Turaco | 10 | 0 | 0 |
| Ampersand | 5 | 0 | 0 |
| Tala | 9 | 3 | 0 |

Two additional unique candidates passed eligibility and exact dedupe: M-KOPA
Senior Backend Engineer — Mobility (12 month FTC) and Senior Backend Engineer —
Asset Sales. Both are Johannesburg, South Africa roles, not evidence of Kenya
eligibility. Zero eligible jobs on the other boards is distinguished from a
failed fetch. Tala's technical jobs did not pass the existing eligibility gates.

The first trial exposed physical electrical-network and logistics-network titles
misclassified as computer networking. Explicit function-based exclusions and
regression tests now reject them without rejecting computer-network engineers.

Hosted verification run 40196220794 and a legacy-source production smoke run
40196217782 succeeded on public standard hosted runners. The corrected trial
selection and taxonomy also passed on hosted run 40196857729, with the same two
candidates and five complete successful crawls. Activation still requires all verification checks, trial review and
publication review. Absence expiry remains disabled for new registry sources.

See [onboarding](employer-onboarding.md) for expanding verified coverage and
[execution and storage](free-execution-and-private-state.md) for quota handling.
