# gpt-6-astra stage-review route result

Date: 2026-09-05
Requested route: `gpt-6-astra`, reasoning effort `high`, fresh context
Result: terminally unavailable; no review verdict produced

- Governance prompt preflight passed for
  `prompts/conference/ci-r2-stage-review-astra-20260905/reviewer.md`.
- Native admission failed because the installed model catalog does not support
  `gpt-6-astra`.
- One same-model CLI compatibility attempt used Codex CLI 0.147.0 and reached the
  service, which returned HTTP 400 stating that `gpt-6-astra` requires a newer
  Codex version.
- No alternate model was substituted. Retry the same preflighted prompt only
  after a supported runtime is available.

## 2026-09-05 resumed one-time retry

The user explicitly requested the same `gpt-6-astra:high` review again. Native
admission still rejected the unregistered model. One and only one same-model CLI
compatibility attempt created session `01a06f78-cb79-7bb3-9f22-6cfe7655e157`,
reached the service, and terminated with the same HTTP 400 requirement for a
newer Codex runtime. No fallback model was substituted and no review verdict was
produced.
