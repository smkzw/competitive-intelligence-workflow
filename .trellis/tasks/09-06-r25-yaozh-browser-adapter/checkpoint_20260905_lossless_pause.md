# Checkpoint — R2.5 无损暂停

Date: 2026-09-05 CST
Status: in progress; P1/P2/P3/P5 complete, P4/P6 partial.

## Completed in this slice

- Removed the production false positive where launching a blank headless Chromium was treated as an
  authenticated Yaozh session.
- Added a closed `YaozhSessionObservation` and immutable content-addressed
  `YaozhRouteAccessReceipt`: project and answer-byte binding, six technical states, canonical
  `https://vip.yaozh.com` origin, offset/future-time checks, host/time visibility, secret/path
  rejection, non-blocking semantics, atomic persistence and byte/mtime-stable replay.
- Added the `commercial_database` research-source role, restricted to `secondary` and the Yaozh
  enterprise hostname; synchronized schemas, CLI `yaozh observe`, package manifest and public/internal
  Skill guidance without browser-profile or credential material.
- Independently repaired two P1 scientific-gate defects identified by the one-time Astra review:
  cross-group reuse of one fact version no longer supplies a missing endpoint group, and four B
  baseline units admit the approved `regulatory_material` role while continuing to reject company
  disclosure.

## Verification

- Focused Yaozh/schema: 39 passed.
- Focused scientific-gate regressions: 2 passed; touched-source Ruff and strict mypy passed.
- Related matrix: 198 passed, 1 environment-conditional skip.
- Full product chain (`tests/integration tests/graph tests/application`): 586 passed.
- Full quality gate: Ruff passed; strict mypy passed for 211 source files; active v1 tests 947 passed
  with 20 deselected; retained compatibility 20 passed with 947 deselected; layer audit 7 passed;
  legacy runtime-path scan passed.
- Governed execution `ci-r25-yaozh-browser-adapter-20260906`: three terminal ZCode workers; execution
  audit and Codex review/metrics gate passed.
- Independent conference `ci-r25-yaozh-browser-adapter-20260906-conference`: one terminal
  `pi/opencode-go/muse-spark-1.3-contributor:xhigh` pass, no fallback; conference structure and Codex
  review/metrics gate passed. Verdict: revise R2.5 before completion.

## Open completion blockers

1. The optional Yaozh route is not operational: persisted receipts have no product-run consumer and
   `login_browser` correctly remains non-blocking unavailable.
2. Source-policy authority is not yet executable through Yaozh-to-A/B/C fact lineage. A buggy host
   could relabel Yaozh-derived content as a result-bearing GateSpec role. This is a P0 scientific
   integrity blocker on R2.5 completion.
3. Receipt freshness/max-age and historical-cutoff semantics require the still-pending native Ask
   product choices. Do not invent a TTL.
4. Damaged/symlink answer-record behavior needs a typed run-level failure path.
5. No real authenticated Yaozh host smoke has run. Do it only after the enforcement/consumer slice,
   retaining no credentials, page content, browser profile or sensitive screenshot.

## Review caveat

The requested one-time `gpt-6-astra:high` CLI review completed after the Codex CLI update, but the
reviewer violated its declared read set by opening Codex memory. Its source findings were therefore
treated only as advisory input and independently reproduced in workspace files/tests; it is not
compliant acceptance evidence.

## Next safe action

Use native Ask (multiple-choice only) to settle freshness behavior. Then create a separate TDD task
for the smallest cross-layer authority/lineage and receipt-consumer contract; do not silently adopt
the worker's broader D1-D4 redesign. Keep this task `in_progress` until real-host smoke and the
remaining P4/P6 gates pass.

## Disk hygiene and boundaries

After all deterministic evidence was recorded, deleted only reproducible `.pytest_cache`,
`.mypy_cache`, `.ruff_cache` and `__pycache__` directories under `src/`, `tests/`, and `tools/`
(about 34 MiB). Runner logs/reports, fixtures, snapshots, historical `tmp/`, `.artifacts`, `runs`,
`logs` and archives were retained. No reset, checkout, clean, broad staging, legacy-workspace access,
credential access or RC/release signal occurred.
