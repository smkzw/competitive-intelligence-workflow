继续同一 Task 3.1 独立方案审查会话 `019ff225-134d-7321-9d40-919702c3d90d`，只复核你上轮的 2 个 P0、7 个 P1 和 1 个 P2 是否已写入可执行合同。

Hard boundaries:

- 只读；不修改文件，不实现 Task 3.1，不扩展到 Task 3.2，不进行安全测试。
- Runner-managed output path: `runs/codex-subagent_ci_phase3_task31_plan_followup.md`. Do not write that report path with tools.

Read these files only:

- `runs/codex-subagent_ci_phase3_task31_plan.md`
- `docs/decisions/0011-phase-3-evidence-gates-and-recovery.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/prd.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/design.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/implement.md`

逐项机械核对：

1. 完整产品/试验/比较/组别集合、输入摘要、`enumeration_complete`、未知/重复/漏评/未证明为空失败关闭。
2. B 的 trial/comparison/group 作用域、治疗/对照、单臂/多臂、总体值不得冒充分组值及披露状态不得变零。
3. A 基础单元、成熟度与 `result_bearing` 从事实推导且不可降级；临床前/早期无结果不误阻断，已有临床数值结果同时要求疗效和 TEAE/SAE。
4. C 的完整核心临床设计字段、登记充分例外、Protocol/SAP 不作为独立阻断、统计扩展字段非阻断。
5. 来源角色、披露成熟度、缺失/冲突策略及项目覆盖逐字段只收紧偏序。
6. 父子合同版本、变更摘要、旧结果不可变和只重算受影响报告。
7. 三个测试文件是否已有足够明确的 exact nodes 覆盖非空反例；内部状态与中文用户说明是否分层。

输出 `# Phase 3 Task 3.1 独立方案复核`，结论 PASS/FAIL、P0/P1/P2、逐项结果、仍需最小修补。只有 P0/P1=0 才可建议激活 Task 3.1。
