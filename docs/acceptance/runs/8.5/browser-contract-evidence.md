# Task 8.5 HTML-PPT 基础浏览器合同证据（worker_03）

范围：结构/功能/`file://` 离线基础合同，以及 Chromium 1440×900 页几何基线。不是 Task 8.6 最大化窗口逐页原图验收。

## 命令

```text
uv run pytest tests/html_ppt/test_report_bc_html_ppt.py tests/html_ppt/test_html_ppt_browser_contract.py tests/html_ppt/test_report_a_html_ppt.py -q
uv run ruff check src/ci_workflow/renderers/html_ppt/projections src/ci_workflow/renderers/html_ppt/notes.py src/ci_workflow/renderers/html_ppt/theme.py src/ci_workflow/renderers/html_ppt/charts.py tests/html_ppt/test_report_bc_html_ppt.py tests/html_ppt/test_html_ppt_browser_contract.py tests/html_ppt/test_report_a_html_ppt.py tools/render_html_ppt.py
```

结果（本机 2026-08-31）：pytest **22 passed**；ruff **All checks passed**。

## 浏览器矩阵

`tests/html_ppt/test_html_ppt_browser_contract.py`：

- A/B/C × Chromium × WebKit：`file://`、逻辑画布 1280×720、ArrowRight、`n` 打开逐字稿抽屉、无远程请求
- A/B/C × Chromium 1440×900：逐页 DOM 几何，活动页节点不得溢出画布、披露行不得横向裁切
- 翻页后等待入场动画稳定，再校验页码正文与总页数完整，且 CSS 不得用伪元素重复写页码

## 代表页截图（基线，非终验）

目录：`docs/acceptance/runs/8.5/screenshots/`（1440×900 完整视口截图；不用已缩放元素截图，避免浏览器工具误裁右下角页码）

A：`a-efficacy` `a-safety` `a-matrix` `a-matrix-2` `a-regulatory`

B：`b-efficacy` `b-safety` `b-matrix` `b-demographics` `b-flow` `b-disposition-overview`

C：`c-inclusion` `c-endpoints` `c-stats` `c-identity` `c-path-1` `c-path-2`

## 独立视觉会商闭环

- 首轮发现并修复：C 类样本量缺值、C 类比较符混用、图表产品身份截断、A 类矩阵标签碰撞。
- 第二轮发现并修复：英文药名被硬切成一到两字符尾行。
- 同一会话第三轮在 1440×900 实际浏览器中复核六个长标签、A 类五页疗效和两页矩阵、B 类疗效；无剩余 8.5 确定性阻断项。
- 会商证据：`runs/conference/ci-phase8-task85-html-ppt-visual-review/visual_single_object.md`、`visual_single_object_round2.md`、`visual_single_object_round3.md`。

## 留给 8.6 的全页美化项

- A 类第二页矩阵个别相邻标签的最终留白与引线精修。
- C 类百分号前空格、B 类 92.2 数值与图例邻近等非阻断排版细节。
- 全部 62 页在用户实际最大化窗口及非 16:9 视口下的逐页原图终验。

## 未做

- Task 8.6 全页最大化视觉终验
- 临床/监管终验
- 改写 Task 8.4 `runtime.js` 或 `gx_fx.{css,js}` 源文件
