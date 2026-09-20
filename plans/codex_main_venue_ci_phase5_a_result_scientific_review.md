# Codex Main-Venue Plan: ci_phase5_a_result_scientific_review

Date: 2026-08-27
Objective: 独立复核特应性皮炎A类报告重建候选的ClinicalTrials.gov结果覆盖、人数到发生率换算、组别语义及不得误报未公开；仅输出接受或拒绝及可执行缺口，不修改文件。

## Task Decomposition

1. Each participant independently reads the locked input, rebuilt candidate, manifest, validator and focused tests.
2. Reproduce deterministic counts and exact high-risk conversions; sample at least one outcome, one TEAE, one SAE, one common AE and one zero-denominator record against the embedded source JSON.
3. Challenge group-role and regimen preservation, fact locator binding and `未公开` semantics.
4. Return a binary scientific recommendation (`accepted` or `rejected`) with precise blocking defects. Do not edit files.

## Source Packet

- `context/ci_phase5_a_result_scientific_review_conference_context.md`
- `.artifacts/a-fresh-source/evidence/library/a-research-package.json`
- `.artifacts/a-atopic-dermatitis-rebuild/research-content.json`
- `.artifacts/a-atopic-dermatitis-rebuild/rebuild-manifest.json`
- `tools/rebuild_atopic_dermatitis_package.py`
- `src/ci_workflow/application/source_research_service.py`
- the two focused integration tests named in the context.

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_pi_antigravity` | `google-antigravity` | `gemini-3.7-flash` | `runs/conference/ci_phase5_a_result_scientific_review/general_pi_antigravity.md` |
| `general_grok46` | `grok-build` | `grok-4.6` | `runs/conference/ci_phase5_a_result_scientific_review/general_grok46.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Start: pending dispatch.
- Wait policy: one live route attempt per declared participant, runner hard wait up to 120 minutes; no fixed-interval controller polling.

## Codex Verification Checklist

- Independently rerun content validation and focused tests.
- Compare participant objections with raw embedded paths, not with another participant's confidence.
- Do not create `scientific_review` until every blocking scientific defect is resolved.
- Keep visual acceptance separate.
