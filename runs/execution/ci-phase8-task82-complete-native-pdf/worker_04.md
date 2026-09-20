I'll start by reading the assigned execution context and plan, then proceed only on the authorized Task 8.2 verification work.Next I'll inspect the existing PDF native stack, verification tooling, and any current A/B/C PDF artifacts so I can implement shared coverage pieces and run the assigned checks.The worker scout failed, so I'll read the PDF native modules and current verification artifacts directly.Shared layout already exists in `_layout.py`; next I’ll extract charts/tables/bookmarks/coverage, add `verify_pdf`, and run full-page checks on the three current PDFs.Implementing shared modules and the verification utility next, keeping `_layout.py` as a compatibility re-export so A/B/C builders stay stable.Creating the shared PDF modules and verification tooling now.Running PDF09 tests and full A/B/C verification next.Verification found coverage gaps. Next I’ll confirm the CLI exit code and spot-check rendered pages for additional visual defects.# Execution Output: ci-phase8-task82-complete-native-pdf - worker_04

## Boundary And Context Check
- Read `context/ci-phase8-task82-complete-native-pdf_execution_context.md`, `plans/codex_execution_ci-phase8-task82-complete-native-pdf.md`, Trellis Task 8.2 PRD/design/implement, `track_pdf.md`, peer worker_01–03 outputs, locked `three-report-complete`, and current A/B/C PDFs under `.artifacts/pdf-complete/`.
- Assigned item only: shared charts/tables/bookmarks + coverage projection; full-page `pypdf`/`pdftotext`/`pdftoppm` verification; **report defects only**.
- Writes stayed inside authorized paths: `src/ci_workflow/renderers/pdf_native/`, `tools/verify_pdf.py`, `tests/pdf/`, `.artifacts/pdf-complete/`, `docs/acceptance/runs/8.2/`.
- Did **not** rewrite A/B/C report projection content to force green coverage.
- Did **not** claim final visual/PDF/clinical acceptance; Codex remains authority.
- Did **not** write `runs/execution/.../worker_04.md` (runner-owned).

## Work Performed
1. Extracted shared PDF09 surfaces from temporary `_layout.py`:
   - `src/ci_workflow/renderers/pdf_native/charts.py`
   - `src/ci_workflow/renderers/pdf_native/tables.py` (incl. `续表`)
   - `src/ci_workflow/renderers/pdf_native/bookmarks.py`
   - `src/ci_workflow/renderers/pdf_native/coverage.py` (PageRegistry ↔ PDF text/bookmark projection)
2. Kept `projections/_layout.py` as a compatibility facade so A/B/C builders keep importing the same names.
3. Added `tools/verify_pdf.py` (report-only verifier) with Poppler path resolution for the runtime native `pdftotext`.
4. Added `tests/pdf/test_pdf09_shared_coverage.py`.
5. Ran full verification on current A/B/C PDFs and inventoried machine + visual defects **without mutating PDFs**.

## Artifacts And Evidence
| Artifact | Note |
|---|---|
| `src/ci_workflow/renderers/pdf_native/charts.py` | bar/forest/line/heatmap/bubble |
| `src/ci_workflow/renderers/pdf_native/tables.py` | styled + continuation tables |
| `src/ci_workflow/renderers/pdf_native/bookmarks.py` | outline helper |
| `src/ci_workflow/renderers/pdf_native/coverage.py` | coverage projection + defect flatten |
| `tools/verify_pdf.py` | pypdf/pdftotext/pdftoppm CLI |
| `tests/pdf/test_pdf09_shared_coverage.py` | PDF09 exact nodes |
| `docs/acceptance/runs/8.2/verification/` | summary/defects/renders/text dumps |
| `.artifacts/pdf-complete/coverage/{A,B,C}.json` | per-report projection snapshots |
| `.artifacts/pdf-complete/verification/defects_all.json` | machine+visual combined |

**Current PDFs verified (unchanged by this worker):**
- A `ebc2530c…` · 12 pages · 10 bookmarks
- B `f57064df…` · 30 pages · 18 bookmarks
- C `820058e2…` · 21 pages · 16 bookmarks · **coverage OK**

### Defects only (no content rewrite)
**Coverage (machine, exit=1):**
1. `COV-A-MISSING-historical-edge`
2. `COV-A-MISSING-evidence-limitations`
3. `COV-B-MISSING-trial-exposure-context`
4. `COV-B-MISSING-subgroups-supporting-evidence`
5. `COV-B-MISSING-evidence-limitations`

**Visual (sampled current renders @120 DPI):**
1. `VIS-A-09-SPARSE` — landscape page almost empty (“安全性” only)
2. `VIS-A-10-HEATMAP-OVERLAP` — safety heatmap Chinese labels collide
3. `VIS-B-09-BUBBLE-OVERLAP` — matrix bubble labels/mapping note overlap + sparse plot
4. `VIS-B-12-SPARSE` — disease-context page mostly whitespace under `未公开` rows
5. `VIS-C-08-ENDPOINT-OVERLAP` — endpoint matrix chart labels collide + sparse lower half

**Evidence:** C coverage 12/12; A 10/12; B 18/21. All three have searchable Chinese, bookmarks, page numbers, and at least one `续表`. No forbidden audience markers (`snapshot-` / `v-fixture`) in extracted text.

## Commands And Observations
```text
uv run pytest tests/pdf/test_pdf09_shared_coverage.py tests/pdf/test_report_{a,b,c}_pdf.py -q
→ 16 passed

uv run python tools/verify_pdf.py --artifacts .artifacts/pdf-complete \
  --output-dir docs/acceptance/runs/8.2/verification --dpi 120
→ EXIT 1 (defects present)
  pdftotext: .../native/poppler/poppler/bin/pdftotext
  pdftoppm:  .../bin/override/pdftoppm
  renders: A12 / B30 / C21

uv run pytest tests/acceptance/test_native_pdf_slice.py -q
→ 3 failed: shutil.which("pdftotext") is None (PATH lacks override shim)
```

- Observation: Poppler `pdftotext` exists in runtime native bin, but no `bin/override/pdftotext` shim; `verify_pdf.py` resolves it explicitly.
- Inference: A/B coverage holes are missing projection sections, not verifier false negatives (source bookmarks/text lack those responsibilities).
- Uncertainty: whether B disease-context sparsity is acceptable disclosure-preserving emptiness vs density failure — reported as medium visual defect for Codex.

## Blockers Or Missing Environment
1. **PATH `pdftotext` shim missing** for tests that use `shutil.which` only.  
   Minimal remediation (no package install): add override shim like `pdftoppm`, or prepend  
   `~/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin` to PATH.
2. **Content gaps in A/B projections** block coverage green; worker_04 did not patch them (report-only rule). Needs worker_02 (or Codex-authorized follow-up) to add:
   - A: `historical-edge`, `evidence-limitations`
   - B: `trial-exposure-context`, `subgroups-supporting-evidence`, `evidence-limitations`
3. **Chart label collision / sparse pages** need projection/layout fixes by A/B/C owners; not silently “fixed” here.
4. Question for Codex: accept current verifier+defect inventory as worker_04 complete, and open a targeted fix pass for the 5 coverage misses + high-severity visual overlaps?

## Rerun Requests Or Next Step
- Worker_04 PDF09 shared surface + verification tooling is ready for Codex review.
- Next: Codex-directed A/B (and C chart) content fixes → re-run  
  `uv run python tools/verify_pdf.py --artifacts .artifacts/pdf-complete --output-dir docs/acceptance/runs/8.2/verification`
- Resume point: after missing page responsibilities and chart-overlap fixes are present in rebuilt A/B/C PDFs under `.artifacts/pdf-complete/`, re-verify; then Codex final page-by-page acceptance.
- Optional env fix before broader Task 8.1 acceptance re-run: expose `pdftotext` on PATH.
