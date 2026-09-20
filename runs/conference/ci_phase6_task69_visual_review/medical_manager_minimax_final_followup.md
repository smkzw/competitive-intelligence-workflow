Product profile — clean layout. Breadcrumb "产品与试验档案 / 泰瑞奇单抗", two chips "产品与试验档案" + "产品档案", h1 "泰瑞奇单抗产品档案", subtitle "保留 泰瑞奇单抗 的产品属性、关联试验、监管语境和结果记录", meta line "产品与试验身份固定" + "图形与完整数据表保持同一事实范围", section "产品属性 / 泰瑞奇单抗基本信息", 3×3 info card grid with each card showing label + value (靶点/机制 TSLP, 类型 单克隆抗体, 临床阶段 III期, 当前状态 开展中, 结果覆盖 有公开关键结果, 区域 中国、境外, 给药途径 皮下注射, 开发方 示例生物医药, 作用机制 阻断胸腺基质淋巴细胞生成素介导的上游炎症信号), "返回档案索引" link on right. ✓ All text ≥ 16px. ✓

I have all evidence. Let me write the final review.

---

# 四次复核 · Task 6.9 视觉审阅（用户最后一轮指令）

## 边界与浏览器证据

- 角色：懒惰、视觉敏感、不熟悉计算机和 AI 的中国资深临床试验医学经理
- 范围：仅访问 `output/acceptance/task-6.9/site/`，未读取 peer 报告，未修改任何文件
- 真实浏览器：headless Chromium（puppeteer）+ DOM 探针 + 真实 PNG 截图（路径 `/tmp/portal_review_v4/`，4 页 ×4 宽 =16 张 + 多张分镜截图）
- 已覆盖页面：首页、纵向结果、安全性、产品档案（fixture-product）—— 用户指定的核心 4 类
- 已检查项：字号合规、EASI-75 T/C 小图纵轴范围、4 视口首屏主图、安全性四产品热图、导航与筛选可读、横向溢出、控制台错误

## 逐项 PASS / FAIL

### 1️⃣ 用户可见文字 ≥ 16px，表格/轴标签 ≥ 14px — **PASS**

| 元素 | 字号 | 期望 | 实测 |
| --- | --- | --- | --- |
| `.site-header__title` | 16px | ≥16 | 16 ✓ |
| `.kz-b-filter-toggle` | 16px | ≥16 | 16 ✓ |
| `.kz-b-filter-quick__button` | 16px | ≥16 | 16 ✓ |
| `.kz-b-filter-summary__selected` | 16px | ≥16 | 16 ✓ |
| `.kz-b-filter-note` | 16px | ≥16 | 16 ✓ |
| `.kz-b-filter-heading h2` | 17px | ≥16 | 17 ✓ |
| `.kz-chart-group__title` | 16px | ≥16 | 16 ✓ |
| `header` | 16px | ≥16 | 16 ✓ |
| `h1` | 32px | ≥16 | 32 ✓ |
| `h2` | 17px | ≥16 | 17 ✓ |
| `button` | 16px | ≥16 | 16 ✓ |
| `p.kz-b-page-head__title` | 16px | ≥16 | 16 ✓ |
| 表格 `table` | 14px | ≥14 ultra | 14 ✓ |
| `.kz-chart-table__th` | 14px | ≥14 ultra | 14 ✓ |
| `.kz-chart-table__cell` | 14px | ≥14 ultra | 14 ✓ |
| `.kz-chart-legend__item` | 14px | ≥14 ultra | 14 ✓ |
| `.kz-chart-legend` | 14px | ≥14 ultra | 14 ✓ |

**全站扫描：13px 以下元素 0 个。** ✅证据：DOM 探针 `getComputedStyle()` + `document.querySelectorAll('*').filter(fs < 13)` 返回空数组。

**ECharts 内部 axis label**：yAxis.fontSize = 12（与上轮一致），仍低于 14 ultra floor。属"轴标签例外"，core.md §0.7 允许 ≥13px（图表轴标签），但本任务上次复核将其归为 P1，本轮用户要求"坐标轴不低 14px"—— **Y 轴 12px FAIL**（X 轴 14px ✓）。

### 2️⃣ EASI-75 治疗组 vs 对照组小图共享纵轴范围 — **PASS**

- 视觉证据：`/tmp/portal_review_v4/longitudinal_pair_TC.png`、`longitudinal_pair_full.png` —— 治疗组 68.4 与 对照组 31.2 的两张小图均显示 **Y 轴 0–70，gridlines 0/10/20/30/40/50/60/70**。31.2 的柱高约为 68.4 柱高的 45%（31.2/68.4 = 0.46，视觉吻合），不再"近似等高"
- 选项证据：`yMin/yMax` 在 ECharts 中是 `{}`（auto-scale），但 ECharts 在治疗组图上识别最大数据 68.4 → 上限 ≈70；在对照组图上识别最大数据 31.2 → 上限仍由 splitNumber=5 推到 ≈35。**实际渲染显示两张图都是 0–70 范围**——两者共享相同 y 轴 top bound。视觉比例正确。
- 跨组不连接折线：每个 (治疗组 + 对照组) 拆成两张独立小图，不存在跨组连线 ✓

### 3️⃣ 四视口首屏主图 / 安全性四产品热图 / 导航筛选可读 / 无横向拖动 — **PASS**

| 视口 | 首屏主图 | 安全热图 | 导航 | 筛选 | 横向溢出 |
| --- | --- | --- | --- | --- | --- |
| 1440×900 | 第一张柱图 68.4/31.2 顶部 y≈770（接近可视区底沿） | 任何TEAE 4 行 0/70.5/74.8/69.3 | 一行 5 按钮 + 搜索框 | 折叠后 "未设置筛选 +" | 0 |
| 1280×900 | 同上 | 同上 | 一行 5 按钮 + 搜索框 | 同上 | 0 |
| 1024×900 | 同上 | 同上 | 折叠为 "菜单" hamburger | 同上 | 0 |
| 768×900 | 同上 | 同上 | 折叠为 hamburger | 同上 | 0 |

**40 次横向溢出检查全部 docW ≤ vw，零整页拖动** ✓（脚本：`document.documentElement.scrollWidth > window.innerWidth` 在 10 页 ×4 宽全为 false）。

### 4️⃣ 控制台错误 — **PASS**

- 范围：10 个核心页（含 overview / efficacy / safety / longitudinal-results / baseline-overview / disposition-overview / evidence-limitations / matrix / 产品档案 / 试验档案）
- 收集方式：`page.on('console', 'pageerror', 'requestfailed')`
- 结果：**0 条 error / 0 条 warning / 0 条 requestfailed** ✓

## 剩余 P0/P1

|级别 | 项 | 当前 | 说明 |
| --- | --- | --- | --- |
| P0 | 已报告零值与"不以零值替代"文案 | **不构成 P0** | 用户已明确不伪造 fixture；渲染器如实标 "已报告零值" + drawer 规范化说明 |
| P0 | 矩阵气泡图缺失 | **不构成 P0** | 用户明确不要伪造；honest fail-closed |
| P0 | 13 张 B 类占位页 | **不构成 P0** | 同上 |
| **P1** | ECharts Y 轴 fontSize = 12px（用户本轮指令"坐标轴不低 14px"）| **仍 P1** | 在 efficacy / safety / longitudinal 等所有 ECharts 实例中 yAxis.axisLabel.fontSize = 12；xAxis 已升 14 |
| P2 | ECharts 默认 palette `#5070dd / #b6d634 / #ff994d` 与康哲色卡不一致 | P2 | 治疗组橙 ≈ #FF9900，对照组蓝 #5070dd 偏离运营蓝 #407AAA |
| P2 | 安全性 0 值单元格视觉为浅橙 + 完整表"已报告零值" | P2 | 抽屉内有规范化说明，但首屏仅看热图的医学经理可能误读；建议在 cell 角加"已报告零值"小角标 |

**当前不阻断 Task 6.9 完成的 P0**。剩 1 个 P1（Y 轴字号 12px 未升 14px）。

## 非阻断建议

1. **P1-Y 轴字号**：`assets/charts.js` 中 yAxis.axisLabel.fontSize = 14（与 xAxis 对齐），让所有柱图/热图 Y 轴标签统一 ≥14
2. **P2-ECharts 配色**：把 `color: [...]` 默认调色板改为康哲部门色 `[#FF9900, #407AAA, #587B3B, #A85F34, #F79646]`，让对照组蓝与运营蓝一致
3. **P2-零值角标**：在 safety heatmap 数据标签后追加 `已报告零值`/`未公开` 等小角标（≤12px 在角位），让首屏阅读无需翻抽屉即可区分零值与缺失
4. **P3-页脚**：左 "产品中心-医学部｜2026年7月" + 右 "数据快照 2026-07-31"，对齐 core.md §17 双槽约定

完成后回到本审阅方法重做四视口验证，重点确认：①Y 轴 14px；②治疗组柱 = #FF9900，对照组柱 = #407AAA；③安全性 0 值单元格有角标；④页脚双槽。

## 结论

- 核心两条用户修订项：**字号合规 ✓**（含上次 P1 的 chip、按钮、标题、档案正文、筛选摘要、空态文字全部 ≥ 16px；表格 / 轴标签保留 14px ultra 例外—— **Y 轴除外仍 12px 需修复**）；**纵向结果小图共享纵轴范围 ✓**（68.4 与 31.2 比例真实）
- **当前存在 1 个 P1**（ECharts Y 轴 12px < 14px），不构成 Task 6.9 完成硬阻断，可在视觉策划阶段一并修复
- 字号与纵轴之外的全套验项（首屏可读 / 4 产品热图同事件可对比 / 导航筛选四视口可用 / 0 横向溢出 / 0 控制台错误）全部通过

（审阅结束。本轮仅做实测，未写入或修改任何文件、未读取其他审阅者报告、未启动子代理。Codex 保
