Active task: `.trellis/tasks/08-14-phase-5-report-a`

你是隔离的 Task 5.2 高风险矛盾审查者，只读，不得修改仓库文件。工作区为当前目录。

Hard boundaries:
- 只读工作区，不修改任何源文件、测试、任务记录或产物。
- 不读取 worker 报告、执行日志或其他模型的审查意见。
- Runner-managed output path: `runs/conference/ci_phase5_task52_verify/luna_verifier.md`. Never invoke a write/edit tool on this report path; return the complete report in the final response and let the CLI persist it.

Read these files only:
- `AGENTS.md`
- `.trellis/tasks/08-14-phase-5-report-a/research/task52-contract-extract.md`
- `.trellis/tasks/08-14-phase-5-report-a/design.md`
- `.trellis/tasks/08-14-phase-5-report-a/implement.md`
- `src/ci_workflow/reports/a/pages.py`
- `src/ci_workflow/reports/a/contracts.py`
- `src/ci_workflow/reports/a/analysis.py`
- `src/ci_workflow/reports/a/__init__.py`
- `src/ci_workflow/gates/models.py`
- `tests/unit/reports/a/`
- `tests/reports/a/`

独立验收 `src/ci_workflow/reports/a/pages.py`、`src/ci_workflow/reports/a/__init__.py` 与 `tests/unit/reports/a/` 是否真实满足实施计划 AV01–AV08 和设计书 §12.1–12.3。不得读取 worker 报告或其私有推理；只读批准合同、当前产物、测试和必要的 Phase 3/Task 5.1 强证据合同。

必须实际构造并运行最小反例；临时文件放系统临时目录并清理，不写仓库：

1. 全量产品、无 Top-N、稳定详情路由；missing/extra/duplicate/reordered 输入失败关闭。
2. 任意视图或扩展记录能否用伪造 `fact_version_id`、伪造 locator，或不属于当前 `evidence_snapshot_id` 的版本混入；是否真正消费锁定快照，而非只检查非空字符串。
3. 产品—试验—地域—阶段—状态是否闭合；非核心试验角色是否有科学来源；临床前空集合语义是否正确。
4. 中国/境外监管事件能否跨记录拼接；合同事件与版本事件的一一对应能否被重复值、同值不同来源或状态绕过。
5. 原研、开发者、许可方/被许可方、合作、并购、地域权益、交易事件、公开条款是否独立；空集合是否会产生错误正面结论。
6. 专利族/成员/法域/范围/期限/监管独占是否分开；未知到期不得推断；跨产品、跨法域、跨成员拼接失败关闭。
7. 暂停、终止、撤回、放弃和邻近机制是否全部保留；历史状态是否与 Task 5.1 监管/开发状态一致并绑定当前快照证据。
8. 用户可见标签必须是中文临床/竞争情报语言，无 prompt、log 或后端枚举泄露。
9. 直接构造或 `model_copy(update=...)` 能否绕过权威 builder/model 边界。

运行精确节点、A 联合测试和自建反例。输出必须包含：`Verdict: PASS` 或 `Verdict: REVISE`；P0/P1/P2 问题及精确类/函数；命令与结果；最小修复建议。只有 P0/P1/P2 均为 0 才可 PASS。
