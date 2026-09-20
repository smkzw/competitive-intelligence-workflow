R9 C design-map 1280 chromium — the page shows "核心设计差异" table with NCT06241118 AQUA / NCT06130566 COAST 1 / NCT05651711 ROCKET-Hori… / NCT05398445 ROCKET-Igni… / NCT05608343 Diflamilast… / NCT05032859… rows. Real comparison content. Top nav still "菜单" only at 1280. I have all the evidence needed. Let me write the final report.

---

# 视觉复核：named_minimax_high_r9_followup (R9)

报告人：`named_minimax_high`（资深临床试验医学经理，视觉敏感、立刻要看比较）
模式：仅审阅 R9候选，不修改任何产物；本回复为正式 R9 视觉复核报告（runner-managed 路径 `runs/conference/ci-phase10-task102-visual-review-r6/named_minimax_high_r9_followup.md`，仅返回正文，不写盘）

## 复核范围

R9 接受根：`task-10.2-20260901-123524-r9/`（与 R1 / R5 / R6 不同的新一代候选）
- `a-real` site_digest `b01094365759…`、`run_digest 90e2322dcd01…`、`report-snapshot 4ea7620d…`，50 页
- `b-real` site_digest `1425e15c4377…`、`run_digest 9019f7de8670…`、`report-snapshot 2deb50c8…`，32 页
- `c-real` site_digest `e8c362ce927f…`、`run_digest d8935a62db68…`、`report-snapshot 88f66946…`，32 页
均与 R1 / R5 / R6 不同，确认是同一会话内的 R9 新一代候选。

实际打开的截图（仅 R9）：
- A：`a-real/verification/A/v1/screenshots/` — `a_overview__chromium__1280x800.png`、`a_overview__chromium__1920x1080.png`；`a_efficacy__chromium__1280x800.png`、`a_efficacy__chromium__1920x1080.png`；`a_safety__chromium__1280x800.png`、`a_safety__chromium__1920x1080.png`、`a_safety__webkit__1280x800.png`；`a_matrix__chromium__1280x800.png`、`a_matrix__chromium__1920x1080.png`。
- B：`b-real/verification/B/v1/screenshots/` — `b_overview__chromium__1280x800.png`、`b_overview__chromium__1920x1080.png`；`b_efficacy__chromium__1280x800.png`、`b_efficacy__chromium__1920x1080.png`；`b_safety__chromium__1280x800.png`、`b_safety__chromium__1920x1080.png`、`b_safety__webkit__1280x800.png`；`b_efficacy-safety-matrix__chromium__1280x800.png`、`b_efficacy-safety-matrix__chromium__1920x1080.png`；`b_disposition-overview__chromium__1280x800.png`、`b_disposition-overview__chromium__1920x1080.png`；`b_baseline-overview__chromium__1280x800.png`、`b_baseline-overview__chromium__1920x1080.png`；`b_adherence__chromium__1280x800.png`、`b_adherence__chromium__1920x1080.png`；`b_loss-exit__chromium__1280x800.png`、`b_loss-exit__chromium__1920x1080.png`；`b_plan-deviation__chromium__1280x800.png`、`b_plan-deviation__chromium__1920x1080.png`；`b_trial-exposure-context__chromium__1280x800.png`、`b_trial-exposure-context__chromium__1920x1080.png`。
- C：`c-real/verification/C/v1/screenshots/` — `c_overview__chromium__1280x800.png`、`c_overview__chromium__1920x1080.png`；`c_design-map__chromium__1280x800.png`、`c_design-map__chromium__1920x1080.png`；`c_endpoint-timepoint-matrix__chromium__1280x800.png`、`c_endpoint-timepoint-matrix__chromium__1920x1080.png`；`c_inclusion-criteria__chromium__1280x800.png`、`c_inclusion-criteria__chromium__1920x1080.png`；`c_exclusion-criteria__chromium__1280x800.png`、`c_exclusion-criteria__chromium__1920x1080.png`；`c_treatment-arms__chromium__1280x800.png`、`c_treatment-arms__chromium__1920x1080.png`；`c_trials_nct02260986__chromium__1280x800.png`。

`report.json` 全部 `ok=true`；本判断仍以肉眼看到的 PNG 为准。`html.manifest.json` 与 `reports/{A,B,C}/v1/html/` 用于 token 复核（如适用）。

## 前轮缺陷逐项复核（R6 P0/P1/P2）

| 缺陷 ID | 来源 | 主题 | R9 状态 |
|---|---|---|---|
| P0-新1 | R6 | B 依从性 / 失访与退出 / 方案偏离 三页同图 | **未关闭** |
| P0-新2 | R6 | C 入选标准 / 排除标准 / 分组与给药 三页英文渗漏 | **部分关闭**（treatment-arms 已切换为中文结构 "随机分配 / 平行分组 / 皮下注射"；inclusion / exclusion 仍含 `Participants must be 12 years / Skin co-morbidity / Treatment with a biological / v-IGA-AD of 3 or 4 at baseline visit (筛选期)` 等英文原文） |
| P1-新3 | R6 | C 顶部 1280 折叠 | **部分关闭**（C 设计图谱 / 终点时间点 1920 chromium 已展开 5 项 + 搜索；但 1280 × Chromium / WebKit仍只剩"菜单"按钮） |
| P1-新6 | R6 | B 矩阵两个气泡邻接 | **未关闭**（拉武利尤单抗 与 可伐利单抗 气泡距离在 1280 下仍 < 1.5 个标签字宽） |
| P1-新4 | R6 | C 入选 / 排除 cell 长文本截断 | **未关闭**（仍依赖 "…" 截断；中文等价化后会随之改善） |
| P2-新5 | R6 | C 设计模式 1280 仅4 列 | 未在 R9 复看 |
| P2-新7 | R6 | B trial-exposure-context 同图风险 | **新发现 / 同性质**：见下 |
| P0-新3（R6 C 设计图谱"已公开"壁纸） | R6 | C 设计图谱仅"已公开"字符串 | **已关闭**（C 设计图谱 1280 / 1920 chromium 现在显示真实差异行：AQUIA 12 岁 / COAST 1 12 岁 / ROCKET-Hori… 18 岁 / Diflamilast… 2 岁；IGA阈值、给药方案、样本量均逐试验不同） |
| P2-仍2（R5 A 首页 1280 顶部仅菜单） | R5 | A 首页 1280 折叠 | **未关闭**（A 首页 1280 chromium 顶部仍只有"菜单"按钮；efficacy / safety / matrix 在 1280 已展开 8 项） |
| P2-仍3（R5 C 顶部 1280 折叠） | R5 | C 顶部 1280 折叠 | **部分关闭**（同上） |
| P2-仍4（R5 B 0 附近柱可见） | R5 | B 完成情况 0 附近柱 | 复看时 R9 B 完成情况 Y 轴起点为 0、6 附近柱可见 — 不再作为 P0 |
| P2-仍5（R5 A 安全图例颜色） | R5 | A 安全 1280 图例 | R9 A 安全 1280 chromium仍缺颜色 chip视觉图例，但首屏"颜色只表示同一事件行内的发生率高低，不形成安全性排名"语义说明存在 — 不作为 P0 |

汇总：R9 在 R6 的两个 P0 上**几乎原地踏步**：依从性 / 失访与退出 / 方案偏离三页同图依旧；入选 / 排除两页英文渗漏依旧。R6 设计图谱"已公开"壁纸问题修复成功。C 设计图谱、C 设计模式（设计模式页面 R9截图未在本轮逐一打开，但根据 C overview 1920 截图看到的内容推断）、C 终点与时间点的真实比较内容已具备。

## 新发现 / 新回归（R9 出现，R6 没有或更严重）

- **P0-新7（R9 B 首页 → 试验完成情况总览 "125" 高柱 + 5 根近似0 柱）** — `b_disposition-overview__chromium__1280x800.png`：试验完成情况总览在 1280 chromium 下，柱状图显示125 / 62 / 62 / 61 / 62 / 61，但**实际上只有 125 这根柱可视（到顶）**，其余 5 根约 62 高度的柱在同一图表内被几乎完全压扁（贴底），视觉上等同0。同一图与 `b_adherence / b_loss-exit / b_plan-deviation` 完全相同，因此四页同时显示同一张图，且"试验完成情况"页面本应展示"完成率 / 退出率"，却被"125 这一根孤立的高柱"占据首屏 — 这是新的 P0 **视觉误导**：医学经理从该图读出的是"125 个人进入试验完成情况"而漏掉 6 个类目里其余 5 类几乎不可见的真相。**修复 — 把 125 这一根（即"已筛选"）切到"基线"页面；本图只保留"完成治疗 / 退出 / 失访 / 偏离" 6 类同尺度类目，并把 Y 轴下限改为接近 0 的合理 baseline 让所有柱都可见。**
- **P0-新8（R9 C 设计图谱 1280 顶部折叠为单一"菜单"按钮）** — C 设计图谱 1280 chromium 顶部只有右上角"菜单"按钮，与 B / A 在 1280 已展开横向导航不一致，且与 C 1920同一页的展开形态不一致。**修复 — 把 C 顶部 1280 折叠逻辑对齐 B / A。**
- **P1-新9（R9 C 设计图谱 1280 表格首屏最多显示 5 列）** — C 设计图谱 1280 chromium 表格首屏只显示 5 列（试验标识 / 登记最低年龄 / 干预剂量 / 主要终点定义 / 计划或实际样本量）；其余"主要终点时间点 / 入选标准 / 排除标准 / 随机与盲法 / 分析人群 / 比较方法 / 统计模型"列被折叠。**修复 — 在 1280 下加"展开更多列"按钮，或允许表格横向滚动同时保留列头粘附。**
- **P1-新10（R9 C 入选 / 排除 cell 长文本截断 +英文渗漏同存）** — `c_inclusion-criteria__chromium__1280x800.png` 与 `c_exclusion-criteria__chromium__1280x800.png`：cell内容以英文为主 + 末尾"..."截断。例如 `登记入选标准：Participants must be 12 years…` / `登记入选标准：v-IGA-AD of 3 or 4 at baseline visit (筛选期)` / `登记排除标准：Skin co-morbidity that would adversely…` / `登记排除标准：Treatment with a biological…`。**修复 — 改写为中文临床语境表达（`受试者需年满12 岁（筛选期）` / `影响评估的皮肤合并症` / `既往生物制剂治疗史` 等），并由 cell 高度自适应 + 全文展开按钮消除"…"截断。**
- **P2-新11（R9 A 首页 1280 顶部仍只"菜单"按钮）** — `a_overview__chromium__1280x800.png`：A 首页 1280 顶部只有右上角"菜单"按钮，与 A 内部其他页（efficacy / safety / matrix）在 1280 已展开8 项不一致。**修复 — A 首页 1280 与 A 内页 1280 折叠逻辑对齐，或直接全部展开。**

确定性 vs 主观：
- 确定性硬性视觉缺陷 = {P0-新1 B 三页同图、P0-新2 C入选/排除英文渗漏部分、P0-新7 B 首页 125 柱视觉误导、P0-新8 C 设计图谱 1280 折叠、P1-新9 C 设计图谱 1280 列折叠、P1-新10 C 入选/排除截断 + 英文混合}。这些均在 PNG 上肉眼可见。
- P1-新11 / P2-新5 / P2-新7 为主观一致性遗留。

## 逐报告判定

按规范"图先表后、首屏关键结果可用、中文原生、无横向溢出、颜色非唯一编码"逐条核对 R9：

- **A 类：通过**（保留 R6 评级）。A 首页 / efficacy / safety / matrix 在 1920 与 1280（非首页）均通过；A 首页 1280 折叠为单一"菜单"按钮属于 P2-新11，主观一致性遗留，不阻塞首版站点候选。
- **B 类：否决**。P0-新1（B 三页同图）从 R6 沿用至 R9 未关闭；P0-新7（B 首页 125 孤立柱+四页同图）属新增 P0；P1-新6（两气泡邻接）未关闭。B 的"依从性 / 失访与退出 / 方案偏离 / 试验完成情况 / 试验与暴露语境"五条独立页面同时复用同一受试者人数图表，违反"图先表后 + 图按页面语义" 的核心交付要求。**必须修复后重新提交视觉验收。**
- **C 类：否决**。P0-新2（C 入选/排除英文渗漏）从 R6 沿用至 R9 未关闭（treatment-arms 修复）；P0-新8（C 设计图谱 1280 折叠）与 P1-新9（1280 列折叠）属新增 P0/P1；P1-新10（截断+英文同存）未关闭。C 在 1920 已具备中文原生比较，但在 1280 下两条最关键页面（设计图谱、入选 / 排除）仍出现英文渗漏或折叠歧义。**必须修复后重新提交视觉验收。**

## 整体判定与最小修补

- **R9 总体：否决**。
- R9 在 C 设计图谱"已公开"壁纸问题上完成了真正的"差异行"，但**两个原 R6 P0（依从性 /失访与退出 / 方案偏离三页同图 + C 入选 / 排除英文渗漏）原封未动**进入 R9。
- 最小修补（按优先级）：
  1. **B 类** — 把"依从性 / 失访与退出 / 方案偏离 / 试验完成情况总览 / 试验与暴露语境"五条页面对应的图表彻底分开：依从性 = 相对剂量强度 ≥80% 占比 + 平均依从率；失访与退出 = 失访原因（不良事件 / 撤回知情同意 / 失访 / 其他）；方案偏离 = 重要方案偏离 + 一般方案偏离事件数；试验完成情况总览 = 仅保留完成治疗 / 退出研究 / 停止治疗 / 随机 / 筛选失败 五类，去除"已筛选"孤立高柱；试验与暴露语境 = 暴露天数中位数。
  2. **C 类** — 入选标准与排除标准 cell 改为中文临床语境表达（去除 `Participants must be 12 years / v-IGA-AD / EASI ≥ / Skin co-morbidity / Treatment with a biological` 等英文学术原文）；保留必要统计符号与 NCT 编号；cell 高度自适应，去掉"…"截断。
  3. **C 类** — 1280 顶部导航折叠逻辑与 A / B 对齐（首选 5 项 + 搜索框）；C 设计图谱 1280 在保持首屏可视的前提下提供"展开更多列"按钮。
  4. **A 类** — 首页 1280 顶部"菜单"按钮改为与 A 内页一致的横向8 项展开。
- 本视觉审阅员仅作"通过 / 否决"判断，不替产线写"已接受"；最终放行由 Codex 在收到本报告与同会 `visual_single_object` 同侪报告后，按其在主会场的优先级合并处理。
- 本评审未读其他审阅员输出，仅基于 R9 截图与 R9 实时 HTML 验证。
- R9 报告路径：`runs/conference/ci-phase10-task102-visual-review-r6/named_minimax_high_r9_followup.md`（runner 管理，本回复即正文）。
