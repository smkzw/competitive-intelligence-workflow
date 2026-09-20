# Codex Main-Venue Plan: ci_phase5_a_values_matrix_visual_review_v4

Date: 2026-08-28
Objective: 以真实医学经理视角启用视觉能力，独立验收最终A类特应性皮炎HTML报告：首页和安全性详情页在768、1024、1280、1440像素下默认完整显示四个安全性维度，无横向拖动；核查中文可读性、图表优先、数值层级、表格与筛选交互，不修改文件，不替代Codex终验。

## Task Decomposition

1. 真实打开最终产物的首页、安全性详情页和疗效详情页。
2. 分别在768、1024、1280、1440像素下检查默认可视范围、水平滚动、四维安全性矩阵与中文标签。
3. 实际操作产品和事件筛选，核查图表同步、数值、观察窗及未公开状态。
4. 以资深医学经理视角评估信息密度、读取路径、图表先后顺序与明显视觉缺陷。

## Source Packet

- `.artifacts/a-values-matrix-fix-final-v4/reports/A/v1/html/`
- `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v4/`
- `context/ci_phase5_a_values_matrix_visual_review_v4_conference_context.md`

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `visual_pi_k3_256k` | `grok-build` | `grok-4.6` | `runs/conference/ci_phase5_a_values_matrix_visual_review_v4/visual_pi_k3_256k.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- 首次执行先进行实际路由连通性检查，随后单次发起并等待最长120分钟。
- 只在明确终态失败、输出空缺或验收不合格时按既定链条处理，不因耗时重复发起。

## Codex Verification Checklist

- [x] Chromium和WebKit在768/1024/1280/1440 px均无页面或矩阵水平溢出。
- [x] 首页和安全性详情页默认均有4个安全性维度，按两块每块2列排布。
- [x] 康哲Logo存在，首页、安全性详情页截图已人工审视。
- [ ] 独立视觉参与者输出已返回并被Codex复核。
