# Task 3.5 同会话复核（第 2 轮）

继续你在同一 Pi/Qwen 会话中的独立只读验收。不要读取执行者报告、Codex 评审或另一位参与者输出，不要编辑工程文件。

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read these files only: `AGENTS.md`, `docs/specs/competitive-intelligence-workflow-design-v1.2.md`, `src/ci_workflow/graph/recovery.py`, `src/ci_workflow/graph/transitions.py`, `src/ci_workflow/graph/guards.py`, `src/ci_workflow/graph/executor.py`, `src/ci_workflow/graph/reducer.py`, `tests/graph/test_transition_matrix.py`, `tests/graph/test_partial_delivery.py`, `tests/graph/test_partial_delivery_blocked.py`.
- Do not edit any repository file. System-temporary probe files are allowed.
- Write exactly one output file: `runs/conference/ci_phase3_task35_acceptance/general_pi_qwen38_round2.md`. This path is runner-owned: return the complete report and let the runner persist it; do not write it with tools.

你上一轮提出的 P0/P1 已由实现者针对性修复。请只基于当前最新源码和测试重新运行你自己的原始复现，并核验：

1. 首次协调时，`running` 下 A-HTML 已可交付且 B 证据受阻，直接进入 `partial_delivery_blocked`；A 单报告 HTML 已可交付而 PPTX 受阻也直接进入该状态；`awaiting_user` 等价场景同样可达。
2. 从 `partial_delivery_blocked` 显式重开后，如果实际问题没有恢复，静默协调会重新回到该状态，不会卡在 `running`。
3. v1 已绑定后再绑定 v2，所有公开读写/重开/重绑路径都拒绝陈旧 v1；同版本选择漂移失败关闭。
4. 原始伪造的重绑事件若旧/新对象标识含尾随或重复空白，统一校验拒绝。
5. 连续两次 `awaiting_user -> running` 都能各自重开，单次重放幂等、原因漂移拒绝。
6. 格式在 v1 下受阻但阻断证据不带合同版本时，v1 不可用 `new_contract_version_reopens` 重开，绑定 v2 后可重开。
7. `rebind_report` 返回结果中的条件已指向新报告对象。
8. GT01 精确状态表节点与两个 Task 3.5 精确节点均通过。

请使用项目虚拟环境和系统临时目录进行你自己的复现。不要把“原始接受事件可被直接写入共享事件库”这一安全强化项作为本轮阻断：用户明确不做系统安全测试；但功能性事件一致性和真实恢复仍在范围内。

输出一个紧凑复核报告，明确列出各原始 P0/P1 是否已消除、仍存的功能性 P0/P1（若有）及最小复现，最后严格给出 `PASS` 或 `FAIL` 以及 `P0=<n>; P1=<n>; P2=<n>`。P0/P1 任一非零即 FAIL。
