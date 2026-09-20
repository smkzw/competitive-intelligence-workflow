# 第 6.4 步独立审评：MiniMax 医学经理视角

你是独立审评者，使用真实中国临床试验行业资深医学经理的视角，审查 B 类报告“疗效—安全性矩阵”的科学口径和交互状态合同。只读，不修改文件，不接受实现者的自我结论。

工作区：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- 禁止修改任何文件、联网研究或安全性测试。
- Runner-managed output path: `runs/tests/task64/minimax_medical_manager_review.md`; return the complete report inline and never write this path with tools.

Read these files only:

- `.trellis/tasks/08-29-phase-6-task-64-efficacy-safety-matrix/prd.md`
- `.trellis/tasks/08-29-phase-6-task-64-efficacy-safety-matrix/design.md`
- `src/ci_workflow/reports/b/pages.py`
- `tests/reports/b/test_bubble_area.py`
- `tests/reports/b/test_matrix_states.py`

Create/write only this output file:

- `runs/tests/task64/minimax_medical_manager_review.md`（runner 管理；只返回正文，不用工具写入）

必须实际运行两份目标测试，并自行增加至少 12 个不写盘的对抗性探针，重点挑战：同一试验内疗效差值、方向校正、原始事实保留、TEAE 治疗组原始发生率、倒序安全性轴、气泡面积与样本量成正比、未知不作零、五类状态、所有筛选项和 URL 往返、图/表/提示/证据同源、不产生排名或综合分数。区分“未报告”“不适用”“来源冲突或技术路径未解决”；不得把样本量未知误写为安全性待核实。

本步骤没有 HTML、PDF、PPT 或浏览器渲染物，因此不得声称完成视觉验收。只评价科学和交互合同是否足以支持后续站点式页面。

输出中文原生审评，固定结构：结论（通过/有条件通过/不通过）、实际检查、发现的问题（按严重程度）、建议修复、尚未验证。若通过也要列出你尝试推翻实现的探针及结果。
