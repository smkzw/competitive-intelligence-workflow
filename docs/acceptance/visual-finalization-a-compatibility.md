# A 类门户定稿前兼容边界复核

日期：2026-08-29

## 复核边界

- 只读产物：`.artifacts/a-values-matrix-fix-final-v5/reports/A/v1/html/`。
- 复核对象：A 类站点式 HTML 的首页、安全性详情、全部静态页面和产品详情路由。
- 本记录是定稿前证据，不替代 Codex 的最终视觉会商、独立放行或临床/监管结论。
- 未修改 `.artifacts/`、科学快照、报告数据或生成产物。

## 合同与控制图负例

- `tests/contract/test_visual_finalization_negative.py` 覆盖：当前运行渲染摘要漂移、外部设计/来源收据、图表声明数值漂移、当前运行检查缺失、视觉策划书必填绑定、固定视觉令牌、科学快照不可变标志、七域验收矩阵和程序状态字段泄漏。
- `tests/contract/test_visual_render_evidence.py` 覆盖：Chromium/WebKit 与 768/1024/1440 呈现矩阵、截图摘要、遮挡裁切、关键交互、工程化文字、响应式字段替代入口、开放阻断缺陷、自签和逐域结论漂移。
- `tests/graph/test_visual_finalization_graph_negative.py` 覆盖：仅真实渲染捷径、非布尔接受信号、跨族/跨对象证据、策划书快照/格式漂移、候选快照/格式漂移、美化轮次超出 1–3、自签视觉结论、结论摘要漂移、未达三轮视觉阻断、缺视觉结论发布和队列直接交付。
- `tests/graph/test_transition_matrix.py` 的 GT03 字面夹具已同步 `quality_check -> generating` 美化回环及全部视觉绑定字段；历史部分交付场景通过同一合同字段复测。

## A 类真实渲染观察

使用真实 Playwright Chromium 与 WebKit 打开冻结站点，在 1024、1280、1440、1920 宽度 × 900 高度检查首页和安全性页：

- 两个浏览器、四个宽度的文档宽度均等于视口宽度，无页面横向溢出。
- 首页保持 4 个概览模块和 4 个可见图表。
- 安全性图表宽度与客户区一致：1024 宽度为 924 px，其他宽度为 1100 px；未出现图表内部横向滚动。
- 安全性页有 598 个不良事件筛选项，严重/特别关注/治疗期间/常见四个中文维度仍在页面中。
- 首页和安全性页主内容未出现 `prompt`、`pipeline`、`accepted`、`pending` 或 `backend` 等程序状态词。

## 中文用户体验观察与剩余风险

安全性不良事件筛选项中 570/598 个可见标签含拉丁字符，例如 `SKIN BACTERIAL INFECTION`、`Hand dermatitis` 和 `TIBIA FRACTURE`。这与保留 `original_term` 的证据可追溯性要求一致，但当前筛选器仍把大量原始英文术语直接作为用户可见标签，不能视为完全中文原生体验。

最小修复建议：在展示投影中增加经审核的中文事件标签词表；保留 `original_term`、来源和证据抽屉中的原文，不对未知术语做相似词自动归一。扩展词表需由医学负责人确认，不能由视觉层改写事实或制造临床同义项。

## 可复现命令

- `uv run pytest -q tests/graph/test_visual_finalization_graph_negative.py`：13 passed。
- `uv run pytest -q tests/graph`：30 passed。
- `uv run pytest -q tests/contract tests/graph tests/browser/test_a_portal.py`：255 passed。
- `uv run pytest -q tests/browser/test_a_portal.py`：51 passed（Chromium 与 WebKit 真实运行）。

生产调用已补充当前候选摘要和视觉策划书摘要，浏览器 fixture 可正常启动；此前 29 个 setup error 已关闭。

## 尚待 Codex 复核

- 在同一当前运行中核对视觉策划书、候选、真实渲染收据和独立结论的实际摘要链。
- 当前冻结 A 产物仍作为机制负例：独立审阅发现 768 宽度下标签与信息密度风险，证明“无横向滚动”不能单独放行；本机制建设不回写或放行该冻结产物。
- PDF、HTML-PPT 和 PPTX 仍需各自真实渲染器验证；本轮没有生成或接受这些格式。
