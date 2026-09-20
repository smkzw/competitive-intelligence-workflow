I'll start with the assigned context and plan files, then do a read-only audit of the blocker_audit / run_service / no-draft product chain.Context is loaded. Next I’ll locate the blocker_audit / run_service / no-draft code and related R2.4 specs for a read-only audit.Key paths are identified. Next I’ll read the R2.4 task specs and the core blocker_audit / run_service implementation.Grep looks unreliable here, so I’ll read the core modules and search with shell `rg` instead.Dual write paths in `run_service` look important — I'll inspect those sections and the BlockerAudit field/schema contract next.# Execution Output: ci-r24-gatespec-blocker-closure-20260905 - worker_03

## Boundary And Context Check

- Role: `worker_03` / read-only product-chain audit only; no production writes; no peer review; no conference.
- Initial reads: `context/ci-r24-gatespec-blocker-closure-20260905_execution_context.md`, `plans/codex_execution_ci-r24-gatespec-blocker-closure-20260905.md`.
- Context `Source Of Truth` is still `TODO`; authoritative references used for this audit (evidence, not self-authorization):
  - `docs/specs/competitive-intelligence-workflow-design-v1.3.md` §6
  - `.trellis/tasks/09-05-r24-gatespec-blocker-closure/{prd,design,implement}.md`
  - Implementation under `src/ci_workflow/gates/blocker_audit.py`, `application/run_service.py`, `application/terminal_recovery.py`, `capabilities/scientific_qc.py`, `renderers/portal/report_b.py`
  - `schemas/blocker-audit.schema.json`
  - Integration negatives under `tests/integration/test_no_draft_*.py`
- Out of scope here: GateSpec/YAML matrix (worker_01), exhaustion/info-gain science binding (worker_02), implementing fixes, running full gates, final acceptance.
- Report file not written by this worker; complete report returned for runner persistence.

## Work Performed

1. Mapped the claimed unique publication path: `build_and_write_blocker_package` → `_build_blocker_audit` → `_write_blocker_package` / `render_audit_markdown_zh`.
2. Traced all product call sites that create `blockers/<A|B|C>/<version>/{audit.json,audit.md}`.
3. Compared machine fields + schema required set against v1.3 §6 / R2.4 design minimum audit object.
4. Audited atomicity, idempotency, drift/history behavior, user Markdown cleanliness, and no-draft residual assertions.
5. Validated the two alternate product payloads against `blocker-audit.schema.json` (expect fail-closed; observed many schema errors).
6. Inventoried existing negative coverage vs product-path residual matrix gaps for Codex RED/minimal fix.

## Artifacts And Evidence

### Evidence — canonical library path is strong

- Unique public publisher is declared and implemented: `build_and_write_blocker_package` (`blocker_audit.py` ~1493–1544).
- Machine model `BlockerAudit` + nested `GapAuditSummary` bind GateSpec identity, universe/evidence snapshot, failed units or typed empty universe, route receipts, `information_gain_rounds` (≥2), omission conclusion, technical diagnosis separation, uncertainty, user-help/minimal action, source links, delivery directory, digests (`schemas/blocker-audit.schema.json` required = 33 top-level fields).
- Atomic first write: temp dir + two files + `os.replace` (`_write_blocker_package` ~1584–1591).
- Same-version idempotency + drift fail-closed: `_verify_existing_package` exact byte compare; tested by `test_blocker_package_write_is_idempotent_and_drift_fails`, extra/single-file integrity tests, atomic temp cleanup test.
- User Markdown is separate and scrubbed via `_FORBIDDEN_USER_TOKENS` + `assert_user_facing_zh_clean` (`render_audit_markdown_zh`).
- Library no-draft assert covers `reports/<kind>/<ver>` FS absence + DB tables: snapshots / coverage / projections / format_jobs / render_queue / artifact_records.
- Product wiring **does** use the canonical path in two places:
  - empty-universe: `_drive_blocker_write` → `build_and_write_blocker_package`
  - B/C gate fail with exhaustion file: `publish_terminal_blocker` → `build_and_write_blocker_package`

### Evidence — product chain is **not** a single closed publisher

| Path | Location | Uses canonical entry? | Schema-valid BlockerAudit? | Atomic rename? | Drift/idempotent? | no-downstream assert? |
|---|---|---|---|---|---|---|
| Empty universe | `run_service._drive_blocker_write` | Yes | Yes (library) | Yes | Yes | Yes |
| B/C terminal with exhaustion | `terminal_recovery.publish_terminal_blocker` | Yes | Yes | Yes | Yes | Yes |
| Publication unavailable | `run_service._write_publication_evidence_insufficiency` (~3409–3441) | **No** | **No** (31 schema errors on sample) | **No** (`mkdir` + per-file `write_bytes`) | Partial (existing file byte check only) | **No** |
| B baseline group gate fail | `report_b.write_report_b_blocker` via `run_service` ~2936 | **No** | **No** (32 schema errors on sample) | **No** | **No** (unconditional overwrite) | **No** |
| Scientific QC exhausted veto | `capabilities/scientific_qc.py` → `evidence_blocked` | **No publish** | N/A / missing package risk | N/A | N/A | Assert only; **does not write audit package** |

Concrete bypass payload shapes:

- Publication: `{schema_version, report, report_version, state, reason, evidence_snapshot_id, user_guidance}` — rejects against `blocker-audit.schema.json` (`additionalProperties` + missing required machine fields).
- B baseline blocker: `{schema_version, report, report_version, state, gate_failures, user_guidance}` — same failure mode.
- Both land in the same user-visible path contract `blockers/<report>/v1/{audit.json,audit.md}`, creating a **parallel truth** next to the R2.4 machine audit.

### Evidence — machine completeness vs v1.3 §6 / R2.4 design

Present in canonical `BlockerAudit` (or nested gap audit): contract/report versions, GateSpec id/version/fingerprint, failed objects/units/fields, missing/conflict/route states, impacted products/trials, route receipt ids, two-round information gain, omission conclusion/notes, technical diagnosis, uncertainty, user-help + minimal action, links, delivery directory, Chinese resume instruction.

Gaps / ambiguities:

1. **No persisted machine `no_draft` assertion field** in schema/model (design.md explicitly lists “no-draft 断言”; enforcement is write-time side effect only).
2. **No first-class machine `resume_node`** field; only `resume_instruction_zh`. Token `resume_node` is forbidden in user text, so machine field is currently absent rather than user-leaked.
3. User Markdown intentionally omits several machine fields (e.g. digests, route ids) — good — but also does not surface `residual_uncertainty_zh` / stored `omission_review_result_zh`; it hardcodes a generic “未发现可归因遗漏” narrative.
4. Empty-universe product write hardcodes `source_links=("https://clinicaltrials.gov/study/NCT01234567",)` in `_drive_blocker_write` — fixture-like residue in product path.
5. `report_version` is hard-pinned to `"v1"` in product publishers; versioned history is path-based only.

### Evidence — history / idempotent recovery

- Same identity + same bytes: return existing package (idempotent resume).
- Same directory + different content: `BlockerAuditDriftError` (protects accepted history from silent overwrite).
- This is **immutability of the current version directory**, not an archived multi-generation history store under one version. New history requires a new `report_version` path segment.
- Resume path in `run_service` (~3181–3192) only checks both files exist; it does **not** re-validate `BlockerAudit` / schema when preserving terminal blocked state. A prior bypass payload would satisfy the existence check.

### Evidence — no-draft / residual negative matrix

Library + integration coverage is dense for the **canonical entry**:

- empty A/B/C; each applicable critical unit alone; conflicts; scientific QC rejection state transitions; schema positives/negatives; forged inputs; route/receipt/entity binding; info-gain alignment; atomicity; drift; extra file; path-jumping source links; Chinese cleanliness.

Product residual gaps (not closed by current tests found):

1. Publication insufficiency writer accepted as product blocker without schema/BlockerAudit.
2. `write_report_b_blocker` overwrite path; no tests requiring schema validation or canonical entry.
3. Scientific QC exhausted → `evidence_blocked` without mandatory blocker publication.
4. `assert_no_report_downstream_artifacts` does **not** scan FS residuals outside `reports/<kind>/<ver>` (e.g. `state/derived/report-*-data.json`, staging, placeholders) and has **no symlink/path-jump checks** on the blocker directory itself.
5. Host receipts assert `no_draft` for blocked outcomes, but that does not prove disk audit JSON is the R2.4 machine package.
6. Collision case missing: bypass package already under `blockers/A/v1`, then canonical empty/non-empty write must fail-closed with typed drift/integrity — product tests not found.

### Inference

R2.4 P4/P5 are **not yet product-closed**. The library contract is largely ready and well-tested; the run-service/product surface still has at least two alternate writers plus one “blocked without package” scientific-QC path. That is the highest-leverage honesty risk: users can receive a short Chinese page whose adjacent `audit.json` is not the claimed machine audit, or a terminal blocked state with no audit package at all.

### Recommendation — minimal fix order for Codex (not executed)

1. **Delete or quarantine bypasses**: route `_write_publication_evidence_insufficiency` and `write_report_b_blocker` through `build_and_write_blocker_package` only (or remove them from product runtime).
2. **Close QC exhausted path**: on unrecoverable scientific QC veto, require `publish_terminal_blocker` / `build_and_write_blocker_package` before accepting `evidence_blocked`.
3. **Harden residuals**: extend no-draft assert to known FS leftovers + reject symlink blocker dirs/files; require resume preservation to revalidate schema/`BlockerAudit`.
4. **Optional schema completeness**: add machine `no_draft_assertion` (+ optionally `resume_node`) if Codex treats design.md wording as normative for JSON, not only runtime side effects.
5. **RED matrix (product-run, not library-only)**:
   - publication unavailable → schema-valid package only; no extra files; no reports/derived portal bytes
   - B baseline missing → same
   - QC exhausted veto → package present + no downstream
   - bypass/tampered audit.json → resume fail-closed
   - softlink/path jump under `blockers/` → fail-closed
   - cross-report reuse / same-version drift → fail-closed
   - empty-universe must not emit fixture NCT links unless bound to real receipts

### Uncertainty

- Whether publication-manual and B-baseline “lite” pages were intentionally temporary during R2.3 and deferred to R2.4 P4 (task implement still unchecked) — Codex must decide if they are bugs or staged stubs.
- Whether “历史快照” means only same-version immutability (current) or a required archival store of prior packages.
- Context still lacks Codex-pinned authoritative file list/screenshots; this audit used design + code as provisional truth.

## Commands And Observations

| Tool / command | Target | Observation |
|---|---|---|
| Read | execution context + plan | worker_03 assigned; Source Of Truth TODO |
| Read | R2.4 prd/design/implement | P4/P5 still open; negative matrix listed |
| Read / `rg` | `blocker_audit.py`, schema | Strong canonical model/publisher |
| `rg` + Read | `run_service.py`, `terminal_recovery.py`, `report_b.py`, `scientific_qc.py` | Three product writers + one no-package blocked path |
| Read | v1.3 §6 | Unified machine JSON + concise MD required |
| `rg` | `tests/integration/test_no_draft_*.py` | Dense library negatives; product bypasses uncovered |
| Python `jsonschema` | sample publication + B payloads | 31 / 32 schema errors respectively |

No package installs. No source edits. No acceptance gates executed.

## Blockers Or Missing Environment

- No Codex-pinned Source Of Truth list beyond TODO in execution context.
- Did not run pytest (assignment is read-only audit; not authorized to claim gate pass/fail from fresh runs).
- `pi-worker` / `pi-worker-docs` wrappers failed with `unknown flags: --no-prompt-templates, --no-context-files`; continued with Read/Shell/`rg`.

## Rerun Requests Or Next Step

Ask Codex to authorize one of:

1. **Minimal repair pass** (same session or new worker): remove/rewire the two bypass writers + bind scientific-QC exhausted publish; then run focused RED tests listed above.
2. **Decision only**: confirm whether publication-manual and B-baseline lite packages are temporary stubs allowed until P4, or immediate fail-closed defects.
3. If continuing audit-only: pin authoritative fixtures/screenshots for a real `no-draft-a-empty` / publication-unavailable / B-baseline-blocked product run so resume/revalidation claims can be checked on disk, not only statically.

Precise question for Codex: **Are `_write_publication_evidence_insufficiency` and `write_report_b_blocker` authorized interim product surfaces for R2.4, or must every `blockers/*/v1/audit.json` validate as `BlockerAudit` via the single public entry before any further implementation?**
