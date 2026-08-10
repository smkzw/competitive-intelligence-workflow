# Conference Participant Output: ci_phase0_contract_review_20260810 - general_grok45

## Boundary Check

- Role: `general_grok45` / provider `grok` / model `grok-build` / `grok-4.5`; Codex-chaired parallel participant; advisory only.
- Workspace boundary observed: only `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` was used for file reads that completed.
- No source edits performed. Runner report path not written.
- No other participant outputs read.
- External Kangzhe dual-read commands were attempted and **cancelled** by the host; no completed observation of those paths was obtained in this session.
- Final clinical / regulatory / visual / live-web authority remains with Codex.

## Independent Work Product

### Pre-audit (active peer)

**Objective:** prove Task 0.1–0.2 true closure and Task 0.3 stable dual-read / single-word drift claim without false-green.

**Highest-impact defect found without re-running commands:** Task 0.1’s pytest contract only exercises a synthetic `tmp_path` tree; it never asserts that the **real repository root** is free of legacy runtime references. That is a structural false-green risk even if unit tests are green. Separately, this participant **did not complete** any decisive hash/test commands (host cancelled all terminal calls), so **true Phase 0 closure cannot be accepted on this pass**.

---

### Task 0.1 — Verdict: **FAIL** (true closure not demonstrated; static false-green gap)

**Status of decisive commands (this session):**

| Command / check | Ran? | Result |
|---|---|---|
| `shasum -a 256 docs/specs/competitive-intelligence-workflow-design-v1.2.md` | **No** (cancelled) | Uncertainty |
| `wc -l` on design v1.2 | **No** (cancelled) | Uncertainty |
| `python3 tools/check_no_legacy_refs.py --root .` | **No** (cancelled) | Uncertainty |
| `uv run pytest` (migration) | **No** (cancelled) | Uncertainty |
| Read `migration/legacy_manifest.jsonl` | **No** (cancelled) | Uncertainty |
| Static read of scanner + migration test + schema + ADR 0000 | **Yes** | Observations below |

**Observed (static):**

- `docs/decisions/0000-design-v1.2-approval.md` records design SHA-256 `f96be175464d06f4a4b2075f020016148e3ac864d07b7ffe05a27db476ca465f`, user approval 2026-08-10, and claims copy/source byte identity. **Not re-verified here.**
- `tools/check_no_legacy_refs.py` walks the tree with `followlinks=False`, skips `.git`/`.venv`/`.trellis`/caches, skips only `migration/legacy_manifest.jsonl`, flags absolute legacy path in non-historical surfaces as `LEGACY_RUNTIME_REFERENCE`, requires `historical:` on `docs`/`fixtures`, flags external symlinks.
- `tests/migration/test_no_legacy_runtime_dependency.py` only builds a **temporary** project under `tmp_path` and never calls the scanner on `REPOSITORY_ROOT` (defined at line 8, unused for a real-root assertion).
- `migration/legacy_manifest.schema.json` requires `runtime_dependency: false` and fixed enums; **actual jsonl rows were not read**.

**P1 — real-root scan not gated by contract test**

- **Locator:** `tests/migration/test_no_legacy_runtime_dependency.py` (full file; especially `test_no_legacy_runtime_dependency_contract`, lines 24–69); contrast `REPOSITORY_ROOT` at line 8 unused as scan target.
- **Evidence class:** observation of test source.
- **Why false-green:** pytest can pass while the live tree still contains unmarked legacy absolute paths (e.g. in `tools/`, `plans/`, `README.md`, `runs/`, or unskipped surfaces). Task 0.1 “closed” via tests alone is insufficient.
- **Minimal repair:** add one assertion that runs the scanner against `REPOSITORY_ROOT` (or an equivalent CI gate command that fails the build) and expects `LEGACY_REF_OK` / exit 0.

**P1 — scanner match is absolute-path-only**

- **Locator:** `tools/check_no_legacy_refs.py` lines 91–133 (`legacy_text = str(legacy_root.resolve())`; membership test `legacy_text not in line`).
- **Evidence class:** observation of scanner source.
- **Why false-green risk:** relative mentions, alternate spellings, or non-resolved path forms of the legacy workspace would not trip the gate.
- **Minimal repair:** if product contract requires fail-closed on any legacy-workspace coupling, extend detectors to known path suffixes / basename of the legacy root (still allowing only `historical:`-marked surfaces), and add fixture cases.

**Inference:** Without a green real-root scan and without re-hashing the design copy, Task 0.1 cannot be treated as truly closed even if prior work claimed it.

**Uncertainty:** live scan outcome; design file hash; manifest row integrity vs schema and target SHA; git commits `5b131be` / `888204b` not inspected.

---

### Task 0.2 — Verdict: **PASS WITH REQUIRED REPAIR** (static contract looks coherent; decisive commands not re-run)

**Status of decisive commands:**

| Command / check | Ran? | Result |
|---|---|---|
| Static read `pyproject.toml` | **Yes** | Observed pins + metadata |
| Static read `tests/contract/test_dependency_manifest.py` | **Yes** | Observed assertions |
| Full `uv.lock` read | **No** | Uncertainty |
| `uv lock --check` | **No** (cancelled) | Uncertainty |
| `uv run pytest` (contract) | **No** (cancelled) | Uncertainty |
| `uv run ruff check tools tests` | **No** (cancelled) | Uncertainty |
| `uv run mypy tools tests` | **No** (cancelled) | Uncertainty |

**Observed (static):**

- Runtime deps pinned exactly: pydantic 2.13.4, Jinja2 3.1.6, reportlab 5.0.0, pypdf 6.15.0, pdfplumber 0.11.10, playwright 1.61.0, PyYAML 6.0.3, jsonschema 4.26.0.
- Dev: pytest 9.1.1, ruff 0.16.2, mypy 2.3.0.
- Python `>=3.12,<3.14`.
- `[tool.ci-workflow.dependencies.*]` records version / license / purpose / https source for each direct dep; ECharts asset 6.1.0 declared under `[tool.ci-workflow.assets.echarts]`.
- Contract test: exact `==` versions; set equality of runtime/dev names; metadata keys == deps; lock package version match via casefold; approved license set `{Apache-2.0, BSD-3-Clause, MIT}`; ECharts dict equality.

**What the test does well (observed):** a name/version mismatch between `pyproject.toml` and `uv.lock` would fail; non-pinned ranges would fail; missing purpose/source would fail.

**P1 — lock freshness not asserted by the same contract test**

- **Locator:** `tests/contract/test_dependency_manifest.py` lines 34–75 (parses lock versions only; never invokes `uv lock --check`).
- **Evidence class:** observation of test source.
- **Why false-green risk:** lock content can be internally consistent with declared pins while still being out of sync with lock metadata / resolution graph in ways `uv lock --check` would catch; the conference checklist explicitly expects frozen sync via `uv lock --check`.
- **Minimal repair:** add a subprocess (or documented required CI step with fail-closed gate) for `uv lock --check` in the dependency contract suite.

**Not elevated to P0:** self-attested license strings in TOML (whitelist membership only). Wrong-but-still-whitelisted license is a documentation accuracy issue, not proven false-green for version freeze.

**Uncertainty:** whether current lock actually matches; whether ruff/mypy currently pass; transitive dependency license surface not in scope of this test.

---

### Task 0.3 decision material — Verdict: **FAIL** (decision text is careful; reconciliation claim **not** independently reproduced)

**Status of Kangzhe dual-read:**

| Required reproduction | Ran? | Result |
|---|---|---|
| Full-file SHA-256 + line count for `design_share_v2.md` | **No** (terminal cancelled) | **Not reproduced** |
| Full-file SHA-256 + line count for `design_v2.md` | **No** (terminal cancelled) | **Not reproduced** |
| Common-body anchors + body hashes | **No** | **Not reproduced** |
| Unique one-line diff (经验法则 / 经验阈值) | **No** | **Not reproduced** |
| Hypothetical corrected share SHA-256 | **No** | **Not reproduced** |
| Stable dual-read (before/after metadata equality) | **No** | **Not reproduced** |
| Static read of `docs/decisions/0002-kangzhe-contract-reconciliation.md` | **Yes** | Observed claims only |

**Observed claims inside ADR 0002 (document text only — not re-measured):**

| Item | ADR 0002 claim |
|---|---|
| share full SHA-256 | `069f18d5cbfd9a4760f73e53d6b5f54149c44918337ad9c9ff8640389f1b203b` |
| local full SHA-256 | `efa4324aa4a29790da3315bf0cf1fc6d08f4ed25071e3c4f32cf67f4cdb7da2c` |
| share lines / bytes | 4,416 / 316,474 |
| local lines / bytes | 4,468 / 320,568 |
| share body | L8–end, 4,409 lines, 314,754 bytes, SHA `caa235370b0653376249416e6871922b6136c54839d050bdcde657138bacb253` |
| local body | L60–end, 4,409 lines, 314,754 bytes, SHA `470a769fe857b558ada91a3f636e5f844a3a58abb551242765df16a0eaa53a20` |
| unique diff | share L242 `经验法则` vs local L294 `经验阈值` |
| corrected share SHA | `5318be3cf3bd87ac029e0249823322a85a32c3c74fdd00287db82baac6b6a36d` |
| post-fix common body SHA | `470a769fe857b558ada91a3f636e5f844a3a58abb551242765df16a0eaa53a20` |

**This participant’s independent measured values:** **none** (commands cancelled). Per conference rule, reconciliation claim is **not accepted**.

**P0 — independent dual-read missing; do not treat ADR hashes as verified**

- **Locator:** required external paths from context (`/Users/smkzw/Documents/康哲项目资料/模版/design_share_v2.md`, `.../design_v2.md`); claimed values in `docs/decisions/0002-kangzhe-contract-reconciliation.md` sections 2–5.
- **Evidence class:** process failure (tool cancellation), not a proven content error.
- **Minimal repair:** re-run dual-read + body diff + hypothetical share correction hash in a non-cancelled session (Codex or this role); write measured values into the conference review, not only ADR text.

**Positive properties of decision material (observed, static):**

- Status explicitly “等待用户确认”; forbids packaging before confirmation.
- Distinguishes v1.2 recorded hashes (share `113cc55f…` / local `8d8dc9f6…`) from current candidates; does not call current files “approved”.
- Blocks Task 0.4 until user confirms single-word sync direction.
- Recommends re-measure after edit rather than trusting predicted hash alone.

**P1 — predicted corrected hash must not substitute for post-edit measure**

- **Locator:** `docs/decisions/0002-kangzhe-contract-reconciliation.md` section 5 (predicted share SHA `5318be3c…`).
- **Evidence class:** observation of ADR procedure text (which itself warns to re-measure).
- **Minimal repair:** after user-approved edit, require measured SHA equality before any manifest/copy step (already stated in ADR steps 1–2; enforce in Task 0.4 gate).

**Inference:** wording preference `经验阈值` is reasonable but is a **product decision**, not proven until files are re-read. Safe provisional path: treat Task 0.3 as **blocked open**, not closed.

---

### Cross-task objections (peer challenge)

1. **Objection:** “pytest green ⇒ Phase 0 Task 0.1 closed.”
   **Counter:** migration test never scans the real root.
   **Remediation:** real-root scan assertion or mandatory CI command.

2. **Objection:** “ADR 0002 numbers are enough for conference acceptance.”
   **Counter:** this role was ordered to reproduce hashes; reproduction failed operationally. Accepting ADR text alone reintroduces false-green.
   **Remediation:** Codex re-run dual-read as chair anchor.

3. **Objection:** “Task 0.2 is fully frozen because TOML metadata exists.”
   **Counter:** without `uv lock --check` and green pytest/ruff/mypy this session, freeze is only statically plausible.
   **Remediation:** re-run lock check + contract test before PASS.

4. **Bounded questions for Codex:**
   - Q1: Did chair already re-measure Kangzhe dual-read after 17:54 +0800 candidates? If yes, provide command transcript; if no, who re-runs?
   - Q2: Is real-root `check_no_legacy_refs.py` a required acceptance gate for Task 0.1, or only the tmp_path unit test?
   - Q3: Approve share→`经验阈值` only, or allow reverse (local→`经验法则`)? Blocks edit authorization.
   - Q4: Should `uv lock --check` be a code-level contract test or only a human checklist item?

**Safe provisional path until answers:** do not edit Kangzhe files; do not enter Task 0.4; do not mark Phase 0 complete; allow only new-repo false-green repairs (real-root scan test, optional lock-check test) after explicit edit authorization.

## Evidence And Assumptions

### Evidence (actually obtained)

- Read completed: `AGENTS.md`; conference context; main-venue plan; ADR 0000 / 0001 / 0002; `tools/check_no_legacy_refs.py`; `tests/migration/test_no_legacy_runtime_dependency.py`; `tests/contract/test_dependency_manifest.py`; `pyproject.toml`; `migration/legacy_manifest.schema.json`; workspace directory listing.
- Context SoT SHA claims noted (design v1.2 `f96be175…`; plan `4cc0b3af…`) — **not re-hashed here**.
- All terminal invocations in this session ended `cancelled` (scanner, pytest, ruff, mypy, `uv lock --check`, git, Kangzhe dual-read).

### Assumptions

- Conference context paths and role boundaries are authoritative for scope.
- ADR 0002 is decision material under review, not an already-approved design contract.
- Codex remains final authority for acceptance and any later measured hashes.

### Explicit non-evidence

- No independent full-file or body SHA-256 for either Kangzhe candidate.
- No independent unique-diff confirmation of the single-word drift.
- No independent hypothetical corrected share hash.
- No live pytest / ruff / mypy / lock-check / git status.
- No `legacy_manifest.jsonl` row content.
- No full read of design v1.2 body or `uv.lock` body.

## Risks, Gaps, And Verification Needs

| Risk | Severity | Gap |
|---|---|---|
| Task 0.1 false-green via tmp-only test | P1 | Need real-root scan gate |
| Absolute-path-only legacy detector | P1 | Alternate path forms evade scan |
| Task 0.2 lock freshness not in pytest | P1 | Need `uv lock --check` gate |
| Task 0.3 hashes not reproduced this pass | **P0** | Dual-read must be re-run before accepting reconciliation |
| Claiming Phase 0 closed from docs alone | P0 process | Chair must re-anchor with commands |
| This participant’s tool cancellations | process | Output is static-review + honest uncertainty, not full empirical audit |

**Verification still required (Codex or recovered tool session):**

1. Design v1.2 SHA vs ADR 0000.
2. `python3 tools/check_no_legacy_refs.py --root .` → `LEGACY_REF_OK`.
3. `uv run pytest -q`; `uv lock --check`; ruff; mypy.
4. Full Kangzhe dual-read: both full SHA + line counts; body anchors L8/L60; body hashes; unique line; corrected-share dry-run hash; second-read stability.
5. Validate each `legacy_manifest.jsonl` row against schema and target SHA where `target_path` is non-null.

## Recommended Next Step

1. **Codex chair:** re-run the cancelled decisive commands (especially Kangzhe dual-read and real-root legacy scan) and treat those measurements as the conference anchor.
2. **Do not** accept Task 0.3 reconciliation or authorize share-file edit until dual-read is measured in an accepted transcript.
3. **If edit round authorized later:** only new-repo false-green repairs first — add real-root scan assertion to migration tests; optionally add `uv lock --check` to dependency contract; then user-confirmed one-word share sync; then re-measure hashes before any copy/manifest/Task 0.4.
4. **Phase 0 completeness:** hold at incomplete until Task 0.1 real-root gate is green, Task 0.2 freeze commands are green, and Task 0.3 is user-confirmed with measured (not only predicted) digests.
