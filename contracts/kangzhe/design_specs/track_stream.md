# 康哲设计规范 · 流式 HTML 报告轨

> **Portable package track pack** · track_id=`stream`  
> **Load order**: `ROUTER.md` → `core.md` → **this file** (to EOF).  
> **Assets**: `assets/logo_bot.svg` (relative to `design_specs/`).  
> **Authority**: This pack + `core.md` are the load-time contract for this product. Machine-only samples live in `local_map.md` (optional).  
> **Do not** require reading the legacy monorepo body for this product.

**Also read**: core.md

---

## 0. 使用入口（本轨 only · stream）

**本文件只约束流式 HTML 报告**（长文档 / 滚动 / 响应式单文档）。  
其他产物（PPTX / HTML-PPT / 站点 / 驾驶舱）**NEVER** 从本文件取版式合同；先读 `ROUTER.md` 判轨再加载对应 `track_*.md`。

### 何时加载本轨

- `HTML报告`、`网页报告`、`长文档`、`滚动页面`、响应式报告
- 用户明确要「可滚动阅读的康哲 HTML 报告」而非翻页幻灯片

### 硬边界

- **NEVER** 套用 1280×720 固定画布、逐页 chrome、页码进度条。
- **NEVER** 把单文档报告冒充多页站点（≥2 互通页 → `track_site.md`）。
- 品牌色 / 字号地板 / 证据与 AI 边界 → 来自 `core.md`，本轨强制继承。

### 0.0 可移植包权威（本包为 SSOT）

本文件是 **portable package**（`design_specs/`）内的**单轨**合同正文，**不是**五轨 monorepo 全文，也不是摘要索引。

| 步骤 | 路径 |
| --- | --- |
| 1. 判轨 | `ROUTER.md`（五轨路由表只在这里） |
| 2. 共享硬合同 | `core.md`（到 EOF） |
| 3. 本轨合同 | 本 `track_*.md`（到 EOF） |
| 4. Logo | `assets/logo_bot.svg` |

- **权威**：固定 HEX、DOM/CSS 合同、I-闸门原文以 **`core.md` + 本 track 文件** 为准。
- **NEVER** 把根目录 `design_v2.md` / `design_share_v2.md` 当作全文 SSOT（二者仅为兼容 stub）。
- **NEVER** 要求手同步 local/share 双全量正文。
- **NEVER** 把本轨版式规则套到其他轨；跨轨路由只读 `ROUTER.md`。
- 架构说明：`ARCHITECTURE.md`。本包可整体拷贝；同文件夹内即可识别依赖。

本文件不是普通风格参考，而是跨 Agent 的设计合约。除非用户明确覆盖，后续 Agent 不得只凭记忆或只看截图生成康哲风格交付物。


## 0.3 生成前的最小输入与默认决策（stream）

开始制作前，Agent MUST 明确：主题、受众、源材料、章节结构。若用户已提供充分材料，不重复追问；按以下默认值执行：

- 默认形态：流式长文档，自然滚动 + 锚点跳转；**无**固定 1280×720 画布。
- 默认背景：白色或中性浅灰。
- 默认字体：§6.1 固定字体栈（见 `core.md`）；正文 ≥16 px。
- 默认页脚：全文末尾一次（`.report-footer`）；**NEVER** 每节重复页脚。
- 默认审阅：管理层 20–30 秒能看懂结论；响应式断点与证据可回溯。

### 14.10 HTML 报告（流式长文档）分轨规范

本节定义 **HTML 报告** 这一类产出，与 §14.1–§14.9 的 **HTML-PPT（按 1280×720 翻页幻灯片渲染）** 明确区分。HTML 报告是流式 / 响应式长文档，不强制分页、不套用页面原型。HTML 报告必须优先采用响应式布局，避免在可变视口中复用 PPT 的固定像素坐标。

#### 14.10.1 与 HTML-PPT 的本质区别

| 维度 | HTML-PPT（§14.1–§14.9） | HTML 报告（本节） |
| --- | --- | --- |
| 形态 | 逐页幻灯片，每页 1280×720 | 长文档，自然滚动/锚点跳转 |
| 版式 | 逐页套用 §8 原型 | 自行布局，不套原型 |
| 交付 | 可导出 PPTX/PDF | 网页/本地 HTML |
| 文字内容 | 受 §9 页面叙事顺序约束 | 不强制§9的逐页叙事顺序；但§14.10.2的证据、来源、不确定性、AI边界与管理层可读性仍强制 |
| 色彩/字体/间距 | 全量 §5/§6/§14 | 仅 §5/§6 的色彩与字体与间距原则（见 §14.10.3） |

#### 14.10.2 内核共享（五轨强制一致，HTML 报告同样适用）

HTML 报告 MUST 继承以下内核，与 PPT / HTML-PPT / 站点 / 交互单页完全一致：

- **配色 token**：使用 §5 / §14.1 CSS 变量；品牌橙 `#FF9900`、黄 `#FFCC00` 仅作识别与强调，不得整页铺满；红 `#C00000` 仅用于风险/缺口/关键结论。
- **字体栈**：`微软雅黑 / Arial / Noto Sans SC`（§6.1）；字号地板见 §0.7（流式正文≥16 px，参考文献≥11 px）。
- **证据与来源**：所有医学/临床/注册/市场/竞品结论可回溯（§10.3）；证据等级 3–4 显式加来源前缀；推测以“推测/基于 MOA 推测/专家判断”开头（§10.3.1）。
- **AI 角色边界**：AI 仅作辅助定位、资料缺口识别、规则一致性检查；必须保留“医学经理终审”；禁止“AI 自动判断”“AI 替代医学判断”措辞（§19 I-08）。
- **占位符/提示清理**：交付前 `&&` 与 `@@` 搜索均为 0（§2、§16.A）。
- **受众背景不出现在可见内容**：不得写“面向董事长/医学部负责人”等（§19 I-09）。

#### 14.10.3 HTML 报告仅强制的视觉原则（色彩 / 间距 / 字体）

HTML 报告不强制页面骨架，但以下视觉原则 MUST 遵守：

- **盒模型**：全局设置`*,*::before,*::after{box-sizing:border-box}`；响应式容器的`width/max-width`和横向padding必须在该盒模型下计算，移动端不得出现`100% + padding`横向溢出。

- **配色**：定义 `:root` CSS 变量（§14.1），全站统一引用，不得散落硬编码 HEX；品牌色占比与 PPT 一致（橙/黄 ≤ 12%，红 ≤ 3%）。页面底色使用白色或中性浅灰`#F6F7F8`，内容区使用白色；`#FCF5E6`只用于局部摘要/callout，同一桌面视口可见面积不超过15%。禁止把整页做成米色/暖灰单色背景。
- **响应式容器**：
  - 桌面正文容器：`max-width: min(1100px, 90vw); margin: 0 auto; padding: 0 4vw;`。
  - 移动端（< 768 px）：容器宽度 100%，padding 0 3vw；复杂表格允许横向滚动或折叠列。
  - 平板（768–1280 px）：容器宽度 90%，最大 960 px。
- **间距与栅格**：
  - 区块间距 24–40 px（桌面），16–24 px（移动端）。
  - 卡片内边距 ≥ 16 px；卡片圆角 8–12 px。
  - 阴影极轻或不用；表格固定列宽，单元格padding沿用§11.1标准`14px 16px`或高密度`8px 12px`，正文不低于16 px。
  - 页面章节是全宽文档流，不把每一章都做成大号悬浮卡；卡片只用于并列摘要、指标、角色或可交互条目，避免“卡片套卡片”。
  - 推荐网格：`display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px;`。
  - 响应式变化可在下述`clamp()`范围内调整HTML报告字号，正文任何视口不得低于16px；卡状主文 SHOULD≥19px（与§0.7一致）；不适用于HTML-PPT。
- **字体**：§6 字体栈；标题层级用字号/字重区分（不靠颜色）。HTML 报告推荐响应式字号：
  - 正文：`font-size: clamp(19px, 1.6vw, 21px);`
  - 一级标题：`font-size: clamp(24px, 3vw, 36px);`
  - 二级标题：`font-size: clamp(20px, 2.4vw, 28px);`
  - 卡片标题：`font-size: clamp(16px, 1.9vw, 20px);`
  - 参考文献：`font-size: clamp(11px, 1.2vw, 13px);`
  - 行距 1.2–1.5；段前 0.6 pt 级间距。
- **图表**：真实 SVG / Canvas，不用纯文字假图；坐标轴必须有单位；同图主色 ≤ 5；SVG 应使用 `viewBox` 实现缩放。
- **打印样式**：如报告需打印/导出 PDF，`@media print` 对齐 PPT 白底，隐藏导航与阴影。

#### 14.10.4 HTML 报告不强制（区别于 PPT）

以下 PPT 类要求对 HTML 报告 NOT enforced，按报告具体布局自行决定：

- §7 固定顶部 chrome、页脚、封面/结束 ribbon。
- §8 页面原型选择器与逐页像素坐标、每页 ≤ N 条 bullet、固定栅格。
- §13.5 页码与转场动画、§13.6 讲者备注。
- 单页画布 1280×720 与“每页一个结论”的硬约束。
- **流式/站点式页脚唯一性（NEVER 逐节重复）**：流式 HTML 报告的页脚/署名（`.report-footer` 或等价容器）仅在**文档最末**出现一次；NEVER 在每个 section/章节末尾重复页脚两槽（部门名＋日期）或页码编号——那是 HTML-PPT 的逐页 `.deck-footer` 规则，不适用于滚动文档。站点式 HTML 的 `.site-footer` 同理：每页一个全局页脚，NEVER 在页面内的 section 级别重复。

#### 14.10.5 HTML 报告文字内容：共享内核强制，章节结构自适应

HTML 报告的章节结构、叙事顺序、信息颗粒度和表格字段，由**该报告的具体需求**决定（例如受试者画像按时间线组织、监管问询回复按问题组织），不强制套用PPT的逐页故事线。但§9的事实与结论分层、证据可回溯、推测显式标注、标题传达明确结论、AI边界、风险措辞和来源规则仍全部强制；不得把“流式”理解为只套配色而放弃医学写作规范。

#### 14.10.6 HTML 报告交付检查（最小集）

- CSS 变量定义完整，`&&`/`@@` 搜索为 0。
- 配色未滥用品牌色、红色仅用于风险/缺口/关键结论。
- 证据结论可回溯；推测已显式前缀。
- AI 相关表述未越界（§19 I-08）。
- 响应式下核心文字可读，无溢出/重叠。
- 不要求逐页截图对照 §8，但建议提供桌面+移动两种视口截图。

- **活基线（流式报告，品牌克制内做"活"，不得退回扁平长文）**：报告 MUST 至少满足以下可感知反馈中的四项，且全部受 `html.js` 门控 + `prefers-reduced-motion:reduce` + `@media print` 冻结（无 JS/打印/降动效时内容直接完整可见，揭示类强制 `opacity:1`）：①章节标题/摘要卡/图表容器用 `IntersectionObserver` 一次性 scroll-reveal（位移≤14px、≤480ms，禁止逐行逐字）；②关键数字用 `data-countup`（DOM 先写真值）；③可交互卡/链接/按钮有 hover 反馈（上浮≤4px 或阴影/色变三选一）+ `:focus-visible`；④粘性章节导航（`backdrop-filter` 仅导航一层、白底≥0.94）+ 滚动高亮当前节；⑤首页/管理摘要用一个**特征开场**（关键数字带+价值链横条+口径 callout），NEVER 居中堆"标题+副标题+CTA"三件套；⑥强字号字重对比（一级标题 clamp 24–36px/700–800 vs 正文 16–18px vs 元信息 12–13px 灰）。丰富度只来自层次/色条/微动效/排版对比；NEVER 极光/玻璃拟态卡片墙/渐变标题/整页铺色/深色霓虹——报告底色仍白或中性浅灰，暖米仅局部 callout。


### 14.11 五轨验收差异速查

| 闸门（§16.A / §19） | PPT | HTML-PPT | 流式 | 站点 | 交互 |
| --- | --- | --- | --- | --- | --- |
| `no_double_ampersand` / `no_double_at` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `clinical_claim_sourced` / `speculation_prefixed` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `risk_red_bounded` / `ai_role_disclaimed` / `ai_human_review_present` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `no_audience_meta_in_body` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `chrome_on_content_pages` / `page_count_match` / `no_meta_spec_in_final` | ✓ | ✓ | — | — | — |
| `no_fullpage_brand_bg` | ✓ | ✓ | ✓ | ✓ | ✓ |
| 正文字号下限 | §0.7 | §0.7 | §0.7 | §0.7 | §0.7 |
| 固定 1280 画布 + 等比缩放 | — | ✓ | — | — | — |
| 全局 nav / 多页互通 / DATA_X | — | — | — | ✓ | DATA_X ✓ |
| `title_not_weak_noun_phrase` | ✓ | ✓ | ✓（章节） | ✓（页面） | ✓ |

> 标 `—` 表示该闸门对本轨不适用。内核闸门五轨一致强制。站点/流式/交互 **NEVER** 套用 HTML-PPT chrome 与页码规则。


## 17. 常见错误与修正

| 错误 | 修正 |
| --- | --- |
| 保留 `@@（表格页示例）@@` 作标题 | 改成真实业务标题，例如“产品基础信息与潜在临床优势” |
| 标题只有“研究结果” | 改成判断句，例如“48 周 Hb 维持支持长期疗效持续性” |
| 正文长段落 | 拆成 2-4 个 bullet 或表格 |
| 表格文字太小 | 拆页，或把不重要列放备份页 |
| AI 页写“自动判断是否入组” | 改为“辅助定位证据和风险，医学经理终审” |
| 竞品横向比较没有口径 | 在标题或脚注写清人群、终点、时间点 |
| 红色用于普通强调 | 改用加粗或橙色，红色只保留风险/缺口 |
| 大量装饰图标 | 保留少数辅助图标，其余删除 |
| 没有来源 | 补引用或降级为待核实/推测 |
| 长规范首个读取块到500行就开始生成 | 按工具返回的offset继续读到EOF，记录覆盖区间；生成后再回读产物到EOF |
| Agent整理的brief给目录改名、给章节页加副标题 | brief只管业务内容；没有用户明确授权时，修订brief并恢复§14固定母版文字与节点 |
| HTML 报告套用 PPT 固定坐标 | 改用 §4.4 响应式布局 |
| HTML-PPT沿用通用`100vw/100vh`页面 | 用固定`1280×720`逻辑画布和单一全精度`transform:scale()` |
| `.deck`设置`max-width:1280px` | 删除上限，让固定画布在大屏按统一比例放大 |
| `.slide`直接挂在`<body>`下、缺少`.deck`包裹层 | 所有`.slide`MUST是`<div class="deck">`直接子元素；缺`.deck`时缩放/翻页/页码整体静默失效，按`deck_wrapper_contract`闸门阻断 |
| 通用`base.css`在康哲主题之后加载 | 固定加载顺序为`base.css → animations.css（可选）→ kangzhe.css`；康哲主题必须最后 |
| 直接复制`html-ppt`通用full-deck或utility类 | 只复用runtime/notes；视觉仅用§14.4–§14.7，禁用class/data按§14.2扫描 |
| `base.css`把`.slide`改回`justify-content:center`或添加`translateX()` | 康哲主题显式覆盖`justify-content:flex-start;align-items:stretch;transform:none`，再查最终computed style |
| 对单页再做一次scale或translate补偿 | 只允许共同祖先`.deck`做一次scale；单页和组件不得二次缩放整页 |
| 用媒体查询把内容标题从32px改成29px | 删除viewport内重排；任何窗口只缩放整张deck |
| 浏览器最大化后内容仍只占上半页 | 在1280逻辑空间检查正文框`y=96–660`；核心内容应自然覆盖到`y≈625`，不能用外部letterbox掩盖页内空白 |
| 内容页只把空表/短卡放在`y<480` | 使用命名全高组件、增加有效行高或把结论条锚定到底部；最后一个受众元素bottom必须≥560，禁止用透明节点凑高度 |
| 四部门应用卡片临时拼四列导致上半页拥挤或下半页空白 | 使用§14.7.0`.department-portfolio-layout`固定48/420/64三段；四卡等宽，结论条底边固定660 |
| 内容页底部结论临时做成黑底反白横条 | 普通结论统一用`.content-conclusion`暖米色底和橙色左边线；只有规范命名的风险变体可用红色 |
| 固定八行信息表声明1168×564却实渲染1172×565 | `border-collapse`固有尺寸会计入粗左边框和外边框；列轨改250/917、行轨改7×58+157，识别条用inset shadow，实测最终rect 1168×564；表后不得追加脚注或callout |
| 非内容页误加`content-slide` | 页面类必须互斥；目录/章节/结束页不得出现内容页橙线、页脚或页码 |
| 目录页没有图片就生成四个空流程框 | 使用§14.5.2默认2×2语义目录板；每张卡必须有真实编号与标题，禁止空卡、假流程和纯装饰占位 |
| 结束页“谢谢”外有透明卡片轮廓 | 保留`.ending-focus`定位容器，但固定`border:0;background:transparent;box-shadow:none` |
| 为减少CSS重复而合并封面/结束页同名横线 | 不得跨母版合并几何不同的选择器；封面黄线固定720px，结束页固定520px，分别验收 |
| 内容页使用`.slide:not(.cover-slide)`等宽泛选择器加chrome | 只用`.slide.content-slide::before`，避免目录、章节和结束页被误套chrome |
| 做“全屏图”时删除内容页chrome | 全幅图仍放在固定`.slide-body`内，保留双斜切、顶线、标题、Logo、页脚和页码 |
| 复制旧模板绝对坐标，元素越出`x=56–1224,y=96–660` | 把坐标转换为相对`.slide-body`的§4.3预设；无法容纳就拆页 |
| 标题容器延伸到右上Logo下方 | 标题固定`right=270px`，Logo固定`right=91px,width=158px`；改短标题，不缩字、不覆盖Logo |
| 标题过长时直接换成两行 | 当前母版没有双行变体；改写、缩短或拆页，除非用户授权且先补齐完整变体合同 |
| 甘特使用裸`repeat(N,1fr)` | 改为`repeat(N,minmax(0,1fr))`并给中间层`min-width:0` |
| 甘特表头与正文分别写列宽 | 只在父组件定义`--dept-col/--label-col/--period-count`，表头和每行共同引用 |
| 甘特表头与正文竖线相差1px | 两处从同一侧画边框并共享时间区起点；机器验收每列边界误差≤0.5逻辑px |
| 甘特阶段文字撑宽单列 | 先缩短阶段标签或增加span；不得靠`nowrap`把`min-content`传到网格，也不得缩到16px以下 |
| 看到总甘特示例后把`.road-bar`简写为`.bar`、把`.portfolio-group`改成`.gantt-group-*` | §14.5–§14.7命名组件是可执行封闭规格；原样复制DOM层级、class、selector、字号和几何，只替换业务文字与明确开放变量 |
| 把`.portfolio-gantt`写成`table`再直接塞入`div` | 根节点必须是`<div class="portfolio-gantt">`；HTML表格内容模型会把非法div移出表格，导致真实渲染纵向爆开，即使源码class齐全也必须阻断 |
| 单季度5字标签被padding裁切 | 加`.is-one-period`、横向padding归零、字距固定-.35px并复查scrollWidth；仍超限就改写或扩span |
| 运营/数统空里程碑塞透明文字、点号或`&nbsp;` | 里程碑DOM保持真正空文本，只用`aria-label`提供可访问名称；机器检查`textContent.trim()==''` |
| 弱化流程节点时给整卡`opacity` | 卡片保持不透明白底，只调边框、编号和文字色 |
| 流程轴线盖在卡片上 | 轴线置于卡片后；卡片`z-index:1;background:#FFFFFF;opacity:1` |
| 调整流程卡高度后转弯线仍用旧坐标 | 同步重算`.chain-turn::before`的top/height，并复测上下轴线与编号圆共点 |
| 文字被`overflow:hidden`裁掉但页面无溢出 | 标记`data-qc-text`，用Range墨迹框检查真实裁切；缩短文案、减项或拆页，不以隐藏溢出掩盖 |
| 卡片、标签或结论条彼此压住但整页无overflow | 在共同父层标记`data-qc-zone`、同层对象标记`data-qc-block`，执行两两矩形相交检查；只有背景/连线可显式`data-qc-overlap="allow"` |
| 为增加设计感给所有卡片做3D旋转或大幅hover | 只对目录或明确交互卡启用最大3px抬升（站点式HTML可交互元素≤4px）；证据、表格、甘特、风险和结束页保持静态，导出/QC冻结transform |
| 把站点动效库整库照搬到幻灯片内容页 | 粒子只允许封面（§14.7.3 C），内容页NEVER出现canvas粒子；轨道环/呼吸灯/扫光按§14.7.3 A四轨边界取用，同页动效对象≤8个 |
| 站点式HTML用fetch加载本地JSON | 数据以`data/*.js`的`window.DATA_X`全局注入，规避file:// CORS（§14.12.2） |
| 资料证据链复用通用`.grid`后变成单列向下堆叠 | 只用§14.7.2`.evidence-layout/.evidence-chain`五列模板；两条连接带必须是水平箭头，子列和整页不得溢出 |
| 三列责任对照做成九张无序卡片 | 只用§14.7.1固定3×3矩阵，每行重复场景名，结论条落到底部 |
| 只检查整页scrollWidth/scrollHeight | 逐个检查可见文字容器、标题行数、卡片容量和`data-qc-id`归一化几何；整页不溢出不代表文字未裁切 |
| 运行时只更新`document.querySelector('.slide-number')` | 初始化并更新每页自己的`.slide-number`，总页数取`.deck > .slide`真实数量 |
| 运行时只切换`.is-active`但CSS没有隐藏非活动页 | 非活动页必须`display:none`、`visibility:hidden`或`opacity:0`且不可交互；机器验收逐页检查所有`.slide:not(.is-active)`，不能只确认活动类数量为1 |
| 运行时写成`#2`或只能解析`#2` | 深链格式固定`#/N`；使用§14.3正则解析与`history.replaceState`写回，实测直接打开`#/5`与翻页后的hash |
| 章节页`data-title`写成“01 整体设计” | `data-title`必须与可见`.section-title`完全一致，只写“整体设计” |
| 用`display:none`把备用页留在`.deck`内 | 备用页放入`<template>`或移出`.deck`，避免页码、进度条和讲者窗口计数错误 |
| `O`总览clone剥掉母版类或复制`data-qc-id` | clone保留source class、递归移除QC属性；所有扫描限定`.deck > .slide`，无法修则不创建overview DOM |
| 只在1280×720截图正常 | 补做1920×1080、2048×1024、实际最大化窗口和多内核原图验收 |
| 内容页左上双斜切在PPT/SVG轨被自行换算clip-path百分比，顶点外推导致拉伸越界（x<0） | 按§14.14.5绝对顶点绘制并跑顶点范围闸门；HTML轨沿用§7.1.2百分比，NEVER跨轨换算 |
| 方案培训PPT把另一期内容混入本期（多期无缝方案） | 按§14.14.0做期别污染扫描；共用条款标"两期共用"、引用它期标"依据" |
| 方案培训把药物介绍放Backup/附录 | 药物概览页MUST为第一章第一个内容页（§14.14.1） |
| 入排标准被概括改写、子条重排、阈值未深红 | 原文逐条+原编号+阈值深红（§14.14.3） |
| 逐字稿出现稽查/自查/整改/迎检口吻 | 只讲方案本身，隐性强调对应条款（§14.14.3） |
| 只比较不同视口是否彼此一致 | 还必须逐项比较§16.A固定母版锚点；“稳定地错位”同样失败 |
| 只在一台Mac运行Chromium和WebKit | 这只是内核预检；跨平台一致必须补Windows Chrome/Edge与macOS Chrome/Safari实机，缺失须明示 |
| 只看`?preview=N`或无浏览器chrome截图 | 最终必须打开真实观众运行时，确认页码、进度条、哈希翻页和窗口最大化后的完整画面 |
| 依赖截图合成图判断列线或对位 | 对疑点页查看原始分辨率单页图；contact sheet仅用于快速总览 |
| 模块化母版继续加载Google Fonts | 删除远程字体，使用固定系统字体栈或获许可的本地WOFF2子集 |
| macOS与Windows各自使用系统默认字体 | 固定使用§6.1字体栈，并在目标系统核实实际命中字体、行数和字宽，不允许浏览器自行回退到衬线体 |
| 单文件只在本地HTTP服务测试 | 用`file://`直接打开并确认翻页、图片、页码、进度条及零外部依赖 |
| 单文件仍保留相对图片、外链CSS或远程脚本 | CSS/JS全部内联，图片转Data URL；网络请求白名单只能是当前HTML、`data:`与运行时创建的`blob:` |
| 为方便直接把官网Logo URL留在最终`img src`里 | 官网地址只用于构建时下载；模块化版随包放`assets/logo_bot.svg`，单文件转Data URL，PPT/PPTX嵌入SVG，观众运行时对官网请求必须为0 |
| 找不到本机模板时用文字`CMS 康哲药业`冒充正式Logo | 从§1.2官网唯一地址下载原始SVG；验证`viewBox="0 0 121 25"`后嵌入所有固定Logo槽，文字只可作为未验收草稿辅助 |
| 把最终HTML的真实闭合标签也写成`<\/script>` | 只在“脚本源码嵌在另一个字符串”这个中间态转义；最终HTML必须还原真实`</script>`并实测运行时翻页、缩放、深链 |
| 页面加载后立即截图 | 等待`document.fonts.ready`与所有图片`decode()`完成，再做几何检查和截图 |
| 翻页后在淡入过渡尚未结束时截图 | 等待`transitionend`，或在最后一次导航后至少等待250ms；否则会把前后页叠影误判为视觉缺陷 |
| 目录meta仍显示“汇报主题 · 2026年7月” | 替换为当前汇报真实主标题/短标题与真实日期；所有模板示意词在受众可见文本中必须为0 |
| Logo、hero、ribbon的`object-fit`由Agent任选 | Logo/wordmark固定`contain`；预裁hero/ribbon固定`cover`；截图证据固定`contain` |
| `color-scheme`未锁定导致暗色模式改表单/背景 | `<meta name="color-scheme" content="only light">`与`:root{color-scheme:only light}`同时保留 |
| 移动端压缩HTML报告正文基础字号 | 可使用`clamp()`，但正文下限保持16px；HTML-PPT不得使用viewport字号 |
| 页脚出现"依据/来源/对应SOP"中间元素，或把源材料 owner 写进页脚左槽/封面/结束页 | 页脚固定两槽：左`.footer-id`=`产品中心-医学部｜20XX年XX月`灰#808080/400，右页码橙#FF9900/700；内部出处进讲者备注或行内括注，NEVER 进页脚；只有外部科学论文/公开法规才用§10.4底部参考文献行且与页脚垂直分离；封面/结束页部门同为`产品中心-医学部` |
| 红色里程碑菱形/状态点/箭头相对节点漂移 | 装饰标记 MUST 画在宿主 SVG 同一 viewBox 内用整数 user-unit 坐标，与节点共享坐标；NEVER 用 CSS 绝对定位 HTML 贴 SVG；标记≥8px、不压字、不越界；见§11.5 |
| 文字溢出/被裁切、卡片或表格与页脚/标题/彼此重叠 | 跑 no_text_overflow 与 no_element_overlap 闸门；缩短文案/拆页/调固定组件行数/改填充式构图，NEVER 用 overflow:hidden 掩盖裁切 |


## 18. Agent 交付格式

当一个 Agent 使用本规范完成工作，应在最终回复里简要说明：

- 使用了本规范。
- 输出文件路径。
- 核心检查：`&&`/`@@`、渲染截图、页数、来源引用。
- 未验证项或缺口。

不要在最终汇报页里写“本页根据康哲PPT设计规范生成”。规范是内部生产规则，不是面向听众的内容。



## Package assets

- Official logo (portable): `assets/logo_bot.svg`
- Prefer embedding this file (or its data-URL) over remote runtime dependency.
