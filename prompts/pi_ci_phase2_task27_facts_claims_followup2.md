你正在继续 Task 2.7 的同一只读验收 session，执行第二次也是最后一次定向复核。不要重启广泛探索，不要修改文件。

Hard boundaries:
- 仅在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 内工作。
- Runner-managed output path: `runs/pi_ci_phase2_task27_facts_claims_followup2.md`. Never write this file; return the complete report in the final response.
- 禁止修改任何文件。

Read these files only:
- `src/ci_workflow/domain/facts.py`
- `src/ci_workflow/capabilities/resolution.py`
- `schemas/fact.schema.json`
- `tests/integration/test_source_to_claim_chain.py`
- `tests/integration/test_conflicts_preserved.py`

Codex 已修复上一轮 P2-A/P2-B/P2-C。请逐项复核：
1. `reported_zero` 的规范值只有数值 0/0.0/null 可接受，字符串 "0" 与布尔值拒绝，且 schema 与 Pydantic 一致。
2. `not_reported`/`not_publicly_disclosed` 的全角数值（如 `５０％`）同时被 Pydantic 和 schema 拒绝，“结果未报告”仍接受。
3. 确定性计算同时满足：正常有符号句通过；含正确值和 -9.9 矛盾值拒绝；“试验组下降 2.1 分，安慰剂组下降 0.8 分，组间差为 1.3 分”通过且底层复算仍保存 -1.3；不一致方向或无关幅度不能借方向词绕过。

真实运行：
- `uv run pytest tests/integration/test_source_to_claim_chain.py tests/integration/test_conflicts_preserved.py -q`
- `uv run pytest -q`
- `uv run ruff check src tests`
- `uv run mypy --strict src`
- `uv run ci-workflow package verify --root .`
- `git diff --check`

输出：`# Task 2.7 最终同 session 修复复核`，给结论 PASS/FAIL、P0/P1/P2 数量、运行证据、三项逐条结果、新缺陷和后续边界。PASS 必须机械检查真实通过且 P0/P1/P2=0；若仍有缺陷，给最小可复现输入。
