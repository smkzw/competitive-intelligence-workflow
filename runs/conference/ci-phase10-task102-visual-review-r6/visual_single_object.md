Delegated visual conference pass: I’ll read the assigned brief first, then inspect the R6 A/B/C HTML independently and return the schema-bound report.The venue plan is still a stub; I’ll use the conference source-of-truth list and inspect the R6 HTML plus visual contracts next.Static HTML already shows empty A-matrix cells and C’s long stacked table; I’ll render the live pages and R6 screenshots next to confirm unit split and first-screen readability.# Conference Participant Output: ci-phase10-task102-visual-review-r6 - visual_single_object

## Boundary Check

- **Fallback identity:** Codex 主角色在可恢复会话前不可用。本通为声明的 `pi` fallback：`cursor` / `cursor-grok-4.6`（effort medium）。Grok Build 主路由未在本会话执行。
- **Capability limits:** `pi-worker` 适配器因未知 CLI flag 失败，改为直接读 R6 HTML/JS、冻结 PNG、Camoufox/Chromium 实页。未启动独立 WebKit 浏览器；WebKit 仅核冻结截图。未写生产路径，未改 R6 产物，未主张最终验收。
- **Work dir:** 只读会议包 + 合同明确列入的 R6 真源：`.../competitive-intelligence-acceptance/task-10.2-20260901-123524-r6/{a,b,c}-real/reports/*/v1/` 与 `/verification/*/v1/`。
- **Read:** `context/ci-phase10-task102-visual-review-r6_conference_context.md`；`plans/codex_main_venue_...`（仍为 TODO 桩）；`contracts/kangzhe/design_specs/project_profile.md`；ADR 0012；A/B/C `overview`、`disposition-overview`、`design-map`、`matrix` HTML；B `charts.js`/`report-b.js`；verifier `report.json`（A/B/C `ok: true`）；冻结图 A/B/C overview、matrix、disposition、design-map、endpoint-timepoint、inclusion、safety；Chromium 实页 A overview、B disposition、C design-map。
- **Changed:** 无源码。仅临时 `python3 -m http.server 8765` 后已 stop。
- **Did not read:** 其他 conference 角色产出。

## Independent Work Product

### 会前审计（异议，不只复述任务）

主会场计划文件几乎为空。若把 verifier `ok: true` 当视觉通过，会直接违反 `project_profile.md` §8（截图存在/0 项问题 ≠ 视觉接受）和 §10（无横向滚动 ≠ 核心图完整可见）。R6 机器报告无 overflow/defect 字段，不能替代医学经理可读性。

默认用户是懒、视觉敏感、不熟悉系统的临床试验医学人员。首屏被筛选器与工程字段占满、轴标签碰撞、设计图谱用长英文题目截断，足以否决，即使图表“有数据”。

### 证据（与推断分开）

**A 首屏 / 矩阵**

- 实页与 `overview.html`：H1「创新治疗格局与医学结果」；导语「先看全部创新治疗的靶点结构、开发阶段与关键疗效安全性，再按产品或专题下钻。」适应症在顶栏「特应性皮炎竞品全景」，截止在页脚「数据截至 2026年07月31日」。
- 疗效图：治疗组橙 / 对照蓝，中文药名 +「EASI-75｜第16周」或「IGA 0/1｜第12周/第8周/第4周」同轴 0–100%。
- 热图：单元格有数（如度普利尤单抗 TEAE 73%）；灰「未公开」；同列观察窗混「16周双盲」与「登记报告期」。
- 气泡：实页可访问文本仅约 6 个产品（Amlitelimab、Etokimab、司普奇拜单抗、乐德奇拜单抗、GR1802、611）；标签「Amlite…」；纵轴文案「纵轴越高表示TEAE发生率越低」。
- `matrix.html` 静态表全是「未纳入当前矩阵」；1440 冻结图经 JS 填数，并列出无法形成坐标的产品。图在表前成立。
- 格局图 1440：大量「17 未上市 / 4 已获批」叠字，点簇不可读。
- 合同对照：§10 要求首屏标题只留报告名/适应症/截止，不得解释图表顺序或系统工作方式。

**B 完成情况单位拆分**

- 结构成立：`disposition-overview.html` 有「计量对象=受试者」「统计形式=例数 / 依从性概览」；表头含分子/分母/数值/单位；图在表前。
- 实页 1423×1514 图组标题按试验+单位拆开，例如「多项可比指标｜APPLY-PNH · 受试者人数」「依从性｜APPLY-PNH · 相对剂量强度」，PEGASUS/ALPHA/CHAMPION/COMMODORE 同理。这比“一张总图混单位”更接近任务意图。
- 可用性失败：`charts.js` 对 disposition 用 `hideOverlap: true`、类目为「字段\\n组别」。实页 SVG 类目同时出现「已筛选 / 全研究人群 / 已随机 / 治疗组 / 筛选失败原因」。1440 Chromium 与 WebKit 冻结图均见轴标签截断碰撞；依从性图把「未公开」与 3.6%、97.6% 放在同一 % 轴。
- 用户可见工程词：`alpha-safety-cohort`、`nct04469465-primary-period`、`baseline_ldh`；首页筛选有 `Any treatment-emergent adverse event`；「分母角色 / 字段族 / 计量对象」。
- 首页 1440：疗效/安全/气泡在首屏，完成情况不在首屏；筛选条很高。

**C 设计图谱可比较性**

- 实页 1440×900 与 1423×1514 默认图标题是「核心设计差异」，试验为列、行为「目标人群 / 给药方案 / 主要终点定义 / 计划或实际样本量」，画布高约 1470px（超过 900 视口）。
- 列标签截断：`Efficacy an…`、`Evaluation …`、`A Study to …`、`This Study …`。单元格是整段中英混写，不是对齐的评分/阈值字段。
- 完整表 340 行，列为产品/试验编号/设计要素/内容/时间点/披露状态，长表而非试验×字段矩阵。入选示例：「特应性皮炎病程至少3年（筛选期）」——要并排比 IGA/EASI 阈值须扫全表。
- 筛选 `data-filter-value` 露出 `trial_identity`、`reported_value`。试验按钮用整段英文登记标题。
- `inclusion-criteria` 1440 冻结图主视觉是「已报告值」计数柱，不是入排阈值并排。
- `endpoint-timepoint-matrix` 1440：试验轴截断，系列 tropism 难读。

**机检 vs 合同**

- A/B/C `verification/*/v1/report.json`：`ok: true`，Chromium+WebKit，1024–1920。JSON 中无视觉缺陷项。按 §8 这只证明路由跑过，不证明可读。

### 推断（非证据）

医学经理无法在默认视野完成：A 格局点读、A 气泡全产品定位、B 完成例数对试验/组别辨认、C 入选评分与阈值并排。单位拆分在 B 的数据结构上存在，渲染把不同字段（含「筛选失败原因」）压进同一人数轴，拆分被抵消。C 的「核心设计差异」是可比较性的半成品：只有 4 个粗字段 + 截断英文列，不满足「定位到某药某试验的评分/时间点/阈值并与竞品同字段并排」。

### 最高影响缺陷与替代方案

1. **C 图谱不是可扫描的同字段矩阵。** 改为默认 试验×标准化字段（最低年龄、IGA 阈值、EASI 阈值、病程、主要终点周、给药），完整句子进下钻/表；列标签只用登记号+短中文简称。入选页禁止用「已报告值」计数当主图。
2. **B 完成情况轴不可读且字段混轴。** 每试验小多图；人数轴只放筛选/随机/治疗/完成/退出；原因与依从性分图；`hideOverlap` 改为换行或旋转；「未公开」用空状态，不上 % 柱；筛选项中文化。
3. **A 格局重叠 + 首屏混终点/气泡子集。** 格局改靶点卡片或 dodging；EASI 与 IGA 分面；气泡缺坐标名单提到图上方且标签不截断。H1 改为报告名+适应症+截止，删工作流导语。

### 通过 / 否决建议（本角色，非最终）

**建议否决 R6 站点式 HTML 的视觉/端到端可用性放行。**

不否决的部分：中文主导航、图在表前、热图像素内印数、B 按试验拆「受试者人数 / 相对剂量强度」、A 疗效对照双柱、证据按钮存在。这些不够达到医学经理默认可读的合同底线。

## Evidence And Assumptions

- **Evidence:** 上文路径、实页 `innerText`/DOM 尺寸、冻结 PNG、`charts.js` `hideOverlap`、HTML 原文。
- **Assumption:** 冻结 1440 C design-map 图若被描述成「已报告值」簇状柱，可能是 caption 误读或首屏裁切；以同文件实页「核心设计差异」为准，并仍记录 inclusion 页计数图。
- **Assumption:** 实页视口约 1423–1440 宽；1024 只会更差，未在实页重设 1024（冻结 1024 PNG 已看）。
- **Uncertainty:** 未做键盘、200% 缩放、`prefers-reduced-motion`、证据抽屉完整点击链；未核对气泡坐标与事实表是否 5/9 vs 6/9 级数值矛盾。
- **Did not assume:** verifier `ok` = 视觉通过。

## Risks, Gaps, And Verification Needs

- 风险：用 R6 机检通过交付，医学经理会把混终点疗效柱和截断设计列当成可横比结论。
- 风险：B 筛选暴露内部 cohort/period id，违反「不得展示后端字段名」。
- 需 Codex 终验：1024 实页核心图 `scrollWidth`、气泡缺测名单与图内点数一致性、C 四行热图在 1024 是否整图无需左右拖、WebKit 实页而非仅 PNG。
- 不在范围：PDF/PPT、改证据、互联网、生产写入。

## Recommended Next Step

Codex 按缺陷 1–3 做定向美化后再开视觉会，不要在 R6 机检 `ok` 上放行。

**对本主席的异议与决策点**

- 异议：把「核心设计差异」四行热图算作 Task 10.2 C 可比较性通过，会把“有一张试验列表格”当成“评分/阈值并排”。
- 异议：B 单位拆分若只看图组标题，会误判已完成；轴碰撞和「筛选失败原因」上人数轴是否决点。
- 决策：C 默认图必须是标准化字段矩阵，还是计数图+长表可接受？
- 决策：A 气泡仅 6 点 + 表内「未纳入」在 JS 填充后是否仍算矩阵可读？
- 决策：更多筛选里的 `alpha-safety-cohort` 是否允许残留？

**有界问题（缺答则暂按否决）**

1. C「核心设计差异」四字段是否被主会场定义为可比较性的验收定义，还是必须能并排读 IGA/EASI/年龄阈值？
2. A 首屏是否允许 EASI-75 与 IGA 0/1 同轴，只要每条有时间点标注？
3. 本 fallback 未跑 WebKit 实页；是否要求同一会话补 WebKit 才能合成，还是冻结 WebKit PNG + Chromium 实页足够？

**暂定安全路径：** 在 Codex 书面扩大 C 验收定义并接受混终点同轴之前，R6 视觉结论保持 **否决 / pending 终验**，不升级为 accepted。
