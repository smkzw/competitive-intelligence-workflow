# Codex Main-Venue Plan: ci-phase9-task95-candidate-bundle

Date: 2026-09-01
Objective: 对已完成修复的 Task 9.5 候选 Skill 包做治理关联复审：核实 bundle 内容闭包、规范 fresh-install、Codex/Hermes/OMP 三真实宿主完整无草稿阻断到补件恢复和站点式 HTML、中文安装说明及当前摘要归档；沿用既有独立审阅会话，不重做实现。

## Task Decomposition

1. 只读核对当前候选包、归档和规范安装摘要。
2. 核对三宿主回执的初始阻断、补件恢复、最终 HTML 与真实宿主身份。
3. 核对公共 Skill 和安装说明的首版中文 HTML-only 口径。
4. 复用既有独立审阅会话给出治理关联结论；Codex 完成最终复验和收口。

## Source Packet

以 conference context 所列 Task 9.5 合同、候选包、安装根、三宿主回执、实现和测试为唯一当前证据；既有 `-review` 输出仅用于定位已修复缺陷。

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_single_object` | `cursor` | `default` | `runs/conference/ci-phase9-task95-candidate-bundle/general_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

复用会话 `01a05a8c-f404-7000-aada-4c33619bd1a4`；无 fallback、无新会话。等待上限 120 分钟，终态后再整合。

## Codex Verification Checklist

- [x] 当前 dist/sidecar/archive/安装版本摘要一致。
- [x] 三宿主均为 PATH 真实入口且进程/会话/运行互异。
- [x] 每份回执均证明初始零草稿阻断、固定补件、显式重开/重绑和最终 HTML。
- [x] 公共 Skill 与中文安装说明符合首版 HTML-only。
- [x] 独立参与者给出明确 Pass/Fail；Codex 重跑关键确定性检查。
