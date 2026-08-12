# Codex Main-Venue Plan: ci_phase3_task34_acceptance

Date: 2026-08-13
Objective: 独立验收 Task 3.4 类型化控制图是否真实满足 v1.2 与批准计划，重点识别状态、身份、节点合同、跨运行和检查点恢复假绿；只读，不修改文件

## Task Decomposition

1. 两名参与者在互相隔离的上下文中独立读取同一源包，不读取工作者报告或对方结论。
2. 各自核对批准计划的 11 个精确测试节点与 v1.2 §10.1–10.2，而不是只运行目录级 pytest。
3. 各自运行精确套件和至少一组自建临时目录反例，攻击状态乱序、身份漂移、节点输入幂等、未知图事件与副作用重放。
4. 只读给出 PASS/FAIL 与 P0/P1/P2；验证者只能否决或接受，不静默改代码。
5. Codex 汇总一致与冲突结论；P0/P1 修复后复用原参与者 session 复验。

## Source Packet

- `AGENTS.md`
- `context/ci_phase3_task34_acceptance_conference_context.md`
- `context/ci_phase3_task34_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `src/ci_workflow/domain/enums.py`
- `src/ci_workflow/storage/event_store.py`
- `src/ci_workflow/storage/checkpoint_store.py`
- `src/ci_workflow/ingestion/manual_inbox.py`
- `src/ci_workflow/graph/` 全部源码
- `tests/graph/test_transition_matrix.py`
- `tests/graph/test_graph_node_contracts.py`
- `tests/graph/test_checkpoint_replay.py`

批准计划的精确节点为：

- `test_project_run_transitions_and_guards_match_v12`
- `test_report_evidence_transitions_and_guards_match_v12`
- `test_artifact_transitions_and_guards_match_v12`
- `test_download_request_transitions_and_guards_match_v12`
- `test_revision_approval_transitions_and_guards_match_v12`
- `test_every_undeclared_transition_is_rejected_and_logged`
- `test_intake_preflight_universe_and_route_nodes_declare_complete_contracts`
- `test_ingest_extract_resolve_and_gate_nodes_declare_complete_contracts`
- `test_snapshot_analysis_format_and_acceptance_nodes_declare_complete_contracts`
- `test_report_branches_share_evidence_without_sharing_gate_state`
- `test_replay_never_duplicates_publish_move_approve_or_delete`

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_pi_qwen38` | `alibaba` | `qwen3.8-max` | `runs/conference/ci_phase3_task34_acceptance/general_pi_qwen38.md` |
| `general_grok45` | `grok-build` | `grok-4.6` | `runs/conference/ci_phase3_task34_acceptance/general_grok45.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- 首次连通性由 runner health check + 真实路线尝试完成；诊断超时不直接 fallback。
- 各路线一次启动、120 分钟硬等待；主控按用户要求以 30 分钟观察窗等待，不因无输出重派。
- 只有完成后存在可操作缺口时才在原 session 发一次合并追问；模型/时段切换保留原 session。

## Codex Verification Checklist

- [x] 两名参与者均有真实 session、声明身份与运行时身份一致，无 fallback。
- [x] 11 个精确节点和三文件套件由 Codex 本地重跑。
- [x] 全库 pytest、Ruff、strict mypy、wheel 内容与 git diff 由 Codex 核验。
- [x] 所有 P0/P1 关闭；P2 有明确后续任务归属且不影响 Task 3.4 本体。
- [x] 接受记录、Trellis、清理与显式提交只在独立验收后进行。
