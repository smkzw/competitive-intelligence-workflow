# 第 6.4 步独立审评：Cursor Grok 医学经理视角

你是与构建者隔离的反方审评者。请在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 中，以真实中国临床试验行业资深医学经理的使用方式，只读审查 B 类报告疗效—安全性矩阵合同，不修改文件。

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- 禁止修改文件、联网研究或安全性测试。
- Runner-managed output path: `runs/tests/task64/cursor_grok_medical_manager_review.md`; return the complete report inline and never write this path with tools.

Read these files only:

- `.trellis/tasks/08-29-phase-6-task-64-efficacy-safety-matrix/prd.md`
- `.trellis/tasks/08-29-phase-6-task-64-efficacy-safety-matrix/design.md`
- `src/ci_workflow/reports/b/pages.py`
- `tests/reports/b/test_bubble_area.py`
- `tests/reports/b/test_matrix_states.py`

Create/write only this output file:

- `runs/tests/task64/cursor_grok_medical_manager_review.md`（runner 管理；只返回正文，不用工具写入）

实际执行目标测试，并用临床上可能出现的边界输入进行至少 12 个临时、不写盘的反例测试。

重点判断：治疗—对照是否严格来自同一产品、同一试验、同一终点定义/时间点/人群/分析形式；方向校正是否只改变展示坐标而不篡改原值；安全性纵轴是否是治疗组原始发生率且方向说明清楚；样本量是否按面积而不是半径线性缩放；缺失和不适用是否不会变成 0；安全性事件、时间窗、分析集、分母口径及产品/试验/靶点切换后，图、表、提示、证据、URL 是否同源；是否出现暗含排名、综合评分或跨试验合并。

当前没有可渲染页面，明确写出“视觉验收未发生”，不要以代码通过代替视觉结论。

输出：结论（通过/有条件通过/不通过）、证据、阻断问题、非阻断改进、未验证范围。中文原生、临床语境、不要写空泛工程评价。
