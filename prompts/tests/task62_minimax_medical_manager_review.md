MODE=TEST

你是独立测试者，以中国临床试验行业资深医学经理身份只读审阅 Task 6.2。不得修改任何文件，不得把测试通过当成最终验收。

工作区：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`

## Hard boundaries

- 只读，不修改工作区文件，不联网，不启动其他 Agent。
- 运行器管理输出文件；不要用工具写入该文件，只在最终回复返回完整测试结论。

Read these files only:

- `.trellis/tasks/08-29-phase-6-task-62-efficacy-longitudinal/prd.md`
- `.trellis/tasks/08-29-phase-6-task-62-efficacy-longitudinal/design.md`
- `.trellis/tasks/08-29-phase-6-task-62-efficacy-longitudinal/implement.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §§11.6、15.3–15.7
- `src/ci_workflow/reports/b/contracts.py`
- `src/ci_workflow/reports/b/efficacy.py`
- `tests/reports/b/test_guideline_endpoint_basis.py`
- `tests/reports/b/test_efficacy_views.py`
- `tests/reports/b/test_user_sorting.py`

Write exactly one output file: `runs/tests/task62/minimax.md`

请真实运行三份测试，并主动设计最小探针核查：
1. CDE/FDA 当前指南平行、草案/废止不驱动默认、语境差异分列；指南推荐但竞品未采用时仍保留依据。
2. 严格多数与“最常采用”分母、主要终点计数和支持研究排除。
3. 第 12 周与第 24 周能组成同一终点族的纵向序列，同时单时间点比较仍不跨时间窗。
4. 疗效事实不能伪造兼容桶；治疗与对照并列；来源效应量不由两臂值推导。
5. 默认不按疗效值排名；用户排序仅在单兼容桶、未知不按零、重置可逆。

输出：`PASS` 或 `FAIL`；列出可复现缺陷、命令与最小证据。不要泛泛评论，不要联网。
