# Execution Metrics: ci-1007-consumer-snapshot-revisions-v1

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| primary author | codebuddy-cli | deepseek-v4.1-flash (requested max) | final report incomplete; source authored | exact runtime retained in logs | recorded primary session exists | not standalone acceptance |
| fallback verifier | zcode | GLM-5.3-Flash (requested max) | terminal exit0 | 994.755s | 36 | 188 reported PASS, owner separately verified affected bytes |

Primary session: 01a11cb6-93da-7801-a34a-7b38fdd8c7ca. Fallback: sess_77161992-5c4a-4afd-85bf-397ff21b36ae. Fallback reason claiming no resumable session contradicts primary receipt; retained as a mechanism deviation, not a factual excuse. No new fallback was manually dispatched. Waited on completion events, without progress polling.

Owner: 79 affected integration PASS/107.51s; strict6/Ruff PASS. Initial milestone gate FAIL on omitted migration packaging; package/isolated-install batch8 PASS after actual manifest repair. Final GATE_OK6/strict284/active1185/414.51s/compat20/layer7/Ruff/legacy pinned in owner packet. None of these are full clinical, browser, three-host or RC acceptance.
