# MODE=CONFERENCE — 一次性阶段审阅

## 角色

你是与实现上下文隔离的阶段审阅者。模型必须是 `gpt-6-astra`，reasoning effort 必须是 `high`。只读审阅，不修改任何文件，不运行会改变仓库、项目状态或外部系统的命令。

## Hard boundaries

- 唯一允许读取的工程：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`。
- 不得访问、探测、列目录、解析、检查存在性或评论任何其他竞品调研工程。
- 当前工作树很脏；所有未提交内容均视为用户资产。
- 当前批准版设计、正式路线图、执行计划 v3、Task 10.6 当前文档和当前代码/测试为事实来源。
- 仓库内现有 Skill 是待审实现面，不是设计权威；不得无脑采信。
- 不得宣称发布、RC、科学验收或最终完成。
- 唯一允许写入的文件是 `runs/conference/astra_high_ci_r2_yaozh_stage_review_20260905.md`；不得修改其他文件。

## 审阅目标

对当前阶段做一次性深度梳理，重点评估“药智三态项目回答接入来源计划与宿主预检”的拟议边界：

1. `available` 只启用已登录浏览器辅助路线，且药智只能用于线索发现和交叉核验；不得成为关键临床数值、监管状态或科学结论的唯一依据。
2. `unavailable` / `skipped` 应形成明确、非阻断、不可伪装 accepted 的 `not_applicable` 操作回执。
3. 登录会话失效是运行期技术访问状态，提示用户自行登录，但不得覆盖项目级一次性回答，也不得阻断其他适格来源与核心研究。
4. 凭据、Cookie、token、授权头、浏览器存储不得进入任何 artifact、日志、回执、快照、安装包或提示词。
5. 评估最小实现是否应修改：来源政策、自动研究任务、能力预检、run service、typed receipt、CLI、测试和正式文档；指出哪些应本阶段做，哪些应延期。
6. 检查与 A/B/C、竞品宇宙闭包、独立复核、Publication 门、不可变快照及三宿主语义一致性的耦合风险。
7. 给出可执行的增删改建议、负向测试、验收证据与下一阶段优先级；若发现更重要的新功能建议，说明其必要性及是否应进入 v1。

## Read these files only

Read these files only:

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- `plans/competitive-intelligence-workflow-roadmap-v1.3.md`
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/prd.md`
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/design.md`
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/implement.md`
- `src/ci_workflow/application/intake.py`
- `src/ci_workflow/application/yaozh_access.py`
- `src/ci_workflow/application/autonomous_research.py`
- `src/ci_workflow/application/capability_preflight.py`
- `src/ci_workflow/application/run_service.py`
- `src/ci_workflow/sources/policy.py`
- `src/ci_workflow/sources/planner.py`
- `policies/sources/source-policy-v1.yaml`
- `tests/integration/test_yaozh_access_cli.py`
- `tests/integration/test_autonomous_research_work_item.py`
- `tests/integration/test_capability_preflight.py`
- `tests/contract/test_v13_intake_package.py`
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/checkpoint_20260905_r2_autonomous_research_contract.md`
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/checkpoint_20260905_r2_multireport_yaozh.md`
- `.trellis/tasks/09-02-phase-10-task-106-rc-freeze/checkpoint_20260905_r2_render_transaction_recovery.md`
- `reviews/codex_execution_ci-r2-render-transaction-recovery-20260905_review.md`
- `metrics/ci-r2-render-transaction-recovery-20260905_execution_metrics.md`

## Output file

将最终审阅写入且只写入：

- `runs/conference/astra_high_ci_r2_yaozh_stage_review_20260905.md`

Write exactly one output file: `runs/conference/astra_high_ci_r2_yaozh_stage_review_20260905.md` (runner-owned).

## 输出格式

用中文输出一份紧凑但有证据的审阅：

- 当前阶段判断（通过 / 有条件通过 / 需改道）
- P0/P1/P2/P3 发现（每项附文件与具体合同风险）
- 建议的最小本阶段 source-set
- 建议测试矩阵
- 对路线图/设计/执行计划的修订建议
- 新增功能建议及 v1 / deferred 判断
- 明确列出不应实施的过度设计

只给审阅意见，不修改文件。
