# 执行输出：ci-phase9-task93-optional-monitoring - worker_02

## 边界与上下文检查

- 工作目录保持在运行器提供的工作区内（`competitive-intelligence-workflow`）。没有生产环境写入，没有安装包，没有凭证，也没有超出我分配的工作项的互联网访问。
- 初始读取集按指定读取（执行上下文 + Codex 计划），然后我读取了权威来源：任务 9.3 `prd.md` / `design.md` / `implement.md` / `research/authoritative-boundaries.md`、产品规范 §17.3 (`docs/specs/competitive-intelligence-workflow-design-v1.2.md`)，以及代码库模式（`storage/event_store.py`、`application/refresh_service.py`、`application/correction_service.py`、`application/project_service.py`、`domain/ids.py`、`domain/contracts.py`）。
- **任务中发现的重要协调事实**：worker_01 和 worker_03 在同一个共享树上并发写入。我首先将服务实现为自包含的（按照存储库惯例使用内联契约）；当 worker_01 的 `src/ci_workflow/domain/monitoring.py` + `schemas/monitoring-change-candidate.schema.json` 出现时，其词汇表、字段名称、摘要 JSON 键和事件常量与我的内联契约产生了偏差。我完全重写了我的模块以供依赖（导入并委托给）worker_01 的领域契约，因为他们的分配（“Python 合同、稳定去重摘要”）是合同层，而我的分配是服务层。该决定已根据权威边界研究得到验证（“候选当前投影使用 monitoring/inbox/ JSON，历史使用事件流”），并在本报告中标记以供 Codex 最终确认。
- 边界已遵守：该服务不导入 `RefreshService`，不调用 accept/snapshot/publish，不添加数据库表或迁移（仅使用 `EventStore` + JSON 投影 + JSONL 收据），并且只读取 `project.yaml`。

## 已完成工作

已基于 `src/ci_workflow/domain/monitoring.py` 中的 worker_01 机器契约实现了 `src/ci_workflow/application/monitoring_service.py`（新文件，约 1,000 行）：

1. **变更观察入口** (`submit_observation`)：获取调用者完成的源观察；结果词汇表是领域的 `ObservationOutcome`（5 个值）。`change_found` 通过 `monitoring_dedupe_digest` + `candidate_id_from_digest` + `build_change_candidate` 注册/合并一个候选者；重复发现返回相同的候选者 ID 并追加到 `discoveries` 中（仅追加，顺序为事件顺序；精确重放是幂等的，并返回首次发现回执）。其他四个结果仅写入观察回执——没有空候选者。
2. **仅追加事件**：为发现 (`monitoring.candidate.discovered`)、重新发现、诊断更新、处置和交接使用 worker_01 的冻结事件常量，以及用于回计数的 `monitoring.observation.recorded`。所有事件都带有内容寻址的事件 ID 和幂等键；EventStore 对相同键/不同负载进行闭合失败（closed-fail）处理。
3. **候选投影恢复** (`load`, `list_candidates`)：规范状态从 `events/events.jsonl` 缩减；`monitoring/inbox/<candidate_id>.json` 是一个投影，在丢失或漂移时进行原子重写（临时文件 + `os.replace`）。每次缩减结束时都会调用 `verify_candidate_dedupe_identity`（聚合边界重新派生，不信任 `model_copy` 缓存字段）。`record_diagnosis`/处置历史在投影丢失后依然存在。
4. **技术诊断** (`record_diagnosis`)：追加 `MonitoringDiagnosticRecord`；仅在尝试次数 ≥ `recovery_attempt_limit` 且存在方法时才允许 `needs_user_assistance`（闭合失败，两个方向：在限制下需要协助被拒绝；限制下的可恢复被拒绝）。`recovered` 仅在存在未解决的失败时有效，并返回 `diagnostic_status: healthy` 而不删除历史记录。用户指导（中文）嵌入在每条记录中，并通过 `failure_category_zh` 进行插值。
5. **用户处置** (`apply_disposition`)：`deferred` / `start_normal_refresh` 作为仅追加的 `MonitoringUserDispositionRecord`（需要中文 `reason_zh`）；精确重放是幂等的；后续决策既追加又保留历史记录。
6. **只读刷新交接**：因为 §17.3 模式要求每当 `user_disposition: start_normal_refresh` 时必须有 `refresh_handoff`，`apply_disposition(start_normal_refresh)` 会在一次操作中记录处置事件和交接事件（中间状态永远不会持久化；重放可幂等地完成中断的运行）。`create_refresh_handoff` 仍然是独立的幂等恢复入口（除非处置为 `start_normal_refresh`，否则闭合失败）。交接通过 `build_refresh_handoff` 绑定候选者 ID/摘要、项目 ID、当前活动项目合同版本（从 `project.yaml` 只读读取）、来源身份和建议的审查范围（中文文字说明）；`verify_refresh_handoff_addressing` 在边界处重新派生；文档投影在 `monitoring/handoffs/<handoff_id>.json` 中自愈。
7. **观察回执** (`observation_receipts`)：从事件中缩减所有回执，并自愈 `receipts/monitoring_observations.jsonl`。

测试：`tests/integration/test_monitoring_service.py`（新文件，24 个测试）映射 PRD 验收 1–6，包括：每个生命周期阶段的收件投影与 worker_01 的 JSON 模式的验证；相同更改 → 相同 ID + 追加历史记录，而不同定位器/版本/值 → 不同的候选者；投影丢失/漂移自愈；预置的冲突幂等键上的 `EventConflictError`；四个结果类别通过中文指导区分（限流 / 需要验证码或登录 / 已尝试 N 轮）；协助门控闭合失败；处置仅追加 + 幂等重放；交接绑定 + 严格只读证明（`project.sqlite` 字节和 `project.yaml` 字节未变，没有 `snapshots/`/`reports/` 文件增量，没有 `refresh.*` 事件）；具有不同身份的第二个交接闭合失败；工作区验证仍然通过。

## 产物与证据

由我创建/修改的文件（没有其他文件）：
- `src/ci_workflow/application/monitoring_service.py` — 新服务（严格的 mypy-clean）。
- `tests/integration/test_monitoring_service.py` — 24 个重点测试。

我消耗（来自并发 worker，非我编写）的文件：`src/ci_workflow/domain/monitoring.py`, `schemas/monitoring-change-candidate.schema.json`, `src/ci_workflow/schemas/monitoring-change-candidate.schema.json`, `tests/contract/test_monitoring_change_candidate_contract.py`, `src/ci_workflow/graph/definitions/monitoring.py`, `tests/graph/test_monitoring_nodes.py`, `tests/graph/test_monitoring_uninstallable.py`。

## 命令与观察

| 命令 | 结果 |
|---|---|
| `uv run pytest tests/integration/test_monitoring_service.py -q` | 24 个通过 |
| `uv run pytest tests/contract/test_monitoring_change_candidate_contract.py tests/graph/test_monitoring_nodes.py tests/graph/test_monitoring_uninstallable.py tests/integration/test_monitoring_service.py -q` | 58 个通过（结合所有三个 worker 的 Task 9.3 测试） |
| `uv run pytest tests/integration/ -q` | 314 个通过 |
| `uv run pytest tests/unit/ -q` | 536 个通过 |
| `uv run pytest tests/contract/ tests/graph/ -q` | 280 个通过，1 个失败 — `test_offline_assets.py::test_html_ppt_runtime_has_required_navigation_presenter_and_offline_boundaries` (HTML-PPT 运行时资产；在此会话前树中已修改 `M assets/html-ppt/runtime.js`, `M assets/html-ppt/runtime.css`；与 Task 9.3 或我的 diff 无关) |
| `uv run ruff check` + `ruff format` on my two files | 清洁 |
| `uv run mypy src/ci_workflow/application/monitoring_service.py` | 成功：未发现问题（测试文件未保持 mypy-clean，与现有测试一致，例如 `test_incremental_refresh.py` 在严格模式下也有 30 个错误） |

已修复的开发中问题：`load`/`_require_candidate` 之间的递归错误；首次发现时投影前写入交接文档缺失；ascii 中文文本拒绝在服务边界被包裹在 `MonitoringServiceError` 中而不是裸 `ValueError`。

## 阻塞点或缺失环境

- 没有阻塞点。一个预先存在的失败（`test_offline_assets`，Task 8 域）存在于我分配的范围之外，并且可证明在我的会话之前就已经存在于工作树中 —— 标记给 Codex 以便知晓，而不是由我修复。
- 共享树的并发编辑意味着 worker_01 的 `domain/monitoring.py` 可能在我最终运行后发生了变化；我的模块针对我执行的快照进行了编译和测试。

## 重跑请求或下一步

1. **Codex 协调检查**：确认服务属于 `application/monitoring_service.py` 并委托给 `domain/monitoring.py` 是预期的分割（我的第一次迭代有分歧的内联契约，并被替换了）。具体确认：(a) `apply_disposition(start_normal_refresh)` 原子地记录处置 + 交接，以满足模式规则“start_normal_refresh ⇒ refresh_handoff 存在”；(b) 服务添加的 `monitoring.observation.recorded` 回执事件族 + `receipts/monitoring_observations.jsonl` 是 PRD #4（“无变化观察写事件/回执”）所要求的，但超出了 worker_01 的五个冻结事件族 —— 如果事件词汇表必须保持关闭，请告诉我，我将通过候选事件或不同的流对其进行路由。
2. worker_03 的图将 `monitor_await_disposition` 和 `monitor_handoff` 分离为两个节点；该服务支持这两种入口样式（组合调用 + 具有幂等恢复的独立 `create_refresh_handoff`）。建议 worker_03 对接线进行健全性检查。
3. 剩余的验证由 Codex 决定：独立的 Task 9.3 审查（候选者无法成为事实，用户决策边界，诊断真实性，中文措辞），并且完整的存储库验收（包括无关的 offline-assets 失败）仍未关闭。
