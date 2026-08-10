# Codex Main-Venue Plan: ci_phase0_contract_review_20260810

Date: 2026-08-10
Objective: 在不修改文件的独立上下文中复核 Task 0.1-0.2 的真实闭合性、康哲合同稳定双读与单词漂移判断，识别任何会导致 Phase 0 假阳性的 P0/P1 缺口。

## Task Decomposition

1. 两位参与者分别在隔离上下文中重跑 Task 0.1 的测试/扫描，并审查扫描范围和例外是否会产生 false-green。
2. 分别检查 Task 0.2 的直接依赖、版本、许可证、用途、锁文件和冻结同步是否真实闭合，关注测试是否把 name/version 错配为通过。
3. 分别完整读取两个康哲候选，复现稳定摘要、共同正文锚点和唯一差异，审查推荐同步措辞与用户确认边界。
4. Codex 等待两路终态，核对 findings 的真实文件和命令锚点；必要时只做同 session 定向追问。
5. 在用户确认前只允许修复新仓内部 false-green，不修改两份康哲模板、不进入 Task 0.4。

## Source Packet

- `AGENTS.md`
- `context/ci_phase0_contract_review_20260810_conference_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- Task 0.1/0.2/0.3 文件清单见 context 的 Source Of Truth。
- workspace 外只读例外仅限两份康哲候选。

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_pi_qwen38` | `alibaba` | `qwen3.8-max` | `runs/conference/ci_phase0_contract_review_20260810/general_pi_qwen38.md` |
| `general_grok45` | `grok-build` | `grok-4.5` | `runs/conference/ci_phase0_contract_review_20260810/general_grok45.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- 每路先执行 runner `--health-check`，其失败仅作为诊断，仍允许一次真实 route attempt。
- 单路 hard timeout 7,200 秒，最大 128 internal turns；运行中不固定间隔轮询、不因慢而 fallback。
- 只在终态输出不完整且存在 session id 时使用同 session follow-up；记录 start/end/session/provider/effective route/fallback reason。

## Codex Verification Checklist

- [ ] 两份 prompt preflight 无 warning/error。
- [ ] 两路 runner 各形成终态报告或明确 pending/failure evidence。
- [ ] Codex 亲自复现所有 P0/P1 finding。
- [ ] Task 0.1 测试、扫描、迁移清单和规格摘要重新通过。
- [ ] Task 0.2 frozen sync、Ruff、mypy、依赖合同和全测试重新通过。
- [ ] Task 0.3 两文件 stable-read 和唯一差异重新通过；当前摘要未被误称已批准。
- [ ] review/metrics 写入真实结论并通过 review-gate。
