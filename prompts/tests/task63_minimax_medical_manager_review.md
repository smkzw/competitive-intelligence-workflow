MODE=TEST

你是独立挑战测试者，以中国临床试验行业资深医学经理身份只读审阅 Task 6.3。不得修改任何文件，不得把现有测试通过当成最终验收，不联网。

工作区：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`

## Hard boundaries

- 只读，不修改工作区文件，不联网，不启动其他 Agent。
- 运行器管理输出文件；不要用工具写入该文件，只在最终回复返回完整测试结论。

Read these files only:
- `.trellis/tasks/08-29-phase-6-task-63-safety-heatmap/prd.md`
- `.trellis/tasks/08-29-phase-6-task-63-safety-heatmap/design.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §13.2、§13.4
- `src/ci_workflow/domain/enums.py`
- `src/ci_workflow/reports/b/safety.py`
- `tests/reports/b/test_safety_heatmap.py`
- `tests/reports/b/test_ae_state_semantics.py`

重点以反例挑战：明确零与缺失混淆、阈值以下被着色、技术异常伪装为未报告、不同事件定义/时间窗/人群/单位/分母共用色阶、治疗与对照跨试验误配、多个试验被合并、低发生率跨试验重复被误判为来源高频、默认子集删除完整事件、MedDRA 不确定映射强行合并、安全性暗中排名。真实运行两份目标测试，并编写最小一次性探针；不得修改工作区。

Write exactly one output file: `runs/tests/task63/minimax.md`

输出 `PASS` 或 `FAIL`，逐项给出可复现证据和阻断级别。不要泛泛评论。
