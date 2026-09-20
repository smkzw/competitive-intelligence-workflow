# Codex Main-Venue Plan: ci-phase8-task84-runtime-visual-review

Date: 2026-08-31
Objective: 独立只读审阅 Task 8.4 HTML-PPT 运行时底座的真实浏览器截图与交互证据，确认固定画布、双轴居中、逐字稿、讲者当前页和下一页、页码、计时及离线图表没有阻断；不得把极简运行时 fixture 当作正式康哲视觉母版，不修改文件。

## Task Decomposition

- 独立复开 Chromium/WebKit 受众页、逐字稿、演讲者视图和离线图表截图。
- 核对浏览器合同证据是否真正覆盖双轴居中、下一页预览完成和窗口独立错误审计。
- 区分运行时阻断与未进入 Task 8.5 的正式视觉母版。

## Source Packet

- `assets/html-ppt/runtime.js`、`runtime.css`、`manifest.json`
- `tests/acceptance/test_html_ppt_runtime_smoke.py`
- `tests/fixtures/html-ppt-runtime/index.html`
- `docs/acceptance/runs/8.4/screenshots/`
- `docs/acceptance/runs/8.4/browser-contract-ledger.json`、`browser-contract-evidence.md`、`verdict.md`

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `visual_single_object` | `kimi-code` | `k3-256k` | `runs/conference/ci-phase8-task84-runtime-visual-review/visual_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

按 runner 单次 120 分钟硬等待；延迟不视为失败，只在终态错误或输出空缺时启用声明回退链。

## Codex Verification Checklist

- 复核会商引用的是当前八张截图和当前运行时哈希。
- 不将 fixture 的极简样式当成正式视觉缺陷。
- 对会商指出的任何阻断重新打开原图或浏览器证据裁决。
