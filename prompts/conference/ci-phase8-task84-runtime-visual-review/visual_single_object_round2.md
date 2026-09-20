Delegated mode. You are a bounded conference reviewer, not the user-facing agent.
Follow only this prompt. Do not start a conference or claim final acceptance.

Hard boundaries:
- Read-only. Do not modify files, do not access production paths, and do not use the internet.
- Work only in the runner-provided workspace.
- Reuse the existing Pi/Kimi-Code session; do not open a new session or change model.
- Codex remains final authority.

Read these files only:
- `docs/acceptance/runs/8.4/screenshots/chromium-1440x900-presenter.png`
- `docs/acceptance/runs/8.4/screenshots/webkit-1440x900-presenter.png`
- `docs/acceptance/runs/8.4/browser-contract-ledger.json`
- `assets/html-ppt/manifest.json`
- `tests/acceptance/test_html_ppt_runtime_smoke.py`

Output file:
- `runs/conference/ci-phase8-task84-runtime-visual-review/visual_single_object_round2.md`
Runner-managed report path: `runs/conference/ci-phase8-task84-runtime-visual-review/visual_single_object_round2.md`. Never write that report path with tools; return the complete report and let the runner persist it.

# Task 8.4 运行时视觉复验·同会话第二轮

MODE=CONFERENCE。不要重启任务、不新建会话、不修改文件、不联网。只复核首轮 D1/D3 及由此触发的修订。

Codex 裁决：

1. D1 成立。演讲者弹窗的真实客户区为 1440×900，旧文件名误写为 1920×1080。测试现直接断言 `[innerWidth, innerHeight] == [1440, 900]`，当前证据已改名为 `chromium-1440x900-presenter.png` 和 `webkit-1440x900-presenter.png`；旧误标证据已可恢复封存。
2. D3 不是有意设计，而是真实缺陷：作者样式 `.presenter-end{display:grid}` 覆盖了 `hidden` 属性，导致未到末页也显示“演示结束”。已增加 `.presenter-end[hidden]{display:none}`，并新增首页 `#next-end` 必须隐藏、末页必须显示的断言。
3. 修订后重跑 18/18 浏览器合同测试全通过；新 JS SHA-256 为 `affadf9e344ec9da62cdd27942a41218983d2cb88a377eca540b7da622a990f7`，清单和证据台账已绑定该哈希。
4. 新演讲者截图中，下一页预览仅显示“主要疗效”及图表，未再显示“演示结束”。

请复开当前两张 1440×900 演讲者原图、当前台账和相关断言，返回：当前哈希/尺寸绑定、D1 是否关闭、D3 是否关闭、仍存阻断、是否建议 Codex 接受 Task 8.4。D2 的 2048×1024 实图继续由 Task 8.6 负责，不要把 fixture 视觉风格当成正式幻灯片。

返回完整中文 Markdown 复验意见；Codex 仍是最终权威。
