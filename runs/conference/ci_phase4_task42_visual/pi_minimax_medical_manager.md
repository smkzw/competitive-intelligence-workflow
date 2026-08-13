Other reviewer files are there. Let me compose the review.

---

# Task 4.2 视觉与浏览器验收 · 资深医学经理视角

## 一、证据来源

**视觉**
- `.artifacts/task42-portal/current/screenshots/overview-1280.png`（1280×900）
- `.artifacts/task42-portal/current/screenshots/overview-1024.png`（1024×900）

**实时浏览器（Camoufox，1728×947 视口）**
- `http://127.0.0.1:8765/overview.html`、`…/longitudinal-results.html`、`…/safety.html`
- 通过 CSS 强制 `html,body{max-width:1024px}` 复现 1024 折叠样式
- 控制台无 error / pageerror；body.innerText 不含英文词；不含 `gate/signal/accepted/pending/not_run/registry-only/TODO/log/API` 等后端词

**源码（只读）**
- `b-portal/overview.html`、`b-portal/efficacy.html`、`b-portal/safety.html`
- `b-portal/assets/portal.css`（1024 / 1100 媒体查询）、`b-portal/assets/portal.js`、`b-portal/assets/logo.svg`

**已发现的工具限制**
- MCP `browser` 的 `run` 通道只回显源码不返回执行值；切换到 `mcp__camofox_*` 后正常。
- Camofox 不开放 viewport 参数；1024 视觉通过 CSS 注入复现（与浏览器媒体查询等效）。
- `overview-1024-menu.png`、`overview-1440.png`、`overview-1920.png` 是 01:06 的旧壳（标题 竞品全景 / 疗效比较 / 安全性比较，无分组导航），与本次 01:26 重写的 `b-portal/` 不一致，不能作为当前验收证据。

## 二、视觉与文字结构

**1280 桌面**：白底 + 浅色 sticky 顶栏。顶栏从左到右：康哲正式 Logo（121×25 SVG，`#F29600` 椭圆 + "CHINA MEDICAL SYSTEM" 黑字与"康哲药业"中文）+ 站点名 `特应性皮炎试验结果比较`；中部 4 组导航（`总览` 高亮橙色下划线；`疗效与安全性` / `基线与人群` / `试验完成情况` / `试验与证据` 折角下拉）；右侧 200px 级搜索框 `搜索页面…`。Logo 与站点名之间无字距冲突，导航与搜索无重叠。

**1280 主页体**：橙色 kicker `总览` + H1 `首页` + 引导文 "本页给出特应性皮炎试验比较总览，便于进入疗效、安全性与人群结构。" + 1×3 阅读路径卡（`01 主要终点总览` / `02 关键安全性` / `03 疗效与安全性位置`），卡顶 1px 橙线、卡身白底圆角，hover 上浮。下方空白到底部，全局页脚 `供产品中心-医学部内部研判使用。` 单行居中。

**1024（强制宽度复现）**：顶栏压缩为 Logo+站点名 + `菜单` 按钮；导航、搜索全部隐藏到折叠区。点开 `菜单`：4 组标签纵向铺开（每组占一行，触发器与桌面相同，箭头下旋）。主页体标题字号降到 28px（H1），阅读路径卡改为 1 列垂直排列。

**文字**：标题、导航、搜索、按钮、页脚、kicker、lead、卡片标题全部中文。"全局搜索""搜索页面…""菜单"皆为标准中文表达，无"A/B/C 报告"、`gate/signal/accepted/pending`、`AI evidence synthesis`、`TODO`、`console`、`fetch`、`placeholder`、lorem ipsum 等禁词。

**Logo**：橙色椭圆 + 白色"CMS"字 + 黑色"CHINA MEDICAL SYSTEM / 康哲药业"，121×25 像素正式资产，不是文字冒充。

## 三、端到端路径（医学经理模拟）

| 步 | 动作 | 结果 |
|---|---|---|
| 1 | 进入 `overview.html` | kicker `总览`、H1 `首页`，active 导航为 `总览` ✓ |
| 2 | 输入"疗效" | 顶部 5 条结果 `疗效 / 疗效与安全性矩阵 / 首页 / 纵向结果 / 安全性`，键盘可用 ✓ |
| 3 | 点 `疗效` 下拉 → `纵向结果` | 跳转到 `longitudinal-results.html`，kicker `疗效与安全性`、H1 `纵向结果`，顶栏 `疗效与安全性` 触发器呈 current 态（橙色下划线） ✓ |
| 4 | 搜索 `安全性` | 5 条结果命中，列表第一项即 `安全性`，回车 / 点击即跳转 `safety.html` ✓ |
| 5 | 在 `safety.html` 返回 `首页` | 顶栏无 `总览` 高亮链接（总览仅在自身页面有 `--active` 标签），必须用 Logo 回首页；用 Logo 成功跳回 `overview.html` ✓ |
| 6 | 1024 折叠：开/关菜单 | `菜单` 按钮切换 `aria-expanded`，`.site-header__nav.is-open` 控制显示；折叠菜单下点击组标签可触发面板 ✓ |

**直观之处**：顶栏 Logo + 站点名 + 导航 + 搜索四件套识别度好；kicker → H1 → lead 的层级清晰；1280 与 1024 折角一致；搜索框对常用关键词命中准确。

**困惑之处**：
- 首页 kicker `总览` 与 H1 `首页` 同时出现，且 lead 又写"比较总览"——同一页面承担三种自称，医学经理会问"这是入口还是总览？"
- 3 张阅读路径卡只有编号 + 标题，没有链接、没有一句话说明、没有目标段落锚点，体感是占位，不是"按结构快速定位重点内容"。
- dropdown 面板在 1280 下展开时与下方 lead 文案在 y≈188–205 发生矩形相交（实测 overlap=true，面板 z-index 120、白底），"便于进入疗效、安全性"被面板遮住一截，"人群结构。"挤到面板右侧——用户视线会被面板切两半。

## 四、对用户既往关切的逐条回应

1. **冗余标题/副标题**：kicker `总览` + H1 `首页` + lead 重述"总览"，三处同一含义——落实。
2. **日志/提示词标签**：body 无任何禁词；CN-原生中文——通过。
3. **混合中英**：body 全文中文（aria-label 等 HTML 属性除外）——通过。
4. **缺 Logo**：使用正式 `assets/logo.svg`（CMS 椭圆+中文康哲药业）——通过。
5. **串行文字**：顶栏 Logo、站点名、4 组导航、搜索在 1280 不串行；1024 Logo+站点名 单行、不挤——通过。
6. **不可达图先入为主**：本任务范围内不存在图表，但也没有"占位图""即将上线"等过渡文案——通过；阅读路径卡的"占位感"是 P1 项。
7. **不像模板 demo**：壳层已经具备品牌橙识别、sticky 头、kicker/H1/lead/卡/页脚的骨架；问题在于首页"阅读路径"卡片是空壳（仅有标题）——见 P1-2。

## 五、判定

### P0（阻塞）

无 P0 阻断。导航/搜索/Logo/可访问性/中文-原生/无 console 错误全部满足 Task 4.2 PRD 的硬性验收点。

### P1（接受前必修）

| # | 现象 | 证据 | 医学经理影响 | 最小修复 |
|---|---|---|---|---|
| P1-1 | 导航 dropdown 面板与下方 lead 文案在 1280 视口 y≈188–205 矩形相交，遮挡"便于进入疗效、安全性" | Camofox 实测 `overlap=true`，1280 截图肉眼可见 | 医学经理打开"疗效与安全性"想看子项时，正文被遮；视线被迫在面板和文案之间跳 | 给 `.site-header__nav` 加 `background:#FFFFFF` 满宽覆盖，或在 lead 与 H1 之间增加 24–32px 间距，或 dropdown 改为 hover-开启并将触发器置于面板上方 |
| P1-2 | 首页"阅读路径"3 张卡只有编号+标题，无链接、无正文、无锚点 | `b-portal/overview.html` 第 98–109 行；`.portal-path-card` outerHTML 不含 `<a>`、tabIndex=-1、cursor:auto | 医学经理把卡片理解为"目录"，点不动；体感是模板 demo，违背"按页面结构快速定位重点内容"的承诺 | 把 `<li>` 升级为 `<a href="…#anchor">`，或给每张卡加 1 句摘要 + 锚链接；至少 `--current` 页面卡片可点击 |
| P1-3 | 顶栏 active 状态只到组级：当前页是 `纵向结果` 时，仅 `疗效与安全性` 触发器有橙色下划线，子链接 `纵向结果` 没有 `--active` 类 | `portal.css` 第 262–266 行定义 `.site-nav-group__link--active`，但 `portal.js` 仅 toggle 触发器、从不给链接加 `--active` | 医学经理在 `纵向结果` 页打开 `疗效与安全性` 看不到当前页高亮，需对照 H1 才能确认位置 | 在 `portal.js` 中读取当前页 slug，给对应 `.site-nav-group__link` 加 `--active` 类；CSS 已有现成选择器 |
| P1-4 | 首页标题冗余：kicker `总览` + H1 `首页` + lead "……比较总览" | `b-portal/overview.html` 第 88–90 行 | 医学经理在同一屏看到 3 次"总览/首页"，层级含糊 | 把 H1 改为 `特应性皮炎试验结果比较·总览` 或 `竞品格局总览`；kicker 保留 `总览` 作章节徽章；lead 去掉"总览"二字重写 |

### P2（可延后到后续 task）

- 1280 截图右下半屏约 250×400px 留白（卡片后无内容），Task 4.2 范围内允许；后续 Task 4.4 图表/表格落地后会自然填满。
- 顶栏搜索框宽 220px，1280 下视觉上偏向"小工具条"；放到 1440+ 会更好（合同允许）。
- Logo 与站点名之间在 1024 折叠态略紧，但不串行。
- 仅截图（overview-1024.png 等）未覆盖 1440/1920 的当前壳——需重新截图以与 HTML 重写保持一致。
- 其他 18 个物理页（基线、试验完成情况、试验与证据）的 kicker / H1 / lead 我已抽样确认（longitudinal-results、safety 均正常），但 21 页内容我未一一打开；建议在 Task 4.6 真实全页验收前至少每个组抽 1 页做视觉确认。

## 六、裁决

**FAIL**：P1-1、P1-2、P1-3、P1-4 中任一项不修都会让医学经理"快速定位重点内容"或"识别当前页"产生迟疑或误解；建议修完后重新走视觉与浏览器复看，再进入 Task 4.3/4.4/4.5。

## 七、残余限制

- Camofox 视口固定 1728×947，1024 折叠态通过 CSS 强制宽度模拟；不是 1024 设备真实像素测量。
- 仅核验 3 个抽样页（overview / longitudinal-results / safety）+ 总览菜单展开；其余 18 个物理页未在浏览器打开。
- 截图 `overview-1440.png`、`overview-1920.png`、`overview-1024-menu.png` 为旧壳残留，不能作为本次验收证据；后续真实浏览器任务（Task 4.6）必须按 1280 / 1440 / 1920 三档重新出图。
- MCP `browser.run` 在本会话不返回值，已切换到 `mcp__camofox_*` 工具完成端到端交互；不会影响最终验收。
- 本评审严格只覆盖 Task 4.2 壳层（branding、标题层级、分组导航、搜索、页面互通、空壳信息节奏、中文-原生、视觉清晰度）；不评价 Task 4.3 筛选、4.4 图表/表、4.5 证据抽屉的真实数据。
