# HTML-PPT FX 层（V1.1 · 本轨强制）

> **track_id=`htmlppt` only.** Load after `track_htmlppt.md`.  
> **Executable assets** (copy verbatim, do not rewrite from memory):
> - `assets/htmlppt/gx_fx.css`
> - `assets/htmlppt/gx_fx.js`  
> PPTX / stream / site / interactive **NEVER** load this layer.

Reference implementation: MG-K10 CRSwNP III期方案讨论会 V1.1（`V1-grok-test`）。本文件是合同；CSS/JS 是封闭实现。

## 1. 强制注入

HTML-PPT 交付 **MUST** 带上本层。缺 CSS 或 JS = 未完成视觉母版。

加载顺序（康哲主题必须在通用 base 之后，本层必须在康哲主题之后）：

```html
<link rel="stylesheet" href="assets/base.css">
<link rel="stylesheet" href="kangzhe.css">
<link rel="stylesheet" href="assets/htmlppt/gx_fx.css"><!-- MUST last visual -->
<script src="assets/runtime.js"></script>
<script src="assets/htmlppt/gx_fx.js"></script>
```

单文件 HTML：把 `gx_fx.css` 内联到 `<style>`（排在 kangzhe.css 之后），把 `gx_fx.js` 内联为独立 `<script>`（排在 runtime 之后）。**NEVER** 凭记忆重写选择器、时长或粒子常量。

JS 在 `DOMContentLoaded` 自举：注入 SVG 折射滤镜、grain、英雄页 `.gx-env` / `canvas.gx-net`、目录玻璃层、图表入场、目录跳章、指针光影。作者 **NEVER** 手工把这些节点写进业务 HTML。

`?preview=` / `?presenter=1` / `html[data-export]` / `html[data-qc]` / `prefers-reduced-motion:reduce` 下 JS **MUST** 停帧并清空 canvas（资产已实现）。

## 2. 分区合同（英雄页活、内容页净）

| 页型 | 环境光斑 `.gx-env` | 粒子网 `canvas.gx-net` | 液态玻璃 | 内容橘黄铺光 |
| --- | --- | --- | --- | --- |
| cover / toc / section / ending | MUST | MUST（cover/ending 节点 48，toc/section 32） | toc 卡 MUST；cover/ending 的 `.blk` MAY | NEVER |
| content / info_table / gantt / … | NEVER | NEVER | NEVER（实底 α≥0.96，`backdrop-filter:none`） | NEVER |

内容页 **MUST** 保持 `#FFFFFF`，**NEVER** 给 `.slide-body` 或整页铺橘黄径向光晕、blob、caustic。这是可读性红线，不是“不够炫”。

## 3. 必须出现的美学件

Agent 不得删减下列件；实现以资产为准。

1. **内容页页眉动效**：左上橙/黄斜切 `gx-facet-a/b` 微旋转 + 多层 drop-shadow 荧光；顶线无额外橙光晕。右上 Logo 浅浮雕 drop-shadow，**无循环动画**。
2. **英雄页环境**：三枚游走暖色 blob + caustic + dust；cover/ending hero 径向光斑 `gx-orb-move`；toc/section 低对比网格+游走光斑。
3. **目录液态玻璃**：`.toc-item` 半透白 + `blur(6px) saturate(1.7)` + 白 rim + 旋转 conic 细边 + `.gx-refract` + `.gx-sheen`。文字 **MUST** 居中。指针进入：高光跟随 `--lx/--ly`，`perspective` 倾斜 `rotateX≤5deg` / `rotateY≤6deg`（覆盖 I-75 的 4deg，仅本轨英雄玻璃卡）。
4. **目录跳章**：点击/Enter/Space 跳到对应 `.section-slide`，深链写 `#/N`。
5. **章节编号**：浅浮雕 text-shadow + ≤5px 循环浮动 + 地面光池。**NEVER** 再套编号圆圈。
6. **黄线扫光**：cover/toc/section/ending 的 rule `::after` 循环扫光。
7. **鼠标光晕**：`.deck::after` 小径向暖光，**仅英雄页**可见；内容页活动时 opacity 0。
8. **卡片光影（内容页）**：`.blk/.panel/.kz-card/.content-conclusion` 实底白卡 + 轻阴影；hover 可用既有 ≤3px 抬升。**NEVER** 在内容页对表格/甘特/证据截图做 3D 倾斜或毛玻璃。
9. **图表动效**：活动页 SVG 品牌色柱 `gx-bar-v/h` 从原点生长；品牌描边 `gx-draw`；图表 `drop-shadow(0 5px 8px …)`。只对品牌填充/描边，轴网格线不动。
10. **强调字**：`strong/b/.r/.kz-em-red` 静态浅立体阴影，**无跳动/循环**。`.r` **MUST** `color:var(--kz-risk)`。
11. **封面主标题** 可对关键词包 `.hl` 做品牌橙扫光渐变（仅封面）。
12. **grain**：全 deck 固定噪点，内容页更淡。

## 4. 覆盖旧禁令（仅 htmlppt）

以下旧条文被本层替换，**不得**再按旧 NEVER 删除 FX：

| 旧口径 | 本层 |
| --- | --- |
| 正式医学汇报不用玻璃拟态 | **英雄页目录卡 MUST 用本层液态玻璃**；内容页仍禁止 |
| 粒子只允许封面 | **四个英雄页 MUST 有 `gx-net`**；内容页仍禁止 |
| 禁止循环漂浮 | **允许**：斜切荧光、章节编号 ≤5px、黄线扫光、封面 `.hl`、目录 conic 边、sheen |
| hover 3D ≤1deg / I-75 ≤4deg | **英雄玻璃卡**按资产 `rotateX≤5` / `rotateY≤6` |
| I-75 玻璃 α≥0.88 | **英雄玻璃卡**允许 α 0.22–0.40 + 白 rim；内容页 α≥0.96 |
| 封面要活、其它页死 | **英雄页都要活**；内容页净白 + 页眉荧光 + 图表入场 |

未列出的品牌 HEX、1280×720、chrome 几何、证据/AI 边界、冻结态 **不放松**。

## 5. 冻结与无障碍（MUST）

- `prefers-reduced-motion:reduce`：资产内 animation 全关；折射层隐藏；编号/斜切 transform none。
- `html[data-export="true"]` / `html[data-qc="true"]`：隐藏 `.gx-env/.gx-refract/.gx-grain/.gx-net/.gx-sheen`；玻璃卡回不透明白；斜切/编号停动画。静态终态仍须可读、几何不变。
- 环境层 `aria-hidden="true"` 且 `pointer-events:none`。
- 动效 **NEVER** 承载唯一信息。截图/无 JS 必须看到全部数字与文案。

## 6. NEVER

- 把本层 CSS/JS 改写成“更现代”的另一套。
- 内容页橘黄洗底、内容页 canvas 粒子、内容页毛玻璃墙。
- 结束页「谢谢」外再套玻璃卡（`.ending-focus` 仍透明无边无阴影）。
- 把单页业务特例（如某页 `data-title` hack）写进可复用 `gx_fx.css`。
- 改品牌 HEX、字号地板、正文框 1168×564。
- 大圆角（>14px）、霓虹、深色模式、整页橙铺底。
- 动画 `width/height/top/left`；只用 `transform` / `opacity` / `stroke-dashoffset` / `@property --gx-a`。

## 7. 验收（在 track_htmlppt §14.9 之上）

交互态（非 export/qc、非 reduced-motion）：

1. 打开封面：可见 `.gx-env` 与 `canvas.gx-net`，主标题可带 `.hl` 扫光。
2. 目录：四卡玻璃 + 居中文字；悬停高光跟随；点击第 2 卡跳到第 2 个 `.section-slide`，hash 为 `#/N`。
3. 章节页：大编号浮雕浮动，无圆圈；背景光斑在动。
4. 任一内容页：背景计算值为白；无 `.gx-env` / `.gx-net`；左上斜切在动；活动页图表柱有生长类或已到达终态。
5. 内容页 `strong`/`.r` 有静态 text-shadow，无循环 transform。

冻结态：`dataset.export="true"` 后等两帧，`.gx-net` 不可见且 rAF 已停。
