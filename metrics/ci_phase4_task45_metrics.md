# Metrics: ci_phase4_task45

Date: 2026-08-14

| Field | Value |
|---|---|
| Task type | `html_ppt_visual_browser` |
| Risk | `high` |
| Result | PASS after two visual repair loops |
| Duration | 07:33–15:20（含执行、三轮视觉复核和全量回归） |
| Focused regression | 419 passed / 201.85s |
| Full regression | 956 passed / 259.46s |
| Static checks | Ruff PASS; strict mypy PASS |
| Independent reviewers | 3/3 R3 PASS |

## Verification Burden

真实交互涉及图点、热图/状态单元、表格、URL、筛选、固定比较、焦点和 1024/1280 视觉；因此采用双浏览器确定性回归、三路医学经理视觉评审和 Codex 独立截图复核。

## Routing Decision

执行按 guard 生成的工作项路由；视觉验收按用户显式指定的 CodeBuddy/kimi-k2.6、Pi/minimax-m3、Grok Build/grok-4.6，所有复核均复用原会话。
