# Task 4.5 r3 复核操作记录

## Check #1：筛选产品乙后柱图与状态矩阵真实内容
- 入口：`http://127.0.0.1:8767/efficacy.html`，1280×900
- 筛选产品乙：URL `ps=product:product-beta`
- 表格可见行：4 行（产品乙·治疗组 EASI / 产品乙·治疗组 治疗期不良事件 / 产品乙·对照组 EASI / 产品乙·试验二 试验完成状态）
- **chart-1（EASI bar）SVG 内容**：bar 文本仅 "-7.9" + x 轴仅 "对照组" — 没有 -18.4 / -8.6（产品甲）和 -7.9 仍在 ✓
- **chart-3（status_matrix）SVG 内容**：Y 轴 "试验二" + X 轴 "状态" + cell "进行中" — 没有 "试验一" 和 "已完成" ✓
- chart-2（heatmap）：height=0，因为产品丙·疾病活动度 不在筛选范围内 ✓
- chart-0（EASI 治疗组）：--undisclosed class，height=0，因为产品乙·EASI 治疗组 = 未公开 ✓
- 截图：02_bar_minus79.png、03_status_trial2.png

## Check #2：固定产品甲 EASI 后打开产品丙 疾病活动度
- 点击当前数据 row 0 → drawer 显 产品甲·主要终点 EASI
- 固定此条 → URL `e=report-row_02b92005...`、pinned panel 出现单列
- 点击 row 4 → drawer 切到 产品丙·次要终点疾病活动度评分
- **Caliber-mismatch 中文提示**：固定对照 panel 顶部显示 "**指标定义、分母存在差异；并列用于核对口径，不代表可以直接比较数值。**"
- 截图：04_diff_alert.png、05_diff_table.png

## Check #3：固定产品甲后筛选产品乙
- 操作：先固定 row 0（产品甲 EASI），然后筛选产品乙
- **主页面显示中文 toast/通知**："**筛选范围已更新：已移除 1 条不在当前筛选范围内的固定数据。**"
- URL 中 `e=` 段被移除（只剩 `ps=product:product-beta`）
- drawer 关闭（因为当前 inspected row 也是产品甲，越界）
- 当前数据表 4 行（产品乙），"匹配 4 项结果"
- 截图：06_filter_overflow.png

## Check #4：1024×768 抽屉可读 + 不拦截图表
- 抽屉 width=397px（自适应收缩），左 611 / 顶 147，宽度约占视口 39%
- 抽屉位于页眉下方（页眉到 y≈50；drawer 从 y=147 开始）✓
- 抽屉内 14+ 字段全可读：产品/试验/组别/终点/量表/时间点/值/阈值/单位/分子/分母/披露状态/规范化说明/来源版本/原文定位/简短原文
- 点击 -8.6 bar 区域 → URL `eo=report-row_31abe33259abf8ba593403a7` → drawer 切换到 产品丙·次要终点 ✓ 点击未被拦截
- 截图：10_1024_drawer_open.png、11_1024_bar_click.png

## 顺带回归检查（EASI / heatmap / status matrix / 2400px 空白）
- EASI 终点单位 = "分"（分数），不是 mg/dL ✓
- chart-1 SVG 文本：-18.4 / -8.6 / -7.9 ✓
- chart-2 heatmap 文本：-12.1 / -9.4 ✓
- chart-3 status_matrix 文本：试验一 / 试验二 / 状态 / 已完成 / 进行中 ✓
- chart-0 EASI 治疗组 = --undisclosed（不是空白 bar）✓
- 文档高度 3493px（r1 5219px → -33%），.kz-fixture-spacer 已不可见 ✓