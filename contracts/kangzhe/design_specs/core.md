# 康哲设计规范 · 共享内核 (core)

> **Portable package track pack** · track_id=`core`  
> **Load order**: `ROUTER.md` → `core.md` → **this file** (to EOF).  
> **Assets**: `assets/logo_bot.svg` (relative to `design_specs/`).  
> **Authority**: This pack + `core.md` are the load-time contract for this product. Machine-only samples live in `local_map.md` (optional).  
> **Do not** require reading the legacy monorepo body for this product.

**Also read**: ROUTER.md

---

## Package entry

适用：PPT/PPTX、HTML-PPT、流式 HTML 报告、站点式 HTML、交互单页。
配套：HTML-PPT 翻页运行时可用 peer skill `html-ppt`；PPT 可用 peer `ppt-master` 若已安装——**非本包硬依赖**。
Logo 包内路径：`assets/logo_bot.svg`（SHA-256 `8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae`）。

## 0.5 强制等级定义（Modality）

本文件的主要读者是未来 AI Agent。所有 Agent 必须把本规范当作可执行协议读取。

| 标记 | 中文 | 含义 | 违反后果 |
| --- | --- | --- | --- |
| MUST | 必须 / 不得 | 强制约束 | 阻断交付，必须修正 |
| SHOULD | 应 / 应当 | 强偏好 | 标记为 gap，并说明理由 |
| MAY | 可 / 可以 / 推荐 | 可选行为 | 无阻断后果 |
| NEVER | 严禁 / 绝对不得 | 不可恢复或高风险错误 | 阻断交付，不得绕过 |

Agent 修订或扩展本文件时，引入的新规则必须显式落入 MUST、SHOULD、MAY、NEVER 四类之一。

### 0.6 冲突裁决与按轨阅读清单（v2.1）

当条文冲突时，按下列顺序裁决（高优先在前）：

1. 用户当前指令与本次交付形态（§0 路由表）。
2. 本轨专章：PPT→§13；HTML-PPT→§14.1–§14.9；流式→§14.10；站点→§14.12；交互单页→§14.13。
3. §19 跨 Agent 不变量与 §16.A 可测闸门。
4. **可执行代码块 / 封闭组件合同**（§14.5–§14.7 给出完整 DOM/CSS 者）优于散文描述。
5. 通用 §7/§8 坐标仅适用于 PPT 与 HTML-PPT；不得覆盖流式/站点/交互轨。

**粗细裁决（与 §3.6 一致）**：

- **细（MUST 原样）**：命名组件、chrome/Logo/页脚几何、**§0.8 强调色/副强调/色系**、证据/AI 边界、占位符清理、冻结态。正文灰阶属和谐层，见 §0.8.3。
- **粗（MAY 自创）**：未命名页的信息分组、SVG 隐喻、页数与分页、站点/流式构图；但必须通过本轨验收清单与 §16.A 适用闸门；**粗自由不含改强调色系**：不得改主/副强调 HEX、不得调换部门色、不得自创霓虹强调；正文与中性灰可和谐微调。

**弱模型按轨最小阅读清单（生成前 MUST 读完所列区间到 EOF 或到该节结束）**：

| 交付轨 | 必读 |
| --- | --- |
| 任意轨 | §0 路由 + §0.5–§0.6 + §5 + §10.3 + §19 |
| 可编辑PPT | + §6–§8 + §13 + §16.A pre_delivery |
| HTML-PPT | + §6–§8 + §14.1–§14.9 + §16.A html_ppt |
| 流式HTML | + §14.10 + §14.7.3 D + §16.A 内核闸门 |
| 站点式HTML | + §14.12 + §14.7.3 E + I-61 |
| 交互单页 | + §14.13 + §14.12.2 数据层 |

### 0.7 字号地板权威表（全文件唯一）

| output_type | 正文/标签默认下限 | 表体/轴标签例外 | 参考文献 |
| --- | --- | --- | --- |
| ppt / pptx | 12 pt（标准 14.25 pt） | `data-density=ultra` 且满足 §13.3：≥10.5 pt / 14 px，仅表体与轴标签 | 8 pt |
| html_ppt | 16 px（标准 19 px） | 同上 ultra：≥14 px | 10.67 px |
| html_report（流式） | **16 px**（推荐 clamp 16–18；卡状主文 **SHOULD≥19 px**） | 高密度表 ≥14 px，**NEVER < 13 px** | ≥11 px |
| site_html | 16 px | 高密度表 ≥14 px，**NEVER < 13 px** | ≥11 px |
| interactive | 16 px | 同站点 | ≥11 px |

- §16.A `html_body_min_font`：默认 ≥16 px；仅当 `data-density=ultra` 且满足 §13.3 全部条件时表体/轴标签可 ≥14 px。
- **NEVER** 在 HTML-PPT 普通正文使用 10.5 pt；10.5 pt 仅 PPT 物理画布 ultra 表体。
- 后文凡与本表冲突，以本表为准。



### 0.8 品牌色系强制合同（强调色 / 副强调 / 色系 / 抬头与控件；五轨）

**意图**：锁定康哲品牌**主强调、副强调、部门色系、风险红与面积红线**；并规定**抬头、Logo、主按钮**等可截图验收的可读规则。在此合同内，Agent MUST 自行处理正文/标题/边框/阴影等中性层的和谐关系——**不要把正文默认色卡死成唯一合法 HEX**。

**等级**：
- 主/副强调原值、部门映射、风险红语义、面积红线、抬头与 Logo 可读、主 CTA 字色对比 → **MUST / NEVER（P0）**
- 正文、标题灰、元信息、边框、阴影透明度 → **SHOULD 推荐 token 或和谐变体**；**MAY** 在对比度达标前提下微调

#### 0.8.1 主强调、副强调与风险红（原值不可改）

| 角色 | Token | HEX | 用途 |
| --- | --- | --- | --- |
| **主强调色** | `kz-orange` | `#FF9900` | 顶线、主斜切、主 CTA 实心底、医学主责识别、关键数字强调 |
| **副强调色** | `kz-yellow` | `#FFCC00` | 黄线、副斜切、次级暖强调 |
| ribbon 中段 | `kz-orange-mid` | `#F5A000` | 封面/结束 ribbon 中段（同族） |
| 大编号暖色 | `kz-number` | `#FFA900` | 目录/章节大编号（同族） |
| **风险强调** | `kz-risk` | `#C00000` | **仅**风险/缺口/关键警示/A0 |

- **MUST**：上表 HEX 在 CSS 变量与 PPT 中原值使用。
- **NEVER**：用 `#C0392B`、`#E74C3C`、`#FF6B00`、`#FFB84D` 等冒充主强调或风险红。
- **MAY**：同色相极浅 tint 仅用于 hover 端点；主识别位仍为原值。

#### 0.8.2 部门色系与面积（映射不可调换）

| 色系 | 主色 | 浅底 | 语义 |
| --- | --- | --- | --- |
| 医学 | `#FF9900` | `#FBE3D6` | 医学主责 |
| 运营 | `#407AAA` | `#DCE6F2` | 临床运营（**仅部门语义**，不得作全站默认主调） |
| 数统 | `#587B3B` | `#DCE9C8` | 生物统计和数据管理 |
| PV | `#A85F34` | `#FCF5E6` | 医学安全 |
| 表头暖橙 | `#F79646` | — | 信息表头/证据卡头带 |
| 默认浅底 | `#FFFFFF` 或 `#F8F9FA` | — | 主背景 |

- **MUST**：多部门同页映射固定；白/浅底视口观感 ≥80%；黄橙品牌合计 ≤12%；风险红 ≤3% 且仅风险语义。
- **MUST**：第一眼为**暖白/浅底 + 橙黄识别**，不是冷蓝/navy tech 主调。
- **NEVER**：整页铺橙/黄/红；霓虹/赛博默认色系；深蓝/灰蓝 hero 大面或默认品牌皮肤。

#### 0.8.3 抬头、Logo、主按钮与截图验收（五轨适用处强制）

本节约束**可看见的抬头与控件**，与 §0.8.1 强调色同等执行。

**A. 默认抬头（站点 / 流式 / 交互）**

- **MUST（默认）**：全局 sticky 或顶栏采用**浅底**（`#FFFFFF` / `#F8F9FA`）+ 深色导航字（`#0F1115` / `#404040`）+ 橙激活条或底边识别（`#FF9900`）。
- **NEVER**：把冷蓝、slate-navy、`#0B1220` 一类色块当作**默认品牌抬头**；也不得在未处理 Logo 的情况下使用深色顶栏。

**B. 局部暗顶栏（可选，条件强制）**

- **MAY**：高度 ≤72px 的 sticky 暗顶栏，且仅当同时满足：
  1. 导航/检索文字对顶栏底对比 ≥4.5:1（通常为白字）；
  2. **Logo 可读**：官网 Logo 含深色字标（约 `#3B3938`）时，MUST 使用反白/反色资源，或置于浅色胶囊/白底条上，使字标与有效衬底对比 ≥3:1（优先 ≥4.5:1）；
  3. 暗顶栏不得扩展为 hero 大面或首屏 40%+ 面积的 navy 墙。
- **NEVER**：深色字标 Logo 直接贴在深蓝/近黑顶栏上（实测对比可低于 1.2，字标不可读）。

**C. 主 CTA / 实心强调按钮 / 微标（尺寸无关）**

- **MUST**：凡实心底为 `#FF9900`（或同亮度亮橙）的可读字元——含主 CTA、实心表头、强调胶囊、**RACI/矩阵单字母钮（A/R/C/I）**、阶段 tag、22px 色块徽标、状态 chip——标签字色均为 `#0F1115` 或同等深中性。白字压 `#FF9900` 对比约 2.1，**不合格**；**不得**以「字母太小 / 装饰性 / 矩阵格」豁免。
- **MUST**：按钮与 chip 内文水平、垂直居中（flex `justify-content:center; align-items:center` 或等效 `text-align:center` + line-height）。
- **MAY**：深橙 `#A85F34`、深绿 `#587B3B`、运营蓝 `#407AAA` 实心底上使用白字（对比通常达标）。
- **SHOULD**：描边副按钮用白/浅底 + 橙边 + 可读深橙字（如 `#9A5B00` / `#E69500`），避免浅橙字压浅底。
- **SHOULD**：RACI 医学格若需实心识别，优先浅橙底 `#FBE3D6` + 深橙字，或亮橙底 + 深字；NEVER 亮橙底 + 白字母。

**D. 表头与强调字**

- **SHOULD**：表头用浅橙底 `#FBE3D6`/`#FFF7ED` + 深字，或橙左边线 + 深字；若用实心橙底，字色规则同 **C**（深字）。
- **SHOULD**：大标题默认深中性；橙仅作关键词或装饰线，避免整句大号橙字压白底导致对比不足。

**E. 截图验收（sole review · 细项）**

交付前 MUST 用桌面视口**实渲染截图**逐项检查：

1. Logo 字标在有效衬底上可读（默认浅底；暗顶栏仅当 §0.8.3B）；
2. 抬头非冷蓝/navy 默认色块；
3. 主按钮与所有 `#FF9900` 实心微标为深字且居中；
4. 无低对比灰字、无元素重叠/裁切；
5. 主识别位为合同橙黄。

仅 CSS 变量写了 `#FF9900` 而截图顶栏/Logo/微标失败 → **仍 P0**。

#### 0.8.4 中性层（正文等，非卡死）

正文默认**不是**纯黑 `#000000`；推荐深灰 `#404040` 一带。标题/元信息/边框/阴影为推荐区间，**不因非唯一 HEX 单独失败**。

| 推荐角色 | 推荐区间 | 说明 |
| --- | --- | --- |
| 标题/深字 | `#0F1115` 一带 | 非强制唯一值 |
| 正文 | `#404040` 或 `#3A3A3A`–`#4A4A4A` | 允许和谐深灰 |
| 次要/元信息 | `#595959`–`#808080` | 弱于正文 |
| 边框 | `#AAA6A1` / `#D6D2CD` 或暖灰系 | 与暖色系协调 |

- **MUST**：普通字对底对比建议 ≥4.5:1；中性层不引入冲突冷紫/荧光绿破坏色系统一。
- **MAY**：在强调色固定下调整灰阶与层次。
- **NEVER**：因「规范写了 #404040」拒绝其他可读深灰；**NEVER** 把配色强制误解为正文必须纯黑。

#### 0.8.5 分轨

| 轨 | 强调色/色系/抬头·Logo·CTA | 正文中性层 |
| --- | --- | --- |
| PPT / HTML-PPT | 强制；内容页 chrome 几何强制；Logo 槽浅底可读 | 推荐默认，可读即可 |
| 流式 / 站点 / 交互 | 强制 token、面积、§0.8.3 抬头/Logo/CTA | 鼓励和谐微调 |

#### 0.8.6 冲突裁决

- 改主/副强调、风险红、部门映射、整页铺品牌色、冷蓝默认抬头、Logo 不可读、主 CTA **或任意 `#FF9900` 实心微标**白字压橙 → **P0**。
- 正文灰阶和谐差异 → **不阻断**（可 P3）。
- 创作自由不得覆盖 §0.8.1–0.8.3；**可以**覆盖「正文必须等于某一灰值」的误解。


## 1. 指令优先级与源事实

### 1.1 优先级

1. 系统/开发者/用户当前指令。
2. 用户提供的本次主题、材料、受众、页数、交付格式。
3. 本可分享规范。
4. §1.2指定的康哲官网正式 Logo；用户明确提供的更新版正式品牌资产；其他品牌图片、PPT 母版或既有页面。
5. 已渲染的真实浏览器画面、PPT/PDF截图和结构化证据。

“用户提供的主题/内容”只决定业务文字、页数和要表达的关系，不自动授权改造固定母版。由Agent整理的内容任务书、设计规划或中间brief若写入“目录标题改名”“章节页增加副标题”“结束页更换分隔符”“基础信息表改列数”等内容，与§14硬母版冲突时，必须回到用户原话判断：只有用户明确要求改变该视觉构件时才可覆盖；否则以§14原值为准并修订brief，不得让Agent自生成的派生文件反向覆盖母规范。

若执行环境另有康哲 PPT Master 模板，可将其作为资产来源；模板不能放松本文件的固定画布、字体下限、证据边界和最大化窗口验收要求。若没有模板，直接使用本文件提供的 fallback，不得停在“缺少本机模板路径”。

### 1.2 来源与无依赖声明

本规范由康哲正式汇报模板及医学AI专题汇报样式归纳而来。原始模板、解析文件和内部项目截图只用于形成规范，不是使用本文件的运行依赖。

- **官方Logo唯一下载源**：`https://web.cms.net.cn/wp-content/themes/qnz/assets/img/logo_bot.svg`。该文件是康哲官网发布的SVG，原始`viewBox="0 0 121 25"`；默认用于封面、目录、章节、内容页、结束页和底部ribbon中的Logo槽。
- **MUST**：构建开始时下载该SVG并保存为模块化资产`assets/logo_bot.svg`；HTTP状态必须成功，响应`Content-Type`应为`image/svg+xml`，文件必须含`<svg`及`viewBox="0 0 121 25"`。不得自行描摹、截图、转写文字或用近似图标替代。
- **MUST**：HTML模块化版只引用随包的`assets/logo_bot.svg`；单文件HTML必须把同一SVG内联为`data:image/svg+xml`或`data:image/svg+xml;base64`，PPT/PPTX必须将下载后的SVG作为图片对象嵌入文件。三种交付都不得在浏览时继续访问官网。
- **MUST**：固定Logo外框和`data-qc-id`保持不变，内部`img`使用`width:100%;height:100%;object-fit:contain`；同一份SVG在内容页右上 158×33 full Logo 槽、hero 页放大 wordmark 槽（封面/结束 240×50、章节/目录 200×44）、ribbon 中心槽中等比缩放；hero 页 Logo 渲染宽 MUST ≥ 内容页 full Logo（品牌在 hero 最醒目），但不得裁切、拉伸或改色。
- **MUST**：其他使用者仅凭本文件和上述公开官网地址即可重建品牌骨架；浅色背景和底部ribbon结构仍用§7.4 fallback，但正式交付的Logo必须使用已下载并嵌入的官网SVG。
- **MAY**：只有用户明确提供并确认“替换官网版本”的更新版正式Logo时，才可覆盖上述地址；必须在任务记录中保留来源，最终仍须嵌入而非远程引用。
- **NEVER**：官网暂时不可访问时不得伪造正式Logo或把文字fallback当作最终验收通过；可生成待复核草稿，但正式交付必须在网络恢复后补齐官网SVG并复测。
- **NEVER**：不得在分享文件中写入个人用户名、绝对路径、账号口令、内部项目名称、模型会商记录或制作日志。
- **NEVER**：不得把“来源文件不存在”当作跳过品牌chrome、页面验收或人工复核的理由。

### 1.3 源事实摘要

| 项目 | 规范值 |
| --- | --- |
| 画布 | 16:9，1280 x 720 px，对应 PPT 13.333 x 7.5 inch |
| 页数 | 由用户任务决定；规范提供页面原型，不规定固定总页数 |
| 页面类型 | 封面、目录、章节页、全局规范页、表格页、甘特图页、单竞品结果页、横向对比页、截图证据页、结束页 |
| 主题色显式要求 | `#FF9900`、`#FFCC00` |
| 实际高频设计色 | `#FFFFFF`、`#0F1115`、`#404040`、`#595959`、`#808080`、`#F79646`、`#FBE3D6`、`#FCF5E6`、`#2E7D32`、甘特 `#D9955D`/`#A85F34`/`#9DBB70`/`#587B3B`/`#AAA6A1`/`#F2D2B5`/`#DCE9C8` |
| 字体显式要求 | 微软雅黑 / Arial |
| 源文件观察字体 | Microsoft YaHei、微软雅黑、Arial、等线、少量 Times New Roman |
| 当前执行字号 | 标准正文14.25 pt；流程/甘特/compact正文12 pt；参考文献8 pt |
| 参考文献 | 8 pt，底部边缘区域 |

## 2. 模板标记语义

### 2.1 双 `&&` 是替换占位符

`&&标题&&`、`&&年月&&`、`&&章节1标题&&` 这类文本是内容槽，不是正文。生成最终 PPT/HTML 时必须替换为真实内容，并删除 `&&` 符号。

规则：

- `&&标题&&`：替换为汇报标题，建议 12-22 个中文字符，最多两行。
- `&&年月日&&`：替换为完整日期，例如 `2026年7月5日`。
- `&&年月&&`：替换为年月，例如 `2026年7月`。
- `&&章节N标题&&`：替换为章节标题，不要带序号，序号由版式负责。
- 若内容缺失，不得保留 `&&...&&`，应改为可交付占位文字，如 `待补充数据`，并在备注或交付说明中标明缺口。

最终交付前必须全文搜索 `&&`，搜索结果必须为 0。

### 2.2 双 `@@` 是给 Agent 的内部提示

`@@（表格页示例）@@`、`@@Imagegen生成与主题相关的右半幅图片@@` 这类文本只给生成者看，不能出现在最终投影、PDF、PPT、HTML 或图片截图中。

规则：

- `@@...@@` 可以转化为设计决策、备注或任务清单，但不能作为可见正文。
- 页面标题处出现的 `@@（某某页示例）@@` 必须替换为业务标题。
- 如果 `@@` 中包含生成指令，例如“生成右半幅图片”，执行后删除提示文本。
- 如果无法执行提示，应在最终说明中列为未完成项，而不是把 `@@` 留在页面。

最终交付前必须全文搜索 `@@`，搜索结果必须为 0。

### 2.3 Agent 标记与 Token 速查

#### 2.3.1 占位符

```text
PLACEHOLDER_RE = r'&&([^&]+)&&'
```

- `&&标题&&`：汇报标题，建议 12-22 个中文字符。
- `&&年月日&&`：完整日期，例如 `2026年7月5日`。
- `&&年月&&`：年月，例如 `2026年7月`。
- `&&章节N标题&&`：章节标题，不带序号。

最终交付前 MUST 满足：搜索 `&&` 命中数 = 0。

#### 2.3.2 Agent 内部提示

```text
AGENT_PROMPT_RE = r'@@([^@]+)@@'
```

1. 若是生成指令，执行后删除提示文本。
2. 若是页面占位，替换为真实业务标题。
3. 若无法执行，列为未完成项，不得留在可见页。

最终交付前 MUST 满足：搜索 `@@` 命中数 = 0。

#### 2.3.3 颜色 Token

颜色 Token 名、CSS 变量、HEX 与用途必须保持一致，详见 §5.1、§5.2 与 §14.1。Agent 引用颜色 SHOULD 使用 token 名或 CSS 变量，不应散落新增 HEX。

#### 2.3.4 页面原型名

合法页面原型只有以下 11 种：

```text
cover / toc / section / content / meta_spec / info_table / gantt /
single_result / comparison / evidence / ending
```

页面原型选择见 §8.0。Agent NEVER 自创新原型；无法判断时 MUST 回退到 `content`。

## 3. 总体设计定位

康哲 PPT 是医学部内部汇报系统，用于项目评估、风险判断、进展跟踪与资源配置决策。本规范只约束可执行的设计、写作与校验规则，不添加场景化叙述。

设计原则：

- 医学证据导向，而非装饰导向。
- 品牌识别依靠黄橙斜切、细线、logo、低饱和背景，不铺满大面积品牌色。
- 适合高密度表格、时间轴、竞品矩阵、项目路径、AI 工具流程。

禁止出现：

- 大面积渐变背景、霓虹、花哨科技感。
- 过度圆角卡片堆叠。
- 只有一句 slogan 的空页面。
- 没有来源的数据结论。
- 将“面向董事长/医学部负责人”等受众背景直接写在正文里。
- “AI 替代医学判断”式过度承诺。

### 3.5 五轨关系对照（PPT / HTML-PPT / 流式 / 站点 / 交互单页）

| 维度 | PPT（含 PPT Master） | HTML-PPT（HTML to PPT） | HTML 报告（流式长文档，§14.10） |
| --- | --- | --- | --- |
| 逻辑画布 | 1280×720 单页 | 1280×720 单页（按页渲染/翻页） | 流式/响应式，不强制分页 |
| 配色 token | §5 全量 | §5 + §14.1 CSS 变量 | §5 + §14.1 CSS 变量（仅配色约束） |
| 字体/行距 | §6 全量 | §6 全量 | §6 字体栈 + 行距/段距（仅字体约束） |
| 顶部 chrome/页脚 | §7 强制 | §7 强制（复刻） | 不强制（按报告布局自行决定） |
| 页面骨架/原型 | §8 强制 | §8 强制（逐页套用） | 不强制（§14.10 仅给色彩/间距/字体原则） |
| 证据/来源/AI边界 | §9–§10、§19 强制 | 同左 强制 | 同左 强制（内核一致） |
| 文字内容组织 | §9 底层逻辑 强制 | §9 强制 | §9事实/结论/证据/边界强制；章节顺序与颗粒度按报告需求 |
| 占位符/提示清理 | §2 强制 | §2 强制 | §2 强制 |
| 页码/动画 | §13.5 | §13.5（框架默认必须被主题覆盖为同一格式） | 不适用 |

**内核一致性**：**强调色/色系按 §0.8 强制（五轨）**、字号按 §0.7、证据可回溯、推测显式、AI 边界、`&&`/`@@` 清零。正文中性色允许和谐微调；**主/副强调与部门色系从不随轨放松**。

**五轨速查（版式）**：

| 维度 | PPT | HTML-PPT | 流式 §14.10 | 站点 §14.12 | 交互 §14.13 |
| --- | --- | --- | --- | --- | --- |
| 画布 | 13.333×7.5 in | 1280×720 缩放 | 响应式 | 响应式多页 | 响应式单页 |
| chrome/页脚 | §7 强制 | §7 强制 | 不强制 | 全局 nav/footer，非幻灯片 chrome | 应用壳，非幻灯片 chrome |
| 原型 §8 | 强制 | 强制 | 不强制 | 不强制（用 §14.12.4 模式） | 不强制 |
| 动效 | 静态终态 | 轻量 MAY | 滚动揭示 MAY | 鼓励层次/立体/局部 dark | 过滤/下钻为主 |
| 内核 §10/§19 | 强制 | 强制 | 强制 | 强制 | 强制 |

站点式HTML（§14.12）为第四轨：多页面互通、全局导航与搜索；共享内核与§14.7.3静态基线，不套§8与固定画布。交互单页（§14.13）为第五轨：数据驱动可过滤/下钻看板；数据层同§14.12.2。

### 3.6 AI 创作空间声明（粗细结合原则）

本规范是**粗细结合**的设计合约：

- **粗（适配各种文件、各种主题）**：在硬约束（品牌色占比、字号下限、chrome 几何、证据规则、AI 边界、占位符清理、冻结态）之内，Agent 对**构图、视觉隐喻、SVG 画法、正文/中性灰和谐关系、信息分组、页数**拥有创作自由；**主强调/副强调/部门色系/风险红/面积红线不在自由范围内（§0.8）**。规范列出的"已验证范式"是示例而非穷举——Agent MAY 自创任何通过丰富度闸门的构图。
- **细（必须遵守的细节）**：每页页眉页脚规范（§7/§14.6）、文字段落规范（§6/§10）、语言表达规范（§9/§10.3）、品牌色映射（§5 / §0.8，绝对强制）、Logo 嵌入（§7.4/§14.8）、机器闸门（§16.A）——这些是锁定值，Agent 不得"发挥"。
- **判断标准**：如果一个决定影响"品牌一致性/可读性/证据可信度/无障碍"，它是细的，必须遵守；如果它影响"这页看起来像什么/信息怎么组织/用什么视觉隐喻"，它是粗的，Agent 自由决定，只要通过闸门。命名组件（§14.5–§14.7 给出完整 DOM/CSS 合同者）一律为细：MUST 原样复制 class/几何/字号，不得以创作自由改名或“等价重写”。

规范中任何"只能/必须从以下预设选择"的表述，如果与§16.A 闸门冲突，以闸门为准——闸门是可测的客观标准，预设列表是经验示例。

## 5. 品牌颜色系统

> **品牌色系强制**：主强调/副强调/部门色系/风险红/面积红线见 §0.8（P0）。正文与中性层推荐本章 token，**允许和谐微调**，不因「非 #404040」单独失败。

> 与 §0.8 一并执行：强制强调色系；中性/正文色以和谐与对比度为准。


### 5.1 核心色

| Token | HEX | 用途 |
| --- | --- | --- |
| `kz-orange` | `#FF9900` | 顶部细线、左上斜切、卡片头、风险/行动结构中的主强调 |
| `kz-orange-mid` | `#F5A000` | 封面/结束页底部ribbon的中间橙段 |
| `kz-yellow` | `#FFCC00` | 封面横线、目录/章节下划线、流程节点、次强调 |
| `kz-number` | `#FFA900` | 目录和章节大编号 |
| `kz-deep-text` | `#0F1115` | **推荐**标题/核心标签（可同深度近黑微调） |
| `kz-body` | `#404040` | **推荐**正文（允许和谐深灰，非唯一合法值） |
| `kz-title-gray` | `#595959` | **推荐**次级标题灰 |
| `kz-meta` | `#808080` | **推荐**元信息/弱标签 |
| `kz-risk` | `#C00000` | 风险、缺口、关键警示，不作普通装饰色 |
| `kz-border` | `#AAA6A1` | 卡片、表格、甘特的主分隔线 |
| `kz-border-weak` | `#D6D2CD` | 弱化节点的浅边框 |
| `kz-table-head` | `#F79646` | 信息表表头、证据卡标题带 |
| `kz-table-soft` | `#FBE3D6` | 表格浅橙底、结构化信息块 |
| `kz-table-line` | `#FAC090` | 表格分隔线 |
| `kz-theme-warm-bg` | `#EEECE1` | PPT theme 中的 warm off-white；仅可作备选浅底，不作为默认页面背景 |
| `kz-surface-warm` | `#FCF5E6` | 暖米色 callout/摘要底，不与主背景混淆 |
| `kz-check-green` | `#2E7D32` | 证据链洞察卡中的绿色对勾图标，仅作正向确认 |
| `kz-white` | `#FFFFFF` | 主背景 |

### 5.2 扩展色

| Token | HEX | 用途 |
| --- | --- | --- |
| `kz-med-blue` | `#407AAA` | 医学/AI 辅助信息、对照数据、特殊对比 |
| `kz-blue-soft` | `#DCE6F2` | AI 能力卡、截图解释卡边框或浅底 |
| `kz-stats-green` | `#587B3B` | 生物统计和数据管理部门主色 |
| `kz-stats-soft` | `#DCE9C8` | 数统部门浅底或浅绿阶段条 |
| `kz-pv-brown` | `#A85F34` | 医学安全/PV部门主色 |
| `kz-gantt-phase1` | `#AAA6A1` | Ⅰ期 / 历史已完成 / 低优先级阶段，深色字 |
| `kz-gantt-phase2` | `#F2D2B5` | Ⅱ期（早期进行中），深褐字 `#3C342E` |
| `kz-gantt-phase2-green` | `#DCE9C8` | Ⅱ期 / Ⅱa期（不同竞品分组的浅绿变体），深褐字 `#3C342E` |
| `kz-gantt-phase3` | `#D9955D` | Ⅲ期（核心进行中阶段），深色字 |
| `kz-gantt-nda-orange` | `#A85F34` | NDA / 申报阶段（深橙），白字 |
| `kz-gantt-gray` | `#AAA6A1` | 已完成、历史或低优先级阶段（同 phase1 灰） |
| `kz-gantt-milestone` | `#C00000` | 里程碑小方块（15×15）与关键节点高亮，旁侧标签用 `#24211F` |
| `kz-gantt-text` | `#3C342E` | 浅色阶段条上的深褐正文 |
| `kz-gantt-label-primary` | `#24211F` | 药品名与关键里程碑标签 |
| `kz-gantt-label-secondary` | `#5F5954` | 厂家标签 |
| `kz-gantt-label-tertiary` | `#514B46` | 适应症标签 |

### 5.2.1 医学AI专题页的部门色

涉及多部门流程、责任地图或总甘特时，默认使用以下稳定映射；同一份演示文稿中不得调换：

| 部门语义 | 主色 | 浅底 | 典型用途 |
| --- | --- | --- | --- |
| 医学科学 / 医学主责 | `#FF9900` | `#FBE3D6` | 主阶段条、流程节点、医学写作/入排/监查 |
| 临床运营 | `#407AAA` | `#DCE6F2` | 中心、SSU、运营质量、平台能力 |
| 生物统计和数据管理 | `#587B3B` | `#DCE9C8` 或白底 | 试验设计、样本量、数统审阅、时间线 |
| 医学安全 / PV | `#A85F34` | `#FCF5E6` | ICSR、信号、PSUR/PBRER、法规监测 |
| 未纳入当前建设 / 弱化节点 | `#AAA6A1` | `#FFFFFF` | 只降低边框、编号和文字对比度 |

- 多部门共同负责的节点 MAY 使用双色编号或双层边框；不得增加第五种装饰色。
- 弱化节点 MUST 保持不透明白底；NEVER 对整张卡片设置 `opacity < 1`，否则后方轴线会透出。
- 颜色只表达部门/状态，不同时承担“风险、完成度、优先级”三种语义。

### 5.2.2 前景与背景对比

- 亮橙 `#FF9900` 实心底上的**任意字元** **MUST** 使用 `#0F1115` 或同等深中性。适用范围含：主 CTA、表头实心橙、强调胶囊、**RACI/矩阵 A·R·C·I 字母钮**、阶段/流程 tag、状态 chip、图例色块内文字。白字压 `#FF9900` 对比约 2.1，**NEVER** 作为默认字色；**字号再小也不豁免**。
- 深橙 `#A85F34`、深绿 `#587B3B`、运营蓝 `#407AAA` 实心底上 **MAY** 使用白字（对比通常达标）。
- 浅橙 `#FBE3D6`、浅蓝 `#DCE6F2`、浅绿 `#DCE9C8`、暖米色 `#FCF5E6`、白底上 **MUST** 使用深色文字。
- 不得只用颜色区分信息；至少同时使用文字、边框、线型或位置中的一种（RACI 必须带字母，且字母与底的对比遵守上款）。
- 与 §0.8.3 冲突时以 §0.8.3 为准（抬头 / Logo / CTA / 微标）。

### 5.3 使用比例

- 白色/浅底面积MUST不低于80%。
- 黄橙品牌色合计面积MUST不超过12%，只作识别和强调。
- 红色面积MUST不超过3%，且只能标记风险、缺口或关键结论。
- 单页部门/数据辅助色最多同时出现2种；多部门责任图可使用§5.2.1固定4色，但不得再增加装饰色。
- 不把文字面积纳入填充面积计算；机器无法准确计算时，人工逐页复核。

### 5.4 禁止用法

- 不要把整页背景铺成橙色或黄色。
- 不要用红色标普通重点。
- 不要把模板变成单一黄橙色系；图表可用柔和绿、蓝、灰来分层。
- 不要使用高饱和紫色、霓虹蓝、深夜科技渐变作为康哲默认风格。
- `#EEECE1` 是 theme 里存在的暖白背景色，但默认仍使用 `#FFFFFF`；只有需要区分备份页、附录页或浅色分组背景时才用它。
- `#FCF5E6` 是暖米色 callout 底，仅用于摘要/结论提示块，不用于整页背景或卡片默认底。

## 6. 字体与排版

### 6.1 字体栈

PPT/PPTX：

```text
中文：微软雅黑；英文与数字：Arial
```

HTML/SVG：

```css
:root {
  --font-sans: "Microsoft YaHei", "微软雅黑", "PingFang SC",
    "Noto Sans SC", "Helvetica Neue", Arial, sans-serif;
}
body { font-family: var(--font-sans); }
```

英文参考文献可使用 Times New Roman，但正文中英混排仍优先 Arial。

字体处理规则：

- 新生成内容：中文固定微软雅黑，英文与数字固定Arial。
- 继承模板或源页中的等线：复制为新演示文稿时统一到微软雅黑/Arial；只有用户明确要求保持原页字形时才保留等线。
- 不按 PPTX theme 的 Calibri 默认值生成康哲正文。
- HTML-PPT默认不加载远程Webfont：Windows通常命中微软雅黑，macOS通常命中苹方；Noto Sans SC只作已安装时的后备。
- CSS字体栈按“第一个已安装字体”生效；macOS若安装了微软雅黑，可能优先使用微软雅黑，这有助于与Windows一致，属于允许结果。若项目必须强制苹方，需显式为macOS构建单独字体变量并在两端实测，不能只凭操作系统假设。
- 跨系统目标是“版式、折行和层级一致”，不是字形像素完全一致。不得声称Windows与macOS文字抗锯齿完全相同。
- 单行标题、阶段条和关键标签MUST满足`text_ink_width <= 0.92 × container_clientWidth`，至少保留8%水平余量；`text_ink_width`用文本Range或唯一内层inline span的`getBoundingClientRect().width`测量。`scrollWidth<=clientWidth`只用于裁切检查，不能用于余量计算。Windows与macOS实测新增换行数必须为0。
- 中文字重优先使用400/600/700；NEVER依赖浏览器合成的800/900字重。需要严格跨系统折行时，只能内嵌或随包提供有再分发许可的WOFF2中文字体子集，并保留系统字体fallback。
- 时间轴、季度、页码和数字表格 SHOULD 使用 `font-variant-numeric: tabular-nums;`，避免数字宽度变化造成抖动。
- 重要单行标签 SHOULD 明确设置 `line-height`、`white-space`和容器高度，不依赖字体默认行盒。
- HTML-PPT NEVER 使用按viewport变化的 `clamp()` 缩放正文；逻辑字号固定，统一缩放整个画布。`clamp()`仅用于流式HTML报告。

### 6.2 固定字号

| 层级 | PPT pt | HTML/SVG px | 字重 / 行高 | 用途 |
| --- | ---: | ---: | --- | --- |
| 封面标题 | 42 pt | 56 px | 700 / 1.2 | 固定正式封面 |
| 结束页“谢谢” | 51 pt | 68 px | 700 / 1.2 | 固定结束页 |
| 章节大编号 | 87.75 pt | 117 px | 700 / 1 | 固定章节首页 |
| 章节标题 | 44.25 pt | 59 px | 700 / 1.2 | 固定章节首页 |
| 目录标题 | 36 pt | 48 px | 700 / 1.15 | “汇报章节” |
| 目录条目 | 22.5 pt | 30 px | 700 / 1.2 | 2×2目录卡一级章节名 |
| 目录/章节编号 | 39 pt / 44.25 pt | 52 px / 59 px | 700 / 1 | 目录编号 / 章节页相关编号；章节大编号另见117 px |
| 内容页标题 | 24 pt | 32 px | 700 / 1.2 | 顶部单行标题 |
| 标准卡片标题 | 18 pt | 24 px | 700 / 1.25 | 普通内容卡 |
| Compact卡片标题 | 15 pt | 20 px | 700 / 1.25 | 高密度总览 |
| 标准正文 | 14.25 pt | 19 px | 400 / 1.4 | bullet、表格正文；局部强调改600 |
| 高密度正文/标签 | 12 pt | 16 px | 600 / 1.2 | 流程、甘特、compact卡；阶段条可改700 |
| 参考文献 | 8 pt | 10.67 px | 400 / 1.2 | 底部来源 |
| 页脚 | 13.5 pt | 18 px | 左侧600、右侧页码700 / 1.2 | 部门、年月、页码 |

以上是标准受众内容语义角色的唯一字号值。§14列名的wordmark、Logo fallback、目录meta、流程组件和结论条字号是封闭组件例外，只能在对应组件原值使用，不得外推到普通正文或在多个值中任选。除用户明确要求且本规范先补入完整专用变体外，不用“空间不足”为理由改小；内容放不下时只允许删减、改写、合并或拆页。

HTML-PPT执行口径：除参考文献、纯装饰性标记外，所有受众可见文字的**逻辑字号不得低于16 px**；不能因为在1920×1080上被整体放大就把逻辑字号压到12–14 px。若内容放不下，依次采用删减低价值文字、缩短标签、合并重复信息、拆页，NEVER继续缩字。

### 6.3 行距与段距

- 标题、正文、列表和卡片内段落统一`margin-top:0`；相邻正文段落`margin-bottom:8px`。
- 标准正文行高固定1.4；高密度标签/甘特行高固定1.2；卡片标题行高固定1.25。
- 一级bullet左缩进24 px，二级bullet在一级基础上再缩进24 px；同级bullet垂直间距8 px。
- 每条bullet最多2行；超过2行必须拆成子bullet、卡片或新页。
- 一页不放长段落，优先bullet、短句、表格、证据图。

### 6.4 加粗和强调

- 标题、表格左列、卡片标题使用加粗。
- 正文中可加粗药物名、终点、关键数值、时间点和风险词。
- 红色强调只给“风险/缺口/结论性警示”。
- 不要一整段加粗；管理层读不出重点。

## 10. 文字风格

### 10.1 标题

好标题应包含判断或任务：

- “AI审核可定位证据链，下一步验证中心级汇总”
- “48周Hb维持支持长期疗效，安全性仍需持续跟踪”
- “投后重点转向入组一致性与关键终点窗口”

弱标题应避免：

- “项目背景”
- “研究结果”
- “AI 工具介绍”
- “下一步”

如果只能写主题词，说明内容还没有想清楚。

管理层内容页标题执行规则：

- 标准内容页标题必须单行，推荐12–26个中文字符，并满足`text_ink_width <= 0.92 × container_clientWidth`；放不下时改写、缩短或拆页。只有用户明确授权且本规范已补入完整命名变体时才可双行，当前不得自然换行。
- 每页最多突出一个橙色短语，突出词不超过标题长度的三分之一。
- 默认不显示英文 kicker、`INTEGRATED ROADMAP`、页型编号或制作标签；除非英文是正式业务术语且对理解必要。
- 总览页、甘特页在用户要求中性标题时，可使用“各子系统整体规划”这类明确主题标题，不强行改成承诺式判断。
- 不把“需求书3.1”“方向性计划”“来源等级”“本轮制作”等记录性标签放到可见页面。

### 10.2 Bullet

**强制排版细节（MUST，跨主题跨模型不变——排版可读性属于"细"，锁死；与 §3.6/§14.7.3 的"发挥空间"互补）**：

- **列表化**：≥3 条并列事实/步骤/要点/职责 MUST 用 `<ul><li>` 或 `<ol>` 呈现，NEVER 写成 run-on 散文或顿号串句；单卡并列项 ≥3 而不列表即违规。
- **强调三件套**：需突出的内容 MUST 用其一——`<strong>`/`<b>`（关键数值/结论/角色）、`.kz-em-red`（深红 `#C00000` 加粗，风险/A0 红线/阻断/关键警示）、`.kz-em-underline`（下划线 `text-underline-offset:3px`，术语/定义/需记住的专名）。每张**非纯数字**卡 MUST ≥1 强调标记；纯 stat 卡（仅大数字+单位+caption）豁免。
- **正文底线（全容器，不限 .kz-card）**：所有受众正文容器（`.kz-card,.panel,.rail-item,.cov-row,.stat-strip__item,.slide-body,[data-kz-depth]` 及任何卡状容器）正文/列表 MUST ≥19 px；仅 §6.2 允许的 compact/流程/甘特/表格场景可 16 px/600；NEVER 14 px 正文；卡脚/来源行可 13 px 灰。

每页建议：

- 2-4 个一级 bullet。
- 每个一级 bullet 最多 2 个子 bullet。
- 每条 bullet 以结论、发现或动作开头。
- 单条尽量 15-28 个中文字符；超过 40 个字符应拆分。

推荐句式：

- “已完成 X，当前瓶颈在 Y”
- “数据支持 X，但 Y 仍需源文件确认”
- “与 SOC 相比，主要差异在 X，而非 Y”
- “下一步建议以 X 作为灰盒验证终点”

避免句式：

- “为了更好地……”
- “通过……来……”
- “可以看出……”
- “本页展示了……”
- “不是……而是……”这类对抗感强的标题。

同时避免：

- “推广决策门”“验证门”“上线门”等非自然中文；改为“扩大使用前的判断标准”“进入下一阶段的条件”。
- 为对齐而手工插入大量 `<br>`；优先通过网格、段落间距和自然折行组织层级。
- 把项目说明、写作提示、模型能力、证据等级日志写成正文。
- 对尚未验证的效率、覆盖率和上线时间作确定承诺；应写“部门初步评估、待试点验证”或采用方向性窗口。

父子级表达：一级bullet先给判断或动作，子bullet补充依据、边界或下一步；每个一级bullet最多2个子bullet。若一个卡片内需要3层以上层级，拆卡或拆页。

### 10.3 证据和不确定性

所有医学、临床、注册、市场或竞品结论都要能回到来源。

证据强度从高到低：

1. CSR、SAP、Protocol、监管审评文件、标签、正式指南。
2. 同行评议论文、会议全文、注册库结果。
3. 公司公告、投资者材料、摘要。
4. 新闻、二级数据库、商业报告。
5. 推测和专家判断。

页面应区分：

- 已证实。
- 数据提示。
- 根据 MOA 推测。
- 未公开披露。
- 源文件未提取到。

### 10.3.1 证据等级 IF/THEN 规则

| 证据等级 | 来源类型 | 强制要求 |
| --- | --- | --- |
| 1 | CSR / SAP / Protocol / 监管审评文件 / 标签 / 正式指南 | MUST 注明文件、章节、页码、表号或版本；无需前缀 |
| 2 | 同行评议论文 / 会议全文 / 注册库结果 | SHOULD 注明作者、年份、DOI/PMID/NCT |
| 3 | 公司公告 / 投资者材料 / 摘要 | MUST 前缀“据公司公告：”或“据公司材料：” |
| 4 | 新闻 / 二级数据库 / 商业报告 | MUST 前缀“据公开报道：”或“据二级数据库：” |
| 5 | 推测 / 专家判断 / MOA 外推 / 临床前外推 | MUST 以“推测：”“基于 MOA 推测：”或“专家判断：”开头 |

NEVER 将证据等级 3-5 的内容写成等级 1-2 的确定性结论。若来源无法确认，MUST 降级为“待核实”或“源文件未提取到”。

### 10.3.2 不确定性标签枚举

Agent 标注不确定信息时 SHOULD 使用以下枚举，不得发明含糊标签：

```text
已证实 / 数据提示 / 根据MOA推测 / 未公开披露 / 源文件未提取到 / 待核实
```

### 10.4 参考文献与出处格式

**底部参考文献行的使用边界（强约束）**：页内底部参考文献行 ONLY 用于引用**外部同行评审科学论文、公开法规/指南、公开数据库（ClinicalTrials.gov / PubMed 等）**。引用**内部** SOP、内部说明书、内部章节、内部需求书、会议纪要等，NEVER 生成底部参考文献行——这些内部出处 MUST 写入该页 `<aside class="notes">` 讲者备注，或在正文行内括注"（见§X.X / SOP-XXXX）"，NEVER 占用页脚槽位、NEVER 在页脚插入"依据/来源"中间元素（见 §7.2）。

外部文献底部引用格式：

```text
Author. Title. Journal. Year;Volume:Pages. DOI/PMID/NCT.
```

公开法规/指南：`机构. 文件标题. 版本/年份. 链接或编号。`

字号 8 pt，颜色 `#808080`，位置放正文框底部，**与页脚垂直分离**：参考文献行底边 ≤ y=648，页脚顶边 ≥ y=684，二者 NEVER 重叠或挤压，也 NEVER 与正文最后一行重叠。若引用过长，拆成两行，最多三行；超过三行应放备份页或备注。一条参考文献行不得混入内部出处。无外部文献引用的页，NEVER 出现底部参考文献行。

分享产物中只写可识别的文件名、版本、页码或表号；不得展示个人用户目录和绝对路径。

## 11. 图表与表格规范

### 11.1 表格

- 标准表头与正文固定14.25 pt / 19 px；表头700，正文400，左标签列700。
- 高密度表头与正文固定12 pt / 16 px；表头700，正文600。不得在区间内任选。
- 左列字段加粗，右列写内容。
- 交替底色使用 `#FBE3D6` / `#FFFFFF`。
- 表头底色固定`#F79646`；表格分隔线固定1 px`#FAC090`，不用黑粗线。
- 标准单元格内边距固定`14px 16px`；高密度单元格固定`8px 12px`。

HTML表格必须先做UA reset，避免Chrome/Safari默认`border-spacing`和内容自适应列宽破坏固定栅格：

```css
.kz-table {
  width:100%; table-layout:fixed; border-collapse:collapse; border-spacing:0;
}
.kz-table th,.kz-table td {
  box-sizing:border-box; vertical-align:middle; border:1px solid var(--kz-table-line);
  padding:14px 16px; font-size:19px; line-height:1.4; font-weight:400;
}
.kz-table th { background:var(--kz-table-head); color:var(--kz-deep-text); font-weight:700; }
.kz-table td:first-child { font-weight:700; }
.kz-table tbody tr:nth-child(odd) td { background:var(--kz-table-soft); }
.kz-table tbody tr:nth-child(even) td { background:var(--kz-white); }
.kz-table.dense th,.kz-table.dense td {
  padding:8px 12px; font-size:16px; line-height:1.2;
}
/* 信息表以 §8.6 为唯一权威；禁止 7px 实体左边框与 918/158 旧轨 */
.kz-table.info col:first-child { width:250px; }
.kz-table.info col:last-child { width:917px; }
.kz-table.info tbody tr { height:58px; }
.kz-table.info tbody tr:last-child { height:157px; }
.kz-table.info tbody td:first-child {
  background:var(--kz-table-soft);
  border-left:1px solid var(--kz-table-line);
  box-shadow:inset 7px 0 0 var(--kz-orange);
}
.kz-table.info tbody tr:nth-child(odd) td:last-child { background:var(--kz-table-soft); }
.kz-table.info tbody tr:nth-child(even) td:last-child { background:var(--kz-white); }
.kz-table p { margin:0; }
.kz-table :is(ul,ol) { margin:0; padding-left:24px; }
.kz-table li + li { margin-top:8px; }
```

表格容量规则：

- 标准产品信息表：最多 2 列 x 8 行。
- 竞品对比表：最多5列×8行；超过应拆成“核心结论页 + 备份明细页”。
- 单页同时放多张表时，最多 2 张小表；3 张以上必须改为卡片、分栏或拆页。
- 若列太多，保留与结论直接相关的列，其他列放备份页或备注；不得把正文字号压到 12 pt 以下。
- 表格溢出时优先删减低价值列、拆页、合并相似字段，不通过缩小字号硬塞。

### 11.2 柱状图/森林图/横向对比图

- 坐标轴必须有单位。
- 同一页图表色彩不超过 5 个主色。
- 康哲/本公司资产可用 `#FF9900`，竞品可用灰、绿、蓝。
- 显著性、样本量、时间点要写清。
- 不能把不同时间点或不同人群直接排在一起做强比较，除非标题明确限制。

### 11.3 甘特图

- 年份和 H1/H2 头部必须锁定同一 x 轴。
- 每个阶段条必须对齐时间范围。
- “获批”“NDA”“数据更新”等节点用短标签，不要长句。
- 对预测节点加“预计”或虚线/浅色。

### 11.4 截图

- 截图应有边框或标题标签。
- 重要证据区域可用细红框或橙色框，但不超过 2-3 处。
- 截图文字太小必须放大局部，而不是整张塞入。
- 患者/受试者/中心敏感信息必须脱敏。


### 11.5 SVG 装饰标记防漂移（里程碑/状态点/强调符/箭头）

"元素漂移"指装饰标记（红色里程碑菱形、状态对勾/圆点、强调箭头、A0 红线胶囊、节点编号圆等）在画布缩放或不同视口下相对其宿主图形/文字位移，根因通常是把标记做成**独立于宿主 SVG 的绝对定位 HTML 元素**（CSS `left/top` 像素定位），而宿主图用 `transform:scale()` 或 `viewBox` 缩放，两套坐标系不一致即漂移。规则：

- **同坐标系绘制**：所有装饰标记 MUST 与所标注的节点/线条/区域画在**同一个 `<svg viewBox>` 内**，用相同整数 user-unit 坐标定位；标记与宿主节点共享坐标（节点 `cx/cy` 即标记中心）。NEVER 用 CSS 绝对定位的 HTML `<div>/<span>` 去"贴"在 SVG 节点上。
- **固定整数坐标 + 等比尺寸**：标记的 `x/y/cx/cy/r/width/height` 用整数 user-unit 写死；标记随 viewBox 等比缩放，NEVER 用 `vector-effect` 或 CSS 把标记尺寸钉成与缩放无关的像素。`vector-effect="non-scaling-stroke"` 只允许用于**描边粗细**一致，NEVER 用于位置或填充尺寸。
- **`preserveAspectRatio` 一致**：宿主 SVG 与任何叠加层（若确有）必须同 `preserveAspectRatio`（推荐 `xMidYMid meet`）且共用同一外框矩形；否则禁用叠加层，改在 SVG 内画。
- **最小可读尺寸**：红色/强调标记渲染后 MUST ≥ 8 px（1280×720 逻辑画布下 ≥ 8 user-unit 等效），NEVER 缩到不可见或 1px 杂点。
- **不压字、不越界、不重叠**：标记包围盒 MUST 落在宿主 SVG viewBox 内且落在 `.slide-body`（56,96,1168,564）内；标记 NEVER 与正文/标签文字矩形相交。标注文字与标记间距 ≥ 4 user-unit，`text-anchor` 显式声明（`middle/start/end`），NEVER 依赖默认对齐导致偏移。
- **红色强调克制**：红色 `#C00000` 标记仅用于风险/里程碑/A0 红线语义，单页红色标记 ≤ 6 处；不得用红色做普通装饰。
- **静态可复现**：标记位置不得依赖运行时 JS 测量（getBoundingClientRect 后写 style.left）；必须由静态 SVG 坐标确定，保证截图/导出/冻结态位置一致。

- **SVG 文字渲染像素下限（结果性，跨主题）**：流程/示意图内 `<text>` 在 1280 逻辑画布下**渲染字号** MUST ≥13 px。渲染字号 = `computed font-size(px) × (svg 渲染宽 clientWidth ÷ viewBox 宽)`；作者应让 **viewBox 宽≈图实际渲染面板宽**（1:1 时 user-unit≈px@1280），NEVER 用 1100+ 宽 viewBox 塞进 ~500 px 面板（会把 14 的字缩到 ~6 px 不可读）。**测量口径**：用上述"渲染字号"公式，**NEVER 用 `getBoundingClientRect().height`**——SVG `<text>` 的 getBoundingClientRect 高是字形 ink 盒（14px 字约 10px），会把合格标签误判为不合格。节点名/标签 user-unit≥14、轴/注释≥12（@1:1）。
- **形状词表（图标不"怪"）**：流程节点只用**圆角矩形/圆/菱形**，统一 `stroke-width:2`、矩形 `rx:8`；NEVER 任意 clip-path 多边形/星形/blob/拟物图标。节点填充=部门色或白底+部门色描边，文字居中。
- **红色标记必须有解释**：每个 `#C00000` 标记 MUST 满足其一——①同 SVG 内邻近文字标签（≤40 user-unit）说明含义；②该页含图例 `.kz-legend`（列明每色/形=何义）。无标签且无图例=违规（"不明所以"反模式）。

## 12. 图标、图片与 Imagegen

### 12.1 图标

- 图标只用于辅助识别，不用于装饰堆叠。
- 风格：线性、扁平、单色或双语。
- 默认颜色：`#FF9900`、`#FFCC00`、`#407AAA`、`#808080`。
- 风险图标可用 `#C00000`，但必须对应真实风险。
- 不使用卡通风、表情包、拟物 3D 图标。

### 12.2 图片

图片应服务于内容：

- 封面/结束页：浅色世界地图、医学企业、实验室、真实业务场景。
- 目录页右侧：主题相关机制图、AI 流程图、医学工具场景图。
- 机制页：简洁机制图优于复杂照片。
- 截图页：真实系统/病历/证据截图优于示意图。

不要用：

- 模糊的暗色科技背景。
- 无关的医生握手、实验室 stock photo。
- 过度裁切导致无法辨认的图。

### 12.3 Imagegen 提示

如果需要生成图，提示词应包含：

- Light corporate medical presentation style。
- White background, warm orange and yellow brand accents。
- Minimal vector medical/AI workflow illustration。
- No dense text in image。
- Suitable for 16:9 PowerPoint slide。

生成图不能替代证据图；医学数据、截图、源文件表格必须来自真实材料。

## 16. 质量检查清单

### 16.A 机器可执行检查

Agent MUST 把下列验收合同实现为项目内validator并实际运行后，才能声明“完成”。YAML是机器可转译合同，不是仅供阅读的伪代码。validator逐个遍历`.deck > .slide`，先识别该页唯一master，再在该页`:scope`内解析对应selector；`min_count:1`表示每个已存在的该master实例必须命中1个，不要求每份deck必须拥有所有master。预期实例数大于0时空集合失败；`min_count:0`只用于明确可选槽。overview/presenter克隆一律排除。HTML伪元素按`owner_rect + getComputedStyle(owner,pseudo)`中的left/top/width/height还原逻辑矩形。PPT/PPTX使用同名语义角色读取shape坐标。任一MUST/NEVER断言未通过时，不得声明文件可交付。

```yaml
selector_map:
  content_orange_facet:
    owner: ":scope.content-slide .title-row"
    pseudo: "::before"
    expected_rect: [24, 9, 70, 62]
    expected_background: "#FF9900"
    min_count: 1
  content_yellow_facet:
    owner: ":scope.content-slide .title-row"
    pseudo: "::after"
    expected_rect: [5, 42, 40, 36]
    expected_background: "#FFCC00"
    min_count: 1
  content_top_rule:
    owner: ":scope.content-slide"
    pseudo: "::before"
    expected_rect: [54, 80, 1203, 1.5]
    expected_background: "#FF9900"
    min_count: 1
  content_title_row:
    selector: '[data-qc-id="content-title-row"]'
    expected_rect: [91, 24, 919, 44]
    min_count: 1
  content_logo:
    selector: '[data-qc-id="content-logo"]'
    expected_rect: [1031, 45, 158, 33]
    min_count: 1
  content_body:
    selector: '[data-qc-id="content-body"]'
    expected_rect: [56, 96, 1168, 564]
    min_count: 1
  department_portfolio_layout:
    selector: '[data-qc-id="department-portfolio-layout"]'
    expected_rect: [56, 96, 1168, 564]
    min_count: 0
  content_footer:
    selector: '[data-qc-id="content-footer"]'
    expected_rect: [24, 684.4, 1224, 21.6]
    min_count: 1
  cover_wordmark: {selector: '[data-qc-id="cover-wordmark"]', expected_rect: [52, 48, 240, 50], min_count: 1}
  cover_title: {selector: '[data-qc-id="cover-title"]', expected_anchor: [60, 156], expected_width: 1160, min_count: 1}
  cover_department: {selector: '[data-qc-id="cover-department"]', expected_anchor: [0, 382], expected_width: 1280, min_count: 1}
  cover_date: {selector: '[data-qc-id="cover-date"]', expected_anchor: [0, 468], expected_width: 1280, min_count: 1}
  cover_rule: {selector: '[data-qc-id="cover-rule"]', expected_rect: [280, 538, 720, 4], expected_background: "#FFCC00", min_count: 1}
  cover_ribbon: {selector: '[data-qc-id="cover-ribbon"]', expected_rect: [0, 565, 1280, 155], min_count: 1}
  toc_wordmark: {selector: '[data-qc-id="toc-wordmark"]', expected_rect: [1028, 44, 200, 44], min_count: 1}
  toc_title: {selector: '[data-qc-id="toc-title"]', expected_anchor: [68, 25], min_count: 1}
  toc_rule: {selector: '[data-qc-id="toc-rule"]', expected_rect: [68, 96, 582, 5], expected_background: "#FFCC00", min_count: 1}
  toc_board: {selector: '[data-qc-id="toc-board"]', expected_rect: [68, 178, 1144, 392], min_count: 1}
  section_wordmark: {selector: '[data-qc-id="section-wordmark"]', expected_rect: [1028, 44, 200, 44], min_count: 1}
  section_number: {selector: '[data-qc-id="section-number"]', expected_rect: [108, 112, 260, 117], min_count: 1}
  section_rule: {selector: '[data-qc-id="section-rule"]', expected_rect: [113, 261, 240, 5], expected_background: "#FFCC00", min_count: 1}
  section_title: {selector: '[data-qc-id="section-title"]', expected_anchor: [114, 290], expected_width: 1066, min_count: 1}
  ending_wordmark: {selector: '[data-qc-id="ending-wordmark"]', expected_rect: [52, 44, 240, 50], min_count: 1}
  ending_focus: {selector: '[data-qc-id="ending-focus"]', expected_rect: [340, 220, 600, 200], min_count: 1}
  ending_rule: {selector: '[data-qc-id="ending-rule"]', expected_rect: [380, 450, 520, 4], expected_background: "#FFCC00", min_count: 1}
  ending_meta: {selector: '[data-qc-id="ending-meta"]', expected_anchor: [0, 495], expected_width: 1280, min_count: 1}
  ending_ribbon: {selector: '[data-qc-id="ending-ribbon"]', expected_rect: [0, 565, 1280, 155], min_count: 1}

computed_style_contract:
  slide_background: {selector: ".deck > .slide", background: "#FFFFFF"}
  content_page_title: {selector: ".deck > .slide.content-slide .page-title", font_px: 32, weight: 700, line_height: 1.2, color: "#0F1115", lines: 1, text_ink_ratio_max: 0.92}
  content_body: {selector: ".deck > .slide.content-slide .slide-body", font_px: 19, weight: 400, line_height: 1.4, color: "#404040"}
  content_logo: {selector: ".deck > .slide.content-slide .brand-lockup", font_px: 17, weight: 700, color: "#595959"}
  content_footer_id: {selector: ".deck > .slide.content-slide .deck-footer .footer-id", font_px: 18, weight: 400, color: "#808080", text_regex: "^产品中心-医学部｜20\\d{2}年\\d{1,2}月$"}
  content_footer_number: {selector: ".deck > .slide.content-slide .slide-number", font_px: 18, weight: 700, color: "#FF9900"}
  cover_title: {selector: ".deck > .slide.cover-slide .cover-main h1", font_px: 56, weight: 700, line_height: 1.2, color: "#404040", max_lines: 2}
  cover_wordmark: {selector: ".deck > .slide.cover-slide .cover-wordmark", font_px: 22, weight: 700, line_height_px: 33, color: "#595959", lines: 1}
  cover_department: {selector: ".deck > .slide.cover-slide .cover-department", font_px: 32, weight: 700, line_height: 1.25, color: "#595959", lines: 1}
  cover_date: {selector: ".deck > .slide.cover-slide .cover-date", font_px: 22, weight: 400, line_height: 1.2, color: "#404040", lines: 1}
  toc_title: {selector: ".deck > .slide.toc-slide .toc-title", font_px: 48, weight: 700, line_height: 1.15, color: "#0F1115", lines: 1}
  toc_wordmark: {selector: ".deck > .slide.toc-slide .toc-wordmark", font_px: 22, weight: 700, line_height_px: 33, color: "#595959", lines: 1}
  toc_meta: {selector: ".deck > .slide.toc-slide .toc-meta", font_px: 20, weight: 400, line_height: 1.2, color: "#808080", lines: 1}
  toc_index: {selector: ".deck > .slide.toc-slide .toc-index", font_px: 52, weight: 700, line_height: 1, color: "#FFA900", lines: 1, max_count: 4}
  toc_label: {selector: ".deck > .slide.toc-slide .toc-label", font_px: 30, weight: 700, line_height: 1.2, color: "#0F1115", lines: 1, max_count: 4, text_ink_ratio_max: 0.92}
  section_wordmark: {selector: ".deck > .slide.section-slide .section-wordmark", font_px: 22, weight: 700, line_height_px: 33, color: "#595959", lines: 1}
  section_number: {selector: ".deck > .slide.section-slide .section-number", font_px: 117, weight: 700, line_height: 1, color: "#FFA900", lines: 1}
  section_title: {selector: ".deck > .slide.section-slide .section-title", font_px: 59, weight: 700, line_height: 1.2, color: "#0F1115", max_lines: 2}
  ending_wordmark: {selector: ".deck > .slide.ending-slide .ending-wordmark", font_px: 22, weight: 700, line_height_px: 33, color: "#595959", lines: 1}
  ending_thanks: {selector: ".deck > .slide.ending-slide .ending-thanks", font_px: 68, weight: 700, line_height: 1.2, color: "#595959", lines: 1}
  ending_meta: {selector: ".deck > .slide.ending-slide .ending-meta", font_px: 18, weight: 400, line_height: 1.2, color: "#404040", lines: 1}
  ending_focus: {selector: ".deck > .slide.ending-slide .ending-focus", border_width_px: 0, background: "transparent", box_shadow: "none"}
  ribbon_lockup: {selector: ".deck > .slide :is(.cover-ribbon-fallback,.ending-ribbon-fallback) .ribbon-lockup", font_px: 28, weight: 700, color: "#595959", lines: 1}
  standard_card: {selector: ".deck > .slide.content-slide .kz-card:not(.compact)", radius_px: 8, background: "#FFFFFF"}
  standard_card_title: {selector: ".deck > .slide.content-slide .kz-card:not(.compact) h3", font_px: 24, weight: 700, line_height: 1.25}
  standard_card_body: {selector: ".deck > .slide.content-slide .kz-card:not(.compact) :is(p,li)", font_px: 19, weight: 400, line_height: 1.4}
  compact_card_title: {selector: ".deck > .slide.content-slide .kz-card.compact h3", font_px: 20, weight: 700, line_height: 1.25}
  compact_card_body: {selector: ".deck > .slide.content-slide .kz-card.compact :is(p,li)", font_px: 16, weight: 600, line_height: 1.2}

verification_gates:
  pre_delivery:
    - id: design_spec_read_to_eof
      assert: "Agent read every supplied design/specification file from line 1 through EOF; any truncated read was continued by offset; final generated artifact was read back through EOF"
      severity: MUST
    - id: no_double_ampersand
      assert: 'output.audience_text.regex_search("&&([^&]+)&&").count == 0'
      severity: NEVER
    - id: no_double_at
      assert: 'output.audience_text.regex_search("@@([^@]+)@@").count == 0'
      severity: NEVER
    - id: no_visible_template_literals
      assert: "output.audience_text DOES_NOT contain [汇报主题, 报告标题, 实际汇报短标题, 实际汇报日期, YYYY年M月]"
      severity: NEVER
    - id: page_count_match
      when: "output_type IN [ppt, pptx, html_ppt]"
      assert: "output.slide_count == expected_count"
      severity: MUST
    - id: chrome_on_content_pages
      when: "output_type IN [ppt, pptx, html_ppt]"
      assert: "ALL slides WHERE archetype IN [content, info_table, gantt, single_result, comparison, evidence] HAVE [orange_facet, yellow_facet, top_rule, page_title, full_logo, content_body, footer, page_number]"
      severity: MUST
    - id: exclusive_page_master
      when: "output_type IN [ppt, pptx, html_ppt]"
      assert: "EACH slide MATCHES exactly_one_of [cover, toc, section, content, ending]"
      severity: MUST
    - id: non_content_has_no_content_chrome
      when: "output_type IN [ppt, pptx, html_ppt]"
      assert: "ALL slides WHERE master IN [cover, toc, section, ending] DO_NOT_HAVE [orange_facet, top_rule, deck_footer, slide_number]"
      severity: NEVER
    - id: no_meta_spec_in_final
      when: "output_type IN [ppt, pptx, html_ppt]"
      assert: "NO slide WHERE archetype == meta_spec"
      severity: NEVER
    - id: no_fullpage_brand_bg
      assert: "NO audience_surface HAS full_background_fill IN [kz-orange, kz-yellow, kz-risk]"
      severity: NEVER
    - id: ppt_body_min_font
      when: "output_type IN [ppt, pptx]"
      assert: "ALL text_elements WHERE role == body HAVE font_size_pt >= 12"
      severity: MUST
    - id: html_body_min_font
      when: "output_type IN [html_ppt, html_report]"
      assert: "ALL audience_text WHERE role IN [body,label] HAVE computed_font_size_px >= 16; exception: data-density=ultra AND §13.3 conditions => body-cell/axis-label >= 14"
      severity: MUST
    - id: html_reference_min_font
      when: "output_type IN [html_ppt, html_report]"
      assert: "ALL audience_text WHERE role == reference HAVE computed_font_size_px >= 10.67"
      severity: MUST
    - id: title_not_weak_noun_phrase
      when: "output_type IN [ppt, pptx, html_ppt]"
      assert: "ALL content_slides.title NOT IN [项目背景, 研究结果, AI工具介绍, 下一步, 情况概述, 总结]"
      severity: MUST
    - id: clinical_claim_sourced
      assert: "ALL text_elements WHERE contains_clinical_claim HAVE source_reference != null"
      severity: MUST
    - id: speculation_prefixed
      assert: "ALL text_elements WHERE evidence_level == 5 START_WITH [推测, 基于MOA推测, 专家判断]"
      severity: MUST
    - id: risk_red_bounded
      assert: "ALL uses_of(#C00000) ARE risk_label OR gap_indicator OR critical_conclusion"
      severity: MUST
    - id: ai_role_disclaimed
      assert: "ALL AI_related_pages_or_blocks DO_NOT contain [AI自动判断, AI替代医学判断, AI自动审核]"
      severity: NEVER
    - id: ai_human_review_present
      assert: "ALL AI_related_pages_or_blocks CONTAIN one_of [医学经理终审, 医学人工复核, 人工复核]"
      severity: MUST
    - id: no_audience_meta_in_body
      assert: "output.audience_text DOES_NOT contain [面向董事长, 面向医学部, 面向领导, 面向负责人]"
      severity: NEVER
  html_ppt:
    - id: fixed_master_geometry
      assert: "ALL present selector_map entries MATCH expected_rect OR expected_anchor/expected_width within 0.5 logical px AND expected_background when declared; ANY required selector empty FAILS"
      severity: MUST
    - id: fixed_master_computed_style
      assert: "ALL present computed_style_contract entries MATCH font/weight/line-height/color/radius/background/line-count/count/text-ink limits"
      severity: MUST
    - id: fixed_master_collision_free
      assert: "cover title/department/date/rule/ribbon; toc title/meta/board/wordmark; section number/rule/title/wordmark; ending wordmark/focus/rule/meta/ribbon ARE pairwise non-overlapping except intentional background containment"
      severity: MUST
    - id: toc_semantic_integrity
      assert: "toc_board_rect==[68,178,1144,392] AND count(.toc-item) IN [2,3,4] AND EACH .toc-item HAS nonempty .toc-index AND nonempty .toc-label AND NO empty card-like element exists"
      severity: MUST
    - id: ending_focus_invisible
      assert: "ending_focus_rect==[340,220,600,200] AND border_width==0 AND background_color==transparent AND box_shadow==none"
      severity: MUST
    - id: html_ppt_logical_canvas
      assert: "active_slide.offsetWidth == 1280 AND active_slide.offsetHeight == 720"
      severity: MUST
    - id: active_slide_count
      assert: "count(.deck > .slide.is-active) == 1"
      severity: MUST
    - id: inactive_slides_not_rendered
      assert: "FOR EACH .deck > .slide:not(.is-active), computed display=='none' OR visibility=='hidden' OR opacity==0; inactive slides MUST NOT remain visually stacked behind/over the active slide"
      severity: MUST
    - id: content_body_fixed_rect
      assert: "ALL content_slide .slide-body normalized_rect == [56,96,1168,564] within 0.5 logical px"
      severity: MUST
    - id: content_vertical_utilization
      assert: "FOR EACH content_slide, max(normalized_bottom of audience-visible .slide-body descendants excluding backgrounds/notes) >= 560 AND <= 660"
      severity: MUST
    - id: department_portfolio_integrity
      when: "slide CONTAINS .department-portfolio-layout"
      assert: "department_portfolio_layout_rect==[56,96,1168,564] AND count(.dept-portfolio-card)==4 AND department_card_grid_columns ARE_EQUAL AND card_grid_height==420 AND content_conclusion.bottom==660 AND content_conclusion.background==#FCF5E6"
      severity: MUST
    - id: fixed_info_table_integrity
      when: "slide CONTAINS .kz-table.info"
      assert: "count(tbody tr)==8 AND count(tbody td)==16 AND table_rect==[56,96,1168,564] AND table.bottom==660 AND NO audience-visible sibling exists after table inside .slide-body"
      severity: MUST
    - id: section_data_title_integrity
      when: "slide MATCHES .section-slide"
      assert: "slide.dataset.title == section_title.textContent.trim()"
      severity: MUST
    - id: hash_navigation_contract
      assert: "direct_open('#/5').active_slide_index==5 AND keyboard_next.hash=='#/6' AND click_next.hash=='#/7' AND runtime NEVER writes '#N'"
      severity: MUST
    - id: deck_wrapper_contract
      assert: "document CONTAINS exactly one .deck AND count(.deck > .slide)==planned_page_count AND NO .slide EXISTS outside .deck AND .deck.parentElement.tagName=='BODY'"
      severity: MUST
    - id: inactive_slides_hidden
      assert: "ALL .slide:not(.is-active) HAVE computed visibility=='hidden' AND pointer-events=='none'; .slide.is-active HAS visibility=='visible' AND pointer-events=='auto'"
      severity: MUST
    - id: content_slide_richness
      when: "slide MATCHES .content-slide"
      assert: "FOR EACH active content_slide: (a) NO empty horizontal band taller than 120px spanning >=70% of .slide-body width (dead-band); (b) CONTAINS >=1 living visual = <svg> rendered width>=0.5*slide-body OR .kz-drawon OR [data-countup]; (c) type hierarchy: an element font-size>=32px AND an element <=14px; (d) FOR EACH card-surface in {.kz-card,.panel,.rail-item,.cov-row,.stat-strip__item,.dept-portfolio-card,[data-kz-depth='1']}: (box-shadow!='none' OR border-top-width>=3px) [depth baseline, no flat white block] AND identity bar (border-top>=3px or ::before>=3px non-transparent) AND mid anchor (svg/.kz-drawon/[data-countup]/.kz-lamp/.dept-chip/.badge; 4px bar alone NOT enough) AND (non-numeric card => >=1 emphasis mark strong/.kz-em-red/.kz-em-underline); (e) NOT dead equal-card row (3+ equal-width card-surfaces, per-box content height<55% box height, mid text-only); (f) ALL body text in card-surfaces computed font-size>=16 (>=19 unless compact per §6.2); (g) >=3 parallel points in any container use <ul>/<ol> not run-on prose. A single full-bleed living visual satisfies (b),(d-mid),(e) by construction."
      severity: MUST
    - id: hero_logo_dominant
      assert: "rendered width of cover/section/ending wordmark img >= rendered width of content-slide .brand-lockup img (hero brand MUST be the largest logo, >=158px); content brand-lockup stays the compact full-logo"
      severity: MUST
    - id: svg_text_legible
      assert: "ALL svg <text> in content slides have rendered_font_size = computed_font_size_px * (svg_clientWidth / viewBox_width) >= 13 at 1280 logical canvas (NEVER use getBoundingClientRect().height as the size measure — for svg text it returns the glyph ink box, not the font size); flow nodes use only rounded-rect/circle/diamond shapes"
      severity: MUST
    - id: red_marker_explained
      assert: "EACH #C00000 marker (polygon/circle/rect/path) HAS either a same-svg text label within 40 user-units OR the slide CONTAINS a .kz-legend enumerating marker meanings; unexplained red marker = violation"
      severity: MUST
    - id: presenter_runtime_and_notes
      when: "delivery_mode == html-ppt"
      assert: "deck embeds a presenter runtime (key 'S' opens window/overlay with current+next preview + speaker script + timer; arrows sync; 'R' resets; 'N' notes) AND EVERY slide CONTAINS aside.notes with 150-300 CJK chars of colloquial speaker script"
      severity: MUST
    - id: footer_two_slots
      when: "slide MATCHES .content-slide"
      assert: ".deck-footer has EXACTLY 2 audience-visible child slots = one .footer-id + one .slide-number; .footer-id textContent MATCHES regex /^产品中心-医学部｜20\\d{2}年\\d{1,2}月$/ AND computed color==rgb(128,128,128) AND font-weight==400; .slide-number computed color==rgb(255,153,0); .deck-footer CONTAINS NO third audience-visible child AND NO descendant whose text contains 依据|来源|对应SOP|对应 SOP|SOP-|§"
      severity: MUST
    - id: presenter_identity_locked
      assert: ".cover-department textContent=='产品中心-医学部' AND .ending-meta textContent MATCHES /^产品中心-医学部 · 20\\d{2}年\\d{1,2}月$/ AND NO slide uses the source-document owner/编制部门 as the department identity"
      severity: MUST
    - id: footer_no_overlap_with_reference
      when: "slide MATCHES .content-slide AND slide CONTAINS a bottom reference line"
      assert: "reference_line.bottom <= 648 AND .deck-footer.top >= 684 AND reference_line rect DOES_NOT_INTERSECT .deck-footer rect AND reference_line DOES_NOT_INTERSECT last body text line"
      severity: MUST
    - id: markers_inside_host_svg
      assert: "ALL decorative markers (milestone diamonds / status dots / accent arrows / numbered circles / red emphasis shapes) ARE descendants of the same <svg> whose viewBox they use (NOT CSS-absolutely-positioned HTML overlays pinned to chart nodes); each marker bbox within its host svg viewBox AND within .slide-body rect [56,96,1168,564]; marker rendered size >= 8px"
      severity: MUST
    - id: no_text_overflow
      assert: "ALL audience-visible text nodes (titles, card text, table cells, svg <text>, footer, labels, badges) HAVE scrollWidth<=clientWidth+1 AND scrollHeight<=clientHeight+1 (no clipped/overflowing text); svg <text> MUST NOT exceed its viewBox width given its text-anchor; NEVER mask clipping with overflow:hidden"
      severity: NEVER
    - id: no_element_overlap
      assert: "FOR EACH slide, audience-visible sibling blocks (cards, panels, svg hosts, tables, conclusion bar, footer, chrome, markers) pairwise DO_NOT_INTERSECT except explicitly allowed background/connector layers marked data-qc-overlap=allow; marker-vs-text and footer-vs-body intersections count as violations"
      severity: NEVER
    - id: heading_no_vertical_clip
      assert: "ALL h1,h2,h3,h4 with computed font-size>=32px EITHER have computed line-height>=font-size*1.3 OR computed overflow=='visible'; if neither, scrollHeight MUST <= clientHeight+1"
      severity: MUST
    - id: cover_ambient_layer
      when: "slide MATCHES .cover-slide"
      assert: "cover CONTAINS (canvas.kz-particles OR .kz-ambient OR .cover-hero::before grid/glow) AND that layer HAS aria-hidden=='true' AND pointer-events=='none'; ambient/particles MUST NOT appear on toc/section/content/ending slides"
      severity: MUST
    - id: section_has_lead
      when: "slide MATCHES .section-slide"
      assert: "section_slide CONTAINS a visible (display!=none AND visibility!=hidden AND not .notes) lead line of font-size>=18px and <=2 lines below the section title"
      severity: MUST
    - id: uniform_scale_formula
      assert: "abs(deck_rect.height/720 - min(viewport_css_width/1280, viewport_css_height/720)) <= 0.001"
      severity: MUST
    - id: centered_scaled_canvas
      assert: "abs(deck_center_x-viewport_center_x) <= 0.5px AND abs(deck_center_y-viewport_center_y) <= 0.5px"
      severity: MUST
    - id: logical_aspect_ratio
      assert: "abs(deck_width/deck_height - 16/9) <= 0.001"
      severity: MUST
    - id: no_viewport_dependent_reflow
      assert: "normalized_rects_and_line_counts(data-qc-id) ARE_EQUAL across 1280x720, 1920x1080, 2048x1024 within 0.5 logical px"
      severity: NEVER
    - id: cross_os_line_count_and_clipping
      assert: "Windows_Chrome_or_Edge AND macOS_Chrome_and_Safari HAVE identical line_counts for same data-qc-id AND clipped_text==0; computed_font_family recorded"
      severity: MUST
    - id: no_document_or_slide_overflow
      assert: "document_scroll_delta == [0,0] AND active_slide.scrollWidth<=1280 AND active_slide.scrollHeight<=720"
      severity: MUST
    - id: content_descendant_containment
      assert: "ALL audience-visible descendants of .deck > .slide.content-slide .slide-body EXCEPT allowed background/notes HAVE normalized bounding rect inside [56,96,1224,660] AND DO_NOT_INTERSECT [title_row,logo,footer]"
      severity: NEVER
    - id: no_text_clipping
      assert: "ALL visible_text NOT allowlisted HAVE scrollWidth<=clientWidth AND scrollHeight<=clientHeight"
      severity: NEVER
    - id: html_visible_font_floor
      assert: "ALL audience_text EXCEPT reference HAVE computed_font_size_px>=16; reference>=10.67"
      severity: MUST
    - id: fonts_and_images_ready
      assert: "document.fonts.status=='loaded' AND target_font_check==true AND ALL images complete AND naturalWidth>0"
      severity: MUST
    - id: official_logo_embedded
      assert: "ALL required wordmark/full-logo/ribbon-logo slots CONTAIN the same official logo_bot.svg content; modular delivery uses only packaged assets/logo_bot.svg; single_file uses only data:image/svg+xml or data:image/svg+xml;base64; PPT/PPTX embeds the SVG; final runtime makes zero requests to web.cms.net.cn"
      severity: MUST
    - id: gantt_column_integrity
      assert: "ALL timeline_rows HAVE expected_period_count AND max_column_width_spread<=0.5 logical px"
      severity: MUST
    - id: named_component_selector_integrity
      when: "slide CONTAINS .portfolio-gantt"
      assert: ".portfolio-gantt.tagName=='DIV' AND its direct children MATCH .portfolio-head + .portfolio-group* AND DOM CONTAINS exact selectors [.portfolio-head,.portfolio-group,.portfolio-dept,.portfolio-tracks,.portfolio-track,.track-label,.track-time] AND every timeline item MATCHES one_of [.road-bar,.road-milestone,.road-pv] AND DOM/CSS DOES_NOT use replacement aliases [.bar,[class^='gantt-group'],[class*=' gantt-group']] AND computed font-size of .road-bar/.road-milestone/.road-pv >=16px"
      severity: MUST
    - id: gantt_boundary_alignment
      assert: "header, department boundary, timeline start and every period boundary errors <=0.5 logical px; ALL bars scrollWidth<=clientWidth"
      severity: MUST
    - id: gantt_empty_milestone_dom
      assert: "ALL .portfolio-group.operations .road-milestone AND .portfolio-group.statistics .road-milestone HAVE textContent.trim()==''; accessible name MAY come only from aria-label"
      severity: MUST
    - id: comparison_matrix_integrity
      when: "slide CONTAINS .responsibility-layout"
      assert: "count(.rc-head)==3 AND count(.rc-cell)==9 AND responsibility_matrix_rect==[56,96,1168,432] AND responsibility_conclusion.bottom==616 AND clipped_text==0"
      severity: MUST
    - id: evidence_chain_integrity
      when: "slide CONTAINS .evidence-layout"
      assert: "evidence_layout_rect==[56,96,1168,564] AND evidence_chain columns==[360,48,360,48,352] AND count(.evidence-connector)==2 AND all connector arrows horizontal AND all evidence descendants scrollHeight<=clientHeight"
      severity: MUST
    - id: title_logo_and_body_footer_separation
      assert: "page_title_rect DOES_NOT_INTERSECT logo_rect AND content_body.bottom<=660 AND content_body DOES_NOT_INTERSECT footer_rect"
      severity: MUST
    - id: weakened_card_opaque
      assert: "ALL .chain-node.off HAVE opacity==1 AND computed backgroundColor==rgb(255,255,255) AND backgroundImage==none"
      severity: MUST
    - id: forbidden_generic_utilities_absent
      assert: ".deck > .slide HAS no forbidden class/data tokens listed in §14.2"
      severity: NEVER
    - id: no_runtime_errors
      assert: "page_errors==0 AND console_errors==0"
      severity: MUST
    - id: final_script_closing_tag
      assert: "final_html HAS literal '</script>' for every inline script AND DOES_NOT use '<\\/script>' as an actual element closing tag"
      severity: MUST
    - id: motion_frozen_stable_state
      when: "html.dataset.export=='true' OR html.dataset.qc=='true'"
      assert: "ALL elements HAVE computed animation=='none' AND transition_duration=='0s' AND transform=='none' AND ALL .kz-drawon strokes HAVE stroke-dashoffset==0 AND [data-countup] textContent EQUALS final true value"
      severity: MUST
    - id: motion_progressive_enhancement
      when: "prefers-reduced-motion==reduce OR html LACKS .js class"
      assert: "ALL audience content VISIBLE at full opacity WITHOUT animation AND [data-countup] shows final value"
      severity: MUST
    - id: glass_scope_compliant
      when: "uses .kz-glass"
      assert: "EVERY .kz-glass computed background-color alpha >= 0.88 (white or brand-tint) AND backdrop-filter blur <= 12px AND 1px border present AND count per viewport <= 4 AND NEVER on table/evidence/gantt/numeric surfaces; frozen/RM -> backdrop-filter none + opaque bg"
      severity: MUST
    - id: soft_scope_compliant
      when: "uses .kz-soft"
      assert: "EVERY .kz-soft has dual shadow PLUS 1px border or top bar (I-72 perceivable hierarchy); NEVER on table/evidence/gantt/numeric surfaces"
      severity: MUST
    - id: stream_body_floor
      when: "delivery_mode in (stream, site)"
      assert: "ALL main/section/article p and li (excluding .kz-card-foot/.footer-id/.slide-number/.kz-legend/.kz-tip/.kz-lamp/.kz-crumb/figcaption/caption/small/time/.kz-badge/nav links) computed font-size >= 19px at every viewport"
      severity: MUST
    - id: stream_hero_ambient
      when: "delivery_mode in (stream, site)"
      assert: "hero/first-screen contains an aria-hidden ambient layer (canvas particles or glow/grid, .kz-ambient or equivalent) AND no other section has it"
      severity: MUST
    - id: svg_internal_no_overlap
      assert: "EACH svg: pairwise bbox intersection area == 0 among visible texts/node shapes/markers (exempt line-endpoint, background-foreground, intended containment); timeline/gantt axis vs track cards vs tick text included"
      severity: MUST
    - id: marker_snapped_to_anchor
      assert: "EACH decorative marker (red diamond/milestone/status dot) center coincides with its annotated node center OR lies on its axis/track centerline (deviation <= 2 user-units) OR aligns a tick column; NEVER floating between two rows/tracks or outside the figure"
      severity: MUST
    - id: legend_semantic_labels
      assert: "EVERY .kz-legend entry label is a semantic term (milestone/red-line/risk/status); NEVER a bare shape name (red diamond/blue circle/square) as the sole label; every red marker has a semantic label within 40 user-units or a legend entry"
      severity: MUST
    - id: site_nav_and_search
      when: "delivery_mode == site"
      assert: "ALL pages share .site-header/.site-footer with correct current-page indicator AND global search jumps to target page with highlight AND zero dead links AND zero console errors"
      severity: MUST
    - id: standalone_has_no_external_requests
      when: "delivery_mode == single_file"
      assert: "ALL requests ARE current_html_same_path_with_optional_query_or_hash OR data: OR runtime_created_blob:"
      severity: NEVER
    # HTML报告（§14.10）与站点式HTML（§14.12）豁免chrome、page_count、meta_spec等版式骨架闸门；
    # 但占位符、来源、推测、风险红、AI角色和受众元信息仍强制。站点式HTML额外执行site_nav_and_search。
```

占位符检查必须只扫描受众可见文本或序列化后的正文DOM，排除`<script>`、`<style>`、注释和规范示例；否则JavaScript逻辑运算符会造成误报。

人类审查项（投影可读性、标题语气、医学证据充分性、口径统一）见 §16.1-§16.3。

### 16.1 视觉检查

- 画布为 16:9。
- 最大化桌面浏览器中画布按比例居中；页面内部不因窗口宽高比改变而重排。
- 封面/结束页与内容页使用正确的不同结构。
- 内容页顶部 chrome 完整。
- 品牌色只作强调，没有大面积滥用。
- 字号：主正文固定14.25 pt / 19 px；只有流程、甘特、compact卡使用12 pt / 16 px；参考文献8 pt / 10.67 px。
- 图表和截图在投影距离下可读。
- 表格没有拥挤到需要眯眼阅读。
- 页脚不遮挡引用。
- 原始分辨率逐页图中，核心内容自然使用页面下半部，没有非设计性大空白。
- 内容卡不得读起来"扁平/模板化"：每张内容卡 MUST 带一条彩色身份顶条 + 一个中段视觉锚点（描边迷你图/数字滚动/徽章或状态灯簇），同页多卡用不同部门色形成节奏；封面 MUST 有环境深度层（粒子/光斑/网格底纹，aria-hidden）；NEVER 出现"三张等大白卡+顶部堆文字+中段空白"的模板布局。丰富度只来自层次、色条、微动效与字号字重对比，NEVER 来自极光/玻璃/渐变标题/深色霓虹（这些仍被§5与§14.7.3 G 禁止）。

### 16.2 内容检查

- 每页有明确结论或任务。
- 每个数据和医学结论有来源。
- 推测、未披露、待核实被明确标注。
- AI 工具页保留医学人工复核边界。
- 没有把受众背景、写作提示或作者提示放入正文。
- 没有使用对抗感强、容易引发反感的标题。

### 16.3 技术检查

- 搜索 `&&` 为 0。
- 搜索 `@@` 为 0。
- PPTX 能打开。
- HTML 能本地打开并键盘翻页。
- 渲染截图页数等于预期页数。
- 图片没有丢失链接。
- 参考文献没有超出页面。
- 若使用 PPT Master，运行相应 quality checker 或导出检查。
- 若使用 HTML-PPT，必须在`1280×720`、`1920×1080`、`2048×1024`和用户实际最大化窗口逐页检查；contact sheet只作总览，不能替代原图。
- 单文件HTML必须经`file://`直接打开，外部渲染资源请求为0；Chromium与WebKit均无console/page error。

> 机器可执行检查（占位符搜索、chrome 完整性、字号下限、证据来源等）见 §16.A；本节保留必须由人工完成的视觉验收项。

### 16.4 构建后强制 QC 与修复闭环（所有 HTML 轨 MUST 执行，带失败交付=不合格）

构建完成后，Agent MUST 在真实浏览器（headless Chromium 可）逐项实测以下五项；任一失败 MUST 按修复策略修改并复测，**循环至全过**；修复轮数≤3，仍失败 MUST 降级图表（减节点/改列表/拆页）达成，NEVER 带已知失败交付，NEVER 以"视觉问题"为由豁免。QC 结果随交付输出（逐项 pass/fail + 修复记录）。

1. **文字溢出（逐节点）**：对每个受众可见文本容器（p/li/标题/span/`.kz-lamp`/胶囊/结论条/表单元格/svg `<text>`）断言 `scrollWidth<=clientWidth+1 && scrollHeight<=clientHeight+1`；svg `<text>` 另断言 getBBox() 不超 viewBox 宽、且不超宿主卡/面板 rect。修复：缩短措辞→换行（line-height≥1.3）→扩容器→拆卡；NEVER 用 `overflow:hidden` 或降字号到下限以下掩盖。
2. **SVG 内部重叠（pairwise）**：每个 `<svg>` 内取可见元素集（text、节点形状 rect/circle/polygon、标记），两两 getBBox() 相交面积 MUST ==0（豁免：连线/箭头与节点端点、背景与前景、有意包含）。重灾区 MUST 重点测：时间线/甘特的轴（line）vs 轨道卡 vs 刻度文字；流程图节点 vs 标签 vs 分支箭头。修复：换泳道/加行距/标签外移带引导线/缩短标签。
3. **标记锚点对齐**：每个装饰标记（红菱形/里程碑/状态点/箭头）MUST 满足其一：①中心与所标注节点中心重合（距离≤节点半径）；②中心落在所属轴/轨道中线（垂直偏差≤2 user-unit）；③与时间刻度列对齐。NEVER 悬空于两行之间、两轨之间或图外。修复：整数 user-unit 坐标 snap 到锚点（I-66）。
4. **图例语义**：`.kz-legend` 每条 MUST 为"形状/颜色 = 语义"格式（如 ◆ = 里程碑/红线节点），标签 MUST 是语义词（里程碑/红线/风险/已完成/进行中）；NEVER 以裸形状名（"红色菱形""蓝色圆""方块"）作为唯一标签。每个红标 MUST 有 40 user-unit 内语义标签或图例条目。
5. **文字与 SVG 互叠**：受众文本块（标题/卡正文/结论条/caption）rect 与任一 svg text/标签 bbox 相交面积 MUST ==0（svg 自身容器除外）。修复：svg 标签移入图内留白/文本块移位/加间距。

## 19. 跨 Agent 不变量（Cross-Agent Invariants）

以下规则对所有使用本规范的 Agent 都生效，无论其是 PPT Master、HTML-PPT、HTML to PPT，还是未来新增 Agent。各 Agent 专属章节（§13、§14 或未来章节）只允许细化，不得放松以下规则。

| 编号 | 不变量 | 等级 |
| --- | --- | --- |
| I-01 | `&&` / `@@` 搜索结果为 0 才算完成 | NEVER |
| I-02 | 内容页必须保留 §7.1 顶部 chrome（橙斜切、橙线、标题、logo） | MUST |
| I-03 | 字号地板以 §0.7 为唯一权威（PPT≥12 pt；HTML-PPT≥16 px；流式/站点/交互≥16 px；参考文献按轨）；后文冲突以 §0.7 为准 | MUST |
| I-04 | **品牌强调色系强制（§0.8）**：主/副强调、部门映射、风险红 `#C00000`、面积红线；默认浅抬头与 Logo 可读；主 CTA **及 RACI/微标/chip** 凡 `#FF9900` 实心底必须深字居中（§0.8.3C）；不得冷蓝/navy 默认抬头或全页铺橙黄红/霓虹。正文灰阶和谐即可 | NEVER |
| I-05 | 每个临床、数据、竞品结论必须可回溯到来源 | MUST |
| I-06 | 证据等级 3-4 必须显式标注“据公司公告”“据公开报道”等来源前缀 | MUST |
| I-07 | 推测或 MOA 外推必须以“推测”“基于 MOA 推测”或“专家判断”开头 | MUST |
| I-08 | AI 工具页必须保留“医学经理终审”边界，禁止“AI 自动判断”“AI 替代医学判断”措辞 | NEVER |
| I-09 | 受众背景（面向董事长、医学部负责人等）不得出现在可见正文 | NEVER |
| I-10 | `#C00000` 仅用于风险、缺口、关键结论；不得用于普通强调 | MUST |
| I-11 | 内容页页脚分隔符固定为竖线（`\|`）；目录/章节页无页脚；结束页元信息固定使用`·` | MUST |
| I-12 | `meta_spec` 页（§8.5）不得出现在最终交付 | NEVER |
| I-13 | HTML 报告（§14.10）与 PPT / HTML-PPT 共享 §5 配色、§6 字体、§10 证据与来源、§19 AI/风险不变量；HTML 报告不强制 §7 固定 chrome、§8 页面骨架、页码与转场 | MUST（内核共享）/ MAY（版式放松） |
| I-14 | 任何产出在交付前受众可见文本中的 `&&` 与 `@@` 搜索均为 0；HTML 报告的文字叙事结构由该报告具体需求决定 | NEVER / MAY |
| I-15 | 本规范正文不得包含版本号头、变更日志、调试笔记、文档编辑过程的元叙述；必要历史记录应通过版本管理或外部文档保存 | NEVER |
| I-16 | HTML-PPT验收以最大化桌面浏览器实渲染为准；1280×720仅是逻辑画布和回归视口 | MUST |
| I-17 | HTML-PPT只允许固定1280×720画布加单一全精度等比缩放，且必须双轴居中；所有`.slide`必须是唯一`.deck`的直接子元素，缩放只作用于`.deck` | MUST |
| I-18 | viewport、DPR、浏览器缩放和媒体查询不得改变页内字号、列数、间距、折行或逻辑坐标 | NEVER |
| I-19 | 等分Grid必须使用`minmax(0,1fr)`，可收缩中间层必须`min-width:0`；甘特各行共享列变量 | MUST |
| I-20 | 弱化流程节点仍须使用不透明背景；不得给整卡设置opacity | NEVER |
| I-21 | 正式HTML-PPT不得依赖CDN字体、在线图片或未随交付包封装的运行时；模块化版本允许随包本地`assets/runtime.js`，单文件版本必须内联 | NEVER |
| I-22 | 模块化目录是维护母版；单文件HTML是从同一母版生成并独立复测的派生产物 | MUST |
| I-23 | 最终视觉验收必须查看实际观众运行时的原始分辨率逐页图；预览页和contact sheet不能代替 | MUST |
| I-24 | 分享产物不得包含个人绝对路径、账号口令、内部制作日志或模型会商记录 | NEVER |
| I-25 | 标准内容页标题必须单行；当前不得现场换行。只有用户授权且本规范先补齐命名变体、完整几何与验收锚点后才可双行 | MUST |
| I-26 | PPT/HTML-PPT每页只允许命中一种视觉母版类：`cover-slide / toc-slide / section-slide / content-slide / ending-slide` | MUST |
| I-27 | 封面、目录、章节首页、结束页必须原值复用§14.5固定DOM/CSS；不得自由改坐标、字号、页眉页脚或增删可见模块 | MUST |
| I-28 | 内容页正文框固定`x=56,y=96,width=1168,height=564`；所有受众内容必须留在该框内 | MUST |
| I-29 | 康哲主题CSS必须在通用基础CSS之后加载，并以最终computed style验证固定画布、顶对齐和无二次变换 | MUST |
| I-30 | HTML-PPT单文件必须在每个可用目标系统用`file://`打开、零外部渲染依赖；字体与图片加载完成后再截图 | MUST |
| I-31 | 内容页橙斜切、黄斜切、顶线、单行标题、full Logo、正文框、页脚和页码必须逐项匹配§14.6原值；存在不等于坐标正确 | MUST |
| I-32 | 多端一致必须有Windows Chrome/Edge与macOS Chrome/Safari实机证据；同一系统的双内核结果不能替代跨OS验收 | MUST |
| I-33 | Agent必须完整读取本规范到EOF；任何截断块必须按offset补读，生成产物必须回读到EOF | MUST |
| I-34 | 目录页默认使用2×2语义目录板；每张卡必须有真实编号与标题，严禁空流程卡、无文字卡片和纯装饰占位 | MUST / NEVER |
| I-35 | 内容页最后一个受众可见正文元素逻辑bottom必须在560–660px内；不得把全部信息堆在上半页或用透明节点凑高度 | MUST |
| I-36 | 运营/数统空里程碑必须为真正空文本DOM；点号、`&nbsp;`、透明字和隐藏阶段名均禁止 | NEVER |
| I-37 | 三列责任对照使用§14.7.1固定3×3矩阵；三栏资料证据链使用§14.7.2五列模板和水平连接带 | MUST |
| I-38 | 不得为去重而合并不同母版的几何选择器；封面黄线720px与结束页黄线520px必须分别定义、分别验收 | NEVER |
| I-39 | 最终截图须在字体/图片就绪且翻页过渡结束后采集；不得用过渡中叠影截图做验收 | MUST |
| I-40 | 四部门应用组合页必须使用§14.7.0固定全高组件；普通结论条不得使用黑底反白样式 | MUST / NEVER |
| I-41 | 固定八行基础信息表必须显式包含边框后高564 px、底边660，表后不得追加脚注或callout | MUST |
| I-42 | HTML-PPT深链格式固定为`#/N`；键盘、点击、hashchange和直接打开深链必须使用同一格式并通过交互测试 | MUST |
| I-43 | 章节页`data-title`必须与可见章节标题完全一致，不得拼接章节编号或副标题 | MUST |
| I-44 | 目录meta必须使用真实汇报标题/短标题与真实日期；模板示意词不得出现在受众可见页面 | MUST |
| I-45 | 最终HTML的真实脚本闭合标签必须是字面量`</script>`；`<\/script>`只允许存在于构建中间字符串，不得作为最终元素闭合标签 | MUST |
| I-46 | §14.5–§14.7命名组件必须原样保留DOM层级、固定class/selector、声明字号与几何；不得用`.bar`、`.gantt-group-*`等别名或“等价实现”替代 | MUST / NEVER |
| I-47 | 正式Logo必须从§1.2康哲官网唯一地址下载并嵌入；最终模块化HTML、单文件HTML和PPT/PPTX均不得在观众运行时远程加载Logo或使用文字近似替代 | MUST / NEVER |
| I-48 | `.portfolio-gantt`根节点必须为`DIV`，直属结构固定为`.portfolio-head + .portfolio-group*`；不得用`table`包裹`div`或依赖浏览器纠错 | MUST / NEVER |
| I-49 | 任一时刻只有活动页可见；所有`.slide:not(.is-active)`必须在computed style层同时满足`visibility:hidden`与`pointer-events:none`（仅`opacity:0`不合格——透明页仍会拦截鼠标并破坏活动页hover），禁止十页绝对定位后同时叠加显示 | MUST / NEVER |
| I-50 | 结束页`.ending-focus`只作定位，必须无边框、透明背景、无阴影；“谢谢”周围不得出现透明卡片轮廓 | MUST / NEVER |
| I-51 | HTML-PPT/HTML的动效只允许增强层次，不得承载唯一信息；打印、截图、QC与HTML-to-PPT必须冻结为无动画稳定终态 | MUST |
| I-52 | 可见文字使用`data-qc-text`做Range墨迹裁切检查；同层组件使用`data-qc-zone/data-qc-block`做矩形相交检查，整页无overflow不能替代这两项 | MUST |
| I-53 | 可编辑PPT只有在PPT Master质量检查、finalize、PPTX导出、OOXML可编辑对象核验和逐页视觉复核全部完成后才可声明完成；初始化或SVG完成不等于PPT完成 | MUST |
| I-54 | 超高密度PPT/HTML-PPT正文首选16 px；18行单页总览绝对下限14 px且须满足行数、行高、对比度和明细入口条件；否则拆页 | MUST |
| I-55 | 正式HTML/HTML-PPT普通打开不得永久处于`data-export=true`或`data-qc=true`；冻结态只在导出和机器验收期间临时启用并恢复 | MUST / NEVER |
| I-56 | 多交付物任务必须逐个完成和验证；长HTML分块写入并在页数、运行时、字面量`</script>`与`</html>`闭合全部存在后才可进入下一产物 | MUST |
| I-57 | `ultra-raci-decision`不得在同页并排完整18行RACI与完整12行决策权表；左侧固定5列18行，右侧最多6条决策摘要 | MUST / NEVER |
| I-58 | `ultra-ai-boundary`左侧固定4列18行，右侧固定A0–A3图例/人机分工/禁止边界三块；主布局高520 px且正文bottom不得超过660 px | MUST |
| I-59 | `ultra-ai-boundary`的18个表体行必须逐行等于24 px且单行不换行；A0–A3图例固定112 px高、四项各18 px且不得溢出或换行 | MUST / NEVER |
| I-60 | HTML-PPT必须逐页绑定页码：内容页`data-current`等于该页在deck中的1-based索引，`data-total`等于总页数；不得所有内容页重复显示`1 / TOTAL` | MUST / NEVER |
| I-61 | 站点式HTML（§14.12）共享§14.10.2内核与§19全部不变量；不套§8页面原型与1280×720画布；数据层必须`window.DATA_X`注入且与源材料一致、自检通过 | MUST |
| I-62 | HTML-PPT粒子只允许`.slide.cover-slide`且节点≤40；内容页/目录页/章节页/结束页NEVER出现canvas粒子；所有环境装饰必须`aria-hidden`且离屏停帧 | MUST / NEVER |
| I-63 | 动效不得承载唯一信息：`[data-countup]`静态DOM即真值，揭示动画`html.js`门控；冻结态（export/qc）与reduced-motion下内容完整可见且无动画 | MUST / NEVER |
| I-64 | 汇报方部门身份固定为`产品中心-医学部`，出现于内容页页脚左槽`.footer-id`（文本匹配`^产品中心-医学部｜20\d{2}年\d{1,2}月$`、灰#808080/400）、封面`.cover-department`、结束页`.ending-meta`；NEVER 用源材料 owner/编制部门/项目名替换；页脚右槽页码橙#FF9900/700；`.deck-footer` 恰两槽，NEVER 出现来源/依据/SOP 等第三元素 | MUST / NEVER |
| I-65 | 底部参考文献行 ONLY 用于外部同行评审论文/公开法规指南；内部 SOP/章节/文件出处 NEVER 生成底部参考文献行（进讲者备注或行内括注）；参考文献行与页脚及正文末行垂直分离、NEVER 重叠；无外部引用页 NEVER 出现该行 | MUST / NEVER |
| I-66 | 所有装饰标记（里程碑菱形/状态点/强调箭头/编号圆/红色强调）MUST 在宿主 SVG 同一 viewBox 内以整数 user-unit 坐标绘制并与所标注节点共享坐标；NEVER 用 CSS 绝对定位 HTML 叠加贴 SVG 节点；标记渲染≥8px、落在 slide-body 内、NEVER 与文字相交 | MUST / NEVER |
| I-67 | 任何受众可见文字不得溢出/裁切（scrollWidth<=clientWidth 且 scrollHeight<=clientHeight，svg text 不超 viewBox 宽）；同页受众块两两不得相交（背景/连线层除外）；NEVER 用 overflow:hidden 掩盖裁切 | MUST / NEVER |
| I-68 | hero 页（cover/section/ending）wordmark 渲染宽 MUST ≥ 内容页 brand-lockup 渲染宽（≥158px），品牌在 hero 最醒目；内容页右上保持紧凑 full-logo | MUST |
| I-69 | 排版强制细节：≥3 并列点须列表；需突出须 strong/.kz-em-red/.kz-em-underline，非纯数字卡≥1 强调标记；所有卡状容器正文≥19px（compact 16px），NEVER 14px 正文 | MUST / NEVER |
| I-70 | SVG 流程/示意图文字渲染字号≥13px@1280，渲染字号=computed font-size×(svg clientWidth÷viewBox 宽)，NEVER 用 getBoundingClientRect 高当字号（那是 ink 盒）；节点仅圆角矩形/圆/菱形；每个红色标记须有邻近标签或全页图例，NEVER 不明所以的红标 | MUST / NEVER |
| I-71 | HTML-PPT MUST 内嵌演讲者运行时（S 弹当前/下页/逐字稿/计时器，翻页同步，R 重置，N 笔记）且每页 aside.notes 含 150–300 字口语逐字稿；流式/站点不强制 | MUST |
| I-72 | 卡状表面须有可感知层次（阴影或顶条，禁纯白扁块）；但阴影深度/hover 幅度/圆角在 token 范围内自由——此为发挥空间，不同模型/主题的合法差异不是缺陷 | MUST（底线）/ MAY（深度） |
| I-73 | 流式/站点式 HTML 的页脚（`.report-footer`/`.site-footer`）仅在文档最末或每页全局出现一次；NEVER 在每个 section/章节末尾重复页脚两槽或页码编号——逐节页脚是 HTML-PPT 专属规则 | NEVER |
| I-74 | 新控件 MUST 用 `kz-` 前缀 class、§5 token、§6 字体栈、§14.7.3 静态基线与冻结语义；NEVER 污染 §14.5–§14.7 命名组件合同 | MUST / NEVER |
| I-75 | 禁止控件（NEVER）：深色霓虹/自定义光标（含附加式）/无限滚动/WebGL/新野兽派/整页视差/整页毛玻璃墙；玻璃拟态仅 scoped（α≥0.88+1px 边界+blur≤12px+每视口≤4 面+冻结回退不透明）、新拟态仅 scoped（图标/按钮/小控件/卡+双阴影叠加边界）；局部视差≤40px、倾斜≤4deg、磁吸≤6px | NEVER（禁止项）/ MUST（scoped 约束） |
| I-76 | 性能预算：单文件≤100MB、同页动效对象≤8 累计计入、新增 IO/rAF 离屏停帧+RM/冻结全清 | MUST |
| I-77 | 构建后强制 QC 闭环：文字逐节点溢出/SVG 内部 pairwise 重叠/标记锚点对齐/图例语义/文字-SVG 互叠五项 MUST 实测并修复到全过；带失败交付=不合格 | MUST |
| I-78 | 图例标签 MUST 语义词（里程碑/红线/风险/状态），NEVER 裸形状名；红标 MUST 有语义解释 | MUST / NEVER |
| I-79 | 标记 MUST snap 到锚点（节点中心/轴中线/刻度列），NEVER 悬空两行两轨之间或图外 | MUST / NEVER |
| I-80 | 内容页左上双斜切在PPT/SVG轨MUST用§14.14.5绝对顶点（橙(24,9)(94,9)(64,71)(24,71)；黄(5,42)(45,42)(25,78)(5,78)），全部顶点0≤x≤1280且0≤y≤88，NEVER自行换算clip-path百分比 | MUST / NEVER |
| I-81 | 命中方案汇报/介绍/培训触发词时MUST套用§14.14 Playbook（PPT与HTML-PPT轨），流式HTML与站点式HTML不适用 | MUST |
| I-82 | 多期无缝方案汇报MUST按指定期别出页；它期专属信息命中即修；共用条款标"两期共用"、引用它期标"依据" | MUST |
| I-83 | 方案培训的药物概览页MUST为第一章第一个内容页；入排标准MUST原文+原编号+阈值深红；逐字稿NEVER暴露稽查/自查/整改措辞 | MUST / NEVER |

PPT Master 适配见 §13；HTML-PPT / HTML to PPT 适配见 §14。若平台专属规则与本节冲突，以本节为上位约束。
