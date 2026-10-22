# Rebaseline v2 M1: C-report service, bounded harness and real-source validation

## Goal

Implement the user-authorized rebaseline-v2 Web subsystem, starting with M1. Product authority is rebaseline-v2/docs/01_PRD.md; the dated ZIP is input, not permission for history rewriting or credential use.

## Requirements

- Preserve all v1 dirty files, paused projects, history and unknown untracked files; v1 is read-only reference.
- C: source-linked design precedents, endpoint/timepoint grouping, structured eligibility thresholds, verified-only numeric charts.
- Bounded tool output must remain recoverable, not silently truncated; stage recovery must not repeat successful work.
- Native Chinese expert-facing HTML with real ECharts and the corresponding table; desktop widths 1440/1600/1920/2560.
- No credentials, local absolute paths, raw research material or runtime logs in commits. No history cleanup, force push, deletion or v1 repairs.

## Acceptance Criteria

- [ ] Reproduce supplied 31-test baseline in isolated v2 environment.
- [ ] Root-cause RED family, coherent implementation, grouped regression and final v2 suite.
- [ ] Ordinary C renderer has timepoint/endpoint comparison and precise source access; no unverified sample size on axis.
- [ ] Real-source smoke and actual browser results recorded separately from ScriptedLLM tests.
- [ ] Real-LLM M1 requires configured authorized service, at least 10 real trial rows and source-backed critical fields; missing service is BLOCKED, not PASS.
- [ ] Replace concise v2 STATUS; explicit staged GitHub milestone with v1 changes excluded.

## Notes

- Latest v2 scope retires v1 report editing/sharing and host-package requirements for this subsystem, without deleting their historical implementation/evidence.
- ZIP SHA256: 5cad486b8b2ac7aea50fc074d9f223353d72d951f01f9d97677351d6d808a4c6.
