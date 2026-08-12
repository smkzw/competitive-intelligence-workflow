# Task 3.5 实施报告 — Pi (Oh My Pi)，Codex 拥有验收权

## 变更文件
- `src/ci_workflow/graph/recovery.py`（新增）：不可变选择合同 `DeliveryContract`/`ReportTarget`、`PartialDeliveryCoordinator`、`DeliveryConditions` 聚合条件、`ContractDriftError`/`InconsistentStateError`/`CoordinationError`。
- `tests/graph/test_partial_delivery.py`（新增）：唯一顶层节点 `test_reports_and_formats_progress_independently_with_partial_delivery`。
- `tests/graph/test_partial_delivery_blocked.py`（新增）：唯一顶层节点 `test_terminal_partial_delivery_requires_explicit_reopen_before_resume`。
- 未改 `src/ci_workflow/graph/__init__.py`（测试直接以模块路径导入，公共导出非必需）；未触碰 Task 3.4 源码/测试、Trellis、schema、CLI、renderer、fixtures、真实项目数据。无 commit/stage。

## RED 证据（实现前，recovery.py 不存在时）
```
FAILED tests/graph/test_partial_delivery.py::... - ModuleNotFoundError: No module named 'ci_workflow.graph.recovery'
FAILED tests/graph/test_partial_delivery_blocked.py::... - ModuleNotFoundError: No module named 'ci_workflow.graph.recovery'
2 failed in 0.07s
```
两个 exact nodes 均真实 RED 后实现 → 各自 GREEN。

## 实现行为
- **机械聚合**：协调器只接收合同，从 `executor.state()`（单一 EventStore 归约）逐矩阵目标分类 delivered/terminal_blocked/continuable，再计算九个聚合守卫布尔键（`selected_objects_continuable`、`all_selected_*` 等）。调用方无法传入结论布尔值；证据还携带 `contract_id/version/selection_digest/reports/optional_formats/target_status` 审计绑定。聚合守卫键从 `TRANSITION_REGISTRY` 守卫声明收集，`getattr` 缺失即失败关闭。
- **选择矩阵**：每个选定报告 ×（强制 `html` + 每个选定 optional format）。改变选择/放弃 PPTX 需更高合同版本；同 `contract_id+version` 下选择漂移由事件流中已记录的绑定检测 → `ContractDriftError`（+ EventStore 同身份不同载荷 `EventConflictError` 兜底）。阻断/取代/矛盾状态（如阻断报告的格式 delivery_ready、superseded 目标）`InconsistentStateError` 失败关闭。
- **场景一**（GREEN 断言）：A snapshot_locked + A:html delivery_ready；A:pptx 因 PPT Master 不可用而 blocked（不撤销 HTML）；B evidence_blocked 不污染 A/C（gate.A 数据不变、C 仍 collecting）；项目 `partially_delivered` 而非 complete/blocked。
- **场景二**：C 与全部剩余选定对象终态阻断、无运行对象 → `partial_delivery_blocked`；无任何交付的相同终态 → 仅 `blocked`；静默 reconcile 不离开两个 blocked 终态。显式 reopen：项目仅接受 `user_material_accepted`/`environment_fix_confirmed`/`new_contract_version_reopens` 三原因回 running；格式仅接受 `environment_fixed`/`generator_fixed`/`new_contract_version_reopens` 回 queued（用户材料重开格式被拒）。旧 `evidence_blocked` 报告不可变（原地改 queued 是未声明迁移 → 拒绝审计事件）；恢复用新对象身份（`report_version_target` → `report_C_v2`）。
- **请求身份**：`stable_id("coord", project, run, contract_id, version, action…)` 确定性派生，项目迁移带 running-entry epoch（重开/重新进入 running 后重新交付不冲突）；同动作重放返回原事件不追加；身份相同但原因漂移 → `EventConflictError`。
- **P2 锚点**：聚合守卫全部使用真实规范状态；本任务不生产任何副作用事件（publish/move/approve/delete），故未触及 Task 3.4 副作用生产入口校验边界——已在 `recovery.py` 模块 docstring 明确声明。未扩改 executor。

## 验证结果
| 检查 | 结果 |
|---|---|
| 两个 exact nodes | RED → GREEN（2 passed） |
| `uv run pytest tests/graph/test_partial_delivery.py tests/graph/test_partial_delivery_blocked.py -q` | 2 passed |
| `uv run pytest tests/graph -q` | 13 passed |
| `uv run pytest -q` | 445 passed（基线 443 + 2 新增） |
| `uv run ruff check src tests` | All checks passed |
| `uv run mypy src/ci_workflow/graph` | Success, no issues（strict，11 files） |
| `uv build --out-dir <tmp>` | wheel 含 `ci_workflow/graph/recovery.py`；临时目录已清理 |
| `git diff --check` / `git status --short` | clean；仅 3 个新文件 + 既有未跟踪 context 文件；未 commit |

## 失败路径与修正
- mypy strict 报 `from_state` 参数类型 `str | None`：`reopen_project` 中 `_single_project` 返回 `str | None`，edge 非 None 时无法自动收窄 → 改为 `if current is None or edge is None` 失败关闭后收窄。修复后全绿。
- 测试二初版 A 报告链驱动重复提交错误 `from_state`（会命中已拒绝事件导致断言失败）→ 重写为显式字面链。

## 残余不确定性
- 合同绑定锚点：首次协调事件尚未发出前无法检测同身份选择漂移（无事件可对照）；一旦任一协调动作落库即被 `ContractDriftError`/`EventConflictError` 严格约束。测试覆盖的是落库后的全部漂移路径。
- 同合同身份对同一已重开格式的再次重开（blocked→queued→blocked→queued）会因确定性身份被 no-op/拒绝——按“重新打开需新合同版本或新诊断”语义设计为失败关闭，未在测试中专门覆盖。

## 下一步建议
- 建议 Codex 独立复核：`recovery.py` 的 epoch/身份派生与守卫键收集逻辑、两个场景测试的字面断言，以及 drift/重放边界；确认后由 Codex 记录验收并进入 Task 3.6（fixture/project CLI）或 Task 3.7（科学质控绑定真实验证结果）。

**Codex 拥有本任务最终验收权。**
