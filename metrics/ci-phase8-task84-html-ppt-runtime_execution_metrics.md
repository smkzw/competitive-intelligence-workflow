# 执行指标：ci-phase8-task84-html-ppt-runtime

| Role | 声明路由 | 实际完成路由 | Status | Duration | Result |
|---|---|---|---|---:|---|
| `worker_01` | `grok-build/grok-4.6` | `pi/cursor/cursor-grok-4.6:medium` | 完成 | 273.733 秒 | 差距审计与最小修补 |
| `worker_02` | `grok-build/grok-4.6` | `pi/cursor/cursor-grok-4.6:medium` | 完成 | 729.967 秒 | 固定运行时合同 |
| `worker_03` | `grok-build/grok-4.6` | `pi/cursor/cursor-grok-4.6:medium` | 完成 | 343.226 秒 | 真实浏览器证据 |

Grok Build 在可恢复会话建立前终止；runner 依声明回退链转入 Cursor Grok，未任意替换模型。治理审计 `ok=true`。

独立确定性验证：18 项浏览器合同测试全部通过，Chromium/WebKit 各四个视口，八张原始截图。
