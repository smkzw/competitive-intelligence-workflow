# Codex Execution Review: ci-0924-r24-26-consumer-recovery-20260926

## Verdict

**Accept with Codex revisions for bounded A/B registry portability only.** Worker output is not whole W04/W07/W08 recovery, C support, or release acceptance. The accepted candidate additionally rejects unsupported C claims, checks A/B trial/group/domain against restored source fact, and protects a different existing sidecar from overwrite.

## Worker Outputs

One CodeBuddy `deepseek-v4.1-flash:max` execution result, exit 0, one 1020.738-second round, output SHA-256 `5eb0629921f70e6b2a6ab36139960e85d726a49a657652edc33513b75f6af910`; no fallback. Worker changed `snapshot_store.py`, added `portal_consumer_binding_recovery.py` and a focused integration test. It correctly distinguished snapshot ingestion hints from later verified A/B registry rows. Its statement that no real registered project existed was disproved by the current English-root R24-23 development candidate; that omission was corrected by Codex rather than copied into status.

## Codex Independent Verification

Codex found a rehashed A+B sidecar could jointly falsify trial/group and still pass the worker's intra-sidecar checks. Two production negative tests first failed, then passed after comparison with persisted source `result_context`; `C` forged binding likewise first passed, then is now rejected until a real registration route exists. Export now refuses to replace different destination bytes while same-byte replay is idempotent. On the frozen real NCT04820530 evidence snapshot SHA-256 `36791d7ed49ff5d8d3eb4759556a6d4d3f907710030e22d1c3ed479d712a10f1`, Codex made an isolated SQLite backup and snapshot copy, exported 19 registered A/B bindings, restored an empty project (0 accepted bindings before sidecar), imported exactly A=18/B=1, compared all registered row bytes with source, and replayed without duplication. The original 140 MiB development project was not modified. Sidecar byte SHA-256 in that temporary probe: `6e113cd9cedb14f77d857b4f1349b236c20880b37bb25c1c028688e8a41ccdb4`; temporary project was removed by its scoped context manager.

Focused recovery + adjacent registry/snapshot/migration batch on candidate before final C guard: `43 passed in 168.02 s`; changed-file Ruff and strict-mypy (2 source files) passed. Final C/overwrite/rehashed-identity selection after the guard: `4 passed, 16 deselected`; changed-file Ruff passed. Codex also repeated the isolated probe on the fixed 50-study, 5839-source-fact development candidate: original verified A registry 1206, snapshot-only restored registry 0, sidecar import 1206 rows byte-identical, in 19.35 seconds; snapshot SHA-256 `0443339f94cdb54678e213182afaa82db4c6b4285656d880a7198f57964ec14d`. This is scale of **verified A only**, not source closure or B/C consumers. A full current gate and final full recovery-file rerun remain pending at this review time; they must be recorded separately before release. C science binding is **not** recovered. A caller-supplied sidecar is not cryptographic proof of registry history by itself; release manifest must bind the exported sidecar hash. `_public_fact` legacy embedded-binding behavior and late restore failures remain separate hardening/transaction issues.

## Cleanup Decision

Preserve the runner report, route receipt, focused tests and candidate review. Do not archive/delete the only worker evidence during active R24 integration. No old workspace, snapshot, CAS or user project cleanup.
