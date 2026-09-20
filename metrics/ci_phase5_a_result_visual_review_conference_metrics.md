# Conference Metrics: ci_phase5_a_result_visual_review

Date: 2026-08-28

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `visual_pi_k3_256k` | `kimi-code` | `kimi-code/k3-256k` | excluded | — | — | — | 用户显式指定其他两条路线 |
| `explicit_minimax` | `cms-router` | `minimax-m3` medium | completed | 233.323s | 1 | 63,199 | 通过；无回退 |
| `explicit_grok` | `grok-build` | `grok-4.6` medium | completed | 539.144s | 1 | 3,258,387 | 通过；无回退 |

## Timeout And Retry Evidence

- 两条真实调用均使用 runner 的 7,200 秒硬等待和 128 内部轮次上限，只启动一次。
- Grok 健康预检成功，真实调用返回码 0。
- Minimax 目录预检返回码 0 且目录明确存在 `MiniMax-M3`，但检查器用小写 selector 误判 `model_not_listed`；该诊断是 advisory。显式路由随后真实调用成功，返回码 0，未回退。
- 两条调用均无超时、无重试、无空输出、无截断。

## Quality Decision

两位独立测试者均有实际视觉/浏览器证据并判定通过；Codex 的双浏览器三视口量化、截图和全工程回归与其结论一致。本次视觉验收通过。
