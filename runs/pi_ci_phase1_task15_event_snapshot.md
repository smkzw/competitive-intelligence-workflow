# Task 1.5 独立验收

**Fallback 声明**：本验收由声明的 `pi` fallback `opencode-go` / `deepseek-v4-flash` 执行，只读角色，未修改任何文件（验收前后 `git status` 均为同一 18 项变更，与会话上下文一致）。所有结论仅依据批准文件、真实命令输出与临时目录实证。**SOUL.md 读取状态：已读到文件末尾**——工具首读截断超长行（最长行 822 字符，第 95 行），已补读第 95 行与 150–267 行，267 行全部内容 + 空行 268 均已覆盖。

## 结论
**PASS**（无 P0/P1；3 精确 + 121 全库测试通过；Ruff/strict mypy/包校验/`git diff --check` 通过；关键假通过路径均有非模型锚点。附 2 项 P2，需 Codex 接受前明确裁决。）

## 已执行锚点
| 命令 | 结果 | 退出 |
|---|---|---|
| `uv run pytest tests/contract/test_artifact_manifest.py tests/integration/test_event_checkpoint_replay.py tests/integration/test_snapshot_identity.py -q` | `3 passed in 0.12s` | 0 |
| `uv run pytest -q` | `121 passed in 5.50s` | 0 |
| `uv run ruff check src tests` | `All checks passed!` | 0 |
| `uv run mypy --strict src` | `Success: no issues found in 19 source files` | 0 |
| `uv run ci-workflow package verify --root .` | `PACKAGE_OK version=0.1.0a0` | 0 |
| `git diff --check` | 无输出 | 0 |

临时目录实证（非模型锚点）：
- 事件流 payload 篡改 → `EventStoreError: 规范事件摘要不匹配`（event_store.py:142）。
- 删除中间记录跳号 → 检测；**尾部截断** → 重放经 `event_stream_digest` 绑定失败关闭 `检查点引用了不存在的事件序号`（event_store.py:190）。
- 跨 run 复用同幂等键同载荷 → `EventConflictError`（失败关闭，1 条记录）。
- run_B 事件插入 run_A 检查点之后：重放 run_A 状态保持 `{'n': 1}`、副作用零重跑；run_A 新事件按全局序号应用一次。
- manifest `status=accepted` + 旧 `producer_run_id` + 不存在的 evidence/claim/report/coverage 快照 ID → **写入成功**（P2-1 实证）。

## P0/P1 缺陷
无

## P2/P3 观察
- **P2-1 旧 run/快照引用不失败关闭**：任务上下文成功标准写有"旧 run/快照/摘要均失败关闭"，但实现仅保证附录 C 字段必填；`status=accepted` 的清单可引用任意不存在的快照 ID 与任意旧 run（实证写入通过）。计划 Task 1.5 step 2 的最小合同测试（字段逐一必填）已满足，"当前 run/快照"权威属应用层（run_service），本层无法单方判定新旧。见 `manifest_store.py:ArtifactManifest/ManifestStore`、`tests/contract/test_artifact_manifest.py`。
- **P2-2 SQLite 与新快照文件零交叉核验**：`migrations/0003_gates_snapshots.sql` 的 `report_snapshots.manifest_json` 与新不可变 `snapshots/reports/*.json` 同时描述同一报告快照，无任何摘要互验；`artifact_records`（0004）与 `manifests/artifacts/*.json` 同理。未来双写时是真实的第二事实库漂移面，需在 report_service 落地前裁决"引用 vs 复制+核验"。当前无代码双写，非活缺陷。
- **P3-1 崩溃窗口**：`side_effect` 执行后、检查点保存前崩溃 → 重放重跑副作用。spec §5.3 已明确声明"副作用必须幂等或位于结构化闸门之后"，`idempotency_key` 字段提供支撑；无测试模拟该窗口，合同仅靠约定。
- **P3-2** 幂等键作用域（project+run，fingerprint 含 run_id）导致跨 run 同键同载荷失败关闭（保守方向），该语义未在 schema/文档显式说明。
- **P3-3** `EventStore.append` 无文件锁，多进程并发追加可能竞态产生重复序号；损坏流在读取时失败关闭，单进程确定性执行器下不成立。
- **P3-4** `CheckpointStore.latest` 对同 run 同 `last_sequence` 的多个自洽检查点按文件名字典序取最后一个，选择不确定；仅非确定性 reducer 可触发。

## 假通过攻击结果
- **JSONL 只追加/跳号/篡改**：`read_all` 逐行校验序号连续、digest 匹配、拒绝空行与坏 JSON；append 用 `O_APPEND`+`fsync`，无覆写路径。篡改、跳号、截断均失败关闭（实证）。尾部截断只有 checkpooint digest 能识别，属追加日志的固有边界，恢复路径已封闭。
- **幂等去重**：同 run 同键同载荷 → 返回既有记录、JSONL 仍 1 行（测试）；同键不同载荷、同 event_id 不同内容 → `EventConflictError`（测试）；跨 run 复用 → 失败关闭（实证）。
- **恢复不依赖私有缓存**：`.langgraph-cache` 写入/删除后仅凭 `events/events.jsonl` + `state/checkpoints/*.json` 恢复且副作用不重跑（测试+实证）。检查点绑定 project/run/applied_event_ids/state_digest/event_stream_digest，状态篡改 → `CheckpointIntegrityError`（测试）。
- **正常重复恢复重放副作用**：不重放（实证 effects 为空）；崩溃窗口见 P3-1。
- **多运行交错**：全局序号不误用，run 间事件隔离，新事件按序应用一次（实证）。
- **快照不可变**：内容寻址、同内容同 ID、变内容新 ID、旧文件不覆盖、相对路径、`..`/绝对路径/反斜杠拒绝、移动项目后可读、篡改 → `SnapshotIntegrityError`（测试，snapshot_store.py `_resolve`/`read`）。
- **职责分离**：与 ADR 0004 一致——SQLite 应用数据层、JSONL 运行史、内容寻址原文、不可变清单；第二事实库风险见 P2-2。
- **附录 C 双合同**：全部根字段及 `design_contract`/`renderer`/`render_verdict`/`artifact`/`deterministic_checks` 嵌套字段在 JSON Schema 与 Pydantic 两侧同时必填（测试逐一 pop 双侧断言）；`accepted` 强制真实文件 sha256/字节数/mtime（±1s）绑定、确定性检查全通过、`render_verdict.verified_at ≥ artifact.modified_at ≥ generated_at`、独立 `accepted_by`、POSIX 相对路径；绝对路径、伪 accepted（None 接受者/失败检查/被拒裁决）、已篡改产物、同 manifest_id 不同内容、验收早于产物全部失败关闭。
- **可假通过项**：旧 run/不存在快照引用（P2-1，实证）；SQLite↔快照/清单漂移（P2-2）。
- **schema↔持久记录互验**：event/checkpoint/evidence/report 四 schema 对真实落盘记录验证（测试）；artifact-manifest schema 对真实 payload 双侧验证；无漂移（`artifact.modified_at` 时区偏移为 Pydantic 单侧更严，属正常）。

## 接受建议
**可接受 Task 1.5**：无 P0/P1、全部要求命令通过、关键假通过路径均有非模型锚点。Codex 接受前必须直接复核：
1. **P2-1 裁决**：旧 run/不存在快照引用不失败关闭——明确记录为延后到 run_service 的应用层增强（需在 Task 记录/ADR 留痕），或补 SnapshotStore 存在性交叉核验（对 `report_snapshot_id`/`evidence_snapshot_id` 检查锁定文件存在且 ID 匹配）。
2. **P2-2 裁决**：`report_snapshots.manifest_json`/`artifact_records` 与新不可变文件的职责（引用 vs 复制+摘要互验），防止未来 report_service 双写产生第二事实库。
3. 确认 P3-1 崩溃窗口依赖调用方幂等为明确合同（spec §5.3 已声明），并决定是否补一条"副作用后、检查点前崩溃"的重放测试。
