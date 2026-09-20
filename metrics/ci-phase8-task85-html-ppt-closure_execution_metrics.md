# Execution Metrics: ci-phase8-task85-html-ppt-closure

| Role | 声明路由 | 实际完成路由 | Status | Duration | Result |
|---|---|---|---|---:|---|
| `worker_01` | `grok-build/grok-4.6:medium` | `pi/cursor/cursor-grok-4.6:medium` | 完成 | 133.723 秒 | 哈希、页数、离线与覆盖一致 |
| `worker_02` | `grok-build/grok-4.6:medium` | `pi/cursor/cursor-grok-4.6:medium` | 完成 | 234.964 秒 | 22 项测试、Ruff、浏览器抽查通过 |
| `worker_03` | `grok-build/grok-4.6:medium` | `pi/cursor/cursor-grok-4.6:medium` | 完成 | 161.681 秒 | 会商与 Trellis 记录审计完成 |

Grok Build 均在建立可恢复会话前终止；runner 使用已声明回退链。`audit-execution` 返回 `ok=true`。
