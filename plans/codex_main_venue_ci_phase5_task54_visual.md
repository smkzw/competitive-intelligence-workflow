# Codex Main-Venue Plan: ci_phase5_task54_visual

Date: 2026-08-18
Objective: 以真实中文资深临床试验医学经理视角，对 Task 5.4 A 类多页面门户进行启用视觉的端到端试用和独立审评

## Task Decomposition

1. 先完成并生成可真实浏览的 A 类门户。
2. 两条用户指定路线分别独立试用、记录问题，不允许改产物。
3. Codex 修复可复现问题，沿原会话做定向复核。
4. 以最终新运行的浏览器证据和全量回归作最终判定。

## Source Packet

- 当前生成站点：`.artifacts/a-complete/reports/A/v-fixture-001/html/`。
- 浏览器证据：`.artifacts/a-complete/verification/A/v-fixture-001/`。
- 项目规范：`contracts/kangzhe/design_specs/` 与 Task 5.4 Trellis 三件套。
- 任务边界：`context/ci_phase5_task54_visual_conference_context.md`。

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `minimax_medical_manager` | `cms-router` | `minimax-m3` | `runs/conference/ci_phase5_task54_visual/minimax_medical_manager_recheck.md` |
| `grok_medical_manager` | `grok-build` | `grok-4.6:medium` | `runs/conference/ci_phase5_task54_visual/grok_medical_manager_recheck.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

Minimax 完成首轮及同会话复核。Grok 前两轮工具取消后使用同一会话完成第三轮和复核；无 fallback、无迟到输出覆盖已验收结果。

## Codex Verification Checklist

- [x] 16 个页面真实访问或逐图复看。
- [x] 搜索、筛选、网址状态、矩阵三维设置与数据依据。
- [x] 用户可见中文、图题、表格、空状态和产品范围。
- [x] 最终运行的双浏览器三视口与全工程回归。
