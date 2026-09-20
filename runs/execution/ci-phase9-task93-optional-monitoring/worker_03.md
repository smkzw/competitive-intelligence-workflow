# Execution Output: ci-phase9-task93-optional-monitoring - worker_03

## Boundary And Context Check

- 工作目录限定在 runner 绑定的仓库根 `.`；未读写任何生产路径；未安装包；未改动同伴 worker 的工件；未创建 runner 报告文件或同级进程文件（本报告仅在最终回复中返回）。
- 初始读取集：`context/ci-phase9-task93-optional-monitoring_execution_context.md`、`plans/codex_execution_ci-phase9-task93-optional-monitoring.md`。两者均指向“已批准 Task 9.3 合同”，该合同的权威定义位于 `.trellis/tasks/09-01-phase-9-task-93-optional-monitoring/{prd,design,implement}.md`，已完整读取作为实现依据（design.md §图与Skill、§边界与依赖方向；PRD 验收 4/7/8）。
- 追加读取（依赖与模式研究，均为只读）：`graph/definitions/{refresh,correction,new_report}__init__.py`、`graph/{types,transitions,executor}.py`、`application/{project,correction}_service.py`、`cli.py`（verify_package 段）、`tests/graph/test_graph_node_contracts.py`、`tests/integration/test_{incremental_refresh,project_workspace,cli_command_catalog}.py`、`skills/_internal/monitoring/{SKILL.md,agents/openai.yaml}`、`package-manifest.json`。
- 会话中段发现 worker_01/02 的工件在我工作期间并行落盘（03:34–03:36：`domain/monitoring.py`、`application/monitoring_service.py`、`schemas/monitoring-change-candidate.schema.json`）；我据此做了词表对齐与集成面核对（证据见下），未做同伴复审。

## Work Performed

1. **监测图节点合同（新增 `src/ci_workflow/graph/definitions/monitoring.py`）**
   - 按 design.md §图与Skill 声明六节点管线：`monitor_scope`（读取监测范围）→ `monitor_observe`（执行来源观察）→ `monitor_dedupe`（归一化与去重）→ `monitor_record`（记录候选/诊断）→ `monitor_await_disposition`（等待用户处置）→ `monitor_handoff`（生成刷新交接），沿用 `REFRESH_NODES` 的 NodeContract 声明模式（执行归 `application/monitoring_service.py`，图不进 `graph/__init__.py`，与 refresh/correction 一致）。
   - 越权边界以导入期失败关闭不变量固化：节点唯一且不与 NEW_REPORT_NODES/REFRESH_NODES 冲突；只写 `monitoring.*` 键（证据/门槛/快照/质控/分析/产物与运行状态族一律不写，`project` 仅只读）；全部节点 `side_effect_class="none"`、`scope="shared"`；输出字段名不含 publish/approv/accept/snapshot/fact/claim/revision 能力词；输出类型禁用 EvidenceReference/QCVerificationReference。
   - 封闭词表与 worker_01 的域机器合同 `domain/monitoring.py` 逐字对齐（`ObservationOutcome` 五值、`UserDisposition` 减去初始态 `pending` 后的两值），并加 `_validate_vocabulary_alignment()` 导入期漂移核对（correction.py 对冻结注册表逐边核对的既有模式）。
   - `monitor_observe` 在输出层面区分四类来源集合（changed/unchanged/not_public/failed），落实 PRD 验收 4 的图级区分；`monitor_handoff` 输出仅内容寻址交接单（handoff_id/handoff_digest/bound_contract_version），无任何事实/快照/报告能力。
2. **内部监测 Skill 中文边界（更新 `skills/_internal/monitoring/SKILL.md`）**
   - 推翻 9.3 之前的错误边界“变化候选必须进入修订流程”，改为：候选只能经用户“启动正常刷新”进入 Task 9.2 正常刷新重新核验，不得直接送入修订批准流。
   - 新增四类诊断中文提示边界专节（无变化/来源确认未公开/技术获取失败/需要用户协助），含“恢复尝试未穷尽前不得要求用户协助”；新增用户处置专节（两种处置、追加保存、重放幂等）；禁止行为补充不得自动接纳事实或声明、不得建立正式快照、不得生成或发布报告；保留不得把抓取时间误作首次披露时间；声明监测 Skill 未安装或被移除时核心工作流不受影响。
   - frontmatter `name: monitoring` 与 `agents/openai.yaml`（`$monitoring` 提示、隐式调用关闭）未动，`package verify` 约束保持满足。
3. **测试（新增 `tests/graph/test_monitoring_nodes.py` 10 项、`tests/graph/test_monitoring_uninstallable.py` 3 项）**
   - 节点合同测试：管线顺序字面钉死；合同完整性/不可变/封闭类型词表（合法 fixture 通过 `validate_typed_outputs` 与完成谓词，空/缺字段/逐类型翻转拒绝）；越权读写断言；与核心图零冲突；词表封闭且与域合同 `get_args` 直接比对（非同源常量自证）；四类结果输出集合分离；Skill 中文边界三测试（正常刷新边界+旧句式禁入、四类诊断提示、处置与禁止行为、可卸载声明）。
   - 可卸载性测试（PRD 验收 7）：(a) 静态 AST 扫描 `src/ci_workflow` 全部 156 个源文件，除三个监测模块（service/domain/graph）自身外任何模块不得导入监测；(b) sitecustomize 元路径钩子在子进程把监测模块标记为“已移除”（导入即失败并记录），真实 CLI `project create` + `project verify` 通过且零监测导入尝试；(c) 独立进程驱动项目服务（新建工作区+校验，含 `monitoring/inbox` 目录保留）、刷新分支裁定、修订迁移绑定、图执行器 `complete_node`，零监测导入尝试。
4. **词表对齐（跨工件缝合，在我边界内）**：发现并行落盘的 worker_01 域合同后，将我的图词表从草稿值改为域合同字面值并加漂移核对，使图/域两条词表任何一方漂移都在导入期失败关闭。

## Artifacts And Evidence

| 文件 | 变更 | 性质 |
|---|---|---|
| `src/ci_workflow/graph/definitions/monitoring.py` | 新增（约 400 行） | 六节点合同 + 封闭词表 + 导入期不变量 |
| `skills/_internal/monitoring/SKILL.md` | 重写正文 | 中文边界：正常刷新而非修订流、四类诊断、两种处置 |
| `tests/graph/test_monitoring_nodes.py` | 新增 | 10 项合同与 Skill 边界测试 |
| `tests/graph/test_monitoring_uninstallable.py` | 新增 | 3 项可卸载性/导入隔离测试 |

未改动：`package-manifest.json`（监测 Skill 已登记；schema 双布局登记属 worker_01）、`graph/__init__.py`（不得重导出监测）、`cli.py`、任何核心服务、同伴工件。git status 中 `render-deliver`/`visual-package-qc` SKILL.md 等修改为会话开始前已存在，与本人无关。

## Commands And Observations

- 聚焦：`pytest tests/graph/test_monitoring_nodes.py tests/graph/test_monitoring_uninstallable.py` → **13 passed**（词表对齐前后各跑一轮）。
- 跨工件互证（非复审）：`pytest tests/integration/test_monitoring_service.py tests/contract/test_monitoring_change_candidate_contract.py` → **43 passed**（我的文件不破坏同伴测试）。
- 最终回归扫描：`pytest tests/graph/ + monitoring service/contract + incremental_refresh + project_workspace + correction_service/flow` → **129 passed**。分簇：项目工作区/移植/合同库/事件回放/修订簇 41 passed；Task 9.2 手动刷新 `test_incremental_refresh.py` 19 passed；包清单+图套件 52 passed；CLI 目录（含 package verify 与 project create/verify/run）5 passed。
- 包完整性：`python -m ci_workflow package verify --root .` → `PACKAGE_OK version=0.1.0a0 stage=phase-2-accepted`。
- Ruff：`ruff check` + `ruff format` 三个新文件 → 全部通过（已格式化）。mypy strict：`mypy src/ci_workflow/graph/definitions/monitoring.py` → 0 错误；`mypy src/ci_workflow/` 全树 75 错误全部位于渲染器（pdf_native/html_ppt/portal）与 run_service——这些文件在会话开始的 git status 中已是修改态，属既有/他线在制工作，与本任务无关（我的模块 0 错误）。测试文件的 mypy 单文件检查在本仓库既有测试上同样不通过（如 `test_graph_node_contracts.py` 95 错，缺 py.typed），非本任务引入。
- 观察（sourced fact）：`grep` 证实核心模块对 `domain.monitoring`/`monitoring_service`/`graph.definitions.monitoring` 的导入为零，静态与动态两层证据一致。

## Blockers Or Missing Environment

无阻塞性缺失。两个非阻塞观察供 Codex 收口：

1. **图合同与服务未互连（推断）**：worker_02 的 `monitoring_service.py` 未导入 `MONITORING_NODES`；design.md 说节点执行由服务持有，服务是否/如何在事件中绑定节点合同 ID 属验收裁量，需要 Codex 决定缝合方式（我这侧的合同与查找 API 已就绪）。
2. **服务内部观察结果字面量与域合同措辞分歧（sourced fact，worker_01↔worker_02 缝合）**：服务 `_OUTCOME` 用 `completed_no_change`/`source_confirmed_not_public`，域合同 `ObservationOutcome` 用 `no_change`/`confirmed_not_public`；公共处置边界一致（`start_normal_refresh`/`deferred`，与我的图词表一致）。不在我的边界内修正。

## Rerun Requests Or Next Step

- 无需重跑即可继续；全部绿色证据如上。建议 Codex 验收时：(a) 裁量 service↔graph 合同缝合与观察结果字面量统一归属；(b) 独立复审步骤（implement.md 末项）覆盖“候选不能成为事实、用户决定边界、技术诊断真实性、可卸载性、中文表达”时，可直接复用 `tests/graph/test_monitoring_uninstallable.py` 的两层证据；(c) worker_01 若后续修改 `domain/monitoring.py` 词表，我的导入期漂移核对会失败关闭并指明冲突取值。
