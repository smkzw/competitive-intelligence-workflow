# 完成记录（2026-08-29）

## 目标与结论

A 类报告两项用户问题已闭合：疗效与安全性已有公开数值不再被错误遮蔽；首页和安全性详情页的默认矩阵不再依赖左右拖动。

## 已验证结果

- 38 个产品中，疗效有数值 28 个，任一安全性有数值 26 个；治疗组精确“任何 TEAE”20 个，治疗/对照均有精确值 19 个。其余按真实公开状态保留“未公开”，没有用估算值填补。
- 最终不可变候选：`.artifacts/a-values-matrix-fix-final-v5/`；运行编号 `run_53cfd694e941fdedbfb28efc`。
- 89 项数据、投影、验收与浏览器测试通过；Ruff、JavaScript 语法和差异格式检查通过。
- Chromium 与 WebKit 在 768、1024、1280、1440 px 检查首页和安全性详情页：页面与图表均无横向溢出、无页面错误。
- 768 px 为 2+2 两块矩阵，1024 px 及以上为四个安全性维度同屏；窄屏表格隐藏“试验”和“人数”列，“未公开”不会逐字断行；粘滞表头位于站点顶栏下方。
- 独立科学复核与同会话视觉复核均通过，Codex 已打开最终截图并复核真实页面。

## 关键证据

- 数据审计：`reviews/ci_phase5_a_values_matrix_fix_data_audit.md`
- 最终截图与测量：`reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v5/`
- 科学复核：`runs/conference/ci_phase5_a_values_science_review_v3/`
- 视觉复核：`runs/conference/ci_phase5_a_values_matrix_visual_review_v4/visual_pi_k3_256k_round2.md`
- Codex 视觉验收：`reviews/codex_conference_ci_phase5_a_values_matrix_visual_review_v4_review.md`

## 后续边界

- 本任务只接受 A 类 HTML 报告的两项指定缺陷，不代表 PDF/PPT 已接受。
- 真实未公开的竞品数据继续显示为“未公开”；后续如取得新证据，应通过证据链入库后重建，不直接修改页面数值。
- 下一项安全动作是进入“定稿前视觉策划—真实渲染—专项美化—独立审阅—放行”机制建设。
