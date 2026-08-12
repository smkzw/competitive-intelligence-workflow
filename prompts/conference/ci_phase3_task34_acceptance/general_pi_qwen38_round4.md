This is the final targeted continuation in the same Pi/Qwen session `019ff704-4620-7000-9f6e-a4e9e0dfc681`.

Hard boundaries:

- Read-only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`; do not modify files. Temporary probes may write only to a system temporary directory.
- Runner-managed output path: `runs/conference/ci_phase3_task34_acceptance/general_pi_qwen38_round4.md`. Never write it with tools.
- Do not read any worker report, Grok output, or Codex conclusion. Codex remains final authority.
- Do not restart the task or open a new session.

Initial read set:
- `src/ci_workflow/graph/reducer.py`
- `src/ci_workflow/graph/executor.py`
- `src/ci_workflow/graph/definitions/new_report.py`
- `src/ci_workflow/graph/types.py`
- `tests/graph/test_checkpoint_replay.py`
- `tests/graph/test_transition_matrix.py`
- `tests/graph/test_graph_node_contracts.py`

本轮只复核自你上次 PASS 后新增的一项修复：直接向共享 EventStore 追加的 `graph.node.completed` 是否仍可能绕过 `GraphExecutor.complete_node()`，以伪造输出污染规范状态。

必须检查并用独立临时目录探针验证：
1. 原复现载荷：`gate`/A，`gate_passed="YES"`、`failures="not-a-list"`、`evidence_digest=""`，直接 append 后调用 `state()` 与 `replay()`，必须在任何规范状态/检查点写入前以 `GraphEventContractError` 失败。
2. raw `graph.node.completed` 的 node_id、scope、report_kind、精确输出键集、完成谓词、输出类型、completion_digest、event_id、idempotency_key 均须与公共执行边界一致。
3. 一个由 `complete_node()` 生成的合法事件必须能被新的 executor 重放，不能把所有节点完成事件一概拒绝。
4. 重跑 GT11 以及完整 11 个 approved exact nodes；报告真实命令与结果。
5. 只判断 Task 3.4 P0/P1；之前确认的非目标副作用字段裸 KeyError 可继续记 P2，不得在没有新证据时升级。

返回完整 Markdown，包含 Boundary Check、Independent Work Product、Evidence And Assumptions、Risks/Gaps、Recommended Next Step，最后 `## Verdict`，单独写 `PASS` 或 `FAIL`，以及 `P0=<n>; P1=<n>; P2=<n>`。
