# 定稿前视觉闭环专项审阅上下文

## 目标

以真实资深临床试验医学经理的使用视角，独立审阅新建立的“视觉策划—候选生成—真实渲染—定向美化—独立放行”机制是否足以防止不可读、工程化、只跑通流程的报告进入正式交付。

## 权威材料

- `.trellis/tasks/08-29-cross-format-visual-finalization/{prd,design,implement}.md`
- `docs/decisions/0012-pre-delivery-visual-finalization-loop.md`
- `contracts/kangzhe/design_specs/project_profile.md`
- `skills/_internal/visual-design-director/SKILL.md`
- `skills/_internal/render-deliver/SKILL.md`
- `skills/_internal/visual-package-qc/SKILL.md`
- `schemas/visual-finalization-plan.schema.json`
- `src/ci_workflow/graph/{visual_finalization,guards,transitions}.py`
- `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/` 中的实际页面截图与 `metrics.json`

## 审阅边界

- 全程只读，不修改代码、合同、报告或证据。
- 必须实际查看至少 768、1024、1440 三种宽度的首页与安全性页面截图；可使用视觉/浏览器工具。
- 不把文件存在、测试通过、没有横向溢出或执行者自述当作视觉接受。
- 重点评估机制，不替代 A/B/C 科学结论或 PDF/PPT 正式成片验收。
- 若发现问题，给出可定位、可验证的修订要求；不得以泛泛“更美观”代替。
