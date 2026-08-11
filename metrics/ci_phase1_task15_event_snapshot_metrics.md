# Metrics: ci_phase1_task15_event_snapshot

Date: 2026-08-11

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | `cms-smk` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 首轮有效 fallback 390.585 秒；同 session 修订复核 224.255 秒；首选健康诊断另 90.009 秒 |
| API calls | 真实首选 1 次（身份不匹配）；声明 fallback 首轮 1 round；同 session 修订复核 2 rounds；无重派 reviewer |
| Artifact size | 首轮报告 7,289 bytes；修订报告 4,236 bytes |
| Result | PASS |

## Verification Burden

独立审查真实重跑精确 3 项、全库 121 项、Ruff、strict mypy、包校验和 diff 检查，并用临时项目攻击事件篡改/跳号/截断、交错 run、幂等冲突、旧 run/快照、伪接受和产物篡改。Codex 修复旧运行/快照绑定与崩溃窗口合同后，复用原 session 进行两轮增量复核，仍为 PASS。

## Routing Decision

按全局有限代码路线先选 `Pi/cms-smk/deepseek-v4-flash:max`。模型目录健康查询 90 秒超时后仍进行了真实调用；真实调用虽返回 0，但 runner 检测到 `runtime_identity_mismatch`，不能作为声明身份的可恢复审查会话，故使用已声明的 `Pi/opencode-go/deepseek-v4-flash:max` fallback。后续修订直接恢复 fallback session，没有另开会话。
