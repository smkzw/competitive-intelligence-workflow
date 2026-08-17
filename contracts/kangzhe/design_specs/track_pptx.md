# 康哲设计规范 · 可编辑 PPT / PPTX 轨

> **Portable package track pack** · track_id=`pptx`  
> **Load order**: `ROUTER.md` → `core.md` → **this file** (to EOF).  
> **Assets**: `assets/logo_bot.svg` (relative to `design_specs/`).  
> **Authority**: This pack + `core.md` are the load-time contract for this product. Machine-only samples live in `local_map.md` (optional).  
> **Do not** require reading the legacy monorepo body for this product.

**Also read**: core.md

---

## 0. 使用入口（本轨 only · pptx）

**本文件只约束可编辑 PPT / PPTX**（含 PPT Master 流程）。  
HTML-PPT / 流式 / 站点 / 驾驶舱 **NEVER** 从本文件取 HTML 版式合同；先读 `ROUTER.md`。

### 何时加载本轨

- `PPT`、`PPTX`、`可编辑PPT`、`非HTML-PPT`、`PPT Master`
- `方案汇报` / 培训且用户要求可编辑 PPTX

### 硬边界

- **NEVER** 用 HTML 截图冒充可编辑 PPTX。
- 画布与页类型以本轨 §4/§7/§8/§13 为准；品牌色与字号地板继承 `core.md`。
- 方案汇报 Playbook 见本轨 §14.14。

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


## 0.3 生成前的最小输入与默认决策（pptx）

开始制作前，Agent MUST 明确：主题、受众、页数、源材料。若用户已提供充分材料，不重复追问：

- 默认画布：`1280×720`，16:9。
- 默认背景：白色。
- 默认第一页：§8.1 固定正式封面；后续页：§7.1 内容页 chrome。
- 默认字体：§6.1 固定字体栈（见 `core.md` / 本轨）。
- 默认交付：可编辑 `.pptx` 源文件；讲者备注按 §13.6。
- 默认审阅：管理层视角，20–30 秒能看懂本页结论。

## 4. 画布与基础网格

### 4.1 画布

| 产出类型 | 画布约定 |
| --- | --- |
| PPT | 宽屏 16:9，13.333 x 7.5 inch |
| HTML-PPT | 逻辑画布 1280 x 720 px，只在共同祖先 `.deck` 上统一缩放 |
| HTML 报告 | 流式/响应式，不绑定固定画布；推荐以 16:9 为基准比例，容器宽度随视口变化 |

PPT 字号与 SVG/HTML 像素换算：1 pt 约等于 1.333 px。

### 4.2 固定安全边距

PPT与HTML-PPT统一使用以下逻辑坐标；不允许按页型临时压缩：

| 区域 | 固定值 |
| --- | --- |
| 逻辑画布 | `x=0, y=0, width=1280, height=720` |
| 内容页正文框 | `x=56, y=96, width=1168, height=564` |
| 内容页顶部chrome | `y=0–88`，坐标见§7.1与§14.6 |
| 内容页页脚 | `left=24, right=32, bottom=14`，字号18 px |
| 非内容页 | 只能使用§14.5固定坐标，不继承内容页安全边距 |

所有受众文字必须位于对应母版的固定框内；截图、图表或背景图可以在其专属组件框内裁切，但不得越过页面边界或遮挡chrome、页脚。

### 4.3 内容区固定栅格

内容构图只能从以下预设选择，坐标均相对`.slide-body`的`1168×564`：

- 单栏：`1168px`。
- 双栏：`564px 40px 564px`。
- 三栏：`repeat(3,minmax(0,1fr))`，固定`column-gap:16px`，三列逻辑宽约`378.67px`。
- 证据链三栏：`430px 16px 430px 16px 276px`。
- 左图右表：`564px 40px 564px`；图内可再上下等分，行间距16px。
- 甘特/大表：全宽`1168px`；左标签列与时间列在组件内部用CSS变量定义，外框不变。

Agent不得创建新的页面外框或任意gutter。若内容不能放进上述预设，必须缩短文案、减少同页对象或拆页，不压缩字体和安全边距。
- **填充式构图（开放类，受 §16.A `content_slide_richness` 闸门约束）**：当一页的核心信息是流程/关系/覆盖率/汇聚/分支等可视化结构时，Agent MAY 自创填满正文框的构图（`display:flex;flex-direction:column;height:564px` 或等效撑满），不必从上述 6 种预设中选择；但 MUST 通过丰富度闸门（无死带、含 living visual、字号层级、非等白卡行）。自创构图的列宽/间距不受上述固定值约束，只受正文框边界（1168×564）与间距八档约束。

### 4.4 HTML-PPT 与 HTML 报告的响应边界

本规范区分三类产出的坐标约束：

| 产出类型 | 坐标约束 | 布局方式 |
| --- | --- | --- |
| PPT | 固定物理画布 13.333 x 7.5 inch | 绝对坐标、固定像素 |
| HTML-PPT | 逻辑画布 1280 x 720 px，视觉缩放 | 固定坐标 + 单次 CSS `transform:scale()` 等比缩放 |
| HTML 报告 | 无固定画布 | 流式/响应式，百分比、flex、grid、clamp |

HTML-PPT 的响应只发生在画布外层：固定 `1280×720` 页面保持完整浮点比例缩放并在视口双轴居中。NEVER 用 `max-width:1280px` 阻止大屏放大，NEVER 对缩放值取整或吸附像素，NEVER 用媒体查询改变页内字号、列数、间距、折行和坐标。可直接执行的 CSS/JavaScript 见 §14.2–§14.3。

HTML 报告响应式规则：

- 容器：`max-width: min(1100px, 90vw); margin: 0 auto; padding: 0 4vw;`。
- 移动端（< 768 px）：容器宽度 100%，padding 0 3vw；复杂表格允许横向滚动或折叠列。
- 平板（768–1280 px）：容器宽度 90%，最大 960 px。
- 字体：使用 `clamp()` 定义响应式字号（示例见 §14.10.3）。
- 网格：优先 `grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px;`。
- 表格：复杂表格允许横向滚动或折叠列，不得通过压字适配窄屏。
- SVG 图表必须使用 `viewBox` 实现缩放。


## 7. 固定品牌构件

### 7.1 内容页顶部 chrome

标准内容页必须包含：

- 左上双斜切标：
  - 橙色主斜切：`x=24,y=9,w=70,h=62`，`clip-path:polygon(44% 0,100% 0,57% 100%,0 100%)`，填充`#FF9900`。
  - 黄色副斜切：`x=5,y=42,w=40,h=36`，使用同一polygon，填充`#FFCC00`。
- 顶部橙线：从 `x=54, y=80` 到 `x=1257, y=80`，`stroke=1.5`，颜色 `#FF9900`。
- 页面标题：`left=91,top=24,right=270,min-height=44`，字号`32 px`、行高1.2、字重700、`#0F1115`；标准内容页必须单行。
- 右上full logo：`x=1031,y=45,w=158,h=33`（内容页紧凑 full logo）；hero 页（封面/章节/结束/目录）的 wordmark 槽更大（见 §7.4.1：封面/结束 240×50、章节/目录 200×44），NEVER 在 hero 页用比内容页更小的 Logo。

内容页不得删除这个chrome。需要全幅图时，图仍必须放在`.slide-body`内并保留完整标题、双斜切、顶线、Logo、页脚和页码；封面、目录、章节首页、结束页使用各自母版而不是“删除内容页chrome”。

#### 7.1.1 坐标系声明与适用范围

- 本章节（§7、§8）给出的像素坐标仅适用于 **PPT 和 HTML-PPT 的固定画布**，坐标系基于 1280 x 720 逻辑画布，单位为 px。PPT 端按 1 pt 约等于 1.333 px 换算；HTML-PPT 端只在共同祖先`.deck`上使用单次CSS transform等比缩放。
- **HTML 报告**（流式长文档）不得直接使用本节固定像素坐标，应按 §4.4 和 §14.10.3 使用响应式布局（百分比、flex、grid、clamp）。
- 涉及字号时，HTML 报告应使用 `clamp()` 或相对单位，不得按 viewport 宽度压缩正文基础字号。

#### 7.1.2 顶部 chrome YAML 摘要（Agent 速查）

```yaml
content_page_chrome:
  required: true
  applies_to:
    - content
    - info_table
    - gantt
    - single_result
    - comparison
    - evidence
  excluded_from:
    - cover
    - toc
    - section
    - ending
    - meta_spec
  elements:
    - id: orange_facet
      type: clipped_rect
      x: 24
      y: 9
      w: 70
      h: 62
      clip_path: "polygon(44% 0,100% 0,57% 100%,0 100%)"
      fill: "#FF9900"
    - id: yellow_facet
      type: clipped_rect
      x: 5
      y: 42
      w: 40
      h: 36
      clip_path: "polygon(44% 0,100% 0,57% 100%,0 100%)"
      fill: "#FFCC00"
    - id: top_rule
      type: line
      x1: 54
      y1: 80
      x2: 1257
      y2: 80
      stroke: "#FF9900"
      stroke_width: 1.5
    - id: page_title
      type: text
      x: 91
      y: 24
      right: 270
      min_height: 44
      font_size_px: 32
      line_height: 1.2
      fill: "#0F1115"
      font_weight: 700
    - id: logo
      type: image
      name: full_cms_logo
      x: 1031
      y: 45
      w: 158
      h: 33
```

#### 7.1.3 实测锚点与模板提示处理

- 顶部斜切以§7.1.2的矩形外框与polygon为唯一重建口径。PPT端可用自由形实现，但外接框、颜色和四个视觉斜边必须与该polygon一致；不得换成圆角梯形、闪电或其他图标。
- 模板中内容页标题文本框（x≈91,y≈31）在源文件里常写成 `@@（某某页示例）@@` 形式，这是给生成者的提示，**不是可见标题**。生成时必须用真实业务标题替换，且不得把 `@@` 留在页上（见 §2.2、§16.A）。
- 封面/结束页无顶部 chrome；若误加，视为偏离规范。

### 7.2 页脚

标准内容页页脚固定为**两槽**，Flex 横向两端对齐，容器 `left=24,right=32,bottom=14`，`gap:16px`，字号 18 px / 13.5 pt，行高1.2：

- **左槽 `.footer-id`**：固定文本 `产品中心-医学部｜20XX年XX月`（部门名为**汇报方固定身份**，NEVER 替换为源材料的 `owner`/编制部门/项目名/章节名；日期为汇报当月）。颜色**灰色** `#808080`（`var(--kz-meta)`），字重 400，`white-space:nowrap`。分隔符固定全角 `｜`。
- **右槽 `.slide-number`**：页码 `N / TOTAL`，颜色 `#FF9900`，字重 700，`white-space:nowrap`。内容页 MUST 显示；封面、目录、章节首页、结束页 MUST 不显示页脚与页码。

**页脚禁止项（NEVER）**：`.deck-footer` 内 MUST 恰有两个受众可见子槽（`.footer-id` + `.slide-number`），NEVER 出现第三个元素——不得插入"依据 / 来源 / 对应SOP / 对应 SOP / 章节号 / 口径 / 内部文件"等中间 `<span>`，也不得在两槽之间加 `|` 分隔符或来源文字。源材料的内部出处（SOP 编号、章节号、内部说明书、需求书、会议纪要）若需保留，MUST 写入该页 `<aside class="notes">` 讲者备注，或在正文内以"（见§X.X / SOP-XXXX）"行内括注；NEVER 进页脚。**唯一例外**见 §10.4：仅当本页引用**外部同行评审论文/公开法规指南**时，才允许在页脚**上方**、正文框**之内**加一行 8 pt 灰色参考文献，且该行与页脚垂直分离、NEVER 重叠。

**汇报方部门身份统一固定为 `产品中心-医学部`**，出现于三处且均不得被源材料 owner 替换：内容页页脚左槽 `.footer-id`、封面 `.cover-department`、结束页 `.ending-meta`。封面/结束页的日期同为汇报当月。

注：目录页与章节首页没有页脚。结束页的部门与日期使用居中 `·` 分隔的 `.ending-meta`（`产品中心-医学部 · 20XX年XX月`，颜色 `#404040`），它是结束页元信息，不是页脚。

### 7.3 封面/结束页底部 ribbon

封面和结束页有全宽底部品牌 ribbon：

- `left=0,top=565,width=1280,height=155`。
- 中心有康哲 logo 或企业标识。
- fallback顶部色条固定高12 px，三段宽度比例`1 : 1.55 : 3`，依次`#FFCC00 / #F5A000 / #FF9900`；正式ribbon图片必须完整覆盖同一外框。

### 7.4 品牌资产嵌入与非Logo fallback

正式Logo一律按§1.2从官网地址下载并嵌入；“没有本机模板”不再构成缺少Logo的理由。只有底部ribbon整图或封面背景图未提供时，才使用本节可重建的非Logo fallback。构建中可暂用文字识别标签辅助排版，但正式验收前必须换成官网SVG。

#### 7.4.1 正式Logo固定槽

内容页右上 full logo 区：

- 位置：`x=1031,y=45,w=158,h=33`。
- 内部固定为`<img src="assets/logo_bot.svg" alt="CMS 康哲药业">`；单文件版把`src`改为同一SVG的Data URL。
- 图片固定`width:100%;height:100%;object-fit:contain;object-position:center`，不得加滤镜、蒙版或颜色覆盖。

封面、目录、章节、结束页 wordmark（hero 页，品牌最醒目，MUST 比内容页 full logo 更大）：

- 尺寸：封面/结束页 `left=52,top=44,w=240,h=50`；章节/目录页 `right=52,top=44,w=200,h=44`。内容页右上 full logo 仍为 `158×33`（紧凑）。即 hero wordmark 渲染宽（200–240）> 内容页 full logo（158）。
- 内部使用同一 `assets/logo_bot.svg` 并 `object-fit:contain`；允许因原始 121:25 比例在槽内产生上下留白，不得为填满外框而拉伸或裁切。

#### 7.4.2 底部 ribbon fallback

封面/结束页底部无正式 ribbon 图片时：

- 背景固定`#FFFFFF`，外框`left=0,top=565,width=1280,height=155`。
- 顶部12 px使用§7.3固定三段色条。
- 剩余143 px内水平垂直居中官网Logo SVG，显示外框固定`width:242px;height:50px`并`object-fit:contain`。
- fallback不增加额外英文副行；官网SVG内容保持原样。

#### 7.4.3 封面/结束页背景 fallback

无背景图时：

- 默认固定使用`#FFFFFF`，不自行生成装饰图。
- 只有用户提供或明确要求生成主题背景时，才可在封面/结束页`1280×565`视觉槽使用世界地图、分子网络、药片轮廓、医院/实验室线框或AI流程线稿；生成后必须经人工审阅，并保持大面积浅色留白。
- 自定义背景中辅助线稿不透明度固定8%，只用`#EEECE1`或`#DCE6F2`。
- NEVER 使用暗色科技背景、强渐变、霓虹、模糊 stock photo 或与医学汇报无关的场景图。


## 8. 页面类型规范

> **适用范围声明**：§8.1–§8.11 给出的坐标均基于 1280×720 逻辑画布，仅适用于 **PPT 和 HTML-PPT** 的固定画布；HTML 报告（流式长文档）应按 §4.4 使用响应式布局，不得直接套用本节像素坐标。

### 8.0 页面原型选择器

当用户描述一页内容时，Agent MUST 先按以下决策表选择页面原型，再套用对应 §8.X 规范。若用户意图同时匹配多个原型，使用列表中第一个命中；若意图不明确，MUST 回退到 `content`（§8.4），不得自创新原型。

```yaml
page_selector:
  - intent_match: [封面, 首页, 标题页, cover, opening]
    archetype: cover
    spec_ref: "§8.1"
  - intent_match: [目录, 章节导航, 汇报章节, toc, contents]
    archetype: toc
    spec_ref: "§8.2"
  - intent_match: [章节切换, 分隔, section, chapter, chapter_break]
    archetype: section
    spec_ref: "§8.3"
  - intent_match: [产品基础信息, 项目概览, 资产概览, 投前信息, info_table, asset_overview]
    archetype: info_table
    spec_ref: "§8.6"
  - intent_match: [时间线, 管线, 里程碑, 临床开发阶段, gantt, timeline, pipeline]
    archetype: gantt
    spec_ref: "§8.7"
  - intent_match: [单产品, 单竞品, 单产品临床结果, 单适应症深度, single_competitor, single_trial_result]
    archetype: single_result
    spec_ref: "§8.8"
  - intent_match: [多竞品对比, 横向比较, 竞品矩阵, 间接比较, comparison, head_to_head, vs]
    archetype: comparison
    spec_ref: "§8.9"
  - intent_match: [截图, 证据链, AI工具截图, 系统截图, 病历证据, evidence, screenshot]
    archetype: evidence
    spec_ref: "§8.10"
  - intent_match: [结束, 谢谢, ending, thank_you, 收尾]
    archetype: ending
    spec_ref: "§8.11"
  - intent_match: [其他分析, 进展页, 策略页, content, progress, analysis]
    archetype: content
    spec_ref: "§8.4"
fallback:
  archetype: content
  spec_ref: "§8.4"
  rule: "IF none of the above matches, use content. NEVER invent a new archetype."
never_use_in_final:
  - meta_spec
```

`meta_spec` 对应 §8.5 全局规范页，是模板元规则页，MUST NOT 出现在任何最终演示文稿、PDF、HTML 或截图交付中。

### 8.1 封面页

用途：项目正式汇报首页。

结构：

- 背景：上部大面积浅色世界地图/医学企业图，底部品牌 ribbon。
- 左上 logo：x=52, y=48, w=81, h=33。
- 标题：`left=60, right=60, top=156`，居中，字号 56 px，行高 1.2，`#404040`，700；单行优先，最多两行。
- 部门：`left=0, right=0, top=382`，居中，字号 32 px，行高 1.25，`#595959`，700。
- 日期：`left=0, right=0, top=468`，居中，字号 22 px，行高 1.2，`#404040`，400。
- 黄线：`left=280, right=280, top=538, height=4`，`#FFCC00`。
- 底部ribbon：`left=0, bottom=0, width=1280, height=155`；完整DOM/CSS以§14.5.1为唯一实现。

写作规则：

- 标题直接写项目/主题，例如“医学 AI 工具专项进展汇报”“XXX 项目投后医学进展汇报”。
- 不写“面向董事长与医学部负责人”等受众说明。
- 不写长副标题；如果需要说明范围，放到第二页或备注。

### 8.2 目录页

用途：4 章左右的管理层结构导航。

结构：

- 左上标题“汇报章节”：`left=68, top=25`，字号 48 px，行高 1.15，700。
- 黄线：x=68, y=96, w=582, h=5，`#FFCC00`。
- 元信息：`left=68, top=112`，字号 20 px，行高 1.2，`#808080`。
- 默认目录板：`left=68, top=178, width=1144, height=392`，固定2列×2行，列间距24 px、行间距20 px。
- 每张章节卡：`560×186 px`，编号字号52 px，标题字号30 px；标题最多12个全角中文字符，必须单行。可增加一行16 px的真实章节范围短语，最多18个全角字符。
- 每张卡必须同时包含真实章节编号和标题；NEVER使用空`i/div`卡片、无文字流程框或仅靠色条占位。
- 有用户提供或获授权的主题图时，MAY使用“左侧四行目录 + 右侧真实图片”变体；图片必须承载真实主题信息。没有图片时MUST回到默认2×2目录板，不得生成假流程fallback。
- 右上wordmark：`right=52, top=48, width=81, height=33`。完整DOM/CSS以§14.5.2为唯一实现。

内容规则：

- 目录最多 4 个一级章节；超过 4 个应合并。
- 每个章节标题应是名词短语或结论短语，避免“第一部分/第二部分”。
- AI 工具类汇报推荐章节：现状与目标、阶段进展、验证结果、下一步计划。
- 投前/投后医学项目推荐章节：项目概览、医学价值、临床/注册路径、风险与建议。

### 8.3 章节页

用途：章节切换，给听众重置注意力。

结构：

- 大编号：`left=108, top=112`，字号 117 px，行高 1，`#FFA900`，700。
- 黄线：x=113, y=261, w=240, h=5，`#FFCC00`。
- 章节标题：`left=114, right=100, top=290`，字号 59 px，行高 1.2，`#0F1115`，700，最多两行。
- 右上小 logo：`right=52, top=48, width=81, height=33`。完整DOM/CSS以§14.5.3为唯一实现。

内容规则：

- 只放章节编号和标题，不塞正文。
- 标题最多两行；若超过两行，改短。
- 章节标题应表达业务任务，例如“投前医学价值判断”“临床开发路径与关键风险”“AI 工具验证与下一步灰盒测试”。

### 8.4 标准内容页

用途：大多数分析页、进展页、策略页。

结构：

- 固定使用§14.6内容页chrome、full Logo、页脚与页码。
- 正文框固定`x=56,y=96,width=1168,height=564`。
- 正文构图只能选择§4.3列名预设，不得自行改变页面外框、gutter或安全边距。
- 页脚固定`left=24,right=32,bottom=14`，不占正文框。

内容规则：

- 页面标题使用“结论/任务/发现”，不要只写主题词。
- 每页只解决一个问题。
- 先给结论，再给证据，再给下一步。
- 优先结构化：bullet、短表、流程、证据截图、时间线。

### 8.5 全局规范页

模板第 4 页是全局规范页，也是元规则页，不得出现在任何最终演示文稿、PDF、HTML 或截图交付中。其规则必须被继承到内容页。

继承规则：

- 标题：微软雅黑/Arial，24 pt。
- 标准卡片标题：微软雅黑/Arial，18 pt；compact卡片标题15 pt。
- 正文：微软雅黑/Arial，14.25 pt；只有流程、甘特、compact卡使用12 pt。
- 主题色：`#FF9900`、`#FFCC00`。
- 可插入 imagegen 图标辅助表达。
- 每页使用 bulletpoints 和子 bulletpoints，避免长篇段落。
- 数据必须标明来源。
- 图片建议使用简洁图表或机制图。
- 表格单元格内边距固定引用§11.1：标准`14px 16px`，高密度`8px 12px`。
- 表头：微软雅黑/Arial，14.25 pt；高密度大表可用12 pt。
- 参考文献：8 pt，底部区域。

### 8.6 产品/项目基础信息表页

用途：投前项目、竞品、资产概览。

结构：

- 表格相对`.slide-body`固定`x=0,y=0,width=1168,height=564`。
- 固定2列8行；在`border-collapse:collapse`下，author track固定`250px 917px`，加1 px折叠外边框后实渲染总宽1168 px；前7行author height各58 px，最后“临床优势”行157 px，加1 px折叠外边框后实渲染总高564 px。前7行每格最多1行，最后一行右格最多4行。
- 左标签列固定`#FBE3D6`、`#0F1115`、19 px/700，并用不参与布局的`inset 7px 0`橙色shadow绘制识别条；不得使用7 px实体`border-left`撑宽表格。右值列19 px/400。
- 交替底色：`#FBE3D6` 与 `#FFFFFF`。
- 分隔线：`#FAC090`，1 px；单元格内边距`14px 16px`。

固定表格CSS必须显式把外边框计入564 px，不得只依赖8行高度相加：

```css
.kz-table.info {
  width:1168px; height:564px; box-sizing:border-box;
  table-layout:fixed; border-collapse:collapse; border-spacing:0;
}
.kz-table.info col:first-child { width:250px; }
.kz-table.info col:last-child { width:917px; }
.kz-table.info tbody tr { height:58px; }
.kz-table.info tbody tr:last-child { height:157px; }
.kz-table.info tbody td:first-child {
  border-left:1px solid var(--kz-table-line);
  box-shadow:inset 7px 0 0 var(--kz-orange);
}
```

浏览器实测必须满足`table.getBoundingClientRect()==[56,96,1168,564]`且`table.bottom==slideBody.bottom==660`（逻辑坐标，误差≤0.5 px）。若仍得到1172×565，说明左列仍使用7 px实体边框或仍沿用918/158 author track；不得用负margin、scale或裁切掩盖。本页的来源、说明和判断已经由标题及8行字段承载；不得在固定表格下再追加参考文献、脚注、callout或透明占位。确需来源脚注时必须另换带参考文献区的页型或拆页。

内容规则：

- 左列字段固定：产品名、厂家、靶点/作用机制、注册分类、适应症、规格、用法用量、临床优势。
- 临床优势必须拆为便捷性、安全性、疗效，必要时加“证据等级/证据成熟度”。
- 若尚无临床数据，只能写“基于 MOA/临床前数据推测”，不得写成已证实临床优势。
- 右列不要堆长段，优先短句和分号。
- 一句话判断写入页面标题，不在固定8行表外再塞callout；需要额外结论块时拆页。

### 8.7 甘特图/竞品管线页

用途：竞品时间线、临床开发阶段、里程碑更新。

结构：

- 组件相对`.slide-body`固定`x=0,y=0,width=1168,height=564`；表头高42 px、背景`#FCF5E6`。
- 左侧标签列固定230 px；时间区固定938 px，按实际期数使用`repeat(N,minmax(0,1fr))`。
- 最多7个产品行；表头外剩余522 px平均分配，每行74.57 px，单元格上下padding各6 px。
- 左侧标签固定三行：产品名19 px/700/1.2，厂家与适应症16 px/600/1.2。
- 条形阶段：I 期、II 期、III 期、NDA、获批。
- 阶段条和里程碑标签固定16 px/700；同页最多3个红色关键里程碑。

颜色（以模板第 6 页实测为准）：

- Ⅰ期 / 历史已完成：`#AAA6A1` 灰，深色字 `#0F1115`。
- Ⅱ期（早期进行中）：`#F2D2B5` 浅橙，深褐字 `#3C342E`。
- Ⅱ期 / Ⅱa期（用于不同竞品分组的浅绿变体）：`#DCE9C8`，深褐字 `#3C342E`。
- Ⅲ期（核心进行中阶段）：`#D9955D` 橙，深色字 `#0F1115`。
- NDA / 申报：固定`#A85F34`深橙、白字；不得按页临时换绿。
- 里程碑（获批 / 关键数据更新）：红色`#C00000` 15×15小方块 + `#24211F` 16 px/700标签。
- 药品名固定19 px/700、`#24211F`；厂家与适应症固定16 px/600，分别`#5F5954`与`#514B46`。内容放不下时缩短标签、减少产品或拆页。
- 本公司（康哲）资产可用更明确橙色边框或加粗标签，但不要破坏全图可比性；预测/未公开阶段用虚线边框或浅填充并标注“预计/未公开披露”。

内容规则：

- 一个甘特页最多7个产品或竞品；超过必须拆页或分适应症。
- 每个条形内文字固定2–4个字；超过4字改写或扩大时间span。
- 年份/半年度坐标必须对齐，不可凭视觉近似随意漂移。
- 对未来预测和未公开进度要标注“预计/推测/未公开披露”。

顶部年份/H1-H2表头统一使用`#FCF5E6`，不交替换色。医学AI多部门总甘特不使用本页竞品标签列，必须改用§14.7的`.portfolio-gantt`固定组件。

### 8.8 单一竞品临床试验结果页

用途：单产品/单竞品深度医学结果。

结构：

- 顶部摘要框相对`.slide-body`固定`x=0,y=0,width=1168,height=96`，暖米色`#FCF5E6`、圆角8 px、内边距`14px 16px`；正文19 px/1.4，关键数值600。
- 主结果区固定`x=0,y=112,width=1168,height=360`，使用双栏`564px 40px 564px`。
- 左栏固定放两张上下图，每张`564×172`，中间16 px；右栏固定三列表，高360 px。
- 结论条固定`x=0,y=488,width=1168,height=38`，暖米色底或白底红色左边线；文字19 px/700，`#C00000`只用于有证据支撑的风险或关键结论。
- 参考文献固定`x=0,y=538,width=1168,height=26`，Times New Roman 10.67 px/1.2、`#404040`，最多两行。

内容规则：

- 顶部 bullet 应直接回答“结果意味着什么”。
- 表格列固定：维度、结果、备注。
- 关键终点、时间点、治疗组、对照组必须写清。
- 安全性不能只写“安全性良好”，应列停药、死亡、AESI、感染、突破性溶血等与疾病/机制相关风险。
- 引文必须完整到作者、题名、期刊/年份/卷页、DOI/PMID/NCT；内部文档使用可识别文件名/文档标题、版本或日期、页码/表号，不得写个人目录或绝对路径。

### 8.9 竞品横向对比页

用途：多个竞品、多个终点、疗效/安全性指标比较。

结构：

- 相对`.slide-body`使用固定双栏`564px 40px 564px`。
- 左栏固定放1张SVG/矢量横向图，外框`564×564`。
- 右栏最多4张总结卡，固定使用§14.2`.comparison-card-grid`；gap16 px，4卡时每卡`274×274`，不足4卡时从左上顺序填充，不拉伸卡片。
- 卡片标题24 px/700，正文19 px/1.4；白底、`#D6D2CD` 1 px边、圆角8 px、标准轻阴影。

内容规则：

- 图表必须有统一口径：人群、时间点、终点定义。
- 不同研究之间不能直接做头对头结论，除非有间接比较方法或明确限定。
- 右侧卡片按“疗效、便利性、安全性、开发/注册风险”组织。
- 每张卡片标题应是判断句，不是空泛词。

### 8.10 截图证据链分析页

用途：展示 AI 工具、原始病历、审核结果、邮件/沟通证据之间的对应关系。

结构：

- 页面标题直接写观点句；正文相对`.slide-body`使用固定证据链三栏`430px 16px 430px 16px 276px`，高度564 px。
- 左栏：AI审核结果或系统输出截图；固定`430×564`。
- 中栏：原始病历/检验/CRF/邮件证据截图；固定`430×564`。
- 右栏：固定3张洞察卡，垂直gap16 px，每张`276×177.33`：
  - 证据可定位
  - 缺口可前置
  - 充分的风险提示
- 洞察卡：标题带固定`#F79646`、白底、圆角8 px、浅蓝边`#DCE6F2`；标题20 px/700，正文16 px/1.25。
- 洞察卡左侧绿色对勾：`#2E7D32` FREEFORM 图标，仅作“已确认/正向”语义，不用于普通装饰。
- 截图统一`object-fit:contain`，白底、1 px`#D6D2CD`边、圆角8 px；框选与箭头不得越出各截图框。

内容规则：

- 不说“AI 完全正确”，而说“AI 结论可回到原始资料复核”。
- 明确 AI 是辅助定位、证据链整理和风险前置，不替代医学判断。
- 涉及患者材料时，必须脱敏；截图不可露出直接身份、电话、身份证、付款、住址等信息。
- 结论要对应截图上的可见证据，不要让页面变成能力宣传。

注：右侧洞察卡标题带使用`#F79646`，不得改成`#FF9900`或其他橙色。

### 8.11 结束页

结构：

- 上部全幅浅色背景：`left=0, top=0, width=1280, height=565`。
- 中心结束焦点区：`left=340, top=220, width=600, height=200`，仅作定位容器；背景透明、无边框、无圆角、无阴影。
- “谢谢”：焦点区内`left=0, right=0, top=14`，居中，字号68 px，行高1.2，`#595959`，700。
- 黄线：`left=380, top=450, width=520, height=4`。
- 部门和年月：`left=0, right=0, top=495`，居中，字号18 px，行高1.2，`#404040`。
- 底部品牌ribbon：`left=0, top=565, width=1280, height=155`；完整DOM/CSS以§14.5.4为唯一实现。

内容规则：

- 结束页只放“谢谢”和简短部门/日期，不放长句。
- “谢谢”周围不得出现可见透明卡片轮廓、玻璃拟态边框或悬浮面板阴影；需要与复杂背景分离时，只能在背景图本身做低对比留白或使用无边框的柔和文字阴影。
- 如果需要“请领导指导”，放在演讲备注，不放可见页。

### 8.12 配色分页面映射（速查）

| 页面原型 | 主背景 | 主文本 | 品牌强调 | 表格/卡片 | 风险红 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| cover | 浅色世界图 + 底部 ribbon | `#404040` 标题 / `#595959` 部门 | `#FFCC00` 黄线 | — | 无 | 无 chrome |
| toc | `#FFFFFF` | `#0F1115` 标题 / `#808080` 元信息 | `#FFA900` 编号 + `#FFCC00` 黄线 | — | 无 | 右半幅图 |
| section | `#FFFFFF` | `#FFA900` 大编号 / `#0F1115` 标题 | `#FFCC00` 黄线 | — | 无 | 无 chrome |
| content | `#FFFFFF` | `#0F1115` 标题 / `#404040` 正文 | `#FF9900` chrome | 浅灰边卡 | 仅风险 | 固定 chrome |
| meta_spec | 同 content | 同 content | 同 content | — | — | **禁止出现在最终交付** |
| info_table | `#FFFFFF` | `#404040` 左列加粗 | `#FF9900` 7px左识别条 | `#FBE3D6` 隔行 / `#FAC090` 线 | 仅风险 | 固定8行，无额外表头 |
| gantt | `#FFFFFF` | `#24211F`/`#5F5954`/`#514B46` 标签 | 阶段橙 `#D9955D` | 阶段条见 §8.7 | `#C00000` 里程碑 | 最多7行 |
| single_result | `#FFFFFF` | `#404040` 正文 | `#C00000` 结论条 | `#FCF5E6` 摘要框 | `#C00000` | Times New Roman 参考文献 |
| comparison | `#FFFFFF` | `#0F1115` 卡标题 | `#FF9900`/`#F79646` 卡强调 | 白底浅边卡 | 仅风险 | 左图右卡 |
| evidence | `#FFFFFF` | `#0F1115` 卡标题 | `#F79646` 卡头 + `#2E7D32` 绿勾 | `#DCE6F2` 蓝边 | 仅风险 | 三栏证据链 |
| ending | 浅色图 + ribbon | `#595959` 谢谢 | `#FFCC00` 黄线 | 无卡片；仅透明无边框定位容器 | 无 | 无 chrome |

> 所有页面的品牌橙/黄合计占比 ≤ 12%，红色 ≤ 3%（仅风险/缺口/关键结论）。


## 9. 医学汇报内容逻辑

> **文字内容底层逻辑（总纲）**：医学汇报不是“资料陈列”，而是“给管理层一个可拍板的判断”。所有演示页面默认走 `结论/问题 → 证据 → 影响 → 下一步`；证据必须可回溯；推测必须显式标注；AI 只作辅助定位与风险前置，医学经理终审。流式HTML报告不强制这一页面叙事顺序，但证据、不确定性和AI边界仍适用（见 §14.10）。

### 9.1 管理层页的底层结构

每页应默认使用以下逻辑：

```text
结论/问题 -> 证据 -> 影响 -> 下一步
```

不要用“背景 -> 过程 -> 结论”的慢启动结构，除非页面是时间线或复盘。

### 9.2 投前项目页

应回答：

- 这个资产解决什么未满足需求？
- 机制与适应症是否匹配？
- 现有证据到什么等级？
- 与 SOC/竞品相比有什么真实优势？
- 临床开发和注册路径的关键风险是什么？
- 需要董事长/负责人做什么判断？

推荐页面组合：

1. 项目一句话判断。
2. 产品基础信息表。
3. MOA 与疾病机制匹配。
4. 临床/临床前证据强度。
5. 竞品与 SOC 对比。
6. 开发路径与里程碑。
7. 关键风险与建议。

### 9.3 投后项目页

应回答：

- 与上次汇报相比，发生了什么实质变化？
- 里程碑是否按计划推进？
- 临床、注册、医学、供应或商业假设有没有变化？
- 新风险是否影响价值判断？
- 下一阶段资源需求是什么？

推荐表达：

- 使用“进展状态 + 偏差 + 原因 + 纠偏动作”。
- 不只写完成事项清单。
- 对延迟、未披露、待确认事项要设单独状态。

### 9.4 AI 工具进展页

应回答：

- 工具现在能解决哪个医学工作流问题？
- 输入是什么，输出是什么，谁复核？
- 已在哪个项目/病例/中心验证？
- 与人工结果是否一致？不一致如何处理？
- 下个灰盒/真实世界试运行怎么定义成功？

推荐表达：

- “AI 辅助证据定位、资料缺口识别、规则一致性检查”优于“AI 自动审核通过”。
- “医学经理终审”必须保留在流程中。
- 对 `通过（需验证）` 这类状态，应表达为溯源提醒，不应升级为失败或重大风险。
- 避免抽象口号，尽量展示规则对象、阈值、证据片段和复核链条。

### 9.5 临床试验开展页

应回答：

- 当前阶段：启动、筛选、入组、治疗、随访、锁库、CSR。
- 关键指标：中心启动、筛选失败、入组速度、PD、AE/SAE、数据缺口、方案偏离。
- 风险：入排一致性、疗效终点窗口、救援治疗、禁用伴随用药、数据可溯源性。
- 下一步：中心沟通、医学监查、统计/数据核查、方案修订或培训。

注意：

- 救援治疗、禁用伴随用药、DMM/intercurrent event 处理要分开写。
- 不确定信息写“待核实/未公开披露/源文件未提取到”，不要补全。


## 13. PPT Master 使用规则

### 13.0 可编辑PPT的强制路由

当用户要求“PPT”“可编辑PPT”“非HTML-PPT”或明确点名PPT Master时，Agent MUST真实调用已安装的`ppt-master`技能完成项目初始化、Strategist、逐页SVG、质量检查、后处理与`svg_to_pptx.py`导出。以下行为均不算PPT Master测试通过：

- 只生成HTML后改扩展名或截图粘贴进PPTX。
- 使用`python-pptx`、PptxGenJS或自写脚本绕开PPT Master主流程。
- 只写`design_spec.md/spec_lock.md`而没有生成真实`.pptx`。
- 生成SVG预览但没有运行PPT Master质量检查、`finalize_svg.py`和`svg_to_pptx.py`。
- 交付的PPTX仅整页位图不可编辑；正文、标题、表格与基础图形必须保留为PowerPoint可编辑对象。

弱模型/跨Agent复现测试还必须记录：读取了哪个`design.md`、调用了哪个PPT Master路径、项目目录、质量检查结果、导出PPTX路径、PPTX内部可编辑文字对象数量。未记录或无法验证时记为路由失败，不得以“视觉接近”替代。

PPT Master状态必须按可观察产物推进，禁止按“已经开始执行”或Agent自述提前完成：

| 阶段 | 允许标记完成的最低证据 |
| --- | --- |
| `initialized` | 项目目录存在，`README.md/templates/images/sources`按任务需要就绪 |
| `specified` | 项目根存在非空`design_spec.md`与`spec_lock.md`，页数和母版清单与任务一致 |
| `svg_complete` | `svg_output/`中逐页SVG数量等于计划页数，文件名顺序连续，每页可被XML/SVG解析器读取 |
| `quality_passed` | `svg_quality_checker.py`最近一次完整运行退出码为0；若曾失败，报告必须记录失败原因和修复项 |
| `finalized` | `svg_final/`页数等于计划页数，`finalize_svg.py`成功完成 |
| `pptx_exported` | `svg_to_pptx.py`成功完成，目标`.pptx`存在且可作为ZIP/OOXML打开 |
| `editable_verified` | `ppt/slides/slide*.xml`页数正确；`<a:t>`文本运行和`<p:sp>`形状数量均大于0；禁止只有每页一个`<p:pic>`的整页位图 |
| `visually_reviewed` | 逐页SVG/PPT渲染原图已查看；使用PowerPoint或目标Office渲染器复核字体、折行与裁切 |

任一阶段失败时保留当前阶段，不得用“占位完成”“后续补做”或只写测试报告绕过。修复后必须重跑该阶段及全部下游阶段。

同一任务同时要求PPTX、HTML-PPT和流式HTML时，按“一个交付物一个检查点”串行完成：先生成并验证PPTX，再生成并验证HTML-PPT，最后生成并验证流式HTML。每个长文件必须分为可恢复的结构块写入，至少在CSS/母版、内容页组、运行时/闭合标签三个边界检查文件尾；不得在一次超长模型响应或单个内存代码单元中同时组装多种成品。出现中断时从最后一个已验证结构块续写，不重做已通过产物。

### 13.1 模板选择

若执行环境已有“康哲公司模板”或“SMK康哲医学AI模板”，MAY用其正式Logo、封面背景和ribbon资产起步；先读取本文件，再读取模板自身说明。若模板规则与本文件冲突，以本文件的最大化窗口、字体下限、证据与AI边界为准。

若执行环境没有任何康哲模板，MUST直接使用§7.4与§14提供的可重建HTML/CSS，不得依赖某台电脑的模板目录。

### 13.2 PPT Master硬锁定

PPT Master的`spec_lock.md`必须至少锁定以下值；不得只写颜色和字体名称后把版式交给Agent自由推断。

```yaml
canvas:
  preset: ppt169
  width_in: 13.333
  height_in: 7.5
  logical_width_px: 1280
  logical_height_px: 720
  px_per_in: 96
page_masters:
  mutually_exclusive: [cover, toc, section, content, ending]
  exact_specs:
    cover: "§14.5.1"
    toc: "§14.5.2"
    section: "§14.5.3"
    content: "§14.6"
    ending: "§14.5.4"
colors:
  primary: "#FF9900"
  accent: "#FFCC00"
  number: "#FFA900"
  text: "#0F1115"
  body: "#404040"
  title_gray: "#595959"
  meta: "#808080"
  risk: "#C00000"
  border: "#AAA6A1"
  border_weak: "#D6D2CD"
  table_head: "#F79646"
  table_soft: "#FBE3D6"
  table_line: "#FAC090"
  surface_warm: "#FCF5E6"
  med_blue: "#407AAA"
  blue_soft: "#DCE6F2"
  stats_green: "#587B3B"
  stats_soft: "#DCE9C8"
  pv_brown: "#A85F34"
  white: "#FFFFFF"
  custom_colors_forbidden_unless_added_here: true
fonts:
  zh: "Microsoft YaHei"
  latin_and_digits: "Arial"
  cover_title_pt: 42
  toc_title_pt: 36
  toc_item_pt: 22.5
  section_number_pt: 87.75
  section_title_pt: 44.25
  content_title_pt: 24
  card_title_pt: 18
  compact_card_title_pt: 15
  body_pt: 14.25
  compact_body_pt: 12
  footer_pt: 13.5
  reference_pt: 8
chrome:
  content_title_rect_px: [91, 24, 919, 44]
  content_top_rule_px: [54, 80, 1203, 1.5]
  full_logo_rect_px: [1031, 45, 158, 33]
  content_body_rect_px: [56, 96, 1168, 564]
  footer_rect_px: [24, 684.4, 1224, 21.6]
  footer_left_id: "产品中心-医学部｜20XX年XX月"
  footer_left_color: "#808080"
  footer_left_weight: 400
  footer_page_number: "N / TOTAL"
  footer_slots: 2
  footer_source_line_forbidden: true
spacing_px:
  discretionary_gap_margin_allowed: [4, 8, 12, 16, 24, 32, 40, 56]
  fixed_exceptions:
    card_padding_y: 14
    component_contracts: "§14列明数值原值复用"
  two_column_gutter: 40
  three_column_gap: 16
  card_padding: [14, 16]
  card_gap: 16
cards:
  radius_px: 8
  compact_radius_px: 6
  shadow: "0 5px 16px rgba(15,17,21,.09)"
placeholder_rules:
  replace_double_ampersand: true
  remove_double_at_prompt: true
```

### 13.3 页面节奏

- 封面、目录、章节、结束页：breathing，留白大，信息少。
- 标准内容页：anchor，以标题和关键结论锚定。
- 表格、甘特、竞品矩阵：dense，正文/标签首选12 pt / 16 px；单页必须完整展示G01–G18等18行总览时，绝对下限为10.5 pt / 14 px，且只允许用于表体和坐标轴标签；辅助说明、标题、结论、风险、来源不得降到该下限。
- 截图证据页：anchor+dense，证据图和结论卡并重。

超高密度页按以下顺序消解容量，Agent不得直接缩字：

1. 删除重复描述、把完整句压成短标签，保留事实标签、阶段号、里程碑和风险边界。
2. 合并同类列、缩短字段名、使用固定图例和缩写表。
3. 将“总览”和“可读明细”拆成相邻两页；总览承担关系导航，明细承担逐项阅读。
4. PPT/HTML-PPT仍放不下时拆页，不得低于上述绝对下限，不得裁字，不得把正文转成图片。
5. 流式HTML表格在桌面保持至少13 px正文；窄屏使用横向滚动、冻结首列或卡片化摘要，不压缩到不可读。

若任务明确要求“单页超高密度总览”，允许10.5 pt / 14 px，但必须同时满足：不超过18个主体行、行高不低于18 px、普通文字与背景对比度至少4.5:1、逐页原分辨率人工可读、另有来源或明细入口。该入口必须是可机器识别的`data-detail-ref="页码/章节/附录ID"`，流式HTML也可使用真实`a[href]`。否则测试记为容量失败。

#### 13.3.1 超高密度命名版式与容量

以下两种页面是18阶段材料的固定压测版式，PPT Master与HTML-PPT均按同一逻辑画布实现。

**A. `ultra-raci-decision`：18阶段RACI + 决策权摘要**

- 正文框仍为`[56,96,1168,564]`；底部28 px只放来源，不进入主布局。
- 主布局固定`grid-template-columns: 688px 464px; gap:16px; height:520px`。
- 左侧只允许RACI压缩表：表头1行 + G01–G18共18行；列固定为`阶段 / A / R / C / I`五列，不得加入“完整部门说明”等第六列。
- 左侧行高固定24 px，表头28 px；表体14 px / 600，阶段号14 px / 700。A/R/C/I内容必须使用部门缩写，不写完整句。
- 右侧不是第二张12行大表。只放`4–6`条最关键决策权摘要，每条固定72–108 px高；字段为`决策主题 / 最终决策 / 不可由AI替代`。完整12项目录移入相邻明细页、附录或流式HTML。
- 任一Agent在同页并排完整18行RACI与完整12行决策权表，直接判容量失败，不进入字号压缩。

**B. `ultra-ai-boundary`：18阶段AI总览 + 人机边界**

- 主布局固定`grid-template-columns: 704px 448px; gap:16px; height:520px`。
- 左侧表固定`阶段 / 主AI场景 / 分级 / 成熟度`四列；表头28 px + 18行×24 px，表体14 px / 600。每个`tbody > tr`的computed height必须**等于**24 px，不是仅设置`min-height`；所有单元格单行、不换行。场景名过长时先压缩为短标签，例如`入排预审/证据定位/缺失提示`、`MRDS/自查核查/PV`，完整解释移入明细入口。
- 右侧固定三块：A0–A3图例`112 px`、人机分工`194 px`、禁止边界`182 px`，块间16 px。右侧每块正文最多5条，每条最多一行半。
- A0–A3图例必须使用紧凑固定结构：容器高112 px、内边距`10px 14px`、`box-sizing:border-box`、`border:0`；需要轮廓时使用不占盒模型空间的`inset box-shadow`。标题20 px/20 px；标题下四行各18 px、14 px/18 px、`white-space:nowrap`。四行只允许短标签：`A0 禁止结论`、`A1 辅助检索/草稿`、`A2 抽取/比对/预警`、`A3 规则内自主执行`；不得写完整解释句。112 px刚好等于上下内边距20 px + 标题20 px + 四行72 px，任何实体边框或额外margin都会造成溢出。
- A0禁止线必须红字或红色左边框，但不得再嵌套完整阶段表；右侧卡片不得把主布局总高度撑过520 px。
- 若阶段说明无法压成一行，缩短措辞或将完整说明放入备注/流式HTML；不得降低到14 px以下。

两种版式的机器验收：

```yaml
ultra_density_gates:
  main_height_px: 520
  body_bottom_max_px: 660
  table_body_font_min_px: 14
  table_row_height_min_px: 24
  normal_text_contrast_min: 4.5
  detail_reference: "至少一个[data-detail-ref]；流式HTML也可用真实a[href]"
  ultra_raci_columns: 5
  ultra_raci_rows: 18
  decision_summary_items_max: 6
  ultra_ai_columns: 4
  ultra_ai_rows: 18
  ultra_ai_header_height_px: 28
  ultra_ai_each_body_row_height_px: 24
  ultra_ai_body_cell_wrap: forbidden
  side_panel_blocks: 3
  ai_legend_height_px: 112
  ai_legend_border_px: 0
  ai_legend_items: 4
  ai_legend_each_item_height_px: 18
  ai_legend_item_wrap: forbidden
  ai_legend_scroll_height_must_not_exceed_client_height: true
  same_page_full_18_raci_plus_full_12_decisions: forbidden
```

### 13.4 生成前后检查

生成前：

- 明确页数、受众、汇报主题、是否投前/投后/AI/临床。
- 明确每页证据来源和未披露边界。
- 删除所有模板说明页中只给 Agent 看的提示。

生成后：

- 导出 PPTX 后打开真实文件或渲染截图。
- 依次验证`quality_passed → finalized → pptx_exported → editable_verified → visually_reviewed`，不得把项目初始化、SVG完成或Agent自述当作PPT完成。
- 检查所有内容页是否保留品牌chrome，并确认封面、目录、章节首页、结束页没有误套内容页chrome。
- 搜索 `&&` 和 `@@`。
- 检查引用和数据来源。
- 检查字号、表格、截图和图表是否可读。
- 在目标Office中记录实际中文字体验收结果。LibreOffice等替代渲染器缺少`Microsoft YaHei/微软雅黑`而出现方框时，必须记录为渲染环境字体缺失，继续用PowerPoint或目标Office复核；不得据此宣称源文本丢失，也不得在未复核时宣称显示正常。
- 同时检查 §19 跨 Agent 不变量，不得被具体 PPT Master deck 规则放松。

### 13.5 页码与动画

页码：

- 内容页固定使用右下角`N / TOTAL`，字号13.5 pt，字重700，颜色`#FF9900`。
- 封面、目录、章节首页、结束页固定不放页码。
- 只有用户明确要求整份演示取消页码时才可全deck取消；不得改成只显示当前页，也不得半数有、半数没有。

动画：

- 默认不使用对象级入场动画。
- 页面切换最多使用简洁 fade；正式汇报可完全无转场。
- 禁止飞入、旋转、弹跳、逐字闪烁、粒子特效等会削弱医学汇报可信度的效果。

### 13.6 讲者备注

是否生成备注取决于任务：

- 用户要求“汇报、演讲、讲稿、逐字稿、speaker notes、Presenter notes”时，必须生成备注。
- 默认医学管理层汇报可提供简短备注，但不要把备注内容放到可见页。
- 每页备注建议 120-250 中文字，围绕“这一页怎么讲、重点停留在哪里、下一页如何过渡”。
- 备注语气应口语化、克制、便于现场汇报；不要重复朗读页面所有 bullet。
- 备注可以包含受众提示和讲述顺序，但不能包含无法公开的患者身份信息或未脱敏敏感信息。
- HTML-PPT 使用 `<div class="notes">` 或框架指定 notes 区；可见 slide 中不得出现 presenter-only 文本。


## 14.14 临床试验方案汇报/介绍/培训 Playbook（PPT 与 HTML-PPT 轨）

### 14.14.0 触发与适用

- 触发词：`方案汇报`、`方案介绍`、`方案培训`、`方案讲解`、`核查前培训`、`protocol training`，且源材料为临床试验方案（protocol）。命中任一触发词时，MUST 在 PPT（§13/ppt-master）或 HTML-PPT（§14.1–§14.9）轨上套用本节；流式 HTML 报告与站点式 HTML 不适用本节。
- 多期无缝设计口径：方案为 Ⅱ/Ⅲ 期等多期操作无缝设计时，MUST 先确认本次汇报的期别；页面默认只纳入指定期别内容。两期共用条款（如"Ⅱ期和Ⅲ期采用相同标准"的排除标准）MUST 标注"两期共用"，不得以另一期叙事呈现；引用另一期分析作为本期依据（如剂量选择）MUST 显式标注"依据/引用"，不得混入主叙事。QC 时 MUST 以另一期专属信息（如 Ⅱ 期的 120 例、1:1:1、高/低剂量组）做污染扫描，命中即修。

### 14.14.1 章节分布与页面骨架（默认 19 页，可按条文量增减）

| # | 页 | 原型 | 内容要求 |
| --- | --- | --- | --- |
| 1 | 封面 | cover | 标题含方案编号与期别；部门=产品中心-医学部 |
| 2 | 目录 | toc | 2×2 板按实际章节数顺序填充，空位不拉伸 |
| 3 | 章节页 01 研究设计 | section | 带一句导语 |
| 4 | **药物概览页** | content | 第一章第一页，结构见 14.14.2 |
| 5 | 基本信息页 | content/info_table | 10 字段：研究药物、适应症、研究题目、研究分期、最新方案版本/日期、方案编号、组长单位及研究者、剂型规格、给药途径、用法用量 |
| 6 | PICOSN 框架页 | content | P/I/C/O/S/N 树状 SVG + 右侧数字 KPI 条（总样本量/组比/主要终点时点/给药次数） |
| 7 | 章节页 02 研究方案 | section | 导语 |
| 8 | 纳入标准页 | content | 原文逐条 + 阈值视觉锚点栏 |
| 9–11 | 排除标准 1–3 页 | content | 原文逐条双栏；洗脱期/实验室阈值数字深红 |
| 12 | 研究终点页 | content | 主终点横幅 + 次要终点分类高密度 + 右轨安全性/PK-PD-免疫原性/探索性三卡 |
| 13 | 伴随用药页 | content | 背景治疗横幅 + 允许/限制/禁用三列 + 补救治疗流程条 |
| 14 | 章节页 03 研究流程 | section | 导语 |
| 15 | 整体流程轴页 | content | 三阶段访视轴 SVG（分期带/人群带/访视节点/随机与主终点菱形/分组卡/提前退出分支/图例） |
| 16–18 | SoA 1–3 页 | content | 上 2/3 日程表 + 下 1/3 附注（沿用方案注号） |
| 19 | 结束页 | ending | — |
| 附 | Backup 页 | content | 附录性质置正文末 |

章节顺序 MUST 为 研究设计→研究方案→研究流程；药物概览页 MUST 为第一章第一个内容页。

### 14.14.2 药物概览页结构

- 标题式：`<药名>药物概览：是什么药 · 怎么起效 · 既往证据`；顶部"一句话记住"条（靶点+抗体类型+关键机制+给药特点）。
- 三栏：①是什么药（研发、成分、分子量、剂型规格、给药途径；结构亮点：Fc 突变与 FcRn 亲和力数值）；②怎么起效（靶点动作+疾病病理+未满足需求数值）；③既往研究（分期卡：期别/关键疗效数值/安全性，数据截止日期 MUST 标注）。
- 底部结论条：本期剂量依据；引用它期分析 MUST 标"依据"。逐字稿须点明"先把药讲清"的定位。

### 14.14.3 内容与口径要求

- 入排标准 MUST 原文（不改写不概括）；重点词加粗；评分阈值、洗脱期、实验室阈值 MUST 深红 #C00000；子条号 MUST 沿用方案原编号（含 6.1–6.11 等），NEVER 因转换重排。
- SoA 页 MUST 上 2/3 表 + 下 1/3 附注；附注沿用方案注号；期别特有规则深红。
- 逐字稿 NEVER 暴露稽查/自查/整改措辞；存在问题清单时只隐性强调对应方案条款。每页 150–300 字（章节页可短）；封面/结束页 NEVER 迎检口吻。

### 14.14.4 超高密度 SVG 作图要求（PPT 与 HTML-PPT 通用）

- 双栏超高密度原文页：左栏文宽 ≤660px、右栏起点 x≥658 且文宽 ≤550px；16px 单行中文 ≤41 字，MUST 手工 tspan 换行，NEVER 依赖渲染器自动换行。
- SoA 表：列宽等分（标签列 286px + 8×126px=1168），访视列中心与流程轴节点对齐；● 符号字体 Arial；阶段色带与流程轴页一致。
- 流程轴：访视节点等宽等距；随机/主终点菱形中心在轴线上；分支卡互不重叠（间距≥20px）；提前退出分支线 NEVER 穿过访视日期文字。
- 所有 SVG 文字 NEVER 越栏、越正文框右界（x≤1224）、与页脚相交（y≤660）。

### 14.14.5 双色斜切绝对顶点锁定（跨轨硬约束）

- PPT（freeform/polygon）与 SVG（polygon/path）轨 MUST 用绝对顶点绘制内容页左上双斜切：
  - 橙主斜切：(24,9)(94,9)(64,71)(24,71)，fill #FF9900
  - 黄副斜切：(5,42)(45,42)(25,78)(5,78)，fill #FFCC00
- HTML 轨 MUST 沿用 §7.1.2 的 clip-path 百分比实现（polygon(44% 0,100% 0,57% 100%,0 100%)），两实现视觉等价，NEVER 混用、NEVER 自行换算。
- 机器闸门：两斜切全部顶点 MUST 满足 0≤x≤1280 且 0≤y≤88；黄斜切最左 x≥5；橙底边=71、黄底边=78。

### 14.14.6 复盘：斜切拉伸越界根因（教训）

- 事故：首版 PPT 轨把 §7.1.2 的 clip-path 百分比自行换算为绝对顶点时误读（把底边左顶点外推），橙斜切左下顶点落到 x=-16、黄斜切 x=-35，斜切向左拉伸超出页面边界。根因：规范只给 CSS clip-path 百分比一种形态，PPT/SVG 轨需 Agent 自行换算且无验收锚点。
- 修正：14.14.5 给出绝对顶点锁定与机器闸门。凡"百分比/相对坐标"型装饰组件，规范 MUST 同时给绝对顶点；Agent NEVER 自行换算。


## 15. 典型页面组合

### 15.1 投前医学项目汇报

1. 封面。
2. 目录。
3. 项目一句话判断。
4. 产品基础信息表。
5. 疾病/机制匹配。
6. 临床或临床前证据摘要。
7. SOC 与竞品对比。
8. 临床开发路径甘特图。
9. 注册与医学风险。
10. 建议与需决策事项。
11. 结束页。

### 15.2 投后项目进展汇报

1. 封面。
2. 本期结论和状态总览。
3. 上次承诺事项闭环。
4. 临床/注册/医学进展。
5. 入组或数据质量状态。
6. 关键风险变化。
7. 资源与下一步计划。
8. 结束页。

### 15.3 AI 工具进展汇报

1. 封面。
2. 目录。
3. 工具目标和当前边界。
4. 真实工作流与角色分工。
5. 规则/证据链示例。
6. 系统截图证据页。
7. 验证结果和不一致处理。
8. 中心/项目级汇总价值。
9. 下一步灰盒测试计划。
10. 需协调资源和决策。
11. 结束页。

### 15.4 临床试验开展情况汇报

1. 封面。
2. 总览状态。
3. 中心启动和入组进展。
4. 入排一致性和筛选失败原因。
5. AE/SAE/PD/数据缺口。
6. 医学监查发现。
7. 风险等级与纠偏动作。
8. 下一阶段里程碑。
9. 结束页。


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



## Package assets

- Official logo (portable): `assets/logo_bot.svg`
- Prefer embedding this file (or its data-URL) over remote runtime dependency.
