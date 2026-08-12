# Codex Main-Venue Plan: ci_phase3_task33_acceptance

Date: 2026-08-13
Objective: 独立验收 Task 3.3 用户辅助下载、自动识别归档与幂等恢复实现，审查真实用户路径、规则绑定、状态事件和假绿

## Task Decomposition

1. 两位参与者独立复现精确测试与临时目录攻击，不读取彼此输出。
2. Codex复现 P1 后修复并回归，再复用原会话复验。
3. 对最终源摘要进行同会话绑定复核，由 Codex综合接受。

## Source Packet

Task 3.3 源码、Schema、三份精确测试、真实 A/B/C GateSpec、事件库、内容库、批准设计 §10.2/§11.5/§11.7。

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_pi_qwen38` | `alibaba` | `qwen3.8-max` | `runs/conference/ci_phase3_task33_acceptance/general_pi_qwen38.md` |
| `general_grok45` | `grok-build` | `grok-4.5` | `runs/conference/ci_phase3_task33_acceptance/general_grok45.md` |

最终摘要绑定输出：`general_pi_qwen38_final_hash.md`、`general_grok45_final_hash.md`。

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Pi 首轮与修复轮均使用原会话并在 120 分钟硬等待内完成；没有因无输出重派。
- Grok 首轮及第一次续跑在工具调用前被运行时取消；保留原会话，调整为允许只读工具后完成，无 fallback。
- 两位最终输出均在本次接受中使用。

## Codex Verification Checklist

- [x] 精确测试与全库回归
- [x] 大写扩展名和中英文标题
- [x] `matched`/`accepted` 崩溃重放
- [x] 事件、来源版本、作业、归档幂等
- [x] 同运行歧义与跨运行隔离
- [x] 中文下载列表与多轮隔离说明
- [x] 最终摘要绑定及 P0/P1 清零
