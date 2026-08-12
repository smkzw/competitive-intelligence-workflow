继续同一 Task 3.1 独立方案审查会话 `019ff225-134d-7321-9d40-919702c3d90d`，只复核上轮剩余 5 个 P1。

Hard boundaries:

- 只读；不修改文件，不实现 Task 3.1，不扩展到 Task 3.2，不进行安全测试。
- Runner-managed output path: `runs/codex-subagent_ci_phase3_task31_plan_followup2.md`. Do not write that report path with tools.

Read these files only:

- `runs/codex-subagent_ci_phase3_task31_plan_followup.md`
- `docs/decisions/0011-phase-3-evidence-gates-and-recovery.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/design.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/implement.md`

逐项核对：

1. A 的开发成熟度与临床结果状态是否为封闭集合；`result_bearing` 是否只由目标适应症适格试验中已接受的观察性疗效/安全数值事实推导，并排除计划样本量、计划终点、目标值和方案假设。
2. 来源角色、披露成熟度、事实状态和冲突处置是否为封闭枚举；C 的登记设计来源是否避免被结果成熟度序误判。
3. 只收紧偏序是否固定集合包含/子集、成熟度序、阻断布尔和允许操作类型，不能靠单元数量或总分。
4. 规则结果不可变键是否绑定报告、证据快照、基础规则、项目合同和适用对象摘要；受影响报告是否由反向依赖计算且拒绝调用方错误声明。
5. B 的逐组基线、治疗/对照、单臂、多臂、组级安全，以及 A 疗效/安全分支和覆盖增加/提高分支，是否已拆成足够明确的 exact nodes。

输出 `# Phase 3 Task 3.1 独立方案最终复核`，结论 PASS/FAIL、P0/P1/P2、五项结果与仍需最小修补。只有 P0/P1=0 才可建议激活 Task 3.1。
