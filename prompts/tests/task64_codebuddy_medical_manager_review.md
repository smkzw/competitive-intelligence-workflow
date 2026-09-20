# 第 6.4 步独立审评：CodeBuddy 医学经理视角

在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 对第 6.4 步做只读、独立、反证式审评。角色是视觉敏感、希望一眼看懂但不熟悉程序操作的中国临床试验资深医学经理。不要修改任何文件。

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- 禁止修改文件、联网研究或安全性测试。
- Runner-managed output path: `runs/tests/task64/codebuddy_medical_manager_review.md`; return the complete report inline and never write this path with tools.

Read these files only:

- `.trellis/tasks/08-29-phase-6-task-64-efficacy-safety-matrix/prd.md`
- `.trellis/tasks/08-29-phase-6-task-64-efficacy-safety-matrix/design.md`
- `src/ci_workflow/reports/b/pages.py`
- `tests/reports/b/test_bubble_area.py`
- `tests/reports/b/test_matrix_states.py`

Create/write only this output file:

- `runs/tests/task64/codebuddy_medical_manager_review.md`（runner 管理；只返回正文，不用工具写入）

运行目标测试，并执行至少 12 个不会写盘的临时对抗探针。

审查科学底线：试验内治疗—对照疗效信号、方向校正、TEAE 默认纵轴、治疗组原始发生率、倒序轴中文说明、气泡面积按治疗组样本量缩放、缺失不作零、五类比较状态、全部筛选项与 URL 可复现、图表/明细/提示/证据身份同步、无排名/无综合分数/无跨试验池化。特别查找“测试绿但真实医学经理会误读”的语义问题。

本步骤尚无页面或导出物，不能完成视觉审评；请把需要留到后续真实浏览器/PDF/PPT 阶段验证的项目单列。

用中文输出：结论、实测证据、严重问题、一般问题、后续真实视觉验收清单。即使通过，也说明你怎样尝试推翻它。
