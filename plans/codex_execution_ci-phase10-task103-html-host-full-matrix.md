# Codex Execution Plan: ci-phase10-task103-html-host-full-matrix

Objective: 实现并验收 Task 10.3 首版站点式 HTML 与 Codex/Hermes/OMP 三宿主全矩阵预演；严格遵守 ADR 0013，不生成 PDF、HTML-PPT 或 PPTX，不提前关闭 Task 10.6/恢复/切换责任。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现 acceptance catalog HTML-only 真值解析、输入摘要核验和空项目失败关闭合同。 | `runs/execution/ci-phase10-task103-html-host-full-matrix/worker_01.md` |
| `worker_02` | 实现 pre-RC runner 的项目运行、A/B/C 三个 HTML 当前产物与真实浏览器 verdict 顺序绑定。 | `runs/execution/ci-phase10-task103-html-host-full-matrix/worker_02.md` |
| `worker_03` | 实现 required-v12 full-matrix 场景 rehearsal 回执，并保护 recovery、legacy 与未来格式责任不被误关闭。 | `runs/execution/ci-phase10-task103-html-host-full-matrix/worker_03.md` |
| `worker_04` | 接入候选安装根 Codex/Hermes/OMP 三宿主真实 smoke 与最终项目核验，补齐失败关闭测试。 | `runs/execution/ci-phase10-task103-html-host-full-matrix/worker_04.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
