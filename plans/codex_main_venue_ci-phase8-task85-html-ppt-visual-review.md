# Codex Main-Venue Plan: ci-phase8-task85-html-ppt-visual-review

Date: 2026-08-31
Objective: 独立审阅 Task 8.5 A/B/C 单文件 HTML-PPT 当前候选的中文医学经理可读性、康哲母版一致性、图表真实性、页码和离线交互合同，判断是否存在必须在进入 Task 8.6 前关闭的确定性阻断项；不执行 8.6 全页终验。

## Task Decomposition

1. 在实际 1440×900 浏览器检查 A/B/C 规定代表页、页码、离线导航和逐字稿抽屉。
2. 从锁定输入核对图表数值、缺失语义、矩阵覆盖和 C 类试验身份。
3. 将确定性缺陷交回 Codex 修订，并在原会话复验，直到无 8.5 阻断。

## Source Packet

- `output/html-ppt/report-{a,b,c}.html`
- `docs/acceptance/runs/8.5/{projection-contract,candidate-inventory,browser-contract-evidence}.md`
- `src/ci_workflow/renderers/html_ppt/` and locked A/B/C inputs
- `docs/acceptance/runs/8.5/screenshots/`

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `visual_single_object` | `kimi-code` | `k3-256k` | `runs/conference/ci-phase8-task85-html-ppt-visual-review/visual_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

同一会话完成三轮：首轮 1065.443 秒；第二轮 528.728 秒；第三轮 265.109 秒。等待期间未重复派发，未启用 fallback；三轮输出均纳入最终裁决。

## Codex Verification Checklist

- [x] A 疗效/安全性/两页矩阵/监管代表页
- [x] B 疗效/安全性/矩阵/基线/完成情况代表页
- [x] C 入选/终点/样本量/定位/两条路径
- [x] 页码只出现一次、键盘导航和逐字稿抽屉
- [x] 锁定输入与数值、缺失和不适用语义
- [x] 修订后同会话复验无 8.5 阻断
