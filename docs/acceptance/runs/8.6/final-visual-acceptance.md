# Task 8.6 HTML-PPT 最终视觉验收

验收日期：2026-08-31  
验收结论：**通过**

## 验收对象

| 报告 | 页数 | 最终 SHA-256 |
|---|---:|---|
| A 类 | 20 | `718705c6d1aa1347907b600e27a9753230f8ad93afb17a0cfa73f44eb164d7a6` |
| B 类 | 24 | `2bf6a334fd484f1df99bca363f1425503f83e9aa9727a73986a6fcd846c3a406` |
| C 类 | 18 | `e284dec451cc8355a5ebdd376a903785b3a10e984a9a6bae9bc3c73a61a8f342` |

## 最终原图证据

- Chromium：62 页 × 4 视口，共 248 张原图；自动检查阻断、高、中、低缺陷均为 0。
- WebKit：62 页 × 4 视口，共 248 张原图；自动检查阻断、高、中、低缺陷均为 0。
- 覆盖视口：1280×720、1280×800、1920×1080、2048×1024。
- 最终台账：
  - `visual-final-4-chromium/visual-baseline-ledger.md`
  - `visual-final-4-webkit/visual-baseline-ledger.md`

## Codex 人工终验

- 逐页查看 Chromium 1920×1080 的全部 62 页。
- 查看 A13、A14 在 Chromium 与 WebKit、四个视口下的全部 16 张原图，确认气泡标签、零值气泡与横轴刻度不再碰撞。
- 对 A06、A07、A12、B04、B06、B07、C09、C15、C16 补看 Chromium 1280×800、Chromium 2048×1024、WebKit 1920×1080 原图。
- 未见文字裁切、页面溢出、图表语义错配、未公开值被误读为零、跨浏览器布局漂移或中文临床表达阻断。
- B、C 部分页面信息量较少，是公开资料边界的如实呈现，不以虚构数据填充版面。

## 独立审阅裁决

- Terra 第二轮确认首轮严重问题已解除，仅提出 A 类“试验项数”不应显示小数；已改为整数并复验通过。
- CodeBuddy 对 10 个改动页面在四视口、双浏览器下复核，建议通过；Codex 已用最终 `visual-final-4-*` 原图再次核对。
- MiniMax 关于 A14 旧版刻度邻近的反馈曾有效，已修复；其关于 A 类临床页仍有治疗/对照柱、C 类结束页独有重复 Logo 的判断与最终原图不符，未采纳。A/B/C 结束页采用相同品牌构图。
- Cursor/default 两次连通性验证失败，按约定排除，不作静默替换。

## 确定性检查

- `python3 -m ruff check tools/collect_html_ppt_visual_baseline.py src/ci_workflow/renderers/html_ppt tests/html_ppt`：通过。
- `.venv/bin/python -m pytest -q tests/html_ppt`：22 项通过。
- 最终 HTML 哈希与双浏览器台账绑定值一致。

## 边界

本结论仅关闭 Task 8.6 的 HTML-PPT 视觉验收，不代表原生 PDF 或可编辑 PPTX 已完成最终验收。
