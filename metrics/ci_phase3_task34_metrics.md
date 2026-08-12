# Metrics: ci_phase3_task34

Date: 2026-08-13

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `high` |
| Selected provider | `opencode-go` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 原执行会话多轮长等待，运行器报告留存 |
| API calls | 原执行会话运行报告 |
| Artifact size | 13 个实现/测试文件，5,259 行 |
| Result | `accepted；P0=0；P1=0` |

## Verification Burden

GT01–GT11、443 项全库、Ruff、strict mypy 与 wheel 检查；两名隔离审查者在原会话追加定向复核。主会场在接受前复现并关闭删除身份、原始迁移事件和原始节点完成事件三类假绿。

## Routing Decision

按有限代码主路线使用 Pi/OpenCode-Go `deepseek-v4-flash:max`；首次只读会话未获写权限后升级同一 session 为可写执行，不切换模型、不新开 session、无 fallback。
