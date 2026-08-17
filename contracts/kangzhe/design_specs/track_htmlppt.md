# 康哲设计规范 · HTML-PPT（1280×720）轨

> **Portable package track pack** · track_id=`htmlppt`  
> **Load order**: `ROUTER.md` → `core.md` → **this file** (to EOF).  
> **Assets**: `assets/logo_bot.svg` (relative to `design_specs/`).  
> **Authority**: This pack + `core.md` are the load-time contract for this product. Machine-only samples live in `local_map.md` (optional).  
> **Do not** require reading the legacy monorepo body for this product.

**Also read**: core.md；可选 peer html-ppt runtime skill

---

## 0. 使用入口（本轨 only · htmlppt）

**本文件只约束 HTML-PPT**（浏览器翻页、固定页数、`1280×720` 逻辑画布）。  
流式报告 / 站点 / 驾驶舱 / 可编辑 PPTX **NEVER** 从本文件套 1280 画布规则；先读 `ROUTER.md`。

### 何时加载本轨

- `HTML-PPT`、`HTML演示`、`浏览器翻页`、`幻灯片HTML`、固定页数/逐页播放
- 用户要「可在浏览器放映的幻灯片」而非滚动长文

### 硬边界

- **MUST** 固定 `1280×720` 逻辑画布 + 等比缩放（见 §0.1）。
- **NEVER** 把本节画布规则套到 stream/site/interactive。
- 可编辑 PPTX 交付走 `track_pptx.md`，不得用本轨 HTML 截图替代。
- 方案汇报 Playbook 见本轨 §14.14；runtime 可与 peer `html-ppt` skill 组合。

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


## 0.1 最高底层验收要求：最大化桌面浏览器实渲染

本节**仅**约束 **HTML-PPT**。流式 / 站点 / 交互 **NEVER** 套用本节的 1280×720 画布、等比缩放或“最大化窗口翻页”验收。优先级高于后续一般版式建议。

- **MUST**：HTML-PPT 使用固定 `1280×720` 逻辑画布；浏览器只缩放整个画布，不重新排版页面内部元素。
- **MUST**：画布缩放比例为 `min(viewportWidth / 1280, viewportHeight / 720)`，并在最大化窗口中水平、垂直居中。
- **MUST**：`1280×720` 只作为设计坐标和基础回归视口；最终验收必须同时覆盖 `1920×1080`、`2048×1024`，以及用户提供的实际窗口尺寸。
- **MUST**：在浏览器缩放为 `100%` 时保存并人工查看每页的原始分辨率截图；至少覆盖 Chromium 内核，macOS/Safari 场景再覆盖 WebKit。
- **MUST**：最终截图来自观众实际放映运行时，包含真实页码、进度条及最终 chrome；`?preview=N` 仅供排版调试。
- **MUST**：跨平台交付至少覆盖Windows 10/11的Chrome或Edge（100%缩放、最大化）与macOS的Chrome和Safari/WebKit（100%缩放、最大化）；比较固定锚点、标题/标签/正文行数与裁切状态。
- **MUST**：只在同一台Mac运行Chromium和WebKit不等于完成跨OS验收。无法获得真实Windows或macOS时，必须在交付说明明确“该操作系统未实机验证”，不得宣称多端一致已确认。
- **MUST**：宽屏出现左右留白、较高屏出现上下留白均可接受；留白必须来自等比缩放，不能来自页面内容只堆在上半部。
- **NEVER**：不得将固定像素页面同时设为 `width:100vw;height:100vh` 后非等比铺满窗口。
- **NEVER**：不得仅凭源码、DOM 数值、无溢出检查、contact sheet 或 `1280×720` 截图宣称视觉验收完成。

### 0.1.1 长规范读取完整性闸门

本文件较长。Agent 使用文件读取工具时，首个返回块可能只覆盖前 500 行，却同时给出 `truncated:true`、`total_lines` 或“continue from offset”提示。以下为生成前置条件，不是可选的流程记录：

- **MUST**：从第 1 行读到 EOF；若工具分页或截断，按返回的下一 `offset` 连续补读，直到最后一块明确 `truncated:false` 或到达 `total_lines`。
- **MUST**：开始编码前记录已读区间，例如 `1–500 / 501–1000 / … / EOF`；未覆盖全部区间时不得声称“已完整读取设计规范”。
- **MUST**：生成文件后回读最终文件到 EOF，确认页数、必需章节、完整代码围栏或文件尾未被截断。
- **NEVER**：不得因首个读取块包含目录或核心 CSS 就推定后文已读；不得把“逻辑存在”“其余省略”“omitted for brevity”当作可交付代码。

本闸门只约束 Agent 的输入/输出完整性，不得写入演示文稿可见页面。

### 0.1.2 固定组件名称与结构完整性闸门

§14.5–§14.7 中给出完整 DOM/CSS 的命名组件是**可直接执行的封闭规格**，不是示意代码或视觉参考。只要页面选择了某个命名组件，Agent MUST 原样复制该组件的 DOM 层级、class 名、CSS selector 名、声明字号和固定几何；只能替换业务文字、来源允许的阶段内容及规范明确开放的 CSS 变量。

- **MUST**：保留规范中的完整组件命名。例如多部门总甘特必须使用`.portfolio-gantt / .portfolio-head / .portfolio-group / .portfolio-dept / .portfolio-tracks / .portfolio-track / .track-label / .track-time / .road-bar / .road-milestone / .road-pv`。
- **NEVER**：不得把固定class改成语义近似的短名、别名或自创名，例如把`.road-bar`改成`.bar`、把`.portfolio-group`改成`.gantt-group-*`，或用行内`grid-column`重写规范已定义的阶段条合同。
- **NEVER**：不得以“代码更简洁”“效果等价”“已经复刻”为由重新实现固定组件；选择器、层级或字号任一变化，都视为未使用该组件。
- **MUST**：validator在几何检查前先做命名组件完整性检查；命中组件根节点但缺少必需子选择器、出现禁止别名或固定组件字号低于声明值时，直接阻断渲染验收。

本闸门不禁止新增业务语义class，但新增class只能附加在既有固定class之后，例如`class="road-bar medical mid"`；不能替代固定class或覆盖其锁定几何与字号。


## 0.2 与 `html-ppt` 的组合规则

当本文件与通用 `html-ppt` 技能一起使用时，按以下顺序执行：

1. **只复用运行时**：只复用`html-ppt`的键盘翻页、哈希深链、页码、进度条、讲者备注与讲者窗口；§14.4–§14.7是唯一视觉模板。NEVER复制通用full-deck/single-page主题DOM，也不在康哲页面使用通用`.card/.pill/.lede/.stack/.mt-m/.g4`体系。
   - 读取本康哲规范即视为已完成theme/template选择；不再展示或追问通用36主题，不允许按`T`切换到其他主题。
   - 用户要求讲稿/讲者视图时，只复用runtime与notes能力；NEVER切换为`presenter-mode-reveal`或其他full-deck视觉模板。
2. **锁定康哲主题**：康哲样式表必须在通用 `base.css`、动画样式之后加载，覆盖通用主题的颜色、圆角、字体、阴影、`.deck` 与 `.slide` 尺寸。
3. **禁止主题漂移**：正式交付不加载通用主题轮换列表，不依赖按 `T` 键切换主题；若保留 `T` 键，必须确保没有可切换的非康哲主题。
4. **不依赖 CDN**：默认删除 Google Fonts 或其他外链字体。康哲Logo按§1.2从公司官网唯一地址下载一次；模块化HTML使用随包本地SVG，单文件HTML转为Data URL，PPT/PPTX直接嵌入下载后的SVG。最终产物不得把官网地址作为运行时图片依赖。
5. **一页一节**：每个逻辑页面只使用一个直属于 `.deck` 的 `<section class="slide">`；备用页放到 `<template>` 内，避免被运行时计入页数。
6. **可见页只放受众内容**：讲者提示写入 `<aside class="notes">` 或 `<div class="notes">`，不得混入正文。
7. **总览须保留母版类**：`O`总览clone必须使用`clone.className = source.className; clone.classList.add('is-active')`，不得重写为只有`slide is-active`；缩略逻辑画布固定1280×720，scale=`thumbWidth/1280`，不注入通用padding。clone须递归删除`data-qc-id`或加`data-qc-ignore`，所有验收扫描限定`.deck > .slide`并排除overview/presenter克隆。无法全部修改时正式版不创建overview DOM并禁用`O`，不能只禁快捷键后保留错误clone。讲者窗口iframe仍加载同一deck，不另写版式。

推荐加载顺序：

```html
<link rel="stylesheet" href="assets/base.css">
<link rel="stylesheet" href="kangzhe.css"><!-- 必须最后 -->
<script src="assets/runtime.js"></script>
```

正式医学汇报允许使用§14.7.3定义的“渐进增强动效层”，但视觉基线必须在无动画、无hover、截图导出和PPT转换时完整成立。对象飞入、弹跳、循环漂浮、逐字动画和持续旋转仍禁止。若加载`animations.css`，必须位于`base.css`之后、`kangzhe.css`之前；康哲主题最终覆盖时长、位移和降级规则。

若执行环境没有 `html-ppt` 的 `runtime.js`，可使用 §14.3 的最小运行时；不得因此放弃固定画布与等比居中。


## 0.3 生成前的最小输入与默认决策

开始制作前，Agent MUST 明确：主题、受众、页数、源材料，以及交付是PPT/PPTX、HTML-PPT、流式HTML报告、站点式HTML还是交互单页应用。若用户已提供充分材料，不重复追问；按以下默认值执行：

- 默认画布：`1280×720`，16:9。
- 默认背景：白色。
- 默认第一页：§8.1 的固定正式封面。
- 默认后续页：§7.1 的康哲内容页 chrome。
- 默认字体：使用§6.1固定字体栈，选择设备上第一个已安装字体；Windows通常命中微软雅黑，macOS通常命中苹方，若macOS已安装微软雅黑则允许优先命中微软雅黑；不下载远程字体。
- 默认转场：页面切换使用180–240ms轻微淡入；卡片可按§14.7.3做一次性短距离揭示与指针hover抬升。`prefers-reduced-motion`、打印、截图和PPT转换模式必须冻结为无动画稳定终态。
- 默认交付：保留模块化源文件；如用户需要直接转发，再额外生成单文件 HTML。
- 默认审阅：管理层视角，20–30 秒能看懂本页结论，正文逻辑字号不低于 16 px。


## 0.4 当前医学AI专题样式的锁定参数

本表与§14是“做出当前样式”的硬母版，不是灵感参考。除用户明确要求改变品牌模板外，Agent MUST 原值复用，不得自行换色、改字号、改坐标、改圆角、换页眉页脚或做“更现代”的再设计。与后文范围值冲突时，一律以本表和§14可执行代码为准。

| 项目 | 锁定值 |
| --- | --- |
| 逻辑画布 | `1280×720 CSS px` |
| PPT物理画布 | `13.333×7.5 in`；坐标换算`1 in = 96 px`，字号换算`1 pt = 1.333 px` |
| 页面类 | `cover-slide / toc-slide / section-slide / content-slide / ending-slide`，不得混用 |
| 封面主标题 | `56 px / 1.2 / 700`，居中，默认单行，最多两行 |
| 封面部门 / 日期 | `32 px / 700`；`22 px / 400` |
| 目录标题 / 条目 | `48 px / 700`；默认2×2目录卡标题`30 px / 700`；编号`52 px / 700` |
| 章节首页编号 / 标题 | `117 px / 700`；`59 px / 700`，标题最多两行 |
| 内容页标题 | `32 px / 1.2 / 700`，标准页MUST单行 |
| 常规正文 | `19 px / 1.4 / 400–600`；普通卡片正文不得自行改成16px |
| 高密度正文 / 标签 | `16 px / 1.2 / 600`，只用于compact卡、流程、甘特、表格；阶段条可700 |
| 卡片标题 | 标准`24 px`；compact`20 px`；均为`700` |
| 页脚 | 固定**两槽**：左`.footer-id`=`产品中心-医学部｜20XX年XX月`灰`#808080`/400，右`.slide-number`=`N / TOTAL`橙`#FF9900`/700；18 px / 1.2；NEVER 在页脚插入"依据/来源/SOP"等第三元素；部门名为汇报方固定身份，NEVER 用源材料 owner 替换 |
| 内容页正文区 | `x=56–1224，y=96–660`；宽`1168 px`、高`564 px`，不得越界 |
| 顶部chrome | 左上黄橙斜切、`y=80`橙线、右上Logo、无英文kicker |
| 卡片圆角 / 阴影 | 默认`8 px`；小组件`6 px`；静态层级使用§14.7.3的`--shadow-1/--shadow-2`（站点hero卡可用`--shadow-3`）；结束页不显示透明卡片边框或卡片阴影 |
| 固定间距刻度 | Agent自由构图时的gap/margin只使用`4 / 8 / 12 / 16 / 24 / 32 / 40 / 56 px`八档；§14列明的固定母版/组件数值均为封闭例外，只能原值复用，不得外推生成新间距 |
| 标准布局间距 | 页面左右`56 px`；双栏gutter固定`40 px`；三栏卡间距固定`16 px`；卡内边距固定`14 px 16 px`；同组元素间距`8 px`；区块间距`24 px` |
| 页面背景 | 默认`#FFFFFF`；暖底只用`#FCF5E6`，不得整页铺品牌橙/黄/红 |
| 进度条 | 浏览器内容视口底部`3 px`品牌橙 |
| 缩放 | 单一全精度`scale(min(vw/1280,vh/720))`，双轴居中 |

标准内容页标题必须单行。放不下时只能改写、缩短或拆页；不得自然换成两行，也不得由Agent临时发明双行标题版式。只有用户明确要求双行标题且本规范先补入完整命名变体、固定DOM/CSS/PPT坐标与验收锚点后，才可使用该变体。


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


## 14. HTML-PPT / HTML to PPT 使用规则

### 14.1 康哲主题Token与通用`html-ppt`别名

康哲样式表必须在通用样式之后加载。除语义明确的图表颜色外，页面CSS只引用token，不散落新增HEX。

```css
:root {
  color-scheme: only light;
  --deck-scale: 1;

  /* 康哲语义token */
  --kz-orange: #FF9900;
  --kz-orange-mid: #F5A000;
  --kz-yellow: #FFCC00;
  --kz-number: #FFA900;
  --kz-deep-text: #0F1115;
  --kz-body: #404040;
  --kz-title-gray: #595959;
  --kz-meta: #808080;
  --kz-risk: #C00000;
  --kz-border: #AAA6A1;
  --kz-border-weak: #D6D2CD;
  --kz-table-head: #F79646;
  --kz-table-soft: #FBE3D6;
  --kz-table-line: #FAC090;
  --kz-theme-warm-bg: #EEECE1;
  --kz-surface-warm: #FCF5E6;
  --kz-check-green: #2E7D32;
  --kz-med-blue: #407AAA;
  --kz-blue-soft: #DCE6F2;
  --kz-stats-green: #587B3B;
  --kz-stats-soft: #DCE9C8;
  --kz-pv-brown: #A85F34;
  --kz-gantt-phase1: #AAA6A1;
  --kz-gantt-phase2: #F2D2B5;
  --kz-gantt-phase2-green: #DCE9C8;
  --kz-gantt-phase3: #D9955D;
  --kz-gantt-nda-orange: #A85F34;
  --kz-gantt-gray: #AAA6A1;
  --kz-gantt-milestone: #C00000;
  --kz-gantt-text: #3C342E;
  --kz-gantt-label-primary: #24211F;
  --kz-gantt-label-secondary: #5F5954;
  --kz-gantt-label-tertiary: #514B46;
  --kz-white: #FFFFFF;

  /* 覆盖html-ppt通用token */
  --bg: var(--kz-white);
  --bg-soft: var(--kz-surface-warm);
  --surface: var(--kz-white);
  --surface-2: var(--kz-surface-warm);
  --border: var(--kz-border);
  --border-strong: var(--kz-meta);
  --text-1: var(--kz-deep-text);
  --text-2: var(--kz-body);
  --text-3: var(--kz-meta);
  --accent: var(--kz-orange);
  --accent-2: var(--kz-yellow);
  --accent-3: var(--kz-med-blue);
  --good: var(--kz-stats-green);
  --warn: var(--kz-pv-brown);
  --bad: var(--kz-risk);
  --radius: 8px;
  --radius-sm: 6px;
  --radius-lg: 10px;
  --shadow: 0 5px 16px rgba(15,17,21,.09);
  --shadow-lg: 0 9px 26px rgba(15,17,21,.12);
  --font-sans: "Microsoft YaHei", "微软雅黑", "PingFang SC",
    "Noto Sans SC", "Helvetica Neue", Arial, sans-serif;
  --font-display: var(--font-sans);
  --letter-tight: 0;  /* 覆盖通用base.css的字距token */
  --letter-normal: 0; /* 覆盖通用base.css的字距token */
  --ease: cubic-bezier(.4,0,.2,1);
}
```

正式医学汇报不使用通用模板的18–26 px大圆角、彩色渐变球、玻璃拟态和重阴影。默认圆角8 px，阴影仅用于把白卡与白底轻微分开。

### 14.2 固定逻辑画布：必须覆盖通用`100vw/100vh`

以下CSS是HTML-PPT的底层必需项。它必须位于通用`base.css`之后；缺少任何一项都可能在最大化宽屏中发生非等比拉伸或上下空间失衡。

```css
*, *::before, *::after { box-sizing: border-box; }

html, body {
  width: 100%;
  height: 100%;
  margin: 0;
  overflow: hidden;
  background: var(--kz-white);
}

body.tpl-kangzhe {
  display: grid;
  place-items: center;
  font-family: var(--font-sans);
  font-synthesis: none;
  color: var(--kz-deep-text);
}

.tpl-kangzhe .deck {
  position: relative;
  width: 1280px;
  height: 720px;
  flex: 0 0 1280px;
  overflow: hidden;
  background: var(--kz-white);
  transform: scale(var(--deck-scale, 1));
  transform-origin: 50% 50%;
}

.tpl-kangzhe .slide {
  position: absolute;
  inset: 0;
  width: 1280px;
  height: 720px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: stretch;
  padding: 96px 56px 60px;
  overflow: hidden;
  background: var(--kz-white);
  transform: none;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity .2s var(--ease);
}
.tpl-kangzhe .slide.is-active {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

body.tpl-kangzhe.single .slide {
  position: absolute;
  inset: 0;
  width: 1280px;
  height: 720px;
}

.tpl-kangzhe .slide-body > .grid.g2 {
  display:grid; grid-template-columns:564px 564px; gap:40px;
}
.tpl-kangzhe .slide-body > .grid.g3 {
  display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px;
}
.tpl-kangzhe .slide-body > .grid.evidence3 {
  display:grid; grid-template-columns:430px 430px 276px; gap:16px;
}
.tpl-kangzhe .comparison-card-grid {
  display:grid; grid-template-columns:274px 274px; gap:16px;
}
.tpl-kangzhe .grid > *, .tpl-kangzhe .comparison-card-grid > * { min-width:0; }
/* 静态基线：默认无位移。交互 hover 由 §14.7.3 C 在 motion 层启用，后加载覆盖本基线 */
.tpl-kangzhe .kz-card { transform:none; }
.tpl-kangzhe .kz-card:not([data-interactive="true"]):hover { transform:none; }
```

基础`.slide`与内容页都使用`padding-bottom:60px`，正文框物理底边固定`y=660`；不存在可占用的额外缓冲带。

康哲页内禁止使用通用`.card* / .pill* / .lede / .stack / .mt-m / .mb-m / .row / .g4 / .eyebrow / .kicker / .h1 / .h2 / .h3 / .h4 / .title / .gradient-text / .serif`，也禁止`data-anim / data-fx / data-themes`；这些类会引入未锁定的padding、gap、字号、字形、圆角、hover transform或英文标签。卡片统一`.kz-card`；`.slide-body`直接子层布局只用`.grid.g2/.grid.g3/.grid.evidence3`，竞品对比右栏内部只用`.comparison-card-grid`，其余使用§14.7命名组件。禁止裸`.grid`。validator必须扫描`.deck > .slide`的class与data属性，命中禁用项或`.grid`未同时命中允许变体即失败。

若需要浏览器打印/PDF，必须覆盖通用print规则，避免绝对定位页面叠在一起：

```css
@page { size:13.333in 7.5in; margin:0; }
@media print {
  html,body { width:auto; height:auto; overflow:visible; }
  body.tpl-kangzhe { display:block; }
  .tpl-kangzhe .deck {
    width:1280px; height:auto; overflow:visible; transform:none;
  }
  .tpl-kangzhe .slide {
    position:relative; inset:auto; display:flex; width:1280px; height:720px;
    opacity:1; pointer-events:auto; transform:none;
    break-after:page; page-break-after:always;
  }
  .tpl-kangzhe .slide:last-child {
    break-after:auto; page-break-after:auto;
  }
  .tpl-kangzhe .deck-footer { display:flex!important; }
  .progress-bar,.notes-overlay,.overview { display:none!important; }
}
```

- **MUST**：`.deck`与`.slide`的唯一逻辑坐标系是`1280×720 CSS px`；字号、行高、列数、间距和绝对坐标在任何桌面视口中保持不变。
- **MUST**：只对共同祖先`.deck`使用一次二维`transform:scale(s)`，其中`s=min(viewportWidth/1280,viewportHeight/720)`；保留完整浮点值，以画布中心为缩放原点。
- **MUST**：画布在浏览器内容视口水平、垂直居中；16:9以外的留白放在画布外，不得重新分配到页面内部。
- **MUST**：监听`window.resize`；可同时监听`visualViewport.resize`。浏览器缩放已反映在CSS视口中，不再做DPR补偿。
- **MUST**：字体加载完成、图片解码完成后再截图和做几何验收；主题或字体变化后重新检查折行与溢出。
- **NEVER**：HTML-PPT页内不得用`vw/vh/dvw/dvh`、`clamp()`、`auto-fit/auto-fill`或viewport媒体查询改变字号、列数、卡片宽高、间距、折行或内容位置。
- **NEVER**：媒体查询不得改变`.page-title`字号、Grid列数、gap、卡片高度或任何受众文字折行；`@media print`和`prefers-reduced-motion`可用，但不能改变观众页逻辑几何。
- **NEVER**：不得把固定页设为`width:100vw;height:100vh`，不得分别缩放X/Y，禁止CSS`zoom`、嵌套整页scale、按`devicePixelRatio`缩放DOM。
- **NEVER**：不得对scale四舍五入、向上/向下取整或“吸附到整数像素”。共线问题必须在1280×720逻辑空间解决，不能在缩放后逐元素补偿。
- **MUST**：最终验收以浏览器缩放100%为准；80%/125%仅作稳健性检查。不同OS的文字抗锯齿可以不同，但逻辑布局、折行与内容完整性必须一致。

### 14.3 最小等比缩放运行时

若配套`html-ppt/runtime.js`已实现同等逻辑，可复用；否则在DOM加载后运行：

```js
const DESIGN_WIDTH = 1280;
const DESIGN_HEIGHT = 720;
let fitRaf = 0;

function fitDeckToViewport() {
  fitRaf = 0;
  const viewportWidth = document.documentElement.clientWidth || window.innerWidth;
  const viewportHeight = document.documentElement.clientHeight || window.innerHeight;
  const scale = Math.min(
    viewportWidth / DESIGN_WIDTH,
    viewportHeight / DESIGN_HEIGHT
  );
  document.documentElement.style.setProperty('--deck-scale', String(scale));
}

function scheduleDeckFit() {
  if (!fitRaf) fitRaf = requestAnimationFrame(fitDeckToViewport);
}

fitDeckToViewport();
window.addEventListener('resize', scheduleDeckFit, { passive: true });
window.visualViewport?.addEventListener('resize', scheduleDeckFit, { passive: true });
document.fonts?.ready.then(scheduleDeckFit);
```

生成DOM后先初始化每一页页码，避免通用运行时只更新第一个`.slide-number`：

```js
const deckSlides = [...document.querySelectorAll('.deck > .slide')];
deckSlides.forEach((slide,index) => {
  const number = slide.querySelector('.slide-number');
  if (!number) return;
  number.dataset.current = String(index + 1);
  number.dataset.total = String(deckSlides.length);
});
```

运行时还应支持`#/N`、方向键、Home/End、页码和进度条。`#/N`是唯一规范深链格式；不得写成`#N`，也不得用只能解析`#N`的`parseInt(location.hash.replace('#',''))`。最小解析与写回逻辑固定如下，可扩展但不能改变格式：

```js
function indexFromHash(total) {
  const match = location.hash.match(/^#\/(\d+)$/);
  if (!match) return 0;
  return Math.max(0, Math.min(total - 1, Number(match[1]) - 1));
}
function writeSlideHash(index) {
  const next = `#/${index + 1}`;
  if (location.hash !== next) history.replaceState(null, '', next);
}
window.addEventListener('hashchange', () => showSlide(indexFromHash(deckSlides.length), false));
```

`showSlide(index,writeHash=true)`在键盘/点击翻页时调用`writeSlideHash(index)`，在处理`hashchange`时必须传`false`防止回写循环。每次翻页须更新当前页内部的`.slide-number`，并更新进度条填充宽度（内联`width`或`--progress`均可）；不得把所有页码寄托在`document.querySelector('.slide-number')`上。若同时有演讲者预览，预览iframe也必须加载同一份HTML和CSS；不得为预览另写一套页面。

### 14.4 最小HTML骨架

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="only light">
  <title>汇报标题</title>
  <link rel="stylesheet" href="assets/base.css">
  <link rel="stylesheet" href="kangzhe.css">
</head>
<body class="tpl-kangzhe">
  <div class="deck">
    <section class="slide cover-slide" data-title="汇报标题">
      <!-- 使用§14.5.1固定封面 -->
    </section>

    <section class="slide toc-slide" data-title="汇报章节">
      <!-- 使用§14.5.2固定目录页；最多4个一级章节 -->
    </section>

    <section class="slide section-slide" data-title="章节标题">
      <!-- 使用§14.5.3固定章节首页 -->
    </section>

    <section class="slide content-slide" data-archetype="content" data-title="本页标题" data-qc-id="content-slide">
      <div class="title-row" data-qc-id="content-title-row"><h1 class="page-title">本页标题</h1></div>
      <div class="brand-lockup" data-qc-id="content-logo"><img src="assets/logo_bot.svg" alt="CMS 康哲药业"></div>
      <main class="slide-body" data-qc-id="content-body"><!-- 本页内容 --></main>
      <div class="deck-footer" data-qc-id="content-footer">
        <span class="footer-id" data-qc-id="content-footer-id">产品中心-医学部｜2026年7月</span>
        <span class="slide-number" data-qc-id="content-page-number" data-current="4" data-total="5"></span>
      </div>
      <aside class="notes">讲者备注，不在观众页显示。</aside>
    </section>

    <section class="slide ending-slide" data-title="谢谢">
      <!-- 使用§14.5.4固定结束页 -->
    </section>
  </div>
  <div class="progress-bar" aria-hidden="true"><span></span></div>
  <script src="assets/runtime.js"></script>
</body>
</html>
```

正式交付时，`.deck > .slide`数量必须等于计划页数；暂停或备用页面放到`<template>`，不能只用`display:none`留在`.deck`下。`.deck`包裹层是硬契约：所有`.slide`MUST是`<div class="deck">`的直接子元素，NEVER直接挂在`<body>`下——§14.2的缩放CSS、§14.3的运行时和§16.A的几何闸门全部以`.deck`为唯一锚点；缺少`.deck`时缩放、翻页、页码、进度条会整体静默失效（`document.querySelectorAll(".deck > .slide")`返回空集），属于阻断型缺陷。

页面类是互斥契约：每页只能命中`cover-slide / toc-slide / section-slide / content-slide / ending-slide`之一。`info_table / gantt / single_result / comparison / evidence`是`content-slide`的`data-archetype`，不是第六种视觉母版；它们必须继续使用内容页chrome、Logo、正文框、页脚和页码。

### 14.5 固定非内容页母版

本节锁定封面、目录、章节首页与结束页。四类页面都不使用内容页黄橙斜切chrome、内容页页脚或页码；不得把`.content-slide`加到这些页面上。

正式资产只能替换固定QC外框内部内容，不能删除或替换带class与`data-qc-id`的外框节点。wordmark/full Logo外框内的`img`固定`width:100%;height:100%;object-fit:contain`；ribbon外框内的预裁图片固定`width:100%;height:100%;object-fit:cover`。内容页`.brand-lockup[data-qc-id="content-logo"]`同样保留外框，只把fallback文字换成内部`img`。

本规范的Logo不是可选正式资产：所有wordmark/full Logo/ribbon中心Logo都必须使用§1.2下载的`assets/logo_bot.svg`。下列母版代码中的文字只可作为无网络草稿的可访问fallback；正式HTML/PPT必须把外框内容替换为同一官网SVG的`img`/图片对象，并保持外框、class、`data-qc-id`和几何不变。单文件HTML进一步把本地SVG转为Data URL。

#### 14.5.1 固定正式封面

第一页默认使用当前医学AI专题汇报的正式居中结构：浅色背景、左上窄wordmark、居中主标题/部门/日期、黄色横线、底部品牌ribbon。封面无内容页chrome、无页码、无英文kicker。

```html
<section class="slide cover-slide" data-title="汇报标题" data-qc-id="cover-slide">
  <div class="cover-hero" aria-hidden="true"></div>
  <div class="cover-wordmark" data-qc-id="cover-wordmark"><img src="assets/logo_bot.svg" alt="CMS 康哲药业"></div>
  <div class="cover-main">
    <h1 data-qc-id="cover-title">汇报标题</h1>
    <p class="cover-department" data-qc-id="cover-department">产品中心-医学部</p>
    <p class="cover-date" data-qc-id="cover-date">YYYY年M月</p>
  </div>
  <div class="cover-rule" data-qc-id="cover-rule" aria-hidden="true"></div>
  <div class="cover-ribbon-fallback" data-qc-id="cover-ribbon" aria-label="CMS 康哲药业">
    <div class="ribbon-colorbar"><i></i><i></i><i></i></div>
    <div class="ribbon-lockup"><img src="assets/logo_bot.svg" alt="CMS 康哲药业"></div>
  </div>
  <aside class="notes">封面讲者提示。</aside>
</section>
```

```css
.tpl-kangzhe .slide.cover-slide { padding:0 !important; background:var(--kz-white); }
.cover-hero {
  position: absolute; inset: 0 0 auto; height: 565px;
  background-color: var(--kz-white);
  background-image: var(--cover-hero-image, none);
  background-position: center top;
  background-size: cover;
  background-repeat: no-repeat;
}
.cover-wordmark {
  position: absolute; left: 52px; top: 48px; z-index: 3;
  width: 240px; height: 50px; color: var(--kz-title-gray);
  font-size: 22px; line-height: 33px; font-weight: 700; white-space: nowrap;
}
.cover-main { position: absolute; inset: 0; text-align: center; z-index: 2; }
.cover-main h1 {
  position: absolute; top: 156px; left: 60px; right: 60px;
  margin: 0; color: var(--kz-body); font-size: 56px;
  line-height: 1.2; font-weight: 700;
}
.cover-department {
  position: absolute; top: 382px; left: 0; right: 0;
  margin: 0; color: var(--kz-title-gray); font-size: 32px;
  line-height: 1.25; font-weight: 700;
}
.cover-date {
  position: absolute; top: 468px; left: 0; right: 0;
  margin: 0; color: var(--kz-body); font-size: 22px; line-height: 1.2;
}
.cover-rule {
  position: absolute; left: 280px; right: 280px; top: 538px;
  height: 4px; background: var(--kz-yellow); z-index: 3;
}
.cover-ribbon-fallback {
  position: absolute; left: 0; bottom: 0; width: 1280px; height: 155px;
  background: var(--kz-white); text-align: center;
}
.ribbon-colorbar { display: grid; grid-template-columns: 1fr 1.55fr 3fr; height: 12px; }
.ribbon-colorbar i:nth-child(1) { background: var(--kz-yellow); }
.ribbon-colorbar i:nth-child(2) { background: var(--kz-orange-mid); }
.ribbon-colorbar i:nth-child(3) { background: var(--kz-orange); }
.ribbon-lockup {
  height: 143px; display: flex; align-items: center; justify-content: center;
  color: var(--kz-title-gray);
}
.ribbon-lockup > img { display:block; width:242px; height:50px; object-fit:contain; }
:is(.cover-wordmark,.toc-wordmark,.section-wordmark,.ending-wordmark) > img {
  display:block; width:100%; height:100%; object-fit:contain;
}
:is(.cover-ribbon-fallback,.ending-ribbon-fallback) > img {
  display:block; width:100%; height:100%; object-fit:cover;
}
```

wordmark和ribbon固定外框内部必须保留上述官网Logo`<img>`；hero 页 wordmark 外框为封面/结束 240×50、章节/目录 200×44，内容页 full logo 外框 158×33，ribbon 1280×155；不得整节点替换。wordmark/Logo固定`object-fit:contain`；只有用户另行提供的完整预裁ribbon整图才用`object-fit:cover`。主标题默认不附加年份范围，除非用户要求。

使用目录资产时，可在康哲样式表中注入封面背景：`:root{--cover-hero-image:url("assets/cover_hero.jpg")}`；单文件构建时将该URL转成Data URL。未提供正式资产则保持`none`，使用浅色fallback。

#### 14.5.2 固定目录页

目录页只承担一级章节导航，不使用页脚、页码、内容页chrome或英文kicker。默认使用四张有语义的2×2章节卡；不再使用空流程框作为fallback。固定最多4个一级章节；少于4个时按阅读顺序填充，不拉伸卡片。

```html
<section class="slide toc-slide" data-title="汇报章节" data-qc-id="toc-slide">
  <div class="toc-wordmark" data-qc-id="toc-wordmark"><img src="assets/logo_bot.svg" alt="CMS 康哲药业"></div>
  <h1 class="toc-title" data-qc-id="toc-title">汇报章节</h1>
  <div class="toc-rule" data-qc-id="toc-rule" aria-hidden="true"></div>
  <p class="toc-meta">实际汇报短标题 · 实际汇报日期</p>
  <nav class="toc-board" data-qc-id="toc-board" aria-label="汇报章节">
    <article class="toc-item"><span class="toc-index">01</span><div><span class="toc-label">章节标题一</span><small>真实章节范围短语</small></div></article>
    <article class="toc-item"><span class="toc-index">02</span><div><span class="toc-label">章节标题二</span><small>真实章节范围短语</small></div></article>
    <article class="toc-item"><span class="toc-index">03</span><div><span class="toc-label">章节标题三</span><small>真实章节范围短语</small></div></article>
    <article class="toc-item"><span class="toc-index">04</span><div><span class="toc-label">章节标题四</span><small>真实章节范围短语</small></div></article>
  </nav>
  <aside class="notes">目录页讲者提示。</aside>
</section>
```

```css
.tpl-kangzhe .slide.toc-slide { padding:0 !important; background:var(--kz-white); }
.toc-wordmark {
  position:absolute; right:52px; top:44px; width:200px; height:44px;
  color:var(--kz-title-gray); font-size:22px; line-height:33px;
  font-weight:700; white-space:nowrap; text-align:right; z-index:3;
}
.toc-title {
  position:absolute; left:68px; top:25px; margin:0;
  color:var(--kz-deep-text); font-size:48px; line-height:1.15; font-weight:700;
}
.toc-rule {
  position:absolute; left:68px; top:96px; width:582px; height:5px;
  background:var(--kz-yellow);
}
.toc-meta {
  position:absolute; left:68px; top:112px; margin:0;
  color:var(--kz-meta); font-size:20px; line-height:1.2; font-weight:400;
  white-space:nowrap;
}
.toc-board {
  position:absolute; left:68px; top:178px; width:1144px; height:392px;
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr));
  grid-template-rows:repeat(2,186px); gap:20px 24px; margin:0; padding:0;
}
.toc-item {
  position:relative; display:grid; grid-template-columns:92px minmax(0,1fr);
  align-items:center; min-width:0; min-height:0; padding:24px 28px;
  border:1px solid var(--kz-border-weak); border-top:4px solid var(--kz-orange);
  border-radius:8px; background:var(--kz-white);
  box-shadow:var(--shadow-1,var(--shadow));
  overflow:hidden;
}
.toc-item::after {
  content:""; position:absolute; inset:0;
  border-top:1px solid rgba(255,255,255,.9);
  pointer-events:none;
}
.toc-item:nth-child(3) { border-top-color:var(--kz-med-blue); }
.toc-item:nth-child(4) { border-top-color:var(--kz-stats-green); }
.toc-item > div { min-width:0; }
.toc-item small {
  display:block; margin-top:12px; color:var(--kz-meta);
  font-size:16px; line-height:1.2; font-weight:600; white-space:nowrap;
}
.toc-index {
  color:var(--kz-number); font-family:Arial,var(--font-sans);
  font-size:52px; line-height:1; font-weight:700; font-variant-numeric:tabular-nums;
}
.toc-label {
  display:block; min-width:0; color:var(--kz-deep-text); font-size:30px;
  line-height:1.2; font-weight:700; white-space:nowrap;
}
```

目录标题固定为“汇报章节”。`.toc-meta`必须替换为当前汇报的真实主标题或可识别短标题，加真实日期，例如“医学部全流程AI系统化构建专题汇报 · 2026年7月”；`汇报主题`、`报告标题`、`实际汇报短标题`、`实际汇报日期`、`YYYY年M月`都只是规范示意词，禁止残留在生产页面。章节编号固定两位数字`01–04`；条目标题最多12个全角中文字符，必须单行且满足8%水平余量。每个`.toc-item`必须有非空`.toc-index`与`.toc-label`，可选`small`也必须是真实章节范围，不得使用“待补充”“章节说明”等模板词。使用正式wordmark图片时只替换固定外框内部内容，外框、class与`data-qc-id`必须保留。

#### 14.5.3 固定章节首页

章节首页只放章节编号和章节标题。不得加入摘要、目标、英文副标题、页脚、页码、内容页chrome或“本章看点”卡片。

```html
<section class="slide section-slide" data-title="章节标题" data-qc-id="section-slide">
  <div class="section-wordmark" data-qc-id="section-wordmark"><img src="assets/logo_bot.svg" alt="CMS 康哲药业"></div>
  <div class="section-number" data-qc-id="section-number" aria-label="第1章">01</div>
  <div class="section-rule" data-qc-id="section-rule" aria-hidden="true"></div>
  <h1 class="section-title" data-qc-id="section-title">章节标题</h1>
  <aside class="notes">章节切换讲者提示。</aside>
</section>
```

`.section-slide[data-title]`必须与可见`.section-title.textContent.trim()`完全一致，只写章节标题，不得前置章节编号、追加副标题或拼接说明。

```css
.tpl-kangzhe .slide.section-slide { padding:0 !important; background:var(--kz-white); }
.section-wordmark {
  position:absolute; right:52px; top:44px; width:200px; height:44px;
  color:var(--kz-title-gray); font-size:22px; line-height:33px;
  font-weight:700; white-space:nowrap; text-align:right;
}
.section-number {
  position:absolute; left:108px; top:112px; width:260px; height:117px;
  color:var(--kz-number); font-family:Arial,var(--font-sans);
  font-size:117px; line-height:1; font-weight:700; font-variant-numeric:tabular-nums;
}
.section-rule {
  position:absolute; left:113px; top:261px; width:240px; height:5px;
  background:var(--kz-yellow);
}
.section-title {
  position:absolute; left:114px; right:100px; top:290px; margin:0;
  max-height:142px; color:var(--kz-deep-text); font-size:59px;
  line-height:1.2; font-weight:700;
}
```

章节编号固定两位数字；章节标题最多两行、最多32个全角中文字符。标题不得通过缩小字号、压缩字距或改变`top=290`来适配；超量时改写。使用正式wordmark图片时 hero 外框固定 200×44（章节页）。

#### 14.5.4 固定结束页

结束页固定复用封面的浅色上部视觉与底部ribbon，只显示“谢谢”、部门和日期。不得显示页脚、页码、内容页chrome、长致谢、联系方式或“请领导指导”等演讲提示。

```html
<section class="slide ending-slide" data-title="谢谢" data-qc-id="ending-slide">
  <div class="ending-hero" aria-hidden="true"></div>
  <div class="ending-wordmark" data-qc-id="ending-wordmark"><img src="assets/logo_bot.svg" alt="CMS 康哲药业"></div>
  <div class="ending-focus" data-qc-id="ending-focus"><h1 class="ending-thanks">谢谢</h1></div>
  <div class="ending-rule" data-qc-id="ending-rule" aria-hidden="true"></div>
  <p class="ending-meta" data-qc-id="ending-meta">产品中心-医学部 · YYYY年M月</p>
  <div class="ending-ribbon-fallback" data-qc-id="ending-ribbon" aria-label="CMS 康哲药业">
    <div class="ribbon-colorbar"><i></i><i></i><i></i></div>
    <div class="ribbon-lockup"><img src="assets/logo_bot.svg" alt="CMS 康哲药业"></div>
  </div>
  <aside class="notes">结束页讲者提示。</aside>
</section>
```

```css
.tpl-kangzhe .slide.ending-slide { padding:0 !important; background:var(--kz-white); }
.ending-hero {
  position:absolute; left:0; top:0; width:1280px; height:565px;
  background-color:var(--kz-white);
  background-image:var(--ending-hero-image,var(--cover-hero-image,none));
  background-position:center top; background-size:cover; background-repeat:no-repeat;
}
.ending-wordmark {
  position:absolute; left:52px; top:44px; width:240px; height:50px;
  color:var(--kz-title-gray); font-size:22px; line-height:33px;
  font-weight:700; white-space:nowrap; z-index:3;
}
.ending-focus {
  position:absolute; left:340px; top:220px; width:600px; height:200px;
  border:0; border-radius:0; background:transparent; box-shadow:none;
}
.ending-thanks {
  position:absolute; left:0; right:0; top:14px; margin:0;
  color:var(--kz-title-gray); font-size:68px; line-height:1.2;
  font-weight:700; text-align:center;
}
.ending-rule {
  position:absolute; left:380px; top:450px; width:520px; height:4px;
  background:var(--kz-yellow);
}
.ending-meta {
  position:absolute; left:0; right:0; top:495px; margin:0;
  color:var(--kz-body); font-size:18px; line-height:1.2;
  font-weight:400; text-align:center; white-space:nowrap;
}
.ending-ribbon-fallback {
  position:absolute; left:0; top:565px; width:1280px; height:155px;
  background:var(--kz-white); text-align:center;
}
```

正式结束页背景和wordmark若由图片替换，显示框与坐标仍按本节；wordmark固定`object-fit:contain`，已预裁的背景与ribbon固定`object-fit:cover`。底部ribbon必须与封面使用同一资产或同一fallback DOM，禁止另配一套颜色。`.ending-focus`只是定位容器，机器检查必须确认其`border-width:0`、`background-color:transparent`、`box-shadow:none`；不得改回玻璃拟态或半透明白卡。

### 14.6 内容页固定chrome与页脚

```css
.tpl-kangzhe .slide.content-slide {
  padding:96px 56px 60px !important;
  background:var(--kz-white);
}
.tpl-kangzhe .slide.content-slide::before {
  content: ""; position: absolute; left: 54px; right: 23px; top: 80px;
  height: 1.5px; background: var(--kz-orange); z-index: 2;
}
.title-row {
  position: absolute; top: 24px; left: 91px; right: 270px;
  min-height: 44px; display: flex; align-items: center; z-index: 3;
}
.title-row::before, .title-row::after {
  content: ""; position: absolute; z-index: -1;
  clip-path: polygon(44% 0,100% 0,57% 100%,0 100%);
}
.title-row::before {
  left: -67px; top: -15px; width: 70px; height: 62px;
  background: var(--kz-orange);
}
.title-row::after {
  left: -86px; top: 18px; width: 40px; height: 36px;
  background: var(--kz-yellow);
}
.page-title {
  margin: 0; color: var(--kz-deep-text); font-size: 32px;
  line-height: 1.2; font-weight: 700; letter-spacing: 0;
  min-width: 0; white-space: nowrap;
}
.page-title .accent { color: var(--kz-orange); }
.brand-lockup {
  position: absolute; top: 45px; right: 91px; width: 158px; height: 33px;
  display: flex; align-items: center; justify-content: flex-end;
  color: var(--kz-title-gray); font-family: Arial,var(--font-sans);
  font-size: 17px; line-height: 1; font-weight: 700;
  white-space: nowrap; z-index: 4;
}
.brand-lockup > img { display:block; width:100%; height:100%; object-fit:contain; }
.slide-body {
  position:relative; width:1168px; height:564px;
  min-width:0; min-height:0; margin:0; padding:0;
  color:var(--kz-body); font-size:19px; line-height:1.4; font-weight:400;
}
.slide-body p { margin:0 0 8px; }
.slide-body p:last-child { margin-bottom:0; }
.slide-body :is(ul,ol) { margin:0; padding-left:24px; }
.slide-body li + li { margin-top:8px; }
.slide-body :is(strong,b) { font-weight:600; }
.deck-footer {
  position: absolute; bottom: 14px; left: 24px; right: 32px;
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  color: var(--kz-meta); font-size: 18px; line-height: 1.2; z-index: 5;
}
.footer-id { color: var(--kz-meta); font-weight: 400; white-space: nowrap; }
.slide-number { color: var(--kz-orange); font-weight: 700; white-space: nowrap; }
.slide-number::before { content: attr(data-current); }
.slide-number::after { content: " / " attr(data-total); }
.progress-bar {
  position: fixed; left: 0; right: 0; bottom: 0; height: 3px;
  background: transparent; z-index: 100;
}
.progress-bar > span {
  display: block; width: var(--progress, 0%); height: 100%;
  background: var(--kz-orange);
}
.notes, aside.notes { display: none !important; }
```

- 正文逻辑区固定为`x=56, y=96, width=1168, height=564`，右边界`x=1224`、下边界`y=660`；页脚不占正文高度。所有受众内容必须放在`.slide-body`内，不能绕过正文框用整页绝对定位。
- 内容页构图从§4.3 预设或§14.7.3 G 已验证范式中选择，或自创满足§16.A `content_slide_richness` 闸门的填充式构图。自创构图 MUST 通过丰富度闸门（无死带、含 living visual、字号层级、非等白卡行）；NEVER 使用 `auto-fit/auto-fill`。若自创构图不通过闸门，回退到预设或已验证范式。
- 标准卡片内边距固定`14px 16px`，普通卡间距固定16 px；同组标题与正文间距8 px，独立区块间距24 px。不得为了“看起来松一点”自行增加无规则间距。
- `content/info_table/gantt/single_result/comparison/evidence`六类标准内容页都必须添加`content-slide`；封面、目录、章节、结束页不得添加，避免误出现顶部橙线。
- 内容页 **MUST** 自然使用页面下半部：在排除背景、`.notes`、页脚和透明装饰后，`.slide-body`内最后一个受众可见元素的逻辑`bottom`必须`>=560px`，并且全部内容仍不超过`y=660`。卡片、短表或对照矩阵内容不足时，优先拉开组件行高、把结论条锚定到底部或改用全高命名组件；不得把全部内容堆在`y<480`后留下非设计性大空白。只有封面、目录、章节首页和结束页可豁免本阈值。
- 稀疏内容页推荐固定两层：主构图占`.slide-body`的`0–440px`或更高，结论/人工边界条固定落在相对正文框`y=488–552px`、高`52–64px`；主构图和结论之间使用16或24px间距。不得通过增加无意义装饰、空文字或透明节点来“通过”纵向利用检查。
- 内容页顶部不显示英文标签或页型编号。
- 页面标题与右上Logo不得相撞；标题容器右边界固定为`x=1010`。超长标题保持32px并改写、缩短或拆页；在本规范尚未定义完整双行变体前不得换行，不得通过缩字或移动Logo解决。
- Logo缺失时使用文字lockup；不得留空或放无关图标。
- 上述`display:none!important`只隐藏观众页中的备注节点；标准`html-ppt`运行时通过DOM读取其`innerHTML`，再写入独立备注抽屉/讲者窗口，因此不会丢失备注。若第三方运行时直接在同一DOM显示备注，必须把隐藏规则限定为`body:not(.speaker-mode)`。
- 进度条是视口级固定元素，位于`.deck`之外；备注是页级数据节点，位于对应`.slide`之内。
- HTML-PPT内容页页码固定`N / TOTAL`；封面、目录、章节首页、结束页无页码。不得在主题层覆盖成只显示当前页。

### 14.7 卡片、流程图与甘特图的稳定实现

本节每个完整代码块都是固定组件的可执行源码。复制组件时必须保留下文原始 DOM 层级、class 名和 selector 名；不得用“视觉相似”的自定义实现替代。特别是总甘特的`.portfolio-group`与`.road-bar/.road-milestone/.road-pv`属于机器验收入口，不得改成`.gantt-group-*`、`.bar`或其他别名。

通用卡片：

```css
.kz-card {
  min-width: 0; min-height: 0; padding: 14px 16px;
  border: 1px solid var(--kz-border);
  border-radius: 8px; background: var(--kz-white);
  box-shadow: var(--shadow);
}
.kz-card h3 { margin:0 0 8px; font-size:24px; line-height:1.25; font-weight:700; }
.kz-card p, .kz-card li { font-size:19px; line-height:1.4; font-weight:400; }
/* 强调三件套（§10.2 强制） */
.kz-em-red { color: var(--kz-risk); font-weight: 700; }
.kz-em-underline { text-decoration: underline; text-underline-offset: 3px; text-decoration-thickness: 2px; }
/* 卡状表面集合：层次基线（§14.7.3 G，class 无关；阴影深度/hover 幅度在 token 范围内自由） */
.kz-card, .panel, .rail-item, .cov-row, .stat-strip__item, .dept-portfolio-card, [data-kz-depth="1"] { box-shadow: var(--shadow-1); border-top: 4px solid var(--card-accent, var(--kz-orange)); }
@media (hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference) {
  .kz-card, .panel, .rail-item, .cov-row, .stat-strip__item, .dept-portfolio-card, [data-kz-depth="1"] { transition: transform var(--motion-fast) var(--ease-out), box-shadow var(--motion-fast) var(--ease-out); }
  .kz-card:hover, .panel:hover, .rail-item:hover, .cov-row:hover, .stat-strip__item:hover, .dept-portfolio-card:hover, [data-kz-depth="1"]:hover { transform: translateY(-3px); box-shadow: var(--shadow-2); }
}
.kz-card p { margin:0 0 8px; }
.kz-card p:last-child { margin-bottom:0; }
.kz-card :is(ul,ol) { margin:0; padding-left:24px; }
.kz-card li + li { margin-top:8px; }
.kz-card.compact h3 { font-size:20px; line-height:1.25; font-weight:700; }
.kz-card.compact p, .kz-card.compact li { font-size:16px; line-height:1.2; font-weight:600; }
```

`.compact`只用于高密度总览、流程拓扑或甘特旁的短标签卡；普通内容卡使用24px标题和19px正文。若compact卡仍放不下，缩文案或拆页，不继续缩字。

流程图：

- 主流程放在页面纵向中部，优先使用Grid/Flex，不用大量绝对坐标拼接。
- 两排蛇形流程固定内容宽度`1080px`、卡宽`200px`。上排5卡有效间隙约20px；下排4卡为对齐两端节点，使用`space-between`后有效间隙约93.33px。CSS中的`gap:18px`只是最小间距，不是两排最终可见间距。
- 连接轴置于卡片后方，卡片`z-index:1`且背景`#FFFFFF`。
- 弱化节点只修改边框、编号和文字为灰色；NEVER给整卡设置opacity。
- 不同部门已经用颜色编码时，部门名称另做独立图例；管理结论另起一行，不与图例塞进同一大卡。

九环节蛇形流程使用以下固定DOM顺序；下排按`9→8→7→6`书写，才能从右侧转弯后沿视觉方向`6→7→8→9`：

```html
<div class="chain-route" aria-label="九环节临床研发流程">
  <div class="chain-row chain-upper">
    <div class="chain-node off"><div class="node-num">1</div><div class="node-label">环节名称</div></div>
    <div class="chain-node science"><div class="node-num">2</div><div class="node-label">环节名称</div><div class="node-tags"><span class="tag science">医学·职责</span></div></div>
    <div class="chain-node shared"><div class="node-num">3</div><div class="node-label">环节名称</div><div class="node-tags"><span class="tag science">医学·职责</span><span class="tag ops">运营·职责</span></div></div>
    <div class="chain-node ops"><div class="node-num">4</div><div class="node-label">环节名称</div><div class="node-tags"><span class="tag ops">运营·职责</span></div></div>
    <div class="chain-node stats"><div class="node-num">5</div><div class="node-label">环节名称</div><div class="node-tags"><span class="tag stats">数统·职责</span></div></div>
  </div>
  <div class="chain-turn" aria-hidden="true"></div>
  <div class="chain-row chain-lower">
    <div class="chain-node pv"><div class="node-num">9</div><div class="node-label">环节名称</div><div class="node-tags"><span class="tag pv">PV·职责</span></div></div>
    <div class="chain-node science"><div class="node-num">8</div><div class="node-label">环节名称</div><div class="node-tags"><span class="tag science">医学·职责</span></div></div>
    <div class="chain-node stats"><div class="node-num">7</div><div class="node-label">环节名称</div><div class="node-tags"><span class="tag stats">数统·职责</span></div></div>
    <div class="chain-node shared"><div class="node-num">6</div><div class="node-label">环节名称</div><div class="node-tags"><span class="tag science">医学·职责</span><span class="tag ops">运营·职责</span></div></div>
  </div>
</div>
<div class="department-legend" aria-label="部门颜色图例">
  <span class="legend-item science"><i></i>医学科学部</span>
  <span class="legend-item operations"><i></i>临床运营部</span>
  <span class="legend-item statistics"><i></i>生物统计和数据管理部</span>
  <span class="legend-item safety"><i></i>医学安全部（PV）</span>
</div>
<div class="blueprint-takeaway">一句管理结论，不重复列举部门</div>
```

```css
.chain-route {
  --chain-node-h:188px; --chain-axis-y:32px; --chain-turn-gap:38px;
  position:relative; width:1080px; margin:25px auto 0;
}
.chain-row {
  position:relative; display:grid; grid-auto-rows:var(--chain-node-h);
  gap:18px; z-index:1;
}
.chain-row::before {
  content:""; position:absolute; left:100px; right:100px; top:var(--chain-axis-y);
  height:4px; z-index:0; background:var(--kz-border);
}
.chain-upper { grid-template-columns:repeat(5,200px); justify-content:space-between; }
.chain-upper::before { background:linear-gradient(90deg,var(--kz-border),var(--kz-orange) 28%,var(--kz-med-blue) 72%,var(--kz-stats-green)); }
.chain-upper::after {
  content:""; position:absolute; right:93px; top:26px; z-index:0;
  border-left:12px solid var(--kz-stats-green);
  border-top:8px solid transparent; border-bottom:8px solid transparent;
}
.chain-lower { grid-template-columns:repeat(4,200px); justify-content:space-between; }
.chain-lower::before { background:linear-gradient(90deg,var(--kz-pv-brown),var(--kz-orange) 36%,var(--kz-stats-green) 68%,var(--kz-orange)); }
.chain-lower::after {
  content:""; position:absolute; left:93px; top:26px; z-index:0;
  border-right:12px solid var(--kz-pv-brown);
  border-top:8px solid transparent; border-bottom:8px solid transparent;
}
.chain-turn { position:relative; height:var(--chain-turn-gap); }
.chain-turn::before {
  content:""; position:absolute;
  top:calc(var(--chain-axis-y) - var(--chain-node-h)); right:100px;
  width:44px; height:calc(var(--chain-node-h) + var(--chain-turn-gap));
  border-top:4px solid var(--kz-stats-green);
  border-right:4px solid var(--kz-stats-green);
  border-bottom:4px solid var(--kz-orange);
  border-radius:0 20px 20px 0;
}
.chain-node {
  position:relative; z-index:1; min-width:0; height:var(--chain-node-h);
  padding:9px 10px 10px; border:1px solid var(--kz-border);
  border-top:4px solid var(--kz-orange); border-radius:8px;
  background:var(--kz-white); box-shadow:var(--shadow); opacity:1;
}
.chain-node.ops { border-top-color:var(--kz-med-blue); }
.chain-node.stats { border-top-color:var(--kz-stats-green); }
.chain-node.pv { border-top-color:var(--kz-pv-brown); }
.chain-node.shared { box-shadow:inset 0 -4px 0 var(--kz-med-blue),var(--shadow); }
.chain-node.off { border-color:var(--kz-border-weak); border-top-color:var(--kz-border); box-shadow:none; background:var(--kz-white); }
.node-num {
  width:42px; height:42px; margin:0 auto 8px; border:4px solid var(--kz-white);
  border-radius:50%; display:flex; align-items:center; justify-content:center;
  background:var(--kz-orange); color:var(--kz-white); font-size:19px;
  line-height:1; font-weight:700; box-shadow:0 2px 9px rgba(15,17,21,.12);
}
.chain-node.ops .node-num { background:var(--kz-med-blue); }
.chain-node.stats .node-num { background:var(--kz-stats-green); }
.chain-node.pv .node-num { background:var(--kz-pv-brown); }
.chain-node.off .node-num { background:var(--kz-border); }
.chain-node.shared .node-num { background:linear-gradient(135deg,var(--kz-orange) 0 50%,var(--kz-med-blue) 50% 100%); }
.node-label { min-height:45px; color:var(--kz-deep-text); font-size:18px; line-height:1.25; font-weight:700; text-align:center; }
.chain-node.off .node-label { color:var(--kz-meta); }
.node-tags { display:flex; flex-direction:column; gap:4px; margin-top:5px; }
.node-tags .tag { min-height:30px; padding:4px 6px; border:1px solid; border-radius:999px; background:var(--kz-white); font-size:16px; line-height:1.2; font-weight:600; text-align:center; white-space:nowrap; }
.tag.science { border-color:var(--kz-orange); background:var(--kz-table-soft); }
.tag.ops { border-color:var(--kz-med-blue); background:var(--kz-blue-soft); }
.tag.stats { border-color:var(--kz-stats-green); }
.tag.pv { border-color:var(--kz-pv-brown); background:var(--kz-surface-warm); }
.department-legend { width:980px; margin:14px auto 0; display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }
.legend-item { display:flex; align-items:center; justify-content:center; gap:8px; min-width:0; min-height:30px; color:var(--kz-body); font-size:16px; line-height:1.2; font-weight:700; text-align:center; }
.legend-item i { display:block; width:8px; height:24px; border-radius:4px; background:var(--kz-orange); }
.legend-item.operations i { background:var(--kz-med-blue); }
.legend-item.statistics i { background:var(--kz-stats-green); }
.legend-item.safety i { background:var(--kz-pv-brown); }
.blueprint-takeaway { width:790px; margin:12px auto 0; padding:9px 20px; border-top:2px solid var(--kz-yellow); border-bottom:1px solid var(--kz-border); font-size:21px; line-height:1.25; font-weight:700; text-align:center; }
```

流程卡容量：环节名最多两行；普通节点最多1个单行标签，共责节点最多2个单行标签；`.tag-two-line`在九环节组件内禁止使用；卡内不放说明段落。上排卡中心为组件内`x=100/320/540/760/980`，下排为`x=100/393.33/686.67/980`；两排轴线必须穿过编号圆中心。轴线在卡后，弱化卡背景仍为不透明白色。机器检查还应验证普通节点标签数≤1、共责节点≤2、卡片`scrollHeight<=clientHeight`，不得用`overflow:hidden`掩盖超量。

流程卡固定高188 px，Grid行高、轴线、转弯区统一引用`--chain-node-h / --chain-axis-y / --chain-turn-gap`。转弯顶部=`axisY-nodeH`，高度=`nodeH+turnGap`，右边界固定`x=980`；不得把卡片改回`min-height`让字体换行自动撑高。任何容量超限必须改文案或拆页，并由clipping gate阻断。

总甘特/多部门时间轴必须共享同一组列变量：

总甘特根节点固定为普通`div`，不得使用`table`、`ul`、`svg`或自定义元素。HTML解析器不允许`table`直接包含`div`；若写成`<table class="portfolio-gantt"><div ...>`，浏览器会把子节点移出表格，源码看似完整但整页会在真实渲染中纵向散开。固定骨架如下，省略号只表示按同一结构继续添加完整业务行，不是产物中可保留的占位符：

```html
<div class="portfolio-gantt" style="--period-count:10">
  <div class="portfolio-head"><div>部门</div><div>子系统/应用</div><!-- 10个时期单元 --></div>
  <div class="portfolio-group medical">
    <div class="portfolio-dept">医学科学部</div>
    <div class="portfolio-tracks">
      <div class="portfolio-track">
        <div class="track-label">子系统名称</div>
        <div class="track-time"><span class="road-bar medical" style="--start:1;--span:2">阶段</span></div>
      </div>
    </div>
  </div>
</div>
```

生产页面必须展开全部组、全部轨道和全部时期单元；不得保留代码注释中的省略说明。

```css
.portfolio-gantt {
  --dept-col: 142px;
  --label-col: 194px;
  --period-count: 10;
  width: 100%;
  border: 0;
  border-radius: 8px; overflow: hidden; background: var(--kz-white);
  box-shadow:inset 0 0 0 1px var(--kz-border);
}
.portfolio-head {
  display: grid;
  grid-template-columns:
    var(--dept-col) var(--label-col)
    repeat(var(--period-count), minmax(0, 1fr));
  min-height: 42px; background: var(--kz-surface-warm);
  border-bottom: 1px solid var(--kz-border);
}
.portfolio-head > div {
  display:flex; align-items:center; justify-content:center;
  min-width:0; border-left:1px solid var(--kz-border);
  color:var(--kz-body); font-size:16px; line-height:1.1; font-weight:700;
  font-variant-numeric:tabular-nums;
}
.portfolio-head > div:first-child { border-left:0; }
.portfolio-group {
  display: grid;
  grid-template-columns: var(--dept-col) minmax(0, 1fr);
  border-bottom:1px solid var(--kz-border);
}
.portfolio-group:last-child { border-bottom:0; }
.portfolio-dept {
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  min-width:0; padding:6px 8px; color:var(--kz-deep-text);
  font-size:16px; line-height:1.15; font-weight:700; text-align:center;
}
.portfolio-group.medical .portfolio-dept { border-left:7px solid var(--kz-orange); background:var(--kz-surface-warm); }
.portfolio-group.operations .portfolio-dept { border-left:7px solid var(--kz-med-blue); background:var(--kz-blue-soft); }
.portfolio-group.statistics .portfolio-dept { border-left:7px solid var(--kz-stats-green); background:var(--kz-white); }
.portfolio-group.safety .portfolio-dept { border-left:7px solid var(--kz-pv-brown); background:var(--kz-surface-warm); }
.portfolio-tracks { min-width:0; box-shadow:inset 1px 0 0 var(--kz-border); }
.portfolio-track {
  display: grid;
  grid-template-columns: var(--label-col) minmax(0, 1fr);
  min-height: 37px;
  border-bottom:1px solid var(--kz-border);
}
.portfolio-track:last-child { border-bottom:0; }
.track-label {
  display:flex; align-items:center; min-width:0; padding:3px 8px;
  color:var(--kz-body); font-size:16px; line-height:1.08; font-weight:700;
}
.track-time {
  display: grid;
  grid-template-columns: repeat(var(--period-count), minmax(0, 1fr));
  min-width: 0; position: relative; align-items: center;
  background-image: linear-gradient(90deg,var(--kz-border) 0 1px,transparent 1px);
  background-size: calc(100% / var(--period-count)) 100%;
}
.road-bar, .road-milestone, .road-pv {
  grid-column: var(--start) / span var(--span, 1);
  min-width: 0; min-height: 29px; margin: 3px 1px; padding: 2px 3px;
  overflow: hidden; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; line-height: 1.05; font-weight: 700;
  text-align: center; white-space: nowrap;
}
.road-bar.medical { background:var(--kz-orange); color:var(--kz-deep-text); }
.road-bar.medical.mid { background:var(--kz-gantt-phase3); color:var(--kz-deep-text); }
.road-bar.medical.light { background:var(--kz-table-soft); color:var(--kz-body); border:1px solid var(--kz-orange); }
.road-bar.is-one-period { padding-inline:0; letter-spacing:-.35px; }
.road-milestone { margin-left:10px; margin-right:10px; padding:0; color:transparent; font-size:0; }
.road-milestone.ops { background:var(--kz-med-blue); }
.road-milestone.stats { background:var(--kz-stats-green); }
.road-pv { border:1px solid var(--kz-pv-brown); }
.road-pv.trial { background:var(--kz-table-soft); color:var(--kz-body); }
.road-pv.verify { background:var(--kz-pv-brown); color:var(--kz-white); }
.road-pv.promote { background:var(--kz-white); color:var(--kz-body); border-style:dashed; }
```

稳定DOM层级必须是`portfolio-gantt > portfolio-head + portfolio-group*`；每个组内为`portfolio-dept + portfolio-tracks`，每条轨道为`track-label + track-time`。运营和数统若源计划只给阶段节点，只能使用**真正空DOM**的`.road-milestone`，例如`<span class="road-milestone ops" style="--start:2" aria-label="阶段节点"></span>`；节点内不得放文字、点号、`&nbsp;`、透明字符或隐藏标签，也不得擅自拆成“准备/可用/优化”。PV若源计划给“试点/验证/推广”，使用三种`.road-pv`状态原样呈现。

在总宽`1168px`、10期时，部门列`142px`、子系统列`194px`，时间区从组件内`x=336px`开始，每期`83.2px`。季度数变化时必须同时修改`--period-count`，表头、轨道和背景线都引用该变量；不得分别维护。

甘特稳定性强制规则：

- **MUST**：表头、每一行时间轴都使用`repeat(N,minmax(0,1fr))`；所有中间容器和条形使用`min-width:0`。
- **MUST**：部门列、子系统列、时间轴列宽只在父容器定义一次，子层引用同一CSS变量。
- **MUST**：表头和正文的竖线从同一侧绘制；不要表头用左边框、正文用右边框造成1 px视觉差。
- **MUST**：阶段条先满足`scrollWidth <= clientWidth`，再决定`nowrap`；文字放不下时缩短标签或扩大span，不缩到16 px以下。
- **MUST**：单期条仍须展示5个全角字符时，加`.is-one-period`、去除横向padding并固定`letter-spacing:-.35px`；仍不能满足`scrollWidth<=clientWidth`时，必须改写标签或扩大span，不得裁切。
- **MUST**：运营/数统空里程碑的`textContent.trim()`必须为空；可访问名称只写`aria-label`，不得用透明字或点号伪装为空。
- **NEVER**：不得使用裸`repeat(N,1fr)`承载不换行中文标签；min-content可能把某一行撑成不等宽列。
- **NEVER**：不得靠目测拖动条形位置；使用`--start`和`--span`表达时间。
- **SHOULD**：时间轴数字使用等宽数字；预测阶段用虚线或浅填充并标注“预计”。

#### 14.7.0 四部门应用组合卡片

当页面需要同时展示医学科学部、临床运营部、生物统计和数据管理部、医学安全部（PV）的应用组合时，固定使用本组件。不得临时写四列卡片后把内容堆在上半页，也不得用黑色、深灰或反白字的底部横条。

```html
<div class="department-portfolio-layout" data-qc-id="department-portfolio-layout">
  <div class="portfolio-summary">一句总体覆盖结论。</div>
  <div class="department-card-grid">
    <article class="dept-portfolio-card medical"><h3>医学科学部</h3><ul><li>应用一</li><li>应用二</li><li>应用三</li></ul></article>
    <article class="dept-portfolio-card operations"><h3>临床运营部</h3><ul><li>应用一</li><li>应用二</li><li>应用三</li></ul></article>
    <article class="dept-portfolio-card statistics"><h3>生物统计和数据管理部</h3><ul><li>应用一</li><li>应用二</li><li>应用三</li></ul></article>
    <article class="dept-portfolio-card safety"><h3>医学安全部（PV）</h3><ul><li>应用一</li><li>应用二</li><li>应用三</li><li>应用四</li></ul></article>
  </div>
  <div class="content-conclusion">AI辅助边界与部门责任人的最终责任。</div>
</div>
```

```css
.department-portfolio-layout {
  width:1168px; height:564px; display:grid;
  grid-template-rows:48px 420px 64px; row-gap:16px;
  min-width:0; min-height:0;
}
.portfolio-summary, .content-conclusion {
  display:flex; align-items:center; min-width:0; min-height:0;
  padding:10px 20px; border-left:5px solid var(--kz-orange);
  border-radius:8px; background:var(--kz-surface-warm);
  color:var(--kz-body); font-size:19px; line-height:1.3; font-weight:700;
}
.department-card-grid {
  display:grid; grid-template-columns:repeat(4,minmax(0,1fr));
  gap:16px; min-width:0; min-height:0;
}
.dept-portfolio-card {
  min-width:0; min-height:0; padding:18px 18px;
  border:1px solid var(--kz-border); border-top:5px solid var(--kz-orange);
  border-radius:8px; box-shadow:var(--shadow); overflow:hidden;
  color:var(--kz-body); background:var(--kz-surface-warm);
}
.dept-portfolio-card h3 { margin:0 0 14px; font-size:22px; line-height:1.2; font-weight:700; }
.dept-portfolio-card ul { margin:0; padding-left:24px; font-size:19px; line-height:1.35; font-weight:600; }
.dept-portfolio-card li + li { margin-top:10px; }
.dept-portfolio-card.operations { border-top-color:var(--kz-med-blue); background:var(--kz-blue-soft); }
.dept-portfolio-card.statistics { border-top-color:var(--kz-stats-green); background:var(--kz-stats-soft); }
.dept-portfolio-card.safety { border-top-color:var(--kz-pv-brown); background:var(--kz-surface-warm); }
```

机器检查固定组件逻辑矩形`[56,96,1168,564]`、四张卡片、四列等宽、卡片区高420 px、底部结论条底边`y=660`。所有普通内容页结论条均沿用`.content-conclusion`的暖米色底与橙色左边线；只有规范明确命名的风险/警示变体可用红色，不得临时发明黑底横条。

#### 14.7.1 三列责任对照矩阵

当页面关系是“三种处理方式 × 三个同名场景”时，必须使用本组件，不得退化为九张无序卡片。三列标题和每一行场景保持同列、同行映射；整页固定使用到正文下部。

```html
<div class="responsibility-layout" data-qc-id="responsibility-layout">
  <div class="responsibility-matrix" data-qc-id="responsibility-matrix">
    <div class="rc-head traditional">传统工作</div>
    <div class="rc-head assisted">AI辅助后</div>
    <div class="rc-head human">人工确认</div>
    <div class="rc-cell traditional"><b>场景一</b><span>传统动作</span></div>
    <div class="rc-cell assisted"><b>场景一</b><span>AI辅助动作</span></div>
    <div class="rc-cell human"><b>场景一</b><span>人工确认事项</span></div>
    <div class="rc-cell traditional"><b>场景二</b><span>传统动作</span></div>
    <div class="rc-cell assisted"><b>场景二</b><span>AI辅助动作</span></div>
    <div class="rc-cell human"><b>场景二</b><span>人工确认事项</span></div>
    <div class="rc-cell traditional"><b>场景三</b><span>传统动作</span></div>
    <div class="rc-cell assisted"><b>场景三</b><span>AI辅助动作</span></div>
    <div class="rc-cell human"><b>场景三</b><span>人工确认事项</span></div>
  </div>
  <div class="content-conclusion" data-qc-id="responsibility-conclusion">一句审慎结论或人工边界。</div>
</div>
```

```css
.responsibility-layout {
  width:1168px; height:564px; display:grid;
  grid-template-rows:432px 64px; row-gap:24px; min-width:0; min-height:0;
}
.responsibility-matrix {
  display:grid; grid-template-columns:repeat(3,minmax(0,1fr));
  grid-template-rows:60px repeat(3,112px); gap:12px; min-width:0; min-height:0;
}
.rc-head, .rc-cell {
  min-width:0; min-height:0; border:1px solid var(--kz-border);
  border-radius:8px; padding:14px 16px; overflow:hidden;
}
.rc-head {
  display:flex; align-items:center; justify-content:center;
  font-size:20px; line-height:1.2; font-weight:700; text-align:center;
}
.rc-cell {
  display:flex; flex-direction:column; justify-content:center; gap:8px;
  font-size:19px; line-height:1.25; font-weight:400; background:var(--kz-white);
}
.rc-cell b { font-size:20px; line-height:1.2; font-weight:700; }
.rc-head.traditional { background:var(--kz-theme-warm-bg); }
.rc-head.assisted { background:var(--kz-table-soft); border-color:var(--kz-orange); }
.rc-head.human { background:var(--kz-blue-soft); border-color:var(--kz-med-blue); }
.rc-cell.traditional { border-left:5px solid var(--kz-border); }
.rc-cell.assisted { border-left:5px solid var(--kz-orange); }
.rc-cell.human { border-left:5px solid var(--kz-med-blue); }
```

每一行的三个`.rc-cell`必须重复同一个场景名，保证听众不依赖位置猜测映射。固定为3列×3场景；不足3个场景时改用普通双栏/三栏，超过3个场景时拆页。机器检查固定`.rc-head==3`、`.rc-cell==9`、矩阵逻辑矩形`[56,96,1168,432]`、结论底边`y=616`。

#### 14.7.2 三栏资料证据链

当页面关系是“资料片段 → 公司知识资产 → 泛项目能力”时，必须使用专属`.evidence-layout`，不得复用通用`.grid/.g3`或使用向下箭头把横向因果链改成纵向堆叠。固定为三栏加两条连接带，所有内容在`564px`正文高度内完成。

```html
<div class="evidence-layout" data-qc-id="evidence-layout">
  <div class="evidence-heads">
    <b>资料片段</b><i></i><b>公司知识资产</b><i></i><b>可迁移能力</b>
  </div>
  <div class="evidence-chain" data-qc-id="evidence-chain">
    <article class="evidence-source">
      <h3>脱敏资料片段</h3>
      <div class="source-snippet c1"><b>结构</b><span>资料原文节选</span></div>
      <div class="source-snippet c2"><b>术语</b><span>资料原文节选</span></div>
      <div class="source-snippet c3"><b>规则</b><span>资料原文节选</span></div>
    </article>
    <div class="evidence-connector" aria-hidden="true"><i class="c1"></i><i class="c2"></i><i class="c3"></i></div>
    <div class="evidence-assets">
      <article class="evidence-item c1"><b>结构模板</b><span>公司确认内容</span></article>
      <article class="evidence-item c2"><b>术语表</b><span>公司确认内容</span></article>
      <article class="evidence-item c3"><b>规则与来源链</b><span>公司确认内容</span></article>
      <article class="evidence-item neutral"><b>审阅问题库</b><span>公司确认内容</span></article>
    </div>
    <div class="evidence-connector" aria-hidden="true"><i class="c1"></i><i class="c2"></i><i class="c3"></i></div>
    <div class="evidence-capabilities">
      <article class="evidence-item c1"><b>结构复用</b><span>泛项目能力</span></article>
      <article class="evidence-item c2"><b>来源定位</b><span>泛项目能力</span></article>
      <article class="evidence-item c3"><b>一致性提示</b><span>泛项目能力</span></article>
    </div>
  </div>
  <div class="content-conclusion">模板和规则可复用；事实、医学解释和正式文本仍按项目确认。</div>
</div>
```

```css
.evidence-layout {
  width:1168px; height:564px; display:grid;
  grid-template-rows:40px 440px 52px; row-gap:16px;
  min-width:0; min-height:0; overflow:hidden;
}
.evidence-heads, .evidence-chain {
  display:grid; grid-template-columns:360px 48px 360px 48px 352px;
  min-width:0; min-height:0;
}
.evidence-heads b {
  display:flex; align-items:center; justify-content:center;
  font-size:20px; line-height:1.2; font-weight:700; text-align:center;
}
.evidence-chain > * { min-width:0; min-height:0; }
.evidence-source {
  height:440px; padding:14px 16px; overflow:hidden;
  border:1px solid var(--kz-border); border-radius:8px; background:var(--kz-white);
  display:grid; grid-template-rows:40px repeat(3,minmax(0,1fr)); gap:10px;
}
.evidence-source h3 { margin:0; font-size:20px; line-height:1.2; font-weight:700; }
.source-snippet, .evidence-item {
  min-width:0; min-height:0; padding:10px 12px; overflow:hidden;
  border:1px solid var(--kz-border-weak); border-left:5px solid var(--kz-orange);
  border-radius:8px; background:var(--kz-white);
  display:flex; flex-direction:column; justify-content:center; gap:6px;
  font-size:16px; line-height:1.2; font-weight:600;
}
.source-snippet b, .evidence-item b { font-size:18px; line-height:1.2; font-weight:700; }
.source-snippet.c2, .evidence-item.c2 { border-left-color:var(--kz-med-blue); }
.source-snippet.c3, .evidence-item.c3 { border-left-color:var(--kz-stats-green); }
.evidence-item.neutral { border-left-color:var(--kz-border); background:var(--kz-theme-warm-bg); }
.evidence-assets { display:grid; grid-template-rows:repeat(4,98px); gap:16px; overflow:hidden; }
.evidence-capabilities { display:grid; grid-template-rows:repeat(3,136px); gap:16px; overflow:hidden; }
.evidence-connector { display:grid; grid-template-rows:repeat(3,minmax(0,1fr)); gap:16px; overflow:hidden; }
.evidence-connector i { position:relative; align-self:center; height:4px; background:var(--kz-orange); }
.evidence-connector i::after {
  content:""; position:absolute; right:0; top:-6px;
  border-left:10px solid var(--kz-orange); border-top:8px solid transparent; border-bottom:8px solid transparent;
}
.evidence-connector i.c2 { background:var(--kz-med-blue); }
.evidence-connector i.c2::after { border-left-color:var(--kz-med-blue); }
.evidence-connector i.c3 { background:var(--kz-stats-green); }
.evidence-connector i.c3::after { border-left-color:var(--kz-stats-green); }
```

`.evidence-heads`和`.evidence-chain`必须使用完全相同的五列模板；左/中/右三栏分别为360/360/352px，两条连接带各48px。连接带只使用水平箭头，三组颜色必须在资料、资产、能力间保持一致。任何子列`scrollHeight>clientHeight`、页面`scrollHeight>720`、连接箭头向下或通用`.grid`覆盖本组件，都直接失败。

#### 14.7.3 视觉层次、微交互与导出冻结

本节用于解决页面过度扁平，同时保证PPT、HTML-PPT、流式HTML报告与站点式HTML共享同一静态视觉基线。交互只能增强识别与层次，不能承载唯一信息，不能改变逻辑几何，也不能掩盖文字容量问题。以下动效组件库归纳自内部成熟交互实现（粒子网络、数字滚动、轨道环、扫光、呼吸灯等均已做医学场景降档），Agent MUST 按五轨边界取用，不得整库照搬到幻灯片内容页。

##### A. 四轨适用边界

| 技术 | PPT/PPTX | HTML-PPT | 流式HTML报告 | 站点式HTML（§14.12） |
| --- | --- | --- | --- | --- |
| 双层轻阴影、顶部高光、细边框 | MUST用于需要分层的卡片 | MUST用于需要分层的卡片 | SHOULD | MUST |
| 页面淡入、卡片一次性揭示 | 转为静态终态 | MAY，180–240ms | MAY，须`html.js`门控 | MAY，首屏stagger≤8项 |
| hover抬升/阴影增强/边框变色 | 不适用，保留静态态 | MAY，仅精细指针，抬升≤3px | SHOULD用于可交互卡片 | SHOULD用于全部可交互元素，抬升≤4px |
| 数字滚动（count-up） | 不适用 | MAY，一次性≤900ms，静态终态即真值 | MAY | MAY |
| SVG描边流动/描边生长（dash-flow/draw-on） | 转为静态终态 | MAY，仅装饰流程线 | MAY | MAY |
| 状态呼吸灯（lamp） | 转为静态终态 | MAY，仅状态图例 | MAY | MAY |
| 环境光斑（radial-gradient静态或低速漂移） | 不适用 | MAY，仅封面且低对比 | MAY，仅首屏 | MAY，首屏与章节分隔 |
| 粒子网络（canvas） | NEVER | MAY，仅封面且用本节C可选脚本 | NEVER | MAY，仅首屏hero |
| 轨道环/环绕图（慢速旋转） | 转为静态终态 | MAY，单页≤1处装饰 | MAY | MAY |
| 轻微3D倾斜 | NEVER | MAY，仅封面/目录的非证据装饰，最大1deg | MAY，最大2deg | MAY，最大2deg，仅非证据卡片 |
| 滚动驱动揭示 | 不适用 | NEVER，幻灯片不是滚动文档 | MAY，必须渐进增强 | MAY，必须渐进增强 |
| 逐卡循环漂浮、玻璃拟态、霓虹发光、视差背景、整页粒子 | NEVER | NEVER | NEVER | NEVER（站点仅§14.12.6列明的hero例外） |

##### B. 深度Token与静态基线

```css
:root {
  --shadow-1: 0 1px 2px rgba(15,17,21,.06), 0 6px 18px rgba(15,17,21,.08);
  --shadow-2: 0 2px 4px rgba(15,17,21,.08), 0 14px 30px rgba(15,17,21,.12);
  --shadow-3: 0 4px 8px rgba(15,17,21,.08), 0 22px 44px rgba(15,17,21,.14);
  --shadow-focus: 0 0 0 3px rgba(255,153,0,.16), 0 12px 28px rgba(15,17,21,.11);
  --shadow-brand: 0 6px 18px rgba(255,153,0,.18), 0 2px 6px rgba(255,179,77,.12);
  --ease-out: cubic-bezier(.22,1,.36,1);
  --ease-spring: cubic-bezier(.2,.9,.25,1.15);
  --motion-fast: 180ms;
  --motion-base: 220ms;
  --motion-slow: 320ms;
  --motion-enter: 420ms;
}
.kz-card,
.toc-item,
[data-kz-depth="1"] {
  position:relative;
  border:1px solid var(--kz-border-weak);
  box-shadow:var(--shadow-1);
  background:var(--kz-white);
}
.kz-card::after,
.toc-item::after,
[data-kz-depth="1"]::after {
  content:""; position:absolute; inset:0; pointer-events:none;
  border-top:1px solid rgba(255,255,255,.9);
  border-radius:inherit;
}
```

- 阴影必须是中性灰黑低透明度；HTML-PPT内容页NEVER使用橙色发光阴影。`--shadow-brand`仅允许站点式HTML的hero主按钮与首屏强调卡使用。
- 卡片静态边界必须在无hover截图中清楚可见，但不能像表单输入框一样处处描边。
- 同页最多一个元素使用`--shadow-2`、`--shadow-3`或`--shadow-focus`；普通卡统一`--shadow-1`。
- 图表、表格和证据截图不做3D倾斜；任何影响数值读取或截图证据几何的transform均禁止。

##### C. HTML-PPT交互增强

```css
.tpl-kangzhe .slide { overflow:hidden; }
.slide.is-active {
  animation:kz-slide-in var(--motion-base) var(--ease-out) both;
}
@keyframes kz-slide-in {
  from { opacity:0; }
  to { opacity:1; }
}
/* 内容页进入时的一次性扫光：低对比品牌橙光带，不承载信息 */
.slide.content-slide.is-active::after {
  content:""; position:absolute; inset:0; z-index:0; pointer-events:none;
  background:linear-gradient(105deg, transparent 42%, rgba(255,153,0,.05) 50%, transparent 58%);
  animation:kz-sweep 1.1s var(--ease-out) 1 both;
}
@keyframes kz-sweep {
  from { transform:translateX(-101%); }
  to { transform:translateX(101%); }
}
/* 成组揭示：目录板、三卡grid等容器整体进入后逐项淡入，最多8项 */
@media (prefers-reduced-motion:no-preference) {
  .slide.is-active .kz-stagger > * {
    animation:kz-item-in var(--motion-enter) var(--ease-out) backwards;
  }
  .slide.is-active .kz-stagger > :nth-child(1) { animation-delay:.05s; }
  .slide.is-active .kz-stagger > :nth-child(2) { animation-delay:.12s; }
  .slide.is-active .kz-stagger > :nth-child(3) { animation-delay:.19s; }
  .slide.is-active .kz-stagger > :nth-child(4) { animation-delay:.26s; }
  .slide.is-active .kz-stagger > :nth-child(5) { animation-delay:.33s; }
  .slide.is-active .kz-stagger > :nth-child(6) { animation-delay:.40s; }
  .slide.is-active .kz-stagger > :nth-child(7) { animation-delay:.47s; }
  .slide.is-active .kz-stagger > :nth-child(8) { animation-delay:.54s; }
}
@keyframes kz-item-in {
  from { opacity:0; transform:translateY(10px); }
  to { opacity:1; transform:none; }
}
@media (hover:hover) and (pointer:fine) and (prefers-reduced-motion:no-preference) {
  .tpl-kangzhe .toc-item,
  .tpl-kangzhe .kz-card[data-interactive="true"] {
    transition:
      transform var(--motion-fast) var(--ease-out),
      box-shadow var(--motion-fast) var(--ease-out),
      border-color var(--motion-fast) ease;
    will-change:transform;
  }
  .tpl-kangzhe .toc-item:hover,
  .tpl-kangzhe .kz-card[data-interactive="true"]:hover {
    transform:translateY(-3px);
    box-shadow:var(--shadow-2);
    border-color:rgba(255,153,0,.55);
  }
  .tpl-kangzhe .toc-item:active,
  .tpl-kangzhe .kz-card[data-interactive="true"]:active {
    transform:translateY(-1px) scale(.995);
  }
}
.tpl-kangzhe .toc-item:focus-visible,
.tpl-kangzhe .kz-card[data-interactive="true"]:focus-visible {
  outline:none;
  box-shadow:var(--shadow-focus);
  border-color:rgba(255,153,0,.7);
}
/* 数字滚动：静态DOM先写真值，JS进入活动页时从0滚回真值 */
[data-countup] { font-variant-numeric:tabular-nums; }
/* SVG描边流动与描边生长 */
.kz-dash { stroke-dasharray:6 5; animation:kz-dash-flow 1.6s linear infinite; }
@keyframes kz-dash-flow { to { stroke-dashoffset:-22; } }
.kz-drawon path, .kz-drawon circle, .kz-drawon polyline, .kz-drawon line {
  stroke-dasharray:var(--kz-draw-len,220);
  stroke-dashoffset:var(--kz-draw-len,220);
  transition:stroke-dashoffset 1s cubic-bezier(.4,0,.2,1) .2s;
}
.slide.is-active .kz-drawon path, .slide.is-active .kz-drawon circle,
.slide.is-active .kz-drawon polyline, .slide.is-active .kz-drawon line {
  stroke-dashoffset:0;
}
/* 状态呼吸灯：仅状态图例，颜色跟随currentcolor */
.kz-lamp { display:inline-flex; align-items:center; gap:8px; }
.kz-lamp::before {
  content:""; width:10px; height:10px; border-radius:50%;
  background:currentColor; box-shadow:0 0 8px currentColor;
}
.kz-lamp.is-live::before { animation:kz-lamp-pulse 2.2s ease-in-out infinite; }
@keyframes kz-lamp-pulse {
  0%,100% { box-shadow:0 0 0 0 currentColor; opacity:1; }
  50% { box-shadow:0 0 0 6px transparent; opacity:.85; }
}
/* 轨道环/环绕图：单页≤1处，仅装饰，部门色经--c注入 */
@media (prefers-reduced-motion:no-preference) {
  .kz-orbit { position:relative; width:300px; height:300px; margin:auto; }
  .kz-orbit__ring {
    position:absolute; inset:0; border-radius:50%;
    border:2px dashed rgba(255,153,0,.45);
    animation:kz-spin 26s linear infinite;
  }
  .kz-orbit__ring--2 { inset:34px; border-color:rgba(64,122,170,.40); animation-duration:34s; animation-direction:reverse; }
  .kz-orbit__hub {
    position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
    width:92px; height:92px; border-radius:50%;
    background:var(--kz-white); border:2px solid var(--kz-orange);
    display:flex; align-items:center; justify-content:center;
    font-size:19px; font-weight:700; color:var(--kz-orange);
    box-shadow:0 0 0 8px rgba(255,153,0,.10), var(--shadow-2);
    animation:kz-hub-pulse 3.4s ease-in-out infinite;
  }
  .kz-orbit__node {
    position:absolute; left:50%; top:50%; width:56px; height:56px; margin:-28px;
    border-radius:50%; background:var(--c,var(--kz-orange)); color:var(--kz-white);
    display:flex; align-items:center; justify-content:center;
    font-size:13px; font-weight:700;
    box-shadow:0 6px 16px rgba(15,17,21,.18);
    transform:rotate(var(--a,0deg)) translate(122px) rotate(calc(var(--a,0deg) * -1));
    animation:kz-orbit-node 18s linear infinite;
  }
}
@keyframes kz-spin { to { transform:rotate(360deg); } }
@keyframes kz-hub-pulse {
  0%,100% { box-shadow:0 0 0 8px rgba(255,153,0,.10), var(--shadow-2); }
  50% { box-shadow:0 0 0 16px rgba(255,153,0,.05), var(--shadow-2); }
}
@keyframes kz-orbit-node {
  from { transform:rotate(var(--a,0deg)) translate(122px) rotate(calc(var(--a,0deg) * -1)); }
  to { transform:rotate(calc(var(--a,0deg) + 360deg)) translate(122px) rotate(calc((var(--a,0deg) + 360deg) * -1)); }
}
- **冻结态 CSS 完整性**：`html[data-export="true"] *` 与 `html[data-qc="true"] *` 的 `animation:none !important; transition:none !important; transform:none !important;` MUST 使用通配 `*` 且带 `!important`；NEVER 只写 `.slide *` 或更窄选择器（会漏掉 `.deck` 直属子元素、`.progress-bar`、封面粒子 canvas 等）。伪元素（`::before`/`::after`）MUST 单独覆盖：`html[data-export="true"] .slide.content-slide.is-active::after { animation:none !important; opacity:0 !important; }` 等。冻结态实测 MUST 在 `data-export=true` 后等两帧，遍历 `.deck *`（非 `.slide *`）确认 `animationName=='none'` 且 `transitionDuration` 全为 `0s`；任何非零即为冻结不完整。
@media (prefers-reduced-motion:reduce) {
  .slide.is-active, .toc-item, .kz-card, .kz-stagger > *,
  .kz-dash, .kz-lamp.is-live::before, .kz-orbit__ring, .kz-orbit__hub, .kz-orbit__node,
  .kz-particles, .kz-ambient, .kz-item-in,
  .kz-reveal, .kz-reveal-stagger, .kz-reveal-stagger > * {
    animation:none !important; transition:none !important;
  }
  .slide.is-active, .toc-item, .kz-card, .kz-stagger > *, .kz-item-in,
  .kz-reveal, .kz-reveal-stagger > * {
    transform:none !important; opacity:1 !important;
  }
  .slide.content-slide.is-active::after { animation:none !important; opacity:0 !important; }
  .kz-particles { display:none !important; }
  .kz-drawon path, .kz-drawon circle, .kz-drawon polyline, .kz-drawon line { stroke-dashoffset:0 !important; }
}
html[data-export="true"] *,
html[data-qc="true"] * {
  animation:none !important;
  transition:none !important;
  transform:none !important;
}
html[data-export="true"] .kz-particles,
html[data-qc="true"] .kz-particles { display:none !important; }
html[data-export="true"] .kz-drawon path, html[data-export="true"] .kz-drawon circle,
html[data-qc="true"] .kz-drawon path, html[data-qc="true"] .kz-drawon circle {
  stroke-dashoffset:0 !important;
}
```

- 本节所有交互选择器MUST带`.tpl-kangzhe`前缀（如`.tpl-kangzhe .toc-item:hover`），不得写成裸`.toc-item:hover`：§14.2/§14.5的母版规则带`.tpl-kangzhe`前缀（特异性0,2,0以上），裸选择器（0,1,1）会被母版的`box-shadow`/`border`声明压过，造成“`:hover`命中但抬升/变色不生效”。

可选JS（模块化交付放入`assets/kz-fx.js`，单文件交付内联；两段均为自执行IIFE，无外部依赖）：

```js
/* 数字滚动：仅no-preference环境；进入活动页时触发，终值必须等于DOM真值 */
(function () {
  if (!window.matchMedia("(prefers-reduced-motion: no-preference)").matches) return;
  var DUR = 900;
  function run(el) {
    var target = parseFloat(el.getAttribute("data-countup"));
    var decimals = parseInt(el.getAttribute("data-decimals") || "0", 10);
    var suffix = el.getAttribute("data-suffix") || "";
    if (!isFinite(target)) return;
    var t0 = null;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min(1, (ts - t0) / DUR);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = (target * eased).toFixed(decimals) + suffix;
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target.toFixed(decimals) + suffix;
    }
    requestAnimationFrame(step);
  }
  function scan(root) {
    if (!root) return;
    root.querySelectorAll("[data-countup]").forEach(function (el) {
      if (el.dataset.kzCounted) return;
      el.dataset.kzCounted = "1";
      run(el);
    });
  }
  function active() { return document.querySelector(".slide.is-active"); }
  document.addEventListener("DOMContentLoaded", function () { scan(active()); });
  window.addEventListener("load", function () { scan(active()); });
  window.addEventListener("hashchange", function () { setTimeout(function () { scan(active()); }, 60); });
})();

/* 封面环境粒子：仅cover-slide、仅no-preference；离屏/隐藏/冻结态自动停帧并清空 */
(function () {
  var root = document.documentElement;
  if (!window.matchMedia("(prefers-reduced-motion: no-preference)").matches) return;
  function frozen() { return root.dataset.export === "true" || root.dataset.qc === "true"; }
  document.addEventListener("DOMContentLoaded", function () {
    var cover = document.querySelector(".slide.cover-slide");
    if (!cover) return;
    var canvas = document.createElement("canvas");
    canvas.className = "kz-particles";
    canvas.setAttribute("aria-hidden", "true");
    cover.insertBefore(canvas, cover.firstChild);
    var ctx = canvas.getContext("2d");
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var W = 0, H = 0, nodes = [], raf = null;
    function resize() {
      W = cover.clientWidth; H = cover.clientHeight;
      canvas.width = W * dpr; canvas.height = H * dpr;
      canvas.style.width = W + "px"; canvas.style.height = H + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function seed() {
      nodes = [];
      for (var i = 0; i < 40; i++) nodes.push({
        x: Math.random() * W, y: Math.random() * H,
        vx: (Math.random() - .5) * .18, vy: (Math.random() - .5) * .18,
        r: 1 + Math.random() * 1.6
      });
    }
    function draw() {
      ctx.clearRect(0, 0, W, H);
      var i, j, a, b, d;
      for (i = 0; i < nodes.length; i++) {
        a = nodes[i];
        a.x += a.vx; a.y += a.vy;
        if (a.x < 0 || a.x > W) a.vx *= -1;
        if (a.y < 0 || a.y > H) a.vy *= -1;
        ctx.fillStyle = "rgba(255,153,0,.30)";
        ctx.beginPath(); ctx.arc(a.x, a.y, a.r, 0, 6.2832); ctx.fill();
        for (j = i + 1; j < nodes.length; j++) {
          b = nodes[j];
          d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < 110) {
            ctx.strokeStyle = "rgba(255,153,0," + ((1 - d / 110) * .14).toFixed(3) + ")";
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
      }
    }
    function loop() { draw(); raf = requestAnimationFrame(loop); }
    function live() {
      return cover.classList.contains("is-active") && !frozen() && !document.hidden;
    }
    function sync() {
      if (live() && raf === null) loop();
      else if (!live() && raf !== null) {
        cancelAnimationFrame(raf); raf = null; ctx.clearRect(0, 0, W, H);
      }
    }
    resize(); seed();
    new ResizeObserver(function () { resize(); seed(); }).observe(cover);
    new MutationObserver(sync).observe(cover, { attributes: true, attributeFilter: ["class"] });
    document.addEventListener("visibilitychange", sync);
    window.addEventListener("hashchange", function () { setTimeout(sync, 80); });
    sync();
  });
})();
```

```css
.slide.cover-slide .kz-particles { position:absolute; inset:0; z-index:1; pointer-events:none; }
```

- 只动画`transform`与`opacity`（SVG描边允许`stroke-dashoffset`）；NEVER动画`width/height/top/left/padding/gap/font-size`。
- transition声明MUST使用显式属性列表（如`transition:transform var(--motion-fast) var(--ease-out), box-shadow var(--motion-fast) var(--ease-out)`）；NEVER使用`transition:all …`或只写时长缓动的简写`transition:180ms ease-out`——后者computed值为`all`，会连带布局属性一起过渡并干扰冻结态检查。
- 媒体查询MUST带空格书写：`@media (hover:hover) and (pointer:fine) and (prefers-reduced-motion:no-preference)`；NEVER写成无空格`@media(...)and(...)`——CSS规范要求`and`前后空白分隔，无空格形式是静默解析错误，会导致整个hover/指针块被浏览器整体丢弃（computed transition回落为`all`、hover抬升失效），且构建期不报错、肉眼难发现。压缩CSS时同样必须保留`and`两侧空格。
- hash写入MUST先归一化：`history.replaceState(null,"",location.pathname+location.search+"#"+token)`，NEVER直接拼接`location.hash+token`；否则深链会退化成`#/2#/3`或`#q=X#q=X`这类重复hash。
- hover位移最大3 px、缩放最大1.01、3D倾斜最大1deg；不能使元素跨出原分配网格或与相邻元素相交。
- 默认只让目录卡和明确标记`data-interactive="true"`的摘要卡响应hover。表格单元格、甘特阶段条、风险标签、证据截图和结束页不响应hover。
- 任何信息在静态态必须完整可见；NEVER把解释、来源、风险或操作提示只放在hover后。
- `kz-stagger`只加在成组容器（`.toc-board`、`.grid.g2/.g3`、`.comparison-card-grid`）上，最多数8个直接子项；超过8个按容器整体淡入，不逐项级联。
- `kz-item-in`的fill-mode固定为`backwards`（不得用`both`/`forwards`）：`both`会把末帧`transform:none`永久锁在子项上，覆盖后续`:hover`的`translateY`抬升，造成“阴影变了但卡片不抬升”的失效；`backwards`只在延迟期保持起始帧，动画结束后交还控制权给transition/hover。
- `data-countup`元素在DOM中必须先写最终真值（截图与无JS环境直接读DOM即为真值），滚动只是进入活动页时的一次性视觉增强；NEVER用滚动过程承载唯一数值。
- 粒子脚本只允许挂在`.slide.cover-slide`，节点≤40、连线距离≤110px、橙色低透明度按本节常量；内容页、目录页、章节页、结束页NEVER出现canvas粒子。
- 可交互卡必须有键盘可达性：`tabindex="0"`且`:focus-visible`使用`--shadow-focus`，hover与focus使用同一信息层级，不得只服务鼠标。
- 正式交付的HTML/HTML-PPT默认根节点不得永久写死`data-export="true"`或`data-qc="true"`；正常打开必须处于交互态。只有静态导出、HTML-to-PPT和机器验收期间才临时设置该属性，完成后MUST删除或恢复原值。
- 截图、PNG/PDF导出、HTML-to-PPT和机器验收前MUST设置`document.documentElement.dataset.export="true"`或`data-qc="true"`，等待两个`requestAnimationFrame`后再测量；导出完成后恢复。允许通过`?export=1`、自动化注入或打印事件进入冻结态，但不得让普通`file://`打开永久冻结。

##### D. 流式HTML报告增强

- 入场揭示MUST使用`html.js`门控，保证无JS、打印和`prefers-reduced-motion:reduce`下内容直接完整显示：

```css
html.js .kz-reveal {
  opacity:0; transform:translateY(14px);
  transition:opacity .48s var(--ease-out), transform .48s var(--ease-out);
}
html.js .kz-reveal.is-in { opacity:1; transform:none; }
html.js .kz-reveal-stagger > * {
  opacity:0; transform:translateY(12px);
  transition:opacity .42s var(--ease-out), transform .42s var(--ease-out);
}
html.js .kz-reveal-stagger.is-in > * { opacity:1; transform:none; }
html.js .kz-reveal-stagger.is-in > :nth-child(2) { transition-delay:.06s; }
html.js .kz-reveal-stagger.is-in > :nth-child(3) { transition-delay:.12s; }
html.js .kz-reveal-stagger.is-in > :nth-child(4) { transition-delay:.18s; }
html.js .kz-reveal-stagger.is-in > :nth-child(5) { transition-delay:.24s; }
html.js .kz-reveal-stagger.is-in > :nth-child(6) { transition-delay:.30s; }
html.js .kz-reveal-stagger.is-in > :nth-child(7) { transition-delay:.36s; }
html.js .kz-reveal-stagger.is-in > :nth-child(8) { transition-delay:.42s; }
```

- MAY使用`IntersectionObserver`触发一次性淡入（阈值0.15，触发后不再隐藏），或在`@supports (animation-timeline:view())`内启用滚动驱动揭示；无支持时内容必须直接显示。
- 滚动揭示位移不超过14 px、时长不超过480ms；只用于章节标题、摘要卡和图表容器，不逐行逐字动画。
- 单文件流式报告MAY复用§14.12.5的共享组件（粘性导航、进度条、抽屉、tooltip、手风琴、数字滚动）；复用时把组件CSS/JS内联进单文件，不新建第二套命名。
- 可交互卡必须有键盘`focus-visible`状态；hover与focus使用同一信息层级，不得只服务鼠标。
- `backdrop-filter`仅允许粘性导航一层（`blur(8px)`+不透明度≥0.94的白底）；复杂混合模式与实时模糊禁用：它们会降低医学文字对比、增加渲染差异并干扰打印/PDF。

##### E. 站点式HTML交互增强

站点式HTML（多页面交互站点，§14.12）的动效直接执行§14.12.7，组件库执行§14.12.5，环境装饰执行§14.12.6；其静态基线、冻结语义与reduced-motion规则与本节B–D一致，且额外允许§14.12.6列明的hero粒子与光斑。站点式HTML不属于幻灯片，§14.2–§14.6的固定画布规则不适用。


##### F. 设计感验收


- **中文标题行高防裁切**：中文标题（≥32 px）的 `line-height` MUST ≥ 1.3（或等效 computed line-height ≥ font-size × 1.3），否则中文字形的 ascender/descender 会被 `scrollHeight > clientHeight` 裁切 3–5 px。若因品牌锁定必须使用 1.2 行高，则该标题元素 MUST 设 `overflow:visible` 以保证视觉不裁切；但 `overflow:visible` 不豁免 `no_text_overflow` 闸门对 `scrollWidth > clientWidth` 的水平溢出检查。
- **站点 hero canvas 属性**：站点式 HTML 的 hero 粒子 canvas MUST 在 HTML 中带 `aria-hidden="true"` 属性（NEVER 只靠 JS 设置）；CSS MUST 含 `@media (prefers-reduced-motion:reduce) { canvas.kz-particles, .kz-particles canvas { display:none !important; } }` 与 `html[data-export="true"] .kz-particles, html[data-qc="true"] .kz-particles { display:none !important; }`。NEVER 依赖 JS 在 reduced-motion 下隐藏 canvas——CSS 媒体查询是唯一可靠路径。

- **卡片层次基线（强制底线，深度自由）**：每个卡状表面（上述集合）MUST 有可感知层次 =（`box-shadow`≠none）或（`border-top`≥3px 且非纯白无边框墙）；NEVER 出现"无阴影+无边框+无顶条"的纯白扁块（扁平 AI 味反模式）。**但**阴影具体深度、hover 抬升幅度、圆角在 §14.7.3 token（`--shadow-1/2/3`、抬升 ≤3px、圆角 8–14px）范围内由模型自主选——这是发挥空间，规范不钉唯一值。
- **HTML-PPT 演讲者运行时 + 逐字稿（强制功能细节）**：HTML-PPT MUST 内嵌演讲者运行时——按 `S` 弹出含**当前页/下页/逐字稿/计时器**的窗口（← → 翻页双向同步、`R` 重置计时、`N` 笔记抽屉），优先采用 `html-ppt` 技能 runtime.js 的 Hybrid 模式（删 theme 循环），或内联等价自包含实现，并支持 `?preview=N` 像素级预览。每张 slide 的 `<aside class="notes">` MUST 写 **150–300 字口语逐字稿**（三铁律：提示信号非讲稿、关键词 `<strong>`、用口语）。无运行时或无逐字稿=不合格。流式/站点不强制此项。
- **发挥空间清单（粗，模型自主，规范不规定唯一答案；不同模型/主题产出不同但都合格的成品是预期结果，不是缺陷）**：构图选型、视觉隐喻、SVG 内部画法（满足上述文字像素/形状词表/标记规则即可）、阴影深度与 hover 幅度（在 token 范围内）、信息分组、页数与分页、动效编排顺序、卡片内部版式。这些在硬约束（**§0.8 强调色系**/品牌身份/页眉页脚/字号/证据/AI 边界）之内自由发挥；可在色系内做和谐中性色与层次，不得改主/副强调或部门映射。
- 阴影不能替代间距。卡片间仍使用固定gap，hover前后不得改变文档流尺寸。
- 页面不应“每个对象都是一张卡”；同组次级信息优先用分隔线、浅底、色条或排版层级。
- 同一页动效对象不超过8个；超过时按容器整体淡入，不逐项级联。
- 交互增强验收：精细指针设备上，目录页或内容页至少一个元素产生可测量的hover变化（transform或box-shadow）；`prefers-reduced-motion:reduce`与`data-export/data-qc`冻结态下所有animation/transition计算值为`none`/`0s`且内容完整可见。
- 环境装饰（粒子、光斑、轨道环）每页合计≤1处，必须`aria-hidden="true"`且`pointer-events:none`，不得与证据区、表格、截图矩形相交，离屏与页面隐藏时自动停帧。
- 数字滚动终值必须等于正文陈述的真值；静态终态（无JS或冻结）DOM即包含完整数值。

##### G. 反扁平设计原则（在品牌克制约束内做"活"）

康哲规范刻意克制（白底≥80%、禁玻璃拟态/极光/深色霓虹/渐变标题/整页铺色），但"克制"不等于"扁平死板"。Agent MUST 在本节约束内主动用层次与微动效让页面有质感，避免"白卡+顶堆文字+下半页空白"的模板感；同时 NEVER 越过§5/§14.7.3 的红线去追求"科技感"。

- **已验证范式（包括但不限于，Agent MAY 自创新范式）**：①**流程脊**——KPI 条+全宽 living SVG+结论条；②**覆盖率+机制**——左栏覆盖率条+右栏闭环图；③**收敛+资产轨**——左栏汇聚图+右栏资产轨卡；④**环形闭环**——KPI 条+环形 N 节点 living SVG（中心 hub+外圈节点+里程碑菱形+描边弦线）+结论条；⑤**分支处置流**——KPI 条+主脊 N 节点→M 处置分支卡→汇聚关闭+底部辅流程泳道；⑥**双泳道对照**——KPI 条+上下两条独立泳道 SVG（各含节点+里程碑+回流线）；⑦**场景+红线 split**——KPI 条+左栏场景状态卡+右栏推进原则+红线胶囊簇。以上 7 套均已在真实构建中验证通过丰富度闸门；Agent 面对新主题时 MAY 组合或自创，只要满足闸门 (a)-(e)。；⑥**粘性叙事**——左栏 sticky 标题+进度、右栏滚动阶段（流式/站点，<768px 降级自然流）；⑦**便当总览**——`.kz-bento` 大小模块开篇，大块核心结论+小块 KPI/状态（流式/站点/交互）；⑧**横向画廊**——`.kz-hscroll`+scroll-snap+边缘渐隐方向暗示（站点/交互）。
- **封面要"活"**：封面（仅封面）MUST 使用§14.7.3 C 的环境层组合——`aria-hidden` 的低对比网格底纹（`mask-image` 径向渐隐）+ 低对比品牌橙/医学蓝光斑 + 粒子网络（节点≤40、连线≤110px、橙色低透明、离屏停帧）。这些是封面唯一允许的"氛围层"；内容页/目录页/章节页/结束页 NEVER 使用粒子或光斑。
- **内容卡要撑满纵向、有视觉锚点（禁止"空中段"）**：内容页卡片用 flex 列布局（`display:flex;flex-direction:column`），让正文与底部 `.card-foot`（来源/口径）之间用 `margin-top:auto` 撑开。每张卡 MUST 同时满足两层：①**身份层**——顶部 4px 部门色条（`--card-accent`，每卡必有，同页用不同部门色形成节奏）；②**内容层视觉锚点**——在标题与卡脚之间的中段 MUST 放一个非纯文本的视觉元素：内嵌 `kz-drawon` 描边迷你图（流程线/环形进度/部门色柱/汇聚图，`aria-hidden`，进场描边生长）、或一个 `data-countup` 大数字+单位块、或一行部门徽章/`.kz-lamp` 状态簇。**仅靠 4px 顶色条不算锚点**；若一张卡的中段只有正文、且正文末行到卡脚之间留下 >120px 的空白，则该卡违反本节（"空中段"反模式，多轮实测中弱模型高频踩中）。同一内容页的三卡中至少两卡应使用描边迷你图或数字块，避免整页只剩"文字+顶线"。
- **层次靠排版与色条，不靠堆卡**：用字号字重对比（大数字 44–46px/800 vs 正文 17px/400 vs 卡脚 13px/600 灰）、部门徽章胶囊、呼吸状态灯 `.kz-lamp` 制造层次；NEVER 把每个次级信息都包成悬浮卡，也 NEVER 用阴影替代间距。
- **章节页加一句 lead**：章节首页在标题下方加一句 20px 的章节导语（`max-height` 受限、不超两行），让章节页不只剩"编号+标题"的空旷感；导语仍只放章节定位，不放摘要卡或目标清单。
- **动效要可感知但一次性**：进入活动页时 `kz-stagger` 逐项淡入、`kz-sweep` 扫光、`kz-drawon` 描边生长、`data-countup` 数字滚动应同时编排，形成"页面活过来"的入场；但全部一次性，NEVER 循环漂浮/逐字闪烁/持续旋转（封面粒子除外且可停）。
- **静态基线优先**：上述所有增强在 `data-export`/`data-qc` 冻结态与 `prefers-reduced-motion:reduce` 下 MUST 退化为完整静态终态（描边画满、数字即真值、揭示可见）。**粒子是 rAF 驱动的 canvas，CSS 的 `animation/transition/transform:none` 停不住它**：除用 `html[data-export] .kz-particles{display:none}` 在视觉上隐藏外，粒子 IIFE MUST 在每次状态同步检查 `html[data-export]`/`[data-qc]` 与 reduced-motion，命中即 `cancelAnimationFrame` 并 `clearRect`，并用 MutationObserver 监听 `<html>` 的 `data-export`/`data-qc` 属性变化触发停帧；只隐藏 canvas 而让循环空转不合格（冻结态截图虽看不到粒子，但"无活动"语义被破坏）。任何增强不得承载唯一信息，截图与无 JS 环境读 DOM 即得完整内容。
- **禁区重申（含 scoped override）**：NEVER 整页毛玻璃卡片墙（毛玻璃面按 §14.13.2 scoped 规则：每视口≤4 面、背景不透明度≥88%、1px 边界、冻结回退）、NEVER 极光/彩色渐变球背景、NEVER 深色模式或近黑底+霓虹、NEVER 渐变填充标题、NEVER 整页橙/黄/红铺底、NEVER 大圆角(>14px)卡片墙。这些是"扁平"的反面但同样不合格——它们破坏医学汇报的可信度与可读性。

### 14.8 资源、字体、离线与单文件交付

Logo下载与封装是生成步骤，不是观众运行时行为。标准命令示例：

```bash
mkdir -p assets
curl --fail --location --silent --show-error \
  'https://web.cms.net.cn/wp-content/themes/qnz/assets/img/logo_bot.svg' \
  --output assets/logo_bot.svg
```

下载后MUST验证：文件非空；包含`<svg`和`viewBox="0 0 121 25"`；模块化HTML所有Logo槽只引用`assets/logo_bot.svg`；PPT/PPTX将该文件嵌入；单文件HTML所有Logo槽只使用由该文件生成的`data:image/svg+xml...`。不得把官网HTTP(S)地址直接保留在最终`img src`、CSS `url()`、SVG `href`或脚本中。

模块化源文件是维护母版，单文件HTML是派生产物。推荐结构：

```text
deck/
  index.html
  kangzhe.css
  assets/
    runtime.js
    cover_hero.jpg        # 必须预裁为1280×565
    logo_bot.svg          # 官网正式Logo；内容页 158×33 槽、hero 页 200–240×44–50 槽内 contain
    footer_ribbon.jpg     # 必须预裁为1280×155
```

- 上述四个文件是正式资产的角色名，不是本规范的硬依赖。用户提供正式资产时按角色替换；没有正式资产时使用§7.4和§14.5的可重建fallback。fallback保证布局、配色和层级一致，不声称逐像素重绘商标或世界地图。
- 默认使用系统字体栈，不加载`fonts.css`或Google Fonts；不得为了字形完全一致而未经许可内嵌完整商业中文字体。
- 所有图片设置明确`width/height/object-fit`：Logo/wordmark与证据截图固定`contain`，预裁hero/ribbon固定`cover`；高DPR栅格资产至少为逻辑显示尺寸的2倍。截图前等待`document.fonts.ready`，并对图片执行`complete && naturalWidth > 0`检查，必要时`await img.decode()`。
- 若使用获许可的WOFF2子集，必须实际声明所需400/600/700字重、设置`font-synthesis:none`并验证`document.fonts.check()`；最终截图不得处于`font-display:swap`的临时fallback状态。
- 单文件模式将CSS、JavaScript、图片转为`<style>`、内联`<script>`和Data URL。只有当脚本源码被暂时放进另一个HTML/JavaScript字符串时，才在该中间字符串内转义字面量`</script>`；写入最终HTML后，真实脚本闭合标签必须是字面量`</script>`。最终文档出现`<\/script>`而没有真实`</script>`会让浏览器把后续内容继续当作脚本，属于运行时阻断错误。
- 单文件模式必须清零外部资源依赖：stylesheet/`@import`、所有`link[href]`、`script src`、`img/src/srcset`、`source src/srcset`、`iframe[src]`、`object[data]`、`embed[src]`、`audio[src]`、`track[src]`、`video poster`、CSS `url()`、SVG `href/xlink:href`、动态`import`、`fetch/XHR`、`Worker/SharedWorker/ServiceWorker`、`WebSocket/EventSource`等位置，不得引用当前HTML之外的HTTP(S)、`file:`或相对路径资源。唯一file例外是讲者预览iframe重新加载当前HTML自身并仅追加query/hash；其余允许项为内嵌`data:`、运行时自产`blob:`和SVG内部`#fragment`。可见参考文献中的DOI/URL允许保留；它们不是渲染依赖，离线时不可点击应如实说明。
- 单文件仍须用`file://`直接打开复测键盘翻页、页码、图片和三档视口；不能只在本地HTTP服务下测试。
- 不把患者敏感信息、账号、绝对路径、内部日志、未用于可见页面的原始附件或源材料全文嵌入分享版。经批准并完成脱敏、且确为可见证据链所需的节选或截图可以嵌入。

### 14.9 HTML-PPT机器验收与人工验收

每次交付的逻辑视口回归至少覆盖`1280×720`、`1920×1080`、`2048×1024`；如果用户提供最大化截图，再增加该实际视口。跨OS实机矩阵最低要求如下，浏览器缩放均为100%：

| 操作系统 | 必测浏览器 | 必测窗口 |
| --- | --- | --- |
| Windows 10/11 | Chrome或Edge至少一个 | 真实最大化窗口；常见补充`1366×768` |
| macOS | Chrome + Safari；自动化可用Chromium + WebKit预检 | 真实最大化窗口；常见补充`1440×900` |

两台系统必须比较所有`data-qc-id`归一化几何、标题/标签/正文行数、computed font family与文字裁切。只在macOS上跑两个内核只能证明内核预检，不能证明Windows微软雅黑折行。基准期望：

| 视口 | 画布可见尺寸 | 预期留白 |
| --- | --- | --- |
| 1280×720 | 1280×720 | 无 |
| 1920×1080 | 1920×1080 | 无 |
| 2048×1024 | 约1820.44×1024 | 左右各约113.78 px |

机器断言速查如下；§16.A是唯一完整权威清单，项目validator必须执行§16.A全部门禁，本速查不能替代或缩减它：

```yaml
html_ppt_runtime_gates:
  slide_count: ".deck > .slide数量 == 计划页数"
  active_slide_count: ".deck > .slide.is-active数量在任一时刻 == 1"
  logical_canvas: "activeSlide.offsetWidth == 1280 && activeSlide.offsetHeight == 720"
  scale: "abs(deckRect.height/720 - min(vw/1280,vh/720)) <= 0.001"
  center_error: "x和y绝对值 <= 0.5px"
  aspect_ratio: "abs(deckWidth/deckHeight - 16/9) <= 0.001"
  document_overflow: "scrollWidth == clientWidth && scrollHeight == clientHeight"
  slide_overflow: "每页scrollWidth == clientWidth && scrollHeight == clientHeight"
  normalized_geometry: "所有[data-qc-id]在三档视口的逻辑坐标和行数一致，误差 <= 0.5逻辑px"
  cross_os_line_count_and_clipping: "Windows与macOS的同一data-qc-id行数一致且均无clipping；字体命中记录非空"
  minimum_visible_font: "正文/标签默认>=16px；仅标记data-density=ultra且满足§13.3全部条件的18行总览表体/轴标签可>=14px；参考文献>=10.67px"
  text_not_clipped: "所有[data-qc-text]的Range墨迹框与容器内容框相交完整；overflow:hidden/clip容器不得裁掉墨迹；允许字体行盒造成不超过2px的scrollHeight虚差"
  semantic_block_overlap: "同一[data-qc-zone]内任意两个[data-qc-block]的相交面积必须为0；明确背景/连线用data-qc-overlap=allow豁免"
  title_logo_separation: "标题与Logo边界框不相交"
  body_footer_separation: "正文边界框bottom <= 660且不进入页脚"
  fonts_ready: "document.fonts.status == loaded且目标字体check为true"
  images_loaded: "所有可见图片complete且naturalWidth > 0，需解码图片decode成功"
  console_and_page_errors: 0
  normal_runtime_not_frozen: "普通打开时html不存在data-export=true和data-qc=true；仅导出/QC运行临时设置"
  page_number_binding: "逐页激活并检查：每个内容页.slide-number的data-current == 该slide在deck中的1-based索引，data-total == deck总页数；非内容页不存在可见页码"
  grid_alignment: "表头、部门边界、时间轴起点、每个周期边界误差 <= 0.5px"
  grid_equal_columns: "同一时间轴max(columnWidth)-min(columnWidth) <= 0.5逻辑px"
  bar_overflow: "所有阶段条scrollWidth <= clientWidth"
  weakened_card: "opacity == 1且背景为不透明白色"
  weakened_card_computed: "computed backgroundColor == rgb(255,255,255)且backgroundImage == none"
  standalone_requests: "单文件模式只允许当前HTML自身（含query/hash）、data:和运行时自产blob:；其他请求 == 0"
```

`normalized_geometry`的实现：只遍历`.deck > .slide`，给标题、Logo、正文根、每行时间轴和页脚添加稳定`data-qc-id`；overview/presenter克隆移除该属性或标记`data-qc-ignore`。将`getBoundingClientRect()`减去deck左上角后除以scale，再跨视口/浏览器比较。该检查用于发现普通overflow测试看不到的媒体查询重排。

文字与重叠检查不得只依赖整页`scrollWidth/scrollHeight`：

- 所有受众文字容器MUST标记`data-qc-text`；validator用`Range.selectNodeContents()`取得实际文字墨迹框，比较容器扣除padding后的内容框。只有墨迹框越界、文字容器设置`overflow:hidden/clip`且墨迹被截断、或宽度余量不满足时才失败；浏览器字体行盒造成的1–2 px `scrollHeight`虚差不得单独判失败。
- 所有布局组件根MUST标记`data-qc-zone`，同层卡片、表格、图表、结论条标记`data-qc-block`。validator对同一zone的block做两两矩形相交检查；背景、装饰线和已知连接线必须显式标记`data-qc-overlap="allow"`，不允许用全局allowlist忽略未知重叠。
- `overflow:hidden`只能用于裁切图片、装饰背景和固定组件外形；NEVER把它当作文字容量修复。任一文字节点被裁切，必须缩短、减项、调整固定组件允许的行数或拆页。
- 页面生成后MUST在`data-export="true"`稳定终态运行上述检查，随后再用正常交互态检查hover不会与相邻block相交。
- 普通运行态必须检查根节点未永久冻结；目录卡或显式交互卡至少一个在精细指针设备上产生不超过3 px的可测hover位移或阴影变化，`prefers-reduced-motion:reduce`下恢复静态。

人工验收：

- 逐页查看1920×1080和2048×1024原图；不能只看缩小contact sheet。
- 检查内容是否使用页面下半部，是否存在非设计性大空白。
- 检查标题、Logo、流程连接线、页脚、页码、甘特竖线和标签裁切。
- 检查Windows/macOS字体变化后是否造成新增换行；不能仅比较DOM数值。
- 检查浏览器100%缩放的最终画面；80%/125%只验证仍能等比居中、无溢出，不作为视觉基准。
- 若无法访问真实Windows，只能把Chromium结果记为内核预检，并在交付说明中写明“未在真实Windows设备测试”；不得据此声明Windows/macOS显示一致。
- macOS/Safari优先用真实Safari；无法自动化时至少用WebKit内核复核。
- 视觉模型或自动化审阅只能提供第二意见；最终视觉接受者仍需查看实际浏览器原图。


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
