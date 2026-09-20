# Codex Execution Review: ci-r2-bc-research-package-wiring-20260905

## Verdict

Accepted after selective integration and Codex repair. This accepts the bounded
execution pass, not R2, R3, RC, or release.

## Worker Outputs

- `worker_01`: rejected wholesale. Its generic package persisted a
  caller-supplied `decision="passed"`, crossing the deterministic gate trust
  boundary. Codex retained only the useful design insight that evidence
  ingestion must be idempotent and review-time anchored.
- `worker_02`: accepted selectively, then repaired. The B typed package,
  GateSpec projection, and immutable snapshot code were retained. Codex added
  a science-bound portal projection, removed caller `gate_status`, allowed
  legitimate single-arm core evidence without inventing control, and wired the
  real RunService sequence.
- `worker_03`: accepted selectively, then repaired. The C typed package and
  snapshot projection were retained. Codex required endpoint plus timepoint,
  prohibited self-review, derived shared atomic facts, and wired RunService.

## Manager Assessment

No separate execution manager was declared by the live route. Codex performed
the required manager disposition directly and did not merge an isolated clone
wholesale.

## Hermes Workflow Disposition

The Hermes workflow guard selected and audited the live ZCode execution route;
Hermes itself was not a transport or substitute model for this packet. All
three declared worker commands completed with matching route identity.

## Codex Independent Verification

- Added `fresh_research_ingestion.py`: sources, fragments, facts, claims,
  receipts, and evidence snapshots only; no gate row is accepted from callers.
- Added stable primitive facade and B/C canonical package discovery.
- B/C actual order is now source package -> evidence ingestion -> deterministic
  gate -> immutable report snapshot -> accepted independent QC binding ->
  analysis -> candidate render.
- B portal values and typed fact views are equality-bound; prelocked B/C report
  snapshot identities are reopened and verified by renderers.
- Focused B/C/project integration: 54 passed.
- Full development gate: Ruff passed; strict mypy passed for 200 source files;
  882 unit/contract tests passed; forbidden legacy-reference scan passed.
- Browser/scientific final acceptance remains separate and pending.

## Cleanup Decision

Archive the governed execution process after `review-gate` and
`audit-execution` pass. Remove only the three exact temporary APFS clones after
archive evidence is secured. Preserve worker reports and this review.
