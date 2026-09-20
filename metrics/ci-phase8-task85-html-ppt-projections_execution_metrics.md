# Execution Metrics: ci-phase8-task85-html-ppt-projections

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `grok-build`→`pi/cursor` | `grok-4.6`→`cursor-grok-4.6` | 完成 | 613.929 秒 | runner 记录 | 结构映射完成 |
| `worker_02` | `grok-build`→`pi/cursor` | `grok-4.6`→`cursor-grok-4.6` | 完成 | 1281.989 秒 | runner 记录 | 共享组件与 A 类实现 |
| `worker_03` | `grok-build`→`pi/cursor` | `grok-4.6`→`cursor-grok-4.6` | 报告失败 | 1162.041 秒 + 补交 | runner 记录 | 文件保留；补交治理审计失败 |

原包 `audit-execution` 返回 `ok=false`；没有将失败记录伪装成完成。最终收口另建干净只读执行包。
