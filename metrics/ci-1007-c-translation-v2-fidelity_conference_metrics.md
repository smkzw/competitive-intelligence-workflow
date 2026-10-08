# Conference Metrics: ci-1007-c-translation-v2-fidelity

Date: 2026-10-08

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `evidence_single_object` | `codebuddy-cli` | `deepseek-v4.1-flash` | terminal exit0, no fallback | 357.906s | 29 observed tool calls, not API billing | native usage locally retained; no token/cost inference | REVISE v2 |
| same-session v3 follow-up | same | same actual init/final model | terminal exit0/no fallback |274.902s|27 observed tool calls|local native cumulative usage, no billing inference|31ACCEPT_BOUNDED, one remaining siblingREVISE|

## Timeout And Retry Evidence

Initial128 turns/7200s requested; native87. Follow-up48/6840s requested; native
cumulative167 implies80 additional, turn limit not enforced. Actual total632.808s,
below7200s; nominalfollow-up omitted exact prior runtime deduction, retained.
Effortmax requested, not provider-attested. Parent no latency redispatch/progress
polling. Inputv2/v3 hashes owner-recomputed. Original follow-up preflight exit1
because missing parser-compatible output/read headings, owner erroneously launched;
separate post-dispatch addendum PASS is not retroactive. Next C follow-up actual
preflight PASS checked before dispatch. No source/product permission widened.

## Quality Decision

Material translation errors corrected from exact source:31 v3 independently
accepted, one sibling5615251a found in necessary control and fixed literally in
v4 by owner. Total32 source-display corrections, no MT rerun/new model/large gate.
Reviewer unsupported Chinese-name/accounting/extraction-cap claims corrected.
Original source tail is still truncated, no inferred suffix. All258 rows/174
translated locators retained, source/current/science unchanged; no productPASS.
