# Codex Main-Venue Plan: ci-phase6-final-visual-review

Date: 2026-08-30
Objective: 以资深临床试验医学经理视角，对当前B类PNH站点新摘要f094848b的真实截图、响应式搜索、键盘交互和信息呈现进行独立视觉接受审阅

## Task Decomposition

1. 独立审阅当前摘要为 `f094848b…` 的真实报告、40 张截图与浏览器指标。
2. 实际复核安全性矩阵、响应式搜索、证据详情键盘操作和中文医学经理使用体验。
3. 按七个视觉维度给出接受或阻断结论；Codex 随后复核并决定是否生成正式签收记录。

## Source Packet

- 候选报告、视觉计划、浏览器指标、渲染证据与截图路径均在 `context/ci-phase6-final-visual-review_conference_context.md` 中列明。
- 当前候选报告摘要必须为 `f094848b41cf9c66ae8c3ecfb58e0305d5a531f477e6e6cdaa5e05ea3694060e`；摘要不一致即停止签收。

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `visual_single_object` | `kimi-code` | `k3-256k` | `runs/conference/ci-phase6-final-visual-review/visual_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- 初始化：2026-08-30 16:28 CST。
- 运行状态与续跑原因由 runner 记录；仅在终态或 120 分钟硬等待返回后处理。

## Codex Verification Checklist

- [ ] 参与者实际检查当前候选与截图，并保持只读。
- [ ] 七个视觉维度均有明确结论，且无未解决阻断项。
- [ ] 768/1024/1440 安全性矩阵无需横向拖动并可读。
- [ ] 菜单展开式搜索与键盘证据详情交互可用。
- [ ] Codex 独立查看代表性截图并复核运行证据。
- [ ] 仅在全部通过后生成并校验正式视觉签收记录。
