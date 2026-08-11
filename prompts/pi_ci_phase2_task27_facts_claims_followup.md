你正在继续 Task 2.7 的同一只读验收 session。Codex 已将你首轮报告的 6 个 P2 全部转成反例并修复。不要重启广泛探索，不要修改文件。

Hard boundaries:
- 仅在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 内工作。
- Runner-managed output path: `runs/pi_ci_phase2_task27_facts_claims_followup.md`. Never write this file; return the complete report in the final response.
- 禁止修改任何文件。

Read these files only:
- `src/ci_workflow/domain/facts.py`
- `src/ci_workflow/domain/claims.py`
- `src/ci_workflow/capabilities/extraction_normalization.py`
- `src/ci_workflow/capabilities/resolution.py`
- `schemas/fact.schema.json`
- `schemas/claim.schema.json`
- `tests/integration/test_source_to_claim_chain.py`
- `tests/integration/test_conflicts_preserved.py`

请逐项复核首轮 P2-1 至 P2-6：
1. schema 拒绝时间点/时间窗均空、已报告状态无原文、零值矛盾和未报告状态数值型原文；Pydantic 与 schema 的可机械跨字段规则是否一致。
2. 已规范化事实重复应用完全相同规则是否直接幂等；同规则版本产生不同结果是否拒绝；新规则版本仍可形成新版本链。
3. 计算声明同时含正确结果和矛盾数值是否拒绝；正常声明与同时列示治疗组、对照组、组间差的合法句子是否不误伤。
4. `review_state` 是否已从科学事实版本身份排除。
5. Claim 模型和 schema 是否都明确要求支持事实链接在声明生成时为 accepted，且 synthesis 文字前缀在模型层也强制。
6. `not_reported`/`not_publicly_disclosed` 是否拒绝数值型原文，同时允许“结果未报告”这类真实原文。

真实运行：
- `uv run pytest tests/integration/test_source_to_claim_chain.py tests/integration/test_conflicts_preserved.py -q`
- `uv run pytest -q`
- `uv run ruff check src tests`
- `uv run mypy --strict src`
- `uv run ci-workflow package verify --root .`
- `git diff --check`

输出：`# Task 2.7 同 session 修复复核`，随后给结论 PASS/FAIL、P0/P1/P2 数量、运行证据、六项逐条结果、新缺陷、仍属后续阶段的边界。PASS 必须机械检查真实通过且 P0/P1/P2=0；若仍有缺陷，给最小可复现输入与最小修复建议。
