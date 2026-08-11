六条命令全部通过（与上轮一致）。变更文件本会话已完整读取，mtime 确认无新改动；四个重点判断基于已读代码 + 本会话实证探针，无需重跑探针。

# Task 1.5 修订后独立验收（收尾）

## 结论
**PASS**

## 真实命令计数
- 精确测试：`3 passed`（exit 0）
- 全库回归：`121 passed`（exit 0）
- `ruff check src tests`：`All checks passed!`（exit 0）
- `mypy --strict src`：`Success: no issues found in 19 source files`（exit 0）
- `ci-workflow package verify --root .`：`PACKAGE_OK version=0.1.0a0`（exit 0）
- `git diff --check`：无输出（exit 0）

## 重点判断
1. **旧 run/旧快照假通过**：已封堵。`manifest_store.py:310-399` — accepted 清单必须提供 `ManifestWriteContext`，其 12 项身份字段（project_id、contract_version、report、report_version、data_cutoff、producer_run_id、source_commit、package_digest、evidence_snapshot_id、claim_snapshot_id、report_snapshot_id、coverage_set_id、coverage_projection_id）与清单逐项相等，缺上下文或任一不符 → `ManifestIntegrityError`。覆盖 ADR 声明的全部权威身份。测试逐一断言无上下文（match "当前运行"）、旧 run（"不是当前接受对象"）、旧 report_snapshot（同）三类拒绝 + 匹配上下文成功 + 篡改产物拒绝。本会话探针实证：无上下文/旧 run 上下文均失败关闭，`generated` 无上下文仍可写。**残留边界**：调用方把旧 run 身份同时写入清单与上下文仍可通过——"上下文新鲜度"权威在应用层（run_service），ADR 已记录，非存储层缺陷。
2. **崩溃窗口测试**：真实覆盖"效果产生 → 中断 → 重放 → 恰好一次"。`test_event_checkpoint_replay.py:100-150` — 首次 replay 副作用执行（键入集合、effects 追加）后抛 `RuntimeError`，无检查点保存；二次 replay 重放同一事件，回调按 `idempotency_key` 去重，最终 `completed_effects == ["artifact_crash"]`、状态正确。去重由调用方集合实现，`IdempotentSideEffect` Protocol docstring 与 ADR 均只声明"回调必须按事件幂等键去重"，未声称本地检查点与外部系统原子提交——合同诚实，无臆造保证。
3. **ADR 双真相裁决**：清晰。0004 新增条款固定"不可变清单 = 规范事实，SQLite = 实体/状态/检索索引/关系查询"，未来双写 `report_snapshots.manifest_json`/`artifact_records` 必须同稳定 ID + 摘要互验；明确保持两类存储分离并规定互验义务，未错误合并。
4. **新引入问题**：无。变更仅收严 accepted 写入路径 + 类型/文档化（replay 主体逐行未变）；新增断言全部真实通过；`generated`/`quality_check`/`failed`/`superseded` 无上下文路径不受影响；事件/检查点/快照文件未变更，此前 PASS 的篡改、跳号、交错隔离、幂等冲突、快照不可变、双合同字段路径全部保留。

## P0/P1
无

## 残留 P2/P3
- **P3-1**（已记录）：`ManifestWriteContext` 新鲜度权威在应用层；存储层只强制清单↔上下文一致。run_service 落地时需补"当前 run"注册表校验。
- **P3-2**（已记录）：SQLite `report_snapshots.manifest_json`/`artifact_records` 与新不可变清单的交叉核验未实现；ADR 已规定未来双写服务义务，决策闭环。
- **P3-3**：`EventStore.append` 无文件锁，多进程并发追加竞态在读取时失败关闭；单进程确定性执行器下不成立。
- **P3-4**：`CheckpointStore.latest` 对同 run 同 `last_sequence` 多自洽检查点按字典序选择；仅非确定性 reducer 可触发。
- **P3-5**：幂等键 run 作用域语义未在 schema 显式说明（Protocol docstring 已说明回调去重义务）。

## 接受建议
**同意 Codex 接受 Task 1.5**。修订闭环了上轮全部 P2（P2-1 实现+测试+探针锚点；P2-2 ADR 决策记录），P3-1 崩溃窗口合同已实现并有恢复测试。剩余 P3 均为已记录边界或单进程设计下的理论竞态，不构成阻断。接受前仅需在 Task 记录中注明 P3-1（上下文新鲜度）与 P3-2（双写互验）为 run_service/后续任务的挂账义务。
