# Codex Main-Venue Plan: ci_phase0_offline_assets_20260811

Date: 2026-08-11
Objective: 独立只读验收离线 Logo、ECharts 6.1.0 与中文 HTML-PPT 固定运行时，主动验证来源、离线性、跨浏览器行为和假绿边界

## Task Decomposition

1. 来源与许可：重算 Logo、ECharts、HTML-PPT 上游和衍生文件摘要，核对版本、许可与来源清单。
2. 运行行为：真实打开 `file://` 样稿，覆盖 Chromium/WebKit、导航、页码、逐字稿、演讲者视图、计时、双窗和预览。
3. 假绿挑战：检查静态测试是否能被错误文件、旧摘要、联网资源、英文界面或缺失功能绕过。
4. 独立结论：两名参与者各自给出 PASS/FAIL；Codex 只在 P0/P1 关闭并亲自复核后接受。

## Source Packet

以 conference context 的 Source Of Truth 为唯一审查包；旧工程与通用设计目录不进入运行依赖，不访问网络，不实现报告页面。

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_pi_qwen38` | `cms-smk` | `cms-model`（北京时间日间替代） | `runs/conference/ci_phase0_offline_assets_20260811/general_pi_qwen38.md` |
| `general_grok45` | `grok-build` | `grok-4.5` | `runs/conference/ci_phase0_offline_assets_20260811/general_grok45.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

由 runner 记录开始/结束、session、模型、终态和 fallback 原因；慢响应保持 pending，只有明确终态故障才按已声明链路切换，同一会话问题优先 follow-up。

## Codex Verification Checklist

- [ ] 两条提示词 preflight 通过，模型/提供方与日间替代正确。
- [ ] 两名参与者均有 runner-owned 完整输出且未互读。
- [ ] 所有 P0/P1 有文件级复现和最小修复，或明确无 P0/P1。
- [ ] Codex 重跑静态/浏览器/全量测试并人工打开三张实际截图。
- [ ] review gate 通过，Trellis 回写，精确清理测试临时目录后再提交。
