# Conference Metrics: ci_phase0_contract_review_20260810

Date: 2026-08-10

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `general_pi_qwen38` | `cms-smk` | `cms-model` | completed | 413.967 s live + 90.017 s diagnostic | not reported | 69,509 | incorporated after Codex reproduction |
| `general_grok45` | `grok-build` | `grok-4.5` | completed after same-session recovery | 16.557 s cancelled + 113.745 s final | not reported | 91,882 cancelled; 98,299 final | static findings incorporated selectively |

## Timeout And Retry Evidence

- Pi declared `alibaba/qwen3.8-max` but the executable Beijing daytime policy selected `cms-smk/cms-model`. The 90.017-second provider health check timed out; policy correctly allowed one live attempt. The live session `019feb40-3b50-7000-8f0b-8c4a0700dc6e` completed in 413.967 seconds with `stop_reason=stop`; no fallback occurred.
- Grok session `c3980202-b8e9-4342-b7d2-2d32f6768129` retained the same session ID. The first recorded round ended `cancelled` after 16.557 seconds and was rejected as incomplete. The recovery round ended `end_turn` after 113.745 seconds and produced the required six-section report. No provider/model fallback occurred.
- Runner未报告可靠 API call 计数，因此表中明确记为 `not reported`，没有用 turn 数伪造 API 调用数。

## Quality Decision

会议对 Phase 0 产生了实质增益：四项假绿缺口被 Codex 复现并修复。Pi 输出可作为实证复核；Grok 只作为静态挑战来源，其被取消轮次和未完成的外部文件测量不作为验收锚点。最终接受仍以 Codex 的确定性命令、实际文件摘要和未越过用户授权边界为准。
