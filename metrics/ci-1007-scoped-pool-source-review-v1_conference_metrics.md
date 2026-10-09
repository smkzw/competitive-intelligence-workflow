# Conference Metrics: ci-1007-scoped-pool-source-review-v1

Date: 2026-10-10

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `evidence_single_object` | `zcode-live-bigmodel` | `GLM-5.3-Flash`;observed max | exit0/one round/no fallback |1200.241s|54 parsed tools/0 parsed results|input105553/output3271/cache_read104384 provider accounting|REVISE: binding holds; dose-prefix drops3 trials|
| `evidence_single_object_dose_fix_v2` | `zcode-live-bigmodel` | sameGLM/observedmax | exit0/same-session/no fallback |404.239s|17 parsed tools/0 parsed results|input133478/output2481/cache_read131136 reported|scoped ACCEPT advisory; new118 rows/old exact subsets|

## Timeout And Retry Evidence

Original runnerEXIT collected once, no progress polling/latency fallback.
Same actual session sess_1d6c4bd4-3cb3-4bb4-83db-22935a130fdb continues only after
the material dose repair and frozenv2. New separate output/log; remaining6000s
hard bound, actual sameGLM5.3Flash/max verified, terminal collected. Do not count
initialization or owner57tests as this independent source acceptance.

## Quality Decision

Owner fixed root via existing normalizer,6RED→57 relatedPASS. v2 restores118
rows/3trials,17sources/3884facts/3481claims, old fact/claim subsets exact.
Source/public/N context guards not relaxed. Scope omissions named; genuine
missing/unknown attribution retained. Original reviewer mistaken trial acronym
and hardcoded scratch replay suggestion explicitly corrected by raw-source/
script inspection. Formal source issuer, adoption/current and release NOT_RUN.
