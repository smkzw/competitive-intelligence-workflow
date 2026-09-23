# W02 实施结果 — 通用入口与共享查询/ViewState

日期：2026-09-22。结论：**W02 代码与确定性相关批次通过；生产独立上下文能力失败关闭；产品、科学、视觉、宿主及 24 门户仍未验收。**

## 身份、边界与写入门

- 请求运行身份：`gpt-5.6-sol/medium`；本会话没有可核验 model/effort 运行时回执，因此身份记 **UNVERIFIED**。
- 工程根：英文工程；`HEAD=2df24bb441e555f20b233ad2011b4ffd3610655b`，实施前后未变化。
- 模式：execution，当前会话为唯一共享源码写入者；未派发子代理。
- 保留：W00/W01 与用户既有 tracked/untracked 改动未覆盖、回滚、格式化或删除；未执行 commit/push/add/reset/checkout/clean；未跑全 gate、24 门户或全视觉。

## 完成的可执行合同

1. **同一公开入口**：现有 `project create` 新增 `--request` 一句话模式；与 `--indication` 高级模式共同落入 `ProjectContract`。缺 `--reports` 时退出码 6 并输出机器可读 `ASK_REQUIRED`，A/B/C 解释完整；指定一种只建立该报告合同及分支。既有 `research submit` 继续以同一项目合同校验高级 research-package。
2. **显式 RunContext**：运行上下文公开并校验 `project_root/indication/reports/data_cutoff/source_input_paths`；跨项目、适应症、报告或截止日漂移失败关闭。没有读取 `/tmp/pnh-proj-path.txt`、隐藏 `TARGET_TRIALS` 或适应症特判。
3. **合并来源计划**：全球/中国/alias/target/company/trial 路线只在 `shared_source_route_ids` 出现一次；每个所选报告只有自己的 `analysis_route_id`。typed graph 继续作为现有控制合同，显式传递 `MergedSourcePlan/SharedExtractionSet/WorkspaceMembership/FacetPlan/NumericFrameEligibility`，未新增任务 DSL。
4. **药智一次询问**：继续复用项目级不可变回答；三个旅程均一次选择 `skipped`，共享计划不生成药智路线，核心研究不受其阻断。
5. **真实独立上下文探针**：生产 `RuntimeCapabilityProbe` 不再接受 `CI_WORKFLOW_INDEPENDENT_CONTEXT=yes/1` 作为证据。只有实际执行普通可执行文件并取得严格回执（不同 producer/reviewer context，机制限 native subagent / independent session / compatible executor）才可 ready。无探针、不可执行、失败、畸形或同上下文均阻断，并给出启用子Agent、独立会话或兼容执行器指引。`StaticCapabilityProbe` 仅用于测试注入。
6. **公共查询与 ViewState**：新增 `WorkspaceMembership`、`FacetPlan`、`NumericFrameEligibility`、`ReportQuery`、`ReportQueryResult`、`ReportViewState` 与 `VisualState`。强制 `Q=P∪U` 且 `P∩U=∅`；零命中保持零；图例隐藏与缩放只改变视觉状态；选中/下钻以同一 `fact_id` 绑定。现有 portal `select_view_rows` 已改为调用公共 typed query，A/B/C 均经同一消费者路径。
7. **C 完成条件**：改为完整可检索设计先例横比；明确单项有效研究即可使用，不强制多个设计路径。

## RED / GREEN

- 集中 RED：相关批次在实现前于测试收集阶段失败，首个决定性错误为 `ImportError: cannot import name 'FacetAssignment'`，证明公共查询/ViewState 合同尚不存在。
- 首轮实现 GREEN：`74 passed in 7.00s`。
- 扩展闭环时一次测试夹具编辑错误导致 `10 failed / 140 passed`（`_project()` 引用未定义变量）；这是新增测试自身问题，不是产品回归。修正后 `150 passed in 6.74s`。
- 最终合并 GREEN：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/contract/test_v13_intake_package.py \
  tests/integration/test_autonomous_research_work_item.py \
  tests/integration/test_capability_preflight.py \
  tests/integration/test_run_capability_execution_gate.py \
  tests/integration/test_cli_command_catalog.py \
  tests/integration/test_research_package_submission.py \
  tests/integration/test_project_run_cli.py \
  tests/graph/test_graph_node_contracts.py \
  tests/unit/reports/test_view_model.py \
  tests/unit/test_portal_filter_contracts.py -q --tb=short
176 passed in 7.45s
```

- `.venv/bin/ruff check <W02 changed source/tests>`：通过。
- `.venv/bin/mypy --strict <8 W02 source files>`：通过。
- `git diff --check`：通过。

## 实际命令旅程

### 原生 Ask

`project create --request '请做特应性皮炎竞品调研'` 未带报告类型，退出码 6；返回 A/B/C 三项原生 Ask 数据，未创建目标项目目录。

### 确定性开发旅程（测试能力注入，非生产能力证据）

三个项目均使用同一真实 CLI：`project create --request ... --reports <单一类型>` → `yaozh answer --answer skipped` → `project run`。测试模式仅注入能力结果，用于可重复集成，不证明真实宿主独立上下文。

| 旅程 | 实际适应症 | 唯一报告 | 共享来源 | 独立分支 | work-item SHA-256 |
|---|---|---|---|---|---|
| `W02-journeys/pnh-a` | 阵发性睡眠性血红蛋白尿症 | A | 6 条，各一次 | `report-a-evidence` | `cea34e38a84d88e4f19ccdc09137ecaf6908d1c4ac10442eb75d35d67fd2c5dc` |
| `W02-journeys/ad-b` | 特应性皮炎 | B | 6 条，各一次 | `report-b-evidence` | `a05cc7c7c232a44e9e5e178972263b89547dc725268085a49d19400a61cf3814` |
| `W02-journeys/ad-c` | 特应性皮炎 | C | 6 条，各一次 | `report-c-evidence` | `c12cdc3a3c0a6bf60097237f9d45bd016ee38b1e2570e6df013f53b86b2e783a` |

这些产物是可追溯的开发待办，不是研究包、报告门户、科学接受或 24 门户验收。B/C 未触碰 W01 已拒绝的非 JSON/粗 locator/生成原文旧夹具，也未放宽新信任合同。

### 生产能力预检与执行门

- 项目：`W02-journeys/pnh-production-preflight`；真实命令使用 `--host codex`，不设置测试模式或静态能力结果。
- 结果：`independent_context=blocked`，说明为“未配置可执行的独立上下文探针，静态声明不构成能力证据”；`project run` 结果 `capability_blocked`，只完成 `intake/preflight`，没有生成 `state/work-items/source-research.json`。
- 能力回执 SHA-256：`40866c3122c3e3cf096808689381937a0d4f5cab13ff98f81412f9852d979886`。
- 当前运行清单 SHA-256：`1711d7ce87db87141c43166a38fde63ead1c32c7432f119ced8cd8ef47f9575a`。

## 主要源码身份

| 文件 | SHA-256 |
|---|---|
| `src/ci_workflow/cli.py` | `5cdb63d9f75bf971db3e1cd17ebdeefa152c07612d7b02b9f5c33ee7235026a4` |
| `src/ci_workflow/application/autonomous_research.py` | `3ca2fd739344ed62ff46c51c26f699aeb13b03e1efdbb92ce338a72265629c1d` |
| `src/ci_workflow/application/capability_preflight.py` | `f27aa6f91d0d3693178e72c6ac1b29b10fefed670acd7e180679d4648e918b1c` |
| `src/ci_workflow/application/run_service.py` | `b3e47076db63ba0766da6866d73244326ed0553c606c4132df937c2b5b3f92e8` |
| `src/ci_workflow/graph/typed_skills.py` | `47649781d9ee1a8388c1b5217ab681bc3ed4fe0702b6e4ee38be12fad4929928` |
| `src/ci_workflow/reports/common/view_state.py` | `7a46eb5ad1491ece928e4343a3d16a4e214624e786cfb0f81798834dd2cb53e4` |
| `src/ci_workflow/renderers/portal/filters.py` | `da807e6a38f5180f957b211fe9e78cbd3bdc7920bcdc16890b11920465cc7652` |

## 限制与下一安全动作

- 当前生产宿主独立上下文能力 **未验证且实际阻断**；需在允许的宿主启用真实子Agent、独立会话或兼容执行器探针后从同一项目 `--resume --host ... --independent-context-probe ...`。
- 未执行真实来源检索/抽取、A/B/C 科学载荷提交、独立科学复核、门户渲染、浏览器交互、三宿主安装恢复或 24 门户验收；不得称产品通过、RC_FROZEN 或 RELEASED。
- W02 公共接口已可供 W03/W04/W05A/B/C 使用；W07 可继续真实来源链。任何 B/C 生产旅程必须使用真实可重放来源和逐事实 locator，继续遵守 W01 信任合同。
