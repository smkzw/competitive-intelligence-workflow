# Codex Main-Venue Plan: ci_phase0_task04_package_cli

Date: 2026-08-11
Objective: 独立验收 Phase 0 Task 0.4 的安装包清单、公开与内部 Skill 边界、唯一中文 CLI 及失败关闭行为，拒绝源码自证和旧产物假绿。

## Task Decomposition

1. 两位参与者独立读取同一源包，不读取彼此输出。
2. 各自核对一个公开入口、15 个内部能力和内部不可隐式调用边界。
3. 各自运行真实 CLI 帮助、包校验、项目创建/校验和后续能力失败关闭负例。
4. 各自挑战打包与安装语义、清单闭合和测试假绿。
5. Codex 汇总缺陷；P0/P1 必须修复并以同一会话复核后才能接受。

## Source Packet

- `context/ci_phase0_task04_package_cli_conference_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `package-manifest.json`、`schemas/package-manifest.schema.json`
- `skills/competitive-intelligence-workflow/`、`skills/_internal/`
- `src/ci_workflow/`、`pyproject.toml`、`uv.lock`
- `tests/contract/test_package_manifest.py`、`tests/integration/test_cli_help.py`、`tests/integration/test_cli_command_catalog.py`

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_pi_qwen38` | `alibaba` | `qwen3.8-max` | `runs/conference/ci_phase0_task04_package_cli/general_pi_qwen38.md` |
| `general_grok45` | `grok-build` | `grok-4.5` | `runs/conference/ci_phase0_task04_package_cli/general_grok45.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Runner 硬等待 120 分钟；慢响应保持 pending，不定时轮询或重复派发。
- 仅在输出完成后发现可执行缺口时，使用同一 session 的 follow-up。

## Codex Verification Checklist

- [x] 冻结测试 3 项通过。
- [x] 全量测试 52 项通过。
- [x] Ruff、mypy、`package verify`、`uv build` 通过。
- [ ] 两位独立参与者均返回可审计输出。
- [ ] P0/P1 归零或按同一会话复核归零。
- [ ] 最终全量验证、Trellis 检查与干净提交。
