# Codex Execution Plan: ci_visual_finalization_loop_20260829

Objective: 为竞品调研工作流实现跨 HTML、PDF、HTML-PPT、PPTX 的定稿前视觉策划、候选生成、美化复测与独立放行机制，保持科学快照不可改写并使用项目自有康哲设计合同。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现 visual-design-director 内部 Skill、视觉策划书 schema、安装包清单与验证器。 | `runs/execution/ci_visual_finalization_loop_20260829/worker_01.md` |
| `worker_02` | 把视觉策划书、美化回环和独立视觉结论接入格式节点、守卫与控制图合同。 | `runs/execution/ci_visual_finalization_loop_20260829/worker_02.md` |
| `worker_03` | 补充合同/控制图负例测试并复核 A 类现有门户的兼容边界和中文用户体验。 | `runs/execution/ci_visual_finalization_loop_20260829/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

- Verify skill and schema package closure, graph node/guard semantics, negative tests, and no scientific snapshot mutation path.
- Run focused Ruff/pytest/package validation, then inspect the current A report in real Chromium and WebKit for compatibility.
- Require a separate visual conference before accepting the mechanism; worker self-reports are not final acceptance.
