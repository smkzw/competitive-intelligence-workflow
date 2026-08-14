# Metrics: ci_phase4_task46

Date: 2026-08-14

| Field | Value |
|---|---|
| Task type | `html_ppt_visual_browser` |
| Risk | `high` |
| Execution route | Pi / `cms-smk` / `deepseek-v4-flash` / max，原会话修订 |
| Visual routes | CodeBuddy `kimi-k2.6`; Pi `minimax-m3`; Grok Build `grok-4.6` |
| Duration | 12:30–14:45（含执行、两轮视觉验收、修复和全量回归） |
| Focused acceptance | 63 passed / 109.55s |
| Adjacent regression | 69 passed / 3.28s |
| Full regression | 1019 passed / 365.09s |
| Runtime matrix | 16 routes × 2 browsers × 3 viewports = 96 screenshots; 2 traces |
| Result | PASS after two false-green repair loops |

## Verification Burden

站点完整性同时涉及实体宇宙绑定、路由集合、入口可达、页面缺陷、真实浏览器差异和中文可用性，因此采用确定性合同、真实 3 视口双浏览器遍历、三路医学经理挑战与 Codex 原图复核。

## Routing Decision

执行由 guard 生成的 finite-code 路由完成；视觉按用户显式指定的三模型复用原会话。CodeBuddy 权限与 Grok 截断均在原会话恢复，不 fallback。
