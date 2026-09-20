# Codex Main-Venue Plan: ci-phase10-task102-r13e-visual-review

Date: 2026-09-02
Objective: 由用户点名的三名独立真实医学经理基于 ego(lite) 逐项审阅 R13e A/B/C 站点式 HTML 的交互、横向比较、方案设计矩阵、默认视野与中文视觉体验；只读，不改代码。

## Task Decomposition

1. 三条用户点名路线先分别完成真实 harness 连通性测试，不替换模型。
2. 三名审阅者分别在 ego(lite) 内完成 A/B/C 全流程试用，不读取彼此结论。
3. Codex 对可复现缺陷逐项回到当前 R13e 页面验证，必要时修订并重新生成新候选。
4. 只有当前候选通过确定性检查、ego(lite) 交互与视觉复核后，才更新任务验收状态。

## Source Packet

见会议上下文中的 R13e 入口、设计合同和当前 ego(lite) 视觉证据。浏览器操作只能使用 ego(lite)。

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `visual_single_object` | `google-antigravity` | `gemini-3.7-flash` | `runs/conference/ci-phase10-task102-r13e-visual-review/visual_single_object.md` |

用户另行点名的独立测试路线为 `pi/cms-router/minimax-m3:high` 与 `zcode/zcode/glm-5.3-flash:max`；它们使用各自明确路线、独立输出和相同 ego(lite) 审阅合同，不替代会议包声明的 Gemini 路线。

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- 每条路线硬等待 120 分钟；启动后不做固定间隔轮询。
- 只在终态失败、明确不可用、输出为空/截断或同会话恢复无进展后处理降级；用户点名路线不得静默替换。

## Codex Verification Checklist

- 当前候选三类项目合同核验通过。
- 1024/1280/1440/1920 四档页面级横向溢出为零。
- A 气泡抽屉、URL 状态、Escape 关闭和回焦通过；全空 AESI 不显示。
- B 跨试验治疗/对照图、8 列默认数据表、基线模糊归组与完成情况图表通过。
- C 360 个矩阵可点击单元格、来源/定位下钻和局部矩阵滚动通过。
- 独立审阅者提出的问题均由 Codex 在当前候选复现或驳回并留证。
