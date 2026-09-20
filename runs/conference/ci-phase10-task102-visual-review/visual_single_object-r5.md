R5 follow-up is in the same bounded reviewer session. I’ll read only the listed prompt and evidence, then return the report inline.R5 screenshots and verifier reports are next: matrix, overview, and the previous P0/P1 surfaces.Opening the R5 PNGs that correspond to the earlier blocking defects.# Conference Participant Output: ci-phase10-task102-visual-review - visual_single_object

**R5 复核**（同一 `visual_single_object` 会话；fallback 仍为 `cursor` / `cursor-grok-4.6`。只读，不改产物，不声称最终放行。）

## 复核范围

只看 R5 候选，不沿用 R1 结论。

- 根目录：`.../task-10.2-20260901-123524-r5/{a-real,b-real,c-real}/verification/{A,B,C}/v1/`
- 机器闸门（`verify_portal`，**不是**视觉接受）：A/B/C 均为 `ok: true`；Chromium+WebKit × **1024×768 / 1280×800 / 1440×900 / 1920×1080**（相对 R1 已补 1024）；A 400 张、B/C 各 256 张 PNG。
- 实际打开的 PNG（路径均在上述 `screenshots/`）：
  - A：`a_overview` chromium 1280/1920、webkit 1280；`a_matrix` chromium 1024/1280/1920、webkit 1280/1920；`a_efficacy` chromium 1280；`a_safety` chromium 1280/1920
  - B：`b_overview` chromium 1280/1920、webkit 1280；`b_efficacy-safety-matrix` chromium 1024/1280/1920、webkit 1280；`b_efficacy` / `b_safety` / `b_disposition-overview` / `b_baseline-overview` / `b_baseline-demographics` chromium 1280
  - C：`c_overview` chromium 1280/1920、webkit 1280；`c_design-map` chromium 1280/1920、webkit 1280；`c_endpoint-timepoint-matrix` chromium 1024/1280/1920；`c_trials_nct03569293` chromium 1280/1920
- 未做：筛选展开后的「更多」面板、证据抽屉打开态、200% 缩放、键盘焦点、全产品路由逐张。

## 已关闭问题

相对本角色 R1 否决项，R5 **默认视野截图**上已关闭：

| 原 P0 | R5 证据 |
|---|---|
| A/B 气泡图空轴、表体「待计算」 | A `matrix` 1280/1920/WebKit 有编号气泡、轴旁中文药名、覆盖说明「已绘入 10 个产品，另有 28 个因缺少疗效或安全性数值未进入坐标」；1920 表体为 51.3% / 15.1% 等，不是「待计算」。B `efficacy-safety-matrix` 1024/1280/1920/WebKit 有气泡与中文覆盖句。 |
| C 终点×时间点空坐标 | `endpoint-timepoint-matrix` 1024/1280/1920 热图格内有数或「—」，有轴标签。 |
| C 表/筛选漏 `trial_identity` 等 schema | C overview/入选相关首屏表头为「产品 / 试验编号 / 试验 / 设计要素 / 内容…」；设计要素列为「试验身份」「目标人群」「入选标准」。默认视野未见英文字段名。 |
| A 首页首屏只有格局、疗效/安全在折页下 | A overview 1280/1920/WebKit 为三列：竞争格局、主要疗效柱、关键安全热图；热图格内有数。 |
| B 首页几乎无图 | B overview 1280/1920/WebKit 首屏可见竞争格局、主要疗效、关键安全性三图。 |
| 机器验收无 1024 | R5 report 含 1024×768；抽查 A/B 矩阵与 C 终点热图在 1024 内容列内完整，**未见**为看核心图而左右裁切。 |
| 安全热图无格内数值 | A/B 安全页与首页热图格内有百分数。 |

C `design-map` 1280/1920/WebKit 有带药名的散点，与终点热图同时存在，说明不是整站图表栈失败。

## 仍存问题

**机器通过 ≠ 视觉通过。** 下列为医学经理可用性，按严重度分开。

### P1（足以否决本轮视觉放行）

1. **观察截止互相打架（A/B/C 全站页头）**  
   页头「观察截止：2026-09-01」（ISO），页脚「数据截至 2026年07月31日」。医学经理无法判断锁定观察日。截图：A/B/C overview、matrix、试验页均同此。

2. **A 矩阵气泡标签互相压盖**  
   1280 Chromium/WebKit：司普奇拜单抗 / 来布利珠单抗 / 曲罗芦单抗等标签叠在一起；1024 更挤。轴说明和覆盖句在，但默认视野会读错「谁是哪个点」。1920 稍好仍挤。合同要求气泡可读，不是「有标签即可」。

3. **A 首页仍在教用户怎么读**  
   h1「创新治疗格局与医学结果」+ 导语「先看全部创新治疗的靶点结构…再按下钻」。合同：首屏标题只留报告/页面名、适应症、观察截止，不得解释图表顺序。

4. **B/C 首页 h1 仍是「首页」**  
   适应症和截止在 meta。B/C 首屏上半仍是两排产品芯片 + 折叠「筛选条件」，图在芯片之下。1280 上三图已入首屏，但层级仍是「筛选器产品」先于「结论图」。

5. **C 试验详情页主标题是「试验档案」**  
   `c_trials_nct03569293` 1280/1920：页面已有 ADvocate1 / NCT03569293 / 来布利珠单抗，但 h1 仍是泛称「试验档案」，违反「正式研究名 + 登记号」优先。

6. **B 人口学页默认无图、表先行**  
   `b_baseline-demographics` 1280：标题「人口学横向比较」后直接宽表（大量「未公开」），首屏看不到基线人口学图。`b_baseline-overview` 有热图，说明总览页已补图，人口学详情页未对齐「图先表后」。

### P2（不单独否决，修复时应收）

- C overview 快速筛选「来布利珠单抗」芯片重复；试验筛选仍用英文登记标题长句。
- B 产品芯片「pegcetacoplan（C3抑制剂）」无中文通用名；「伊普可泮（iptacopan）」中英并列可接受。
- A 疗效页筛选写「默认显示全部 38 项」，图上仅约 3 组柱，空白大（更像默认终点过滤，不是空图）。
- A/B/C 导航形态仍不一致（A 扁平+更多 vs B/C 分组下拉）；证据入口 A 为面板、B/C 为抽屉——本次未打开抽屉，不升 P1。
- 未展开 B/C「更多筛选」，因此 **不能** 证明英文 schema 已从折叠层消失；只证明默认首屏未见。

### 不确定（不升格为缺陷）

- 页头 2026-09-01 究竟是生成日还是观察截止：以互相矛盾的可见文案记 P1，不猜哪个对。
- 1024 热图/气泡在截图像素上完整，但本角色未做真实拖动手势；「无需横向拖动」的判断限于这些 viewport 截图未裁切坐标区。

## 结论

| 站点 | 建议 | 理由 |
|---|---|---|
| A | **否决** | 空矩阵/待计算已关；仍有气泡标签重叠、首屏教程式导语、截止日矛盾。 |
| B | **否决** | 空气泡已关、首页三图已入 1280 首屏；仍有「首页」空标题、筛选压过图、人口学无图、截止日矛盾。 |
| C | **否决** | 空热图与 `trial_identity` 默认漏出已关；仍有「试验档案」泛标题、筛选占首屏、截止日矛盾。 |
| **总体** | **否决** | 通过条件是无 P0/P1。R5 关掉了 R1 的 P0 空图，但 P1 仍在。**不要**用 `report.json ok: true` 放行。 |

**给 Codex 的最短恢复（生成侧，非本角色改文件）：**

1. 统一并中文化观察截止（页头与页脚同一天，写成「2026年7月31日」或经核实的另一天）。  
2. A 矩阵：避让/外置图例，禁止标签压点。  
3. A 去教程式导语；B/C h1 改为报告名；C 试验页 h1 用「ADvocate1（NCT03569293）」。  
4. B 人口学补图于表前；压缩 B/C 默认芯片，筛选默认收起。  
5. 抽查折叠「更多筛选」确认无 schema id 后再开一轮隔离视觉审阅。

**Safe provisional path：** R5 三站均未通过视觉接受；R1 保持历史；不修改产物。
