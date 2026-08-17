# 康哲设计规范 · 交互单页 / 驾驶舱轨

> **Portable package track pack** · track_id=`interactive`  
> **Load order**: `ROUTER.md` → `core.md` → **this file** (to EOF).  
> **Assets**: `assets/logo_bot.svg` (relative to `design_specs/`).  
> **Authority**: This pack + `core.md` are the load-time contract for this product. Machine-only samples live in `local_map.md` (optional).  
> **Do not** require reading the legacy monorepo body for this product.

**Also read**: core.md

---

## 0. 使用入口（本轨 only · interactive）

**本文件只约束交互单页 / 数据驾驶舱**（可过滤、下钻、dashboard）。  
其他产物 **NEVER** 从本文件取版式合同；先读 `ROUTER.md`。

### 何时加载本轨

- `驾驶舱`、`看板`、`交互板`、`可过滤`、`下钻`、`dashboard`、`控制台`

### 硬边界

- **NEVER** 套用 HTML-PPT 翻页 chrome 或多页站点信息架构（除非用户明确要求混合，再分轨交付）。
- 品牌 / 证据 / AI 边界继承 `core.md`；风险红仅用于风险语义。

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


## 0.3 生成前的最小输入与默认决策（interactive）

开始制作前，Agent MUST 明确：数据源、筛选维度、默认视图、受众。若用户已提供充分材料，不重复追问：

- 默认形态：单页数据驱动应用；过滤/下钻状态可恢复。
- 默认背景：白色或中性浅灰；顶栏浅色默认。
- 默认字体：§6.1；控件与数字可读。
- 默认审阅：真实交互路径（筛→结果变）+ 截图证据。

### 14.13 高级控件词表与第五轨：交互单页应用

本节定义可选高级控件词表与第五轨（交互单页应用）。**所有采纳项 MUST 使用 §5 token、§6 字体栈、§14.7.3 静态基线与冻结语义**；禁止清单内的词条 NEVER 进入任何轨道。本节只扩大"丰富度"发挥空间，不放松 §5/§14.7.3/§19 任何硬约束。

#### 14.13.1 第五轨：交互单页应用（Interactive Deck / Dashboard）

| 维度 | HTML-PPT（§14.1–§14.9） | 流式HTML（§14.10） | 站点式（§14.12） | 交互单页（本节） |
| --- | --- | --- | --- | --- |
| 形态 | 固定页数翻页 | 单文档滚动 | 多页面互通 | 单页、数据驱动、可过滤/下钻/看板 |
| 典型场景 | 会议汇报 | 阅读型报告 | 反复查阅 | **管理驾驶舱**：KPI 看板、工具矩阵过滤、项目组合下钻、双周数据板 |
| 数据层 | 内联 | 内联 | `data/*.js` 注入 | `data/*.js` 注入（同 §14.12.2，规避 file:// CORS） |
| 演讲者运行时 | MUST | 不强制 | 不强制 | 不强制（若需投屏可叠加 HTML-PPT runtime） |

路由词：`驾驶舱`、`看板`、`交互板`、`可过滤`、`下钻`、`数据板`、`dashboard`、`控制台`。

#### 14.13.2 采纳控件词表（MAY/SHOULD，新 class 一律 `kz-` 前缀）

控件实现层已预编码进 `kangzhe-brand.css` 第 9 段（`.kz-glass/.kz-soft/.kz-bento/.kz-sticky-story/.kz-timeline/.kz-marquee/.kz-hscroll/.kz-spot/.kz-tilt/.kz-magnet/.kz-parallax/.kz-clip/.kz-mask`，含幅度上限与冻结/RM 全清）。逐字内联该文件后直接以 class 取用；NEVER 从零自写这些控件的 CSS（同首选机制）。

**布局与结构（流式/站点/交互轨）**：
- **便当盒 `.kz-bento`**：大小不一矩形模块（`grid-template-areas`），大块承载核心结论、小块承载 KPI/状态/术语；NEVER 等宽卡行（丰富度闸门 e）。适合开篇总览、能力矩阵。
- **固定叙事区 `.kz-sticky-story`**：左栏 sticky（标题+进度），右栏滚动切换阶段；用于流式报告的"流程叙事/项目复盘"段；<768px 降级为自然流。
- **时间线 `.kz-timeline`**：竖线+部门色节点+里程碑菱形（复用 §14.7.3 形状词表与红色标记规则）；节点标签≥16px。
- **分屏 `.kz-split`**：左文右视或一侧固定；用于流式章节开场或站点 hero 变体。
- **全出血 `.kz-fullbleed`**：色块/图延伸到屏幕边缘，仅限章节过渡带（高≤240px）；NEVER 整页铺色（I-04）。

**导航与切换**：
- **标签切换 `.kz-tabs`**：内容分类视图（如四部门视角）；键盘 ←→ 切换、`aria-selected`；指示条 2px 品牌橙。
- **面包屑 `.kz-crumb`**：站点式多层下钻路径；灰 #808080、当前节点 #404040。
- **返回顶部 `.kz-top`**：滚动>600px 出现，右下 40px 圆、白底橙边、hover 抬升≤3px。
- **命令面板 `.kz-cmdk`**：`Ctrl/⌘+K` 弹搜索/操作面板（站点全局搜索的键盘增强），Esc 关闭、焦点陷阱；遮罩复用 `.drawer` 规则。
- **分页 `.kz-pager`**：交互轨长列表用页码+上/下页；NEVER 无限滚动（见 §14.13.3）。

**组件与反馈**：
- **气泡提示 `.kz-tip`**：hover/focus 显示短说明（术语口径、图标含义），13px、对比≥4.5:1、延迟 150ms；NEVER 承载唯一信息（I-63）。
- **轻提示 `.kz-toast`**：复制/导出等轻量反馈，右上、3s 自灭、`aria-live="polite"`。
- **灯箱 `.kz-lightbox`**：缩略图点击放大查看原图（站点截图/证据图），Esc 关闭、焦点陷阱。
- **手风琴 `.kz-acc`**：FAQ/附录折叠，`<details>` 原生或等价，键盘可达。
- **骨架屏 `.kz-skeleton`**：仅交互轨异步数据块用 #EEECE1 脉冲占位；流式/站点静态数据 NEVER 假加载（无真实异步=无骨架屏）。
- **空态/错误态 `.kz-empty`/`.kz-error`**：交互轨过滤无结果 MUST 空态（解释+重置按钮）；错误态 MUST 带重试入口。

**滚动与动效（流式/站点）**：
- **视差 `.kz-parallax`**：仅局部（hero 环境层/章节过渡带），位移≤40px、速度比≤0.3；RM/冻结清零。
- **滚动驱动 `.kz-scrollline`**：流程脊/时间线进度线随滚动推进（`scroll-timeline` 或 IO 回退）；静态基线=画满。
- **横向滚动 `.kz-hscroll`**：横向画廊（项目卡排/标签墙），MUST 有方向暗示（边缘渐隐+箭头）+ `scroll-snap` 对齐。
- **跑马灯 `.kz-marquee`**：术语/部门标签带低速横移（≤40px/s）、hover 暂停、RM 静态排布；仅站点 hero 或流式开篇，NEVER 内容正文。
- **聚光灯悬停 `.kz-spot`**：大卡内光标跟随柔光（radial-gradient+mask）；白底用低对比暖光（#FF9900 6–8% 透明度），NEVER 深色霓虹。
- **三维倾斜卡 `.kz-tilt`**：旋转≤4deg+内部高光位移；仅交互/站点精选卡；NEVER 用于证据/表格/甘特（数值读取几何不可变）；RM/冻结回零。
- **磁吸按钮 `.kz-magnet`**：主 CTA 朝光标位移≤6px；仅站点 hero 主按钮；RM 禁用。
- **裁切揭示 `.kz-clip`**：章节过渡图/文以 clip-path（圆/矩形展开）一次性入场；静态基线=全展开。
- **视图过渡**：站点式跨页 `@view-transition` + `@supports` 回退（列表卡→详情封面平滑）；不支持即直跳。
- **文字蒙版 `.kz-mask`**：hero 大标题/章节数字内显低对比网格/粒子纹理（`background-clip:text`）；纹理仅品牌灰/橙低透明，NEVER 彩色渐变。

**玻璃拟态 scoped 采纳 `.kz-glass`**：允许层=粘性导航/抽屉遮罩面板/hero 叠层/正文卡片（适度）；约束：背景 `rgba(255,255,255,α)` α≥0.88（或品牌浅底同不透明度）、`backdrop-filter:blur(≤12px)`、1px `#D6D2CD` 边界保证边界可见、文字对合成背景对比≥4.5:1；每视口毛玻璃面≤4 且 NEVER 覆盖表格/证据/甘特/数值读取面；打印/`data-export`/`data-qc`/RM 冻结 → `backdrop-filter:none`+不透明背景。NEVER 深色玻璃/彩色玻璃/渐变玻璃/整页毛玻璃墙。
- **新拟态 scoped 采纳 `.kz-soft`**：允许=图标、按钮、小型控件、卡片；约束：双阴影（亮/暗同族）MUST 叠加 1px 边界或顶部色条满足 I-72 可感知层次，阴影色与背景差≥两档（亮 `#FFFFFF`/暗 `rgba(15,17,21,.12)` 起）；NEVER 用于表格/证据/甘特/数值读取面；打印保留边界。
- **视觉风格采纳边界**：
- **编辑杂志风**：MAY 借大标题/引语/栏目节奏（流式章节页）；字体栈与白底不变。
- **瑞士风**：网格/客观排版与本规范天然一致，鼓励。
- **颗粒噪点**：MAY 在 hero 环境层叠 ≤3% 透明度噪点降塑料感；内容区不可感知。

#### 14.13.3 禁止清单（NEVER，品牌红线）

- 深色模式/近黑底+霓虹、极光/网格渐变色球（同 §14.7.3 禁区重申）。
- 自定义光标（含附加式圆点/圆环——系统光标 MUST 保持原样；破坏医学汇报操作可预期性与无障碍）。
- 整页毛玻璃卡片墙、深色/彩色/渐变玻璃（玻璃拟态仅按 §14.13.2 scoped 规则）。
- 无限滚动（破坏精确定位、打印与冻结态）。
- WebGL/Three.js（违反 §14.8 离线单文件与性能预算；canvas 粒子已覆盖氛围需求）。
- 新野兽派粗边框/高对比撞色；单色/双色整站（品牌为四部门多色体系）。
- 整页持续视差/晃动（仅局部，见 §14.13.2）。
- 任何新控件 MUST 通过 §16.A 闸门与 §19 不变量；新 class 一律 `kz-` 前缀，NEVER 污染 §14.5–§14.7 命名组件合同。

#### 14.13.4 性能预算（新控件必守）

- 单文件总量≤100MB；新增控件 JS 体量不设硬上限，但须满足本节其余各项（离屏停帧、RM/冻结全清、零远程依赖）。
- 同页动效对象≤8（§14.7.3 A），新控件计入总额。
- 所有新增 IO/rAF MUST 离屏停帧、RM/冻结全清（同 §14.7.3 F 静态基线优先）。
- NEVER 远程字体/CDN（§14.8）。


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
