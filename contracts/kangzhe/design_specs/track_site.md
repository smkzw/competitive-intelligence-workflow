# 康哲设计规范 · 站点式 HTML 轨

> **Portable package track pack** · track_id=`site`  
> **Load order**: `ROUTER.md` → `core.md` → **this file** (to EOF).  
> **Assets**: `assets/logo_bot.svg` (relative to `design_specs/`).  
> **Authority**: This pack + `core.md` are the load-time contract for this product. Machine-only samples live in `local_map.md` (optional).  
> **Do not** require reading the legacy monorepo body for this product.

**Also read**: core.md

---

## 0. 使用入口

当用户说以下任一表达时，必须先读取本文件，再开始写作、设计、生成或审阅：

- `使用康哲PPT设计规范`
- `用康哲PPT规范`
- `康哲汇报模板`
- `康哲医学汇报规范`
- `康哲模板`
- `PPT Master 用康哲规范`
- `HTML-PPT 用康哲规范`
- `康哲html设计规范`
- `康哲HTML设计规范`
- `康哲html报告设计规范`
- `康哲HTML报告设计规范`
- 语义等价的“按康哲医学部汇报模板做/改/审”
- `方案汇报`、`方案介绍`、`方案培训`、`方案讲解`、`核查前培训`、`protocol training`

产出路由按用户交付词决定，不能只看“HTML”三个字：

| 用户表达或交付特征 | 固定路由 | 必须读取/执行 |
| --- | --- | --- |
| `PPT`、`PPTX`、`可编辑PPT`、`非HTML-PPT`、`PPT Master` | 可编辑PPT | 本文件§13 + 已安装`ppt-master`全流程；不得用HTML转截图替代 |
| `HTML-PPT`、`HTML演示`、`浏览器翻页`、`幻灯片HTML`、固定页数/逐页播放 | HTML-PPT | 本文件§14.1–§14.9 + `html-ppt`运行时 |
| `HTML报告`、`网页报告`、`长文档`、`滚动页面`、响应式报告 | 流式HTML报告 | 本文件§14.10；不得套1280×720幻灯片坐标 |
| `站点`、`多页面`、`说明书站点`、`门户`、`导航站`、≥2个互通页面/全局搜索 | 站点式HTML | 本文件§14.12；不得套1280×720幻灯片坐标，不得用单文档报告冒充 |
| `驾驶舱`、`看板`、`交互板`、`可过滤`、`下钻`、`数据板`、`dashboard`、`控制台` | 交互单页应用 | 本文件§14.13；数据驱动单页，不套翻页也不套多页 |
| 同时要求多种格式 | 多轨分别生成 | 按§13.0“一个交付物一个检查点”依次完成和验证 |
| `方案汇报`、`方案介绍`、`方案培训`、`方案讲解`、`核查前培训`（源材料为临床试验方案） | 可编辑PPT 或 HTML-PPT | 本文件§14.14 Playbook + §13/§14 对应轨全流程；流式HTML与站点式HTML不适用 |

仅说“康哲HTML设计规范”而没有页面形态时：出现“汇报播放/翻页/页数”按HTML-PPT；出现“报告/阅读/滚动/响应式”按流式HTML；出现“站点/多页面/导航/门户/全局搜索”按站点式HTML；仍无法判断且两条路线会显著改变交付物时才向用户确认。

本规范同时覆盖 **PPT（含 PPT Master）**、**HTML-PPT（按 1280×720 翻页幻灯片渲染）**、**HTML 报告（流式长文档，见 §14.10）**、**站点式HTML（多页面交互站点，见 §14.12）** 与 **交互单页应用（数据驾驶舱，见 §14.13）** 五类产出。五者共享**品牌强调色/副强调/色系（§0.8/§5，强制）**、字体下限、证据、医学写作与品牌内核；版式精细度按轨不同。HTML 报告与站点不受固定画布约束，仍必须守强调色系与证据/AI 边界。**强制的是强调色与色系，不是把正文锁成唯一黑色**；违反主/副强调、部门映射、风险红语义、面积红线 → 阻断交付。

### 0.0 分轨加载层（Agent 默认入口，权威仍在本文件）

为降低误读无关轨与截断读取风险，本机提供**投影加载层**（非第二套 SSOT）：

| 步骤 | 路径 |
| --- | --- |
| 1. 判轨 | `design_specs/ROUTER.md` |
| 2. 共享硬合同 | `design_specs/core.md` |
| 3. 本轨包 | `design_specs/track_{pptx\|htmlppt\|stream\|site\|interactive}.md` |
| 4. 专章全文/代码块 | **回到本文件**对应 §13 / §14.x，读到节末或 EOF |

- **权威**：固定 HEX、DOM/CSS 合同、I-闸门原文 **以本文件（及同步的 `design_share_v2.md`）为准**。
- **NEVER** 只读 `design_specs/*` 摘要、跳过本文件可执行代码块即宣称合规。
- 架构评估与演进：`design_specs/ARCHITECTURE.md`。

本文件不是普通风格参考，而是跨 Agent 的设计合约。除非用户明确覆盖，后续 Agent 不得只凭记忆或只看截图生成康哲风格 PPT。


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


### 14.12 站点式HTML（多页面交互站点）设计规范

本节定义第四类产出：**站点式HTML**——多页面、多层级交互的静态站点（如流程说明书站点、部门门户、专题导览站）。它与§14.1–§14.9的HTML-PPT（固定1280×720翻页）和§14.10的流式HTML报告（单文档长报告）明确区分：站点式HTML由多个互通页面组成，带全局导航、全局搜索与跨页下钻，面向反复查阅而非一次播放。本节框架归纳自内部已验收的成熟站点实现，Agent MUST 原样执行目录结构、令牌与组件命名，只替换业务数据与文案。

#### 14.12.1 适用边界与路由

| 维度 | HTML-PPT（§14.1–§14.9） | 流式HTML报告（§14.10） | 站点式HTML（本节） |
| --- | --- | --- | --- |
| 形态 | 逐页幻灯片，每页1280×720 | 单文档，自然滚动 | 多页面站点，页面间导航+页内下钻 |
| 页面数 | 固定页数，逐页播放 | 1个HTML | ≥2个HTML，共享导航 |
| 版式 | §8页面原型强制 | 不套原型 | 不套§8原型；执行§14.12.4页面模式 |
| 交互 | 翻页为主，hover为辅 | 滚动阅读+锚点 | 多层级下钻、过滤、搜索、抽屉 |
| 交付 | 可导出PPTX/PDF | 单文件/模块化网页 | 静态目录，`index.html`直接打开 |

路由：用户说`站点`、`多页面`、`说明书站点`、`门户`、`导航站`、要求≥2个互通页面或全局搜索时，按本节执行；单文档长报告仍按§14.10；固定页数播放仍按§14.1–§14.9。三者不得混用同一文件。

#### 14.12.2 技术约束（强制）

- 纯静态站点：目录以`index.html`直接打开即可运行，`file://`与任意静态服务器均可；无构建步骤、无前端框架（不用React/Vue），原生HTML + CSS自定义属性 + vanilla JS（ES2020+）。
- 数据不用`fetch`加载本地JSON（规避`file://`的CORS限制）：数据以`data/*.js`文件通过`window.DATA_X = {...}`全局注入，页面脚本读取全局变量。
- 大文件写入稳定性：单文件超过300行（约15KB）时MUST分块写入（先写基础层，再用编辑工具追加），并在写完后回读校验完整性；一次性写入超大payload是Agent工具调用失败的高频原因。
- 不加载远程字体、远程图片、远程脚本；允许但不依赖CDN（流程图/泳道/矩阵一律HTML+CSS+SVG手绘，默认不引入图表库）。
- 总资源（不含数据层）≤100MB；无控制台报错/警告；无死链、无占位符、无lorem ipsum。
- 目录结构固定（页面可按需增减，但资产与数据分层不变）：

```text
site/
  index.html            # 首页·管理摘要
  <page>.html           # 各专题页（panorama/stages/departments/ai/...）
  assets/css/tokens.css # 设计令牌（唯一配色来源）
  assets/css/app.css    # 组件与页面样式
  assets/js/components.js # 共享组件（导航/页脚/抽屉/表格/筛选/tooltip）
  assets/js/kz-fx.js    # 动效运行时（reveal/count-up/particles，§14.12.7）
  assets/js/page-*.js   # 各页逻辑
  data/*.js             # window.DATA_X 数据层
```

- 单文件站点变体（用户要求直接转发时）：把tokens/app样式、components/kz-fx脚本与数据全部内联进一个HTML，保持class与data命名不变，并按§14.8内联Logo为Data URL。

#### 14.12.3 设计令牌（唯一配色来源）

执行时把以下令牌原样复制为`tokens.css`的`:root`变量；页面CSS只引用变量，不散落新增HEX（图表语义色除外）。与§5冲突时以§5为准，本节是§5在站点场景的落地值。

```css
:root {
  /* 品牌与部门色（§5.2.1映射，不得调换） */
  --kz-orange:#FF9900; --kz-orange-mid:#F5A000; --kz-yellow:#FFCC00; --kz-gold:#E69500; --kz-risk:#C00000;
  --kz-med:#FF9900;    --kz-med-soft:#FBE3D6;
  --kz-co:#407AAA;     --kz-co-soft:#DCE6F2;
  --kz-dmst:#587B3B;   --kz-dmst-soft:#DCE9C8;
  --kz-pv:#A85F34;     --kz-pv-soft:#FCF5E6;
  /* 表面与边界 */
  --bg:#F8F9FA; --surface:#FFFFFF; --bg-warm:#FCF5E6;
  --border:#E5E7EB; --border-strong:#D1D5DB; --border-glass:rgba(15,17,21,.08);
  --text-1:#0F1115; --text-2:#404040; --text-3:#808080;
  /* 功能色 */
  --good:#2E7D32; --warn:#A85F34; --info:#407AAA;
  /* 阴影（与§14.7.3 B一致，站点允许--shadow-3用于hero卡） */
  --shadow-sm:0 1px 2px rgba(15,17,21,.05);
  --shadow-1:0 1px 2px rgba(15,17,21,.06), 0 6px 18px rgba(15,17,21,.08);
  --shadow-2:0 2px 4px rgba(15,17,21,.08), 0 14px 30px rgba(15,17,21,.12);
  --shadow-3:0 4px 8px rgba(15,17,21,.08), 0 22px 44px rgba(15,17,21,.14);
  --shadow-glow:0 0 0 1px rgba(255,153,0,.22), 0 8px 28px rgba(255,153,0,.12);
  --shadow-brand:0 6px 18px rgba(255,153,0,.18), 0 2px 6px rgba(255,179,77,.12);
  /* 圆角与间距 */
  --radius-sm:8px; --radius:14px; --radius-lg:20px;
  --header-h:60px;
  /* 字体与行高 */
  --font-sans:"Microsoft YaHei","微软雅黑","PingFang SC","Noto Sans SC","Helvetica Neue",Arial,sans-serif;
  --lh-tight:1.2; --lh-body:1.65; --lh-dense:1.4;
  /* 动效 */
  --ease-out:cubic-bezier(.22,1,.36,1);
  --ease-spring:cubic-bezier(.2,.9,.25,1.15);
  --dur-fast:160ms; --dur:280ms; --dur-slow:480ms;
}
html { color-scheme:only light; }
```

红线（与§5.3/§5.4一致）：

- 四部门固定映射不得调换：医学MED`#FF9900`/浅橙`#FBE3D6`；运营CO`#407AAA`/浅蓝`#DCE6F2`；数统DMST`#587B3B`/浅绿`#DCE9C8`；PV`#A85F34`/暖米`#FCF5E6`；弱化/其他`#AAA6A1`+白底。
- 白/浅底面积≥80%；黄橙品牌色合计≤12%；风险红`#C00000`≤3%且仅风险/阻断语义。
- 默认浅色模式，主背景`#FFFFFF`或`#F8F9FA`；暖米`#FCF5E6`只用于callout/摘要块；禁止整页铺品牌橙/黄/红。**全站深色主题 NEVER**。**默认 sticky 顶栏为浅底+深字+橙识别**（§0.8.3）。局部 dark sticky 仅当满足 §0.8.3B（含 Logo 反白/浅底胶囊、字对比≥4.5:1），且 **NEVER** 深色 hero 大面。hero 光斑/粒子按§14.12.6低对比例外；禁止高饱和整页渐变与霓虹描边堆叠。
- 正文≥16px（高密度表格可14px，不低于13px）；字重只用400/600/700；数字`font-variant-numeric:tabular-nums`。
- 间距只用`4/8/12/16/24/32/40/56px`八档。
- 不得只用颜色区分信息：同时用文字/边框/线型/位置（如RACI的A/R/C/I必须带字母）。

#### 14.12.4 页面模式库

站点页面 **SHOULD** 从以下模式库组合；**MAY** 自创模式，但 MUST 仍使用 §14.12.5 组件命名与 §14.12.3 token，并通过 §14.12.10 验收。模式库：

1. **首页·管理摘要（index）**：hero区（大标题32–40px、一句话定位、3–4个关键数字卡，数字卡用`data-countup`）+ 阅读路径卡（按角色推荐入口页）+ 价值链/总览横条（可点击跳转）+ 口径声明callout（暖米底）。
2. **全景/总览页（核心页，投入最多精力）**：L0段视图（顶部价值段色带，可折叠）→ L1节点流（横向滚动+缩放0.6x–1.5x，节点=白卡+4px部门色顶边+编号圆+名称+里程碑菱形+AI成熟度圆点，节点间连线带方向箭头）→ L2抽屉（点击节点出右侧抽屉，固定tab：概览/子活动/部门泳道/交付物/交互接口/AI介入）→ L3活动级内联展开（不新开抽屉）。顶部sticky工具条提供部门过滤、AI视图、里程碑开关、控制流叠加、图例面板；过滤/选中状态写入URL hash可分享，提供"重置视图"。接口高亮时两端节点强调、其余降至透明度0.35。
3. **浏览器页（左树右文）**：左侧分组树（当前高亮），右侧渲染选中条目全文（表格化、小节锚点、目录悬浮），顶部锚点导航+"上一条/下一条"。
4. **矩阵页**：n×n网格（行=交付方，列=接收方），有接口则显示数量徽章，点击单元格列出该部门对全部接口；行/列高亮联动；配热力条（参与度三档着色）。
5. **时间轴/甘特页**：横向时间轴总览（分组+菱形里程碑定位），点击出详情卡（进入/退出条件、决策权、必要证据、常见卡点、AI支持点）；提供分组切换。
6. **卡片流页**：统一卡片流，每卡触发/参与者（部门徽章）/关键属性，点击展开完整字段；支持按部门/属性过滤。
7. **治理/驾驶舱页**：RACI总表（A橙实心、R部门色描边、C浅底、I灰字，均带字母）+ 响应等级说明卡 + KPI平衡计分卡（每栏KPI列表+口径标签）+ 升级路径流程图（HTML/CSS/SVG绘制，不用mermaid运行时）。

#### 14.12.5 全局组件规范（固定命名）

以下组件DOM/class命名固定，跨页一致；`components.js`统一渲染导航与页脚，页面不重复实现。

- **顶部导航`.site-header`**：左侧站点名+版本/口径标签；中间页面导航项（当前页橙色下划线指示）；右侧全局搜索框。默认浅色：白底、底部1px`#D6D2CD`；**MAY** 使用半透明暗色 sticky 头（`rgba(11,18,32,.82)` 级）+ 玻璃模糊，但对比度达标且品牌三段细线保留。`position:sticky;top:0`；导航下方品牌橙→黄细线（可用三段实色）。1024px以下折叠为汉堡菜单。
- **页脚`.site-footer`**：版本、编制口径声明（"时间点均为目标/需求口径，非承诺"类表述按报告实际口径写）、页内锚点目录。**每页仅一个全局 `.site-footer`**；NEVER 在页面内的 section/章节级别重复页脚或页码编号。
- **按钮`.btn`**：主按钮`.btn--primary`橙底深字（≥18px加粗可白字）；次按钮`.btn--ghost`/`.btn--outline`白底橙边橙字；危险按钮红边红字（仅风险动作）。hover上浮`translateY(-1px)`+`--shadow-2`，active`scale(.98)`，`:focus-visible` 2px`#407AAA`外描边；过渡150–200ms`ease-out`。
- **卡片`.card`**：白底、1px`#D6D2CD`或无边+`--shadow-1`、8–14px圆角、内边距14–16px；部门相关卡片顶部4px部门色条。hover上浮≤4px+`--shadow-2`。
- **抽屉`.drawer`**：右侧滑出，宽`min(560px,92vw)`，顶部标题栏+关闭按钮，内容区分tab；遮罩`rgba(15,17,21,.32)`，滑入250ms`cubic-bezier(.2,.8,.2,1)`；Esc关闭；焦点圈定在抽屉内。
- **标签/徽章`.badge`**：胶囊999px，12–14px，语义色仅按功能色；部门徽章固定`.badge--MED/--CO/--DMST/--PV`（浅底深字+同族边框）。
- **Tooltip**：深色`#0F1115`底白字12–13px，用于缩写解释；不用`title`属性。
- **表格**：支持横向滚动、粘性表头与首列、行hover浅橙底`#FFF7ED`、可排序列头带箭头；表头`#F79646`白字或深字、隔行`#FBE3D6`/`#FFF`、分隔线1px`#FAC090`。
- **手风琴**：用`<details>/<summary>`（可用`name`互斥），箭头旋转动效。
- **空态/加载态**：骨架屏用`#EEECE1`脉冲，不用花哨loading。
- **状态灯`.kz-lamp`**、**数字滚动`[data-countup]`**、**揭示`.kz-reveal/.kz-reveal-stagger`**：直接复用§14.7.3 C/D的定义，不另写一套。

#### 14.12.6 环境装饰（hero与章节分隔专用）

环境装饰只允许出现在首页hero与章节分隔区，内容阅读区NEVER出现。每处必须`aria-hidden="true"`+`pointer-events:none`，且在`prefers-reduced-motion:reduce`、打印与页面隐藏时停止。

- **粒子网络**：复用§14.7.3 C的`kz-particles`脚本，挂到hero容器；节点≤70、连线距离≤120px、橙色低透明度；IO离屏暂停、`visibilitychange`停帧、`ResizeObserver`重播种。
- **光斑`.kz-ambient`**：`radial-gradient`双色低对比光斑（部门色`color-mix` 4–6%透明度），20s低速漂移（`translate(-3%,2%)`往返），仅装饰。
- **网格底纹**：1px线`rgba(148,163,184,.08)`、48px格距，`mask-image`径向渐隐，opacity≤.35，仅hero。
- **扫光`raySweep`类**：1px高橙色渐变线横扫，仅hero，延迟错开，reduced-motion下`animation:none`。
- 禁止：全站深色主题、整页粒子、视频背景、WebGL、玻璃拟态卡片墙。局部 dark hero + 有限 tilt/glow（`--shadow-brand`）MAY，须 reduced-motion 与导出冻结。

#### 14.12.7 动效规范（站点专用，与§14.7.3共享基线）

- **采用**：CSS自定义属性、grid/flex、`:has()`（选中态联动）、`clamp()`流式字号、`position:sticky`（导航/表头/工具条）、`<details>`手风琴、Popover API（tooltip/过滤面板）、`@starting-style`+`allow-discrete`（抽屉/浮层进场，须有回退）、`color-mix()`（派生hover/浅底，令牌原值兜底）、IntersectionObserver入场reveal（`translateY(8–14px)`+opacity，200–480ms，仅首屏以下元素，`html.js`门控）、URL hash深链、SVG连线与描边流动。
- **谨慎采用**：container queries（卡片内自适应）、View Transitions（页面内视图切换，须`@supports`回退）、scroll-driven animations与anchor positioning（仅增强，`@supports`+JS兜底）。
- **禁止**：重型动画库、3D背景、玻璃拟态卡片、深色模式、自动播放动效（hero粒子除外且可停）、滚动劫持、任何影响阅读的视差。
- 动效只动`transform`/`opacity`（SVG允许`stroke-dashoffset`）；时长：微交互100–200ms、进场250–300ms（`cubic-bezier(.05,.7,.1,1)`或`--ease-out`）、退场200ms；所有动效`prefers-reduced-motion`下关闭；hover反馈必须有（上浮/色变/阴影三选一以上）。
- 键盘可达：所有交互元素可Tab到达、`:focus-visible`可见、抽屉Esc关闭、支持Enter/Space激活。
- 性能：全景页节点+连线用SVG或CSS绘制，交互重绘<16ms；大数据表格避免重复渲染。

#### 14.12.8 数据层规范

- 数据从受控源材料提取生成`data/*.js`，字段结构按页面模式定义（节点/活动/接口/里程碑/AI场景/部门/场景），示例：

```js
window.DATA_STAGES = [{
  id:"G12", name:"招募、预筛选与入排决策", segment:"实施与监查",
  gateOwner:"CO", milestones:["M13","M14","M15"],
  upstream:["G11"], downstream:["G13"],
  departments:{ MED:"lead", CO:"lead", DMST:"support", PV:"consult" },
  activities:[{id:"G12-A01",name:"…",owner:"CO",participants:["MED"],inputs:"…",outputs:"…",system:"EDC/IRT"}],
  ai:[{name:"入排标准逐条预审",grade:"A2",maturity:"M3",humanRole:"关键排除条件100%人工确认",benefitTag:"内部确认"}]
}];
```

- 数据必须与源材料一致，禁止编造；提取后跑一致性自检（实体计数、编号无重号、引用无悬空）。
- 收益/时间类表述一律带口径标签（【内部确认】/【部门需求】/目标口径），并有全局声明"目标口径非承诺"。

#### 14.12.9 响应式与质量底线

- 桌面优先（1280–1920px），1024px以下导航折叠为汉堡菜单；全景页在移动端允许横向滚动+缩放，不强制重排。
- 兼容：新版Chrome/Edge全功能；Safari/Firefox不报错、布局不破。
- 打印：浏览器页与时间轴页提供可用打印样式（隐藏导航/抽屉/工具条）。

#### 14.12.10 站点验收清单（交付前逐项自检并输出结果）

**功能**：页面互通、导航当前态正确、无死链；全景页多层级下钻（L0折叠/L1抽屉/L2六tab/L3内联）全部生效；接口高亮两端+其余降透明；部门/AI/里程碑/控制流过滤全部生效；URL hash可分享定位；全局搜索可命中并跳转；抽屉/手风琴/筛选Esc可关、键盘可达。
**视觉**：配色100%来自令牌；四部门映射无调换；白底≥80%、红色仅风险语义；无文字溢出/卡片错位/表格断列；1280/1440/1920三档宽度检查；阴影/圆角/间距符合令牌；动效克制、reduced-motion生效。
**活基线**：站点 MUST 在品牌克制内"活"起来，不得退回扁平静态页——首页 hero 用 `aria-hidden` 环境层（粒子网络节点≤70+低对比光斑+径向渐隐网格底纹，仅 hero，离屏/隐藏/冻结停帧）+ 特征开场（关键数字带+阅读路径卡+价值链横条，NEVER 居中三件套）；全景/矩阵/时间轴页的节点、单元格、banner、抽屉触发器 MUST 有 hover 反馈（上浮≤4px+阴影/边框色变）+ `:focus-visible` + 键盘可达；scroll-reveal 用 `html.js` 门控 + IO 一次性淡入；关键数字用 `data-countup`；粘性导航+sticky 工具条+滚动高亮；强字号字重对比。所有动效 `prefers-reduced-motion:reduce` 与 `data-export`/`data-qc` 下退化为完整静态终态（粒子 `display:none`、揭示 `opacity:1`、描边画满、数字即真值）。NEVER 极光/玻璃拟态/渐变标题/深色霓虹/整页铺色——白底≥80%、部门色仅作识别与强调。
**内容**：源材料实体全部呈现且无占位符；抽查10处数据与源材料一致；时间表述全部带口径标签；无口号词（赋能/生态/革命/颠覆等）。
**工程**：`file://`直接打开可用；控制台无报错；无远程字体/图片依赖；数据层自检通过；总资源（不含数据）≤100MB。

站点式HTML同样强制§14.10.2内核共享（配色token、字体栈、证据与来源、AI角色边界、占位符清理、受众背景不出现）与§19全部不变量；§7固定chrome、§8页面原型、§13.5页码对站点不适用。



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
