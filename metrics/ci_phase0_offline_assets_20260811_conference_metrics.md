# Conference Metrics: ci_phase0_offline_assets_20260811

Date: 2026-08-11

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `general_pi_qwen38` | `cms-smk` | `cms-model` | 完成 | 610.524 秒 | runner 未单列 | 119,379（含缓存） | 初审 P1；同会话修复复验 PASS |
| `general_grok45` | `grok-build` | `grok-4.5` | 完成 | 369.990 秒 | runner 未单列 | 1,757,135（含缓存） | 两次权限取消不计；同会话实测 P1；修复复验 PASS |

## Timeout And Retry Evidence

- Pi 模型目录健康探测 90 秒超时；按全局规则仍进行一次 live route，实际成功创建 session 并完成，不 fallback。
- Grok 健康探测成功。其 `plan` 权限模式连续两次在工具动作前 `stopReason=cancelled`，输出只有进度句，Codex明确拒绝这两次空壳成功。
- Grok 保持原 session/model/provider，将权限模式改为自动批准只读命令后完成 229.756 秒实测；修复后再用同 session 67.853 秒复验。没有使用 Cursor/Minimax fallback。
- 两个 provider 均保留 session ID、终态、时长、usage 和 runner-owned 输出摘要；未因延迟重派。

## Quality Decision

两名独立参与者均发现同一实际 P1，证明会议不是形式性同意。最小修复后，两人各自用坏路径/坏字节变异证明合同 fail closed，并给出 P0=0、P1=0 的 PASS。会议产出被 Codex 复核并纳入最终 Task 0.3 接受；被取消的 Grok 空输出未计入结论。
