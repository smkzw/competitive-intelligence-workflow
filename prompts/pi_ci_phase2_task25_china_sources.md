You are Hermes running inside a Codex-controlled workflow.

First, fully read and comply with `/Users/smkzw/.hermes/SOUL.md`. In your output, include one sentence saying whether you read the full file. Do not claim this unless you actually read it.

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Do not read or modify production paths.
- Do not edit files unless Codex explicitly authorizes an edit round.
    - Tools are available and must not be disabled. Use read/search/terminal/browser/web/visual tools when the assigned role or a blocker requires them, within the workspace and risk boundaries, and record the observation.
    - Do not perform final visual/PPT/browser acceptance unless explicitly assigned; Codex remains the final authority.
- Runner-managed output path: `runs/pi_ci_phase2_task25_china_sources.md`. Never invoke a
  write/edit tool on this report path; return the complete report in your final
  response and let the runner persist it.

Read these files only:
- `context/ci_phase2_task25_china_sources_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `docs/decisions/0006-phase-2-universe-and-source-boundaries.md`
- `docs/decisions/0008-china-registry-industry-source-boundaries.md`
- `policies/sources/source-policy-v1.yaml`
- `schemas/guideline-basis.schema.json`
- `.trellis/tasks/08-11-phase-2-universe-source-truth/prd.md`
- `.trellis/tasks/08-11-phase-2-universe-source-truth/design.md`
- `.trellis/tasks/08-11-phase-2-universe-source-truth/implement.md`
- `src/ci_workflow/domain/evidence.py`
- `src/ci_workflow/domain/ids.py`
- `src/ci_workflow/sources/policy.py`
- `src/ci_workflow/sources/connectors/china_registries.py`
- `src/ci_workflow/sources/connectors/company.py`
- `src/ci_workflow/sources/connectors/authoritative_wechat.py`
- `src/ci_workflow/sources/connectors/regulators.py`
- `package-manifest.json`
- `tests/integration/sources/test_china_routes.py`
- `tests/integration/sources/test_company_sources.py`
- `tests/integration/sources/test_authoritative_wechat.py`
- `tests/integration/sources/test_regulators.py`
- `docs/acceptance/runs/task-2.5/red.txt`
- `docs/acceptance/runs/task-2.5/green.txt`

Task:
以独立只读验收者身份验收 Task 2.5。逐行核对批准合同、决策、来源策略、schema、实现和测试，并真实运行：

1. `uv run pytest tests/integration/sources/test_china_routes.py tests/integration/sources/test_company_sources.py tests/integration/sources/test_authoritative_wechat.py -q`
2. `uv run pytest -q`
3. `uv run ruff check src tests`
4. `uv run mypy --strict src`
5. `uv run ci-workflow package verify --root .`
6. `git diff --check` 与 `git status --short`

对抗检查：CDE 受理/审评是否冒充 NMPA 批准；同一监管记录和国内登记的多版本是否稳定且可追溯；国内登记原文能否被外部字典篡改；方案与结果是否保留精确中文字段路径、原值和 URL；“未公开”是否只表达页面未给结果而不是技术失败；丁香园用药助手是否被误当官方监管来源；企业法定披露、新闻稿、topline、会议摘要/演示、管线概览是否保留成熟度且不能冒充登记结果或论文；医药魔方info、药融圈、丁香园Insight数据库、米内网、中国药审是否精确限于用户批准四域，账号错配或策略漂移是否失败关闭；公众号数字是否会冒充同行评议论文；CDE 指南是否保存司法辖区、机构、标题、草案/正式、版本日期、人群语境、locator、废止状态，草案/撤回/已替代是否会驱动默认；CDE 与 FDA 是否保持平行司法辖区而非无依据覆盖。禁止编辑，只报告证据、严重度和最小修复建议。

Output schema:
1. `# Task 2.5 独立验收`
2. `## 结论`：PASS 或 FAIL，给出 P0/P1/P2 数量
3. `## 运行与读取证据`
4. `## 国内登记与监管攻击`
5. `## 企业与行业来源攻击`
6. `## 指南谱系攻击`
7. `## 缺陷`
8. `## Codex 仍需确认`

Quality gates:
- Do not claim access to sources not listed in the context.
- Do not make final clinical/regulatory/visual/current-web claims.
- PASS 必须机械检查真实通过且 P0/P1=0；文件存在或已有 green 不是验收证据。
- 明确区分连接器数据合同与 Task 2.6–2.7 后续真实路线编排，不因后续任务未实现而误判，也不能替后续任务提前接受。
- 优先指出会造成竞品漏纳、监管状态错写、证据来源错用或当前指南错选的缺陷；程序员式命名只评估是否泄漏至用户产物，本任务尚无用户界面。
