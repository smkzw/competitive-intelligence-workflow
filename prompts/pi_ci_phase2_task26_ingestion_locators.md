You are Hermes running inside a Codex-controlled workflow.

First, fully read and comply with `/Users/smkzw/.hermes/SOUL.md`. In your output, include one sentence saying whether you read the full file. Do not claim this unless you actually read it.

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Do not read or modify production paths.
- Do not edit files unless Codex explicitly authorizes an edit round.
    - Tools are available and must not be disabled. Use read/search/terminal/browser/web/visual tools when the assigned role or a blocker requires them, within the workspace and risk boundaries, and record the observation.
    - Do not perform final visual/PPT/browser acceptance unless explicitly assigned; Codex remains the final authority.
- Runner-managed output path: `runs/pi_ci_phase2_task26_ingestion_locators.md`. Never invoke a
  write/edit tool on this report path; return the complete report in your final
  response and let the runner persist it.

Read these files only:
- `context/ci_phase2_task26_ingestion_locators_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `docs/decisions/0009-version-bound-clinical-source-locators.md`
- `.trellis/tasks/08-11-phase-2-universe-source-truth/prd.md`
- `.trellis/tasks/08-11-phase-2-universe-source-truth/design.md`
- `.trellis/tasks/08-11-phase-2-universe-source-truth/implement.md`
- `src/ci_workflow/domain/evidence.py`
- `src/ci_workflow/domain/ids.py`
- `src/ci_workflow/ingestion/classifier.py`
- `src/ci_workflow/ingestion/fragmenter.py`
- `src/ci_workflow/ingestion/locators.py`
- `schemas/source-version.schema.json`
- `schemas/evidence-fragment.schema.json`
- `schemas/guideline-basis.schema.json`
- `package-manifest.json`
- `tests/unit/test_source_classifier.py`
- `tests/integration/test_fragment_locators.py`
- `tests/integration/test_source_version_chain.py`
- `tests/integration/sources/test_regulators.py`
- `docs/acceptance/runs/task-2.6/red.txt`
- `docs/acceptance/runs/task-2.6/green.txt`

Task:
以独立只读验收者身份验收 Task 2.6。逐行核对批准合同、ADR、实现、schema 和测试，并真实运行：

1. `uv run pytest tests/unit/test_source_classifier.py tests/integration/test_fragment_locators.py -q`
2. `uv run pytest -q`
3. `uv run ruff check src tests`
4. `uv run mypy --strict src`
5. `uv run ci-workflow package verify --root .`
6. `git diff --check` 与 `git status --short`

对抗检查：未知自动文件是否会被猜成已分类；supplement 无父文档是否失败；手工收件文件是否保留原文件名；规范文件名是否由稳定身份/中文角色/版本/摘要生成；内容相同的用户副本是否保留相同摘要但独立文档/版本身份；登记 JSON 是否精确处理数组路径且外部字典修改不影响快照；网页同名标题是否靠出现次序精确区分；PDF 是否按页/表/行/列定位且同页重复数值不会错引；所有定位器是否绑定 source_version_id 和内容摘要并拒绝跨版本；EvidenceLocator Pydantic 与三个 schema 是否同步；任何无法重开的数值是否仍可能绕过进入事实层。禁止编辑，只报告证据、严重度和最小修复建议。

Output schema:
1. `# Task 2.6 独立验收`
2. `## 结论`：PASS 或 FAIL，给出 P0/P1/P2 数量
3. `## 运行与读取证据`
4. `## 分类与用户文件攻击`
5. `## 登记、网页和 PDF 定位攻击`
6. `## 共享合同攻击`
7. `## 缺陷`
8. `## Codex 仍需确认`

Quality gates:
- Do not claim access to sources not listed in the context.
- Do not make final clinical/regulatory/visual/current-web claims.
- PASS 必须机械检查真实通过且 P0/P1=0；文件存在或已有 green 不是验收证据。
- 明确区分结构定位合同与后续真实 HTML/PDF 抽取、Task 2.7 事实/声明链，不因后续任务未实现而误判，也不能替后续任务提前接受。
- 优先指出会造成数值错引、来源版本错配、用户补件丢失或无法回到原文的缺陷。
