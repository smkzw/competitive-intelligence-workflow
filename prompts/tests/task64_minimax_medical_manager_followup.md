继续同一 MiniMax 审评 session，复核 Codex 对 Task 6.4 的定向修订。不要重启宽泛审查。

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- 只读；禁止修改文件、联网或安全性测试。
- Runner-managed output path: `runs/tests/task64/minimax_medical_manager_followup.md`; return inline, never write it with tools.

Read these files only:
- `runs/tests/task64/minimax_medical_manager_review.md`
- `runs/tests/task64/cursor_grok_medical_manager_review.md`
- `src/ci_workflow/reports/b/pages.py`
- `tests/reports/b/test_bubble_area.py`
- `tests/reports/b/test_matrix_states.py`

Create/write only this output file:
- `runs/tests/task64/minimax_medical_manager_followup.md`（runner 管理）

实际运行两份目标测试。重点以反例核验：宽泛产品/试验/组别样本量键不能借给具体试验臂，但精确三元键和试验内嵌组别键仍可用；多个安全性时间窗必须“待核实并请选择口径”，不能误写“未报告”；已有安全性维度但筛选不匹配也须与真实未报告区分；无唯一总体 TEAE 时默认不得静默退到 SAE/AESI；疗效桶须包含效应量形式。明确判断 P0/P1 是否清零，并列出仍须留到真实页面的视觉项。
