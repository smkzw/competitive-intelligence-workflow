# Metrics: ci_phase0_renderer_boundary_review_20260811

Date: 2026-08-11

| Field | Value |
|---|---|
| Task type | `high_risk_contradiction_review` |
| Risk | `high` |
| Declared route | `codex-subagent/codex/gpt-5.6-luna:max` |
| Native capability result | rejected: `Unknown model gpt-5.6-luna` |
| Effective adapter | ChatGPT bundled Codex CLI compatibility |
| Effective provider/model | `codex` / `gpt-5.6-luna` |
| Effective effort | `max` |
| Session id | `019fee44-1f71-7820-b0da-b075c930af27` |
| Duration | 约 10 分钟（Luna 首轮复核、修复后同会话复核；不含上游 S1 等待） |
| Recovery | same-session follow-up after actionable FAIL |
| First verdict | `FAIL` with 2 P1 |
| Final verdict | `PASS` after 2 P1 repairs |
| Fallback used | none beyond required native-to-CLI adapter transition |
| Result scope | renderer boundary only; Task 0.3 and Phase 0 remain open |

## Mechanical Evidence

- `uv run pytest -q` -> 6 passed.
- `uv run ruff check tools tests` -> passed.
- `uv run mypy tools/check_no_legacy_refs.py tests/migration tests/contract` -> passed.
- `uv run python tools/check_no_legacy_refs.py` -> `LEGACY_REF_OK`.
- `uv lock --check` -> passed.
- `git diff --check` -> passed.
- `contracts/kangzhe` -> absent.
- Approved v1.2 spec diff -> none.

## Cleanup

守卫初始化但未实际派发的 Pi/Grok 提示、空白结果、会商壳和占位指标已删除；只保留真实 Luna 提示、结果、上下文、复核和指标。
