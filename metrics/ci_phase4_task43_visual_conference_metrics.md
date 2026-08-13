# Conference Metrics: ci_phase4_task43_visual

Date: 2026-08-14

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| 真实医学经理 1 | `codebuddy-cli` | `kimi-k2.6` | completed | 原会话续跑 | 未用作验收指标 | 未用作验收指标 | PASS |
| 真实医学经理 2 | `cms-router` | `minimax-m3` | completed | 原会话续跑 | 28+ 真实操作 | 未用作验收指标 | PASS |
| 真实医学经理 3 | `grok-build` | `grok-4.6` | completed | 原会话续跑 | 1280/1024 完整路径 | 未用作验收指标 | PASS |

## Timeout And Retry Evidence

- 首次 CodeBuddy 运行因计划权限不能调用视觉工具，未计入真实试用；按用户要求保留原会话并启用可执行权限后完成。
- Grok 浏览器入口受占用/权限影响时保留原会话，改用独立 Chromium；未因延迟或一次取消新开会话。
- Minimax 首轮真实操作发现问题，修复后同会话复核并保存 v2 证据。

## Quality Decision

三者最终均 PASS、P0=0、P1=0。关键结论由浏览器真实状态、截图、轨迹和确定性测试共同支撑，不以模型文字自证。
