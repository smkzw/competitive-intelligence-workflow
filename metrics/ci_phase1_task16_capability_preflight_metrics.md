# Metrics: ci_phase1_task16_capability_preflight

Date: 2026-08-11

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | `cms-smk` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 首轮 258.217 秒；同 session 修订复核 169.863 秒 |
| API calls | 首轮 1 round；同 session 增量复核 2 rounds；无 fallback、无重派 |
| Artifact size | 首轮报告 9,946 bytes；修订报告 5,150 bytes |
| Result | PASS |

## Verification Burden

独立审查真实重跑 11 项精确测试、132 项全库回归、Ruff、strict mypy、包校验、diff 检查和 `local` 全矩阵 CLI，并攻击未选择能力、PPTX 选择性阻断、入口一致性、矩阵伪造、恢复重排、测试 override 隔离与中文说明。Codex 对网络单次超时和 LibreOffice 语义进行修订后，复用原 session 完成增量复核。

## Routing Decision

按全局有限代码首选路由使用 `Pi/cms-smk/deepseek-v4-flash:max`；健康/真实会话均建立成功，首轮和修订复核保持 session `019ff10c-d3e2-7000-b372-d52aa2fb1d14`，没有触发 fallback 或日夜间替换。
