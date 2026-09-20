# Codex Execution Plan: ci-r2-review-runtime-fixture-rebaseline-20260905

Objective: 关闭 R2 的真实独立复核授权边界，并重基线 HTML-only 活跃验收：真实回执是科学状态迁移唯一授权；preview fixture 快照语义可运行但不可被接受；非 HTML 测试保留且与 v1 release gate 明确分层。不得触碰旧根，不得宣称 R2 或 RC 完成。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 设计并实现 B/C 两阶段科学复核状态迁移：候选先为 rendered_unreviewed，真实 scientific-review-v1 回执经实际文件字节与权威 ScientificQcCurrentContext 绑定后才生成 scientifically_reviewed_rendered_candidate；缺回执、伪回执、同会话、自审、旧内容和宿主不可用全部失败关闭。 | `runs/execution/ci-r2-review-runtime-fixture-rebaseline-20260905/worker_01.md` |
| `worker_02` | 审计并修复 report-data preview fixture 的报告快照合同：调用方声明但项目中不存在的快照不得被信任；开发预览应可确定性生成自身 snapshot 并保持 rendered_unreviewed，且不能进入视觉/真实来源/RC 接受。覆盖单报告与 three-report-complete。 | `runs/execution/ci-r2-review-runtime-fixture-rebaseline-20260905/worker_02.md` |
| `worker_03` | 建立 HTML-only v1 活跃 pytest/验收分层并修复与当前科学合同冲突的旧断言：保留 PDF/HTML-PPT 源码和基础回归，不把它们算作 v1 release gate；审计 B 抽屉分子分母断言，禁止从百分比反推或回填未报告 n/N；输出可复现的全量债清单。 | `runs/execution/ci-r2-review-runtime-fixture-rebaseline-20260905/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
