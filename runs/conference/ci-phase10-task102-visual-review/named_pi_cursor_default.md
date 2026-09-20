先读取会议上下文、设计规范与验收计划，再定位 A/B/C 截图并做只读视觉审查。
接下来我会打开各报告在 1280/1920 下的关键页面截图，并核对浏览器验证报告里的溢出与布局指标。
再用浏览器打开本地验收站点，核对疗效页横向滚动和证据抽屉等交互。
# Visual Review: named_pi_cursor_default

## Boundary Check

- **角色边界**：只读独立审阅；未修改任何验收站点、证据、报告或仓库文件。
- **证据范围**：Task 10.2 隔离验收根目录 `competitive-intelligence-acceptance/task-10.2-20260901-123524/{a-real,b-real,c-real}/` 下的 PNG 截图、`report.json` 浏览器验收报告，以及对本地 HTML 的 live 只读浏览。
- **权威对照**：`contracts/kangzhe/design_specs/project_profile.md`。
- **与 deterministic pass 的关系**：三份 `report.json` 均为 `ok: true`、全路由零 `violations`；**这不等于医学经理视觉放行**——自动化只证明“没报溢出/路由错误”，不证明“打开就能比、看得清、像临床报告”。

---

## Inspected Evidence

### 浏览器 deterministic 报告
| 报告 | 路径 | 结果 |
|---|---|---|
| A | `.../a-real/verification/A/v1/report.json` | `ok: true`，0 violations |
| B | `.../b-real/verification/B/v1/report.json` | `ok: true`，0 violations |
| C | `.../c-real/verification/C/v1/report.json` | `ok: true`，0 violations |

### 代表截图（Chromium，1280×800 / 1920×1080）
**A 类**
- `a_overview__chromium__1280x800.png` / `1920x1080.png`
- `a_efficacy__chromium__1280x800.png` / `1920x1080.png`
- `a_safety__chromium__1280x800.png` / `1920x1080.png`
- `a_matrix__chromium__1280x800.png` / `1920x1080.png`
- `a_overview__webkit__1280x800.png`（跨浏览器抽查）
- `a_matrix__webkit__1280x800.png`（跨浏览器抽查）

**B 类**
- `b_overview__chromium__1280x800.png` / `1920x1080.png`
- `b_efficacy__chromium__1280x800.png` / `1920x1080.png`
- `b_safety__chromium__1280x800.png` / `1920x1080.png`
- `b_efficacy-safety-matrix__chromium__1280x800.png` / `1920x1080.png`
- `b_baseline-demographics__chromium__1280x800.png` / `1920x1080.png`
- `b_disposition-overview__chromium__1280x800.png`

**C 类**
- `c_overview__chromium__1280x800.png` / `1920x1080.png`
- `c_design-map__chromium__1280x800.png` / `1920x1080.png`
- `c_endpoint-timepoint-matrix__chromium__1280x800.png` / `1920x1080.png`
- `c_trial-profile__chromium__1280x800.png` / `1920x1080.png`
- `c_trials_nct04773600__chromium__1280x800.png`（试验详情抽查）

### Live 只读页面（1280 视口）
- A：`overview.html`、`efficacy.html`（含证据抽屉）、`safety.html`、`matrix.html`
- B：`overview.html`、`disposition-overview.html`
- C：`design-map.html`、`endpoint-timepoint-matrix.html`

---

## Medical-manager Findings

### 做得对、能用的部分
1. **A/B 疗效与安全专页基本达标**  
   - A 疗效页：柱状图在前，治疗组/对照组并列，跨试验差异有中文提示；1280 下未见整页横向滚动。  
   - A 安全性热图：单元格内直接印数值 + 观察窗，颜色不作“安全排名”，符合临床阅读习惯。  
   - A 疗效—安全性矩阵：气泡图轴含义（横轴疗效、纵轴 TEAE、气泡=样本量）有中文说明，1280 下完整可见。  
   - B 疗效森林图、安全性热图、气泡矩阵：信息密度高但结构清楚，试验名/登记号保留，不是“某药 III 期”这种糊名。

2. **证据抽屉（A 疗效页 live 验证）**  
   - “查看数据依据”可打开右侧 `数据依据` 面板，列出涉及试验（含 NCT、样本量）和登记/文献/监管来源，中文表达正常——这是我愿意点下去核对的地方。

3. **B 类 live 首页比截图更好**  
   - live `overview.html` 首屏直接给“关键结果”柱状图 + 下方完整表，图先表后；不是空 KPI 卡片。

### 一打开就不满意的部分
1. **C 类是硬伤，当前不可交付**  
   - “设计图谱”“终点、定义与时间点”两个核心页，首屏大表中文内容**叠字、串行、几乎不可读**；我作为医学经理无法做并排设计比较。  
   - 页名写“设计图谱”，实际只有筛选卡 + 宽表，没有图谱/关系图/并排视觉结构——名不副实。  
   - 表里直接露出后端字段 **`trial_identity`**，这是程序字段，不是临床语言。

2. **首屏比较价值不均衡**  
   - A live 首页首屏是“靶点×阶段”格局表，能看竞争分布，但**首屏没有疗效/安全迷你图**，要下滚才看到“主要疗效”柱状图。对“懒惰、只想扫一眼”的医学经理来说，比较动作偏晚。  
   - 验收 PNG 里的 A/B/C 首页却呈现“四个 KPI 全是 — + 大表”，与 live 页面不一致——**截图证据链不可信**，我会质疑验收是否抓到了真实渲染结果。

3. **B 试验完成情况图能看但有脏点**  
   - live 页已有柱状图（比 disposition PNG 里的空卡片好），但 Y 轴标签与数值（如 `125`、合并成 `99.6100.6`）发生重叠，扫一眼会误判。

4. **中文边界仍有工程味**  
   - 页脚“运行记录”、C 表内 `trial_identity` 等，破坏“这是给临床看的报告，不是后台”的感觉。

5. **筛选/下钻一致性**  
   - 三站左侧筛选栏结构基本一致，可用；但 C 类核心表读不懂时，筛选再一致也没有意义。证据抽屉在 C 设计页 live 未稳定触发（按钮/表内“查看依据”未复现 A 类体验）。

---

## Defects And Remediation

| 严重度 | 位置 | 问题 | Remediation |
|---|---|---|---|
| **P0** | C `/c/design-map` @1280/1920 | “设计事实比较”大表文字重叠/ garble，无法阅读试验设计并排内容 | 修复 C 类宽表布局：为“内容/设计要素”列设最小宽度与换行；禁止多行文本 absolute/stack 渲染；1280 下要么列折叠+详情展开，要么改横向对比为小多图/分面试验卡，**不得**靠缩字硬塞 |
| **P0** | C `/c/endpoint-timepoint-matrix` @1280/1920 | “主要终点与评估时间”表中心列同样叠字，终点定义不可读 | 同上；终点定义列单独拉宽或改“试验 × 时间点”矩阵为热图/行卡；确保 IGA/EASI 原文完整可见 |
| **P1** | C `/c/design-map` | 用户可见 **`trial_identity`** 后端字段 | 建立字段→中文标签映射（如“试验标识”或直接隐藏内部 key）；验收加 grep 阻断 `trial_identity`、`gate` 等内部词 |
| **P1** | C `/c/design-map` | 页名“设计图谱”但无图谱，仅表 | 增加真正 design map：按试验/药物节点展示随机、盲法、对照、关键入排阈值；表作“完整字段”下沉，不是首屏唯一载体 |
| **P1** | B `/b/disposition-overview` @1280 | 柱状图数值与轴标签重叠（如 `125` 压 Y 轴名、`99.6100.6`） | 调整 label collision：增大 left margin、智能避让、必要时把数值放到 bar 内部；多试验分面或小 multiples |
| **P1** | A `/a/overview` 首屏 @1280 | 首屏只有格局表，疗效/安全比较需下滚 | 首屏增加“主要疗效/关键安全”各 1 个缩略图（与详情页同口径），保持图先于表 |
| **P1** | 验收 PNG vs live HTML | 多页 PNG 显示空 KPI“—”，live 已有图表内容 | 重跑截图前加 render-ready 等待；manifest 绑定截图 SHA 与 site_digest，防止旧图复用 |
| **P2** | 全站页脚 | “运行记录”偏工程语言 | 改为“数据来源说明”或移出主报告导航 |
| **P2** | B `/b/baseline-demographics` @1280 | 人口学 9 列宽表首屏偏表、列多时阅读吃力 | 默认折叠非核心列；核心字段（年龄/性别/种族/基线 Hb）前置；保留完整表于下方 |
| **P2** | C `/c/trial-profile`、试验详情 | 信息全但首屏偏“档案表”，缺一张“这一试验的设计一眼图” | 试验详情页顶部增加设计摘要卡（阶段、N、随机、盲法、主要终点、关键入排阈值） |

---

## Verdict

**Deterministic browser pass：通过**（三份 `report.json` 全绿、无 violations）。

**医学经理主观视觉验收：否决（Reject）。**

**理由（一句话）**：A/B 的疗效、安全、矩阵专页已基本达到“打开就能比”的临床阅读标准，但 **C 类两个核心比较页在 1280 下不可读**，且存在内部字段泄漏；再叠加验收截图与 live 页面不一致，我不能签字放行 Task 10.2 的视觉交付。

**放行条件**：至少消掉全部 **P0/P1**（C 类表可读 + 去工程字段 + B 处置图 label 修复 + A 首屏比较补强 + 截图证据链重绑），再由非生成方复核 PNG 与 live 一致后，方可重审。
