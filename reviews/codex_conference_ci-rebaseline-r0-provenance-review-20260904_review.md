# Codex Conference Review: ci-rebaseline-r0-provenance-review-20260904

Date: 2026-09-04

## Verdict

**PASS for R0 controlled-rebaseline closure.** This accepts the provenance recovery point, truthful full quality gate, historical-source-set demotion, zero-contact legacy boundary and fail-closed disk-hygiene policy. It does not accept an HTML-only release source set, R2-R6 implementation, any portal, host bundle, RC or release.

## Boundary Compliance

- The independent participant was read-only and stayed inside the authorized workspace.
- The forbidden legacy project root was not read, inventoried, resolved, checked for existence, modified, chmod-ed or deleted.
- The participant did not inspect the external recovery backup; Codex retained that anchor and verified it separately.
- No reset, checkout, clean, `git add .`, speculative history reconstruction or release-state signal was used.
- The working tree remains intentionally dirty. Historical 422-file source-set records remain preservation evidence only.

## Participant Outputs Reviewed

- Role: `general_single_object`; runtime identity: `pi / cursor / default`.
- Hermes was not used for this conference pass; no Hermes result is claimed or counted.
- Session: `01a06b65-d857-7000-8f30-816c54f99ec5`; the correction review resumed this exact session with no fallback.
- Round 1 returned VETO: two P1 findings and three P2 findings covering symlink-target resolution, missing R0.4 policy, dead gate forwarding, missing shell-level negative coverage and incomplete ReportLab-ignore disclosure.
- Codex accepted and repaired every substantive finding. Round 2 re-read the current bytes, re-ran focused and full checks, and returned PASS.

## Conference Panel Review

The first VETO was evidence-bearing and was not averaged away. The same participant then verified that symlink targets are lexicalized with `os.readlink` plus `abspath`, the R0.4 disk policy is explicit, the gate rejects an invalid historical-source-set/clean combination before any quality step, both ReportLab ignore classes are disclosed, and the consolidated gate remains labelled `quality-only`.

The only residual suggestion was optional strengthening of literal policy assertions. The policy and its decisive deny/retain contract already exist, so this is non-blocking and may be folded into later governance maintenance.

## Main-Venue Codex Review

Codex accepts the corrected R0 implementation and rejects the original worker's false-green or release-like interpretations. The current gate is a quality gate only: it proves Ruff, strict mypy, unit/contract tests and the no-legacy-runtime scanner over their declared scopes. It does not prove clean source provenance, release packaging or RC readiness.

The existing full recovery snapshot predates the final conference corrections. It remains the previous verified recovery point; a second current recovery point is required at milestone closure. Both are explicitly outside the future HTML-only release source set.

## Codex Independent Verification

- Independent participant full gate: `GATE_OK status=quality-only steps=4`; Ruff passed, strict mypy passed over 191 files, unit/contract tests reported 860 passed, and `LEGACY_REF_OK` passed.
- Focused remediation suite reported 10 passed; the invalid dual-flag gate invocation exited 2 before any quality step.
- Codex revalidated both external manifests and their source/backup equality: 19,498 nodes and 5,910,548,662 bytes.
- Codex rehashed every regular file and symlink in the external backup against its validated manifest without following symlink targets: all 19,498 nodes matched; writable nodes were 0.
- Physical manifest-file SHA-256 values remain `ee8242d7b0afb6df8bd406091e3bd0e8ec786adbc551a149cd17f3231bd8e42f` for the source manifest and `f91d2840346b041c607e6bca8822335f70ff35d39eff0266aa535aafe55ef5d6` for the backup manifest.
- `git diff --check` passed. Browser, visual, PDF and PPT checks are not R0 claims and were not counted.

## Final Decision

Accept R0 as the controlled-rebaseline foundation. R2-R4 may start only after the current milestone checkpoint, second recovery point, conference validation and disk-hygiene receipt are complete. Preserve the first recovery point as the previous rollback anchor and continue to withhold all RC/release signals.
