# Codex Execution Plan: ci-r2-terminal-recovery-review-boundary-20260905

Objective: 完成 R2 剩余科学控制：为 fresh B/C 实现两轮不同策略恢复后的类型化双重穷尽终态与审计/证据不足页；绑定可验的独立上下文复核回执；阻止 rendered_unreviewed 预览路径进入发布接受。不得触碰旧根，不得宣称 R2/RC 完成。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 设计并实现 fresh B/C 共用的类型化双重穷尽记录、终端 evidence_blocked 状态、blocker 审计 JSON/Markdown 与简洁证据不足页，先写负向测试且不允许单轮恢复伪装穷尽。 | `runs/execution/ci-r2-terminal-recovery-review-boundary-20260905/worker_01.md` |
| `worker_02` | 设计并实现独立科学复核的不可变宿主回执合同：绑定生产上下文、复核上下文、内容摘要、review artifact digest 和时间顺序；无独立上下文能力时失败关闭，保持三宿主可适配。 | `runs/execution/ci-r2-terminal-recovery-review-boundary-20260905/worker_02.md` |
| `worker_03` | 审计并修复发布接受边界：rendered_unreviewed/report-data/preview 路径可用于开发预览但不得生成可被科学/视觉/RC 接受的后继；补充 fail-closed 合同与回归测试。 | `runs/execution/ci-r2-terminal-recovery-review-boundary-20260905/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

Codex will selectively integrate only changes that satisfy the current v1.3 contract.
Required checks: worker route/output audit; actual diff review; focused RED/GREEN
reproduction; strict type/static checks; full Gate; blocker JSON/Markdown/page byte
inspection; proof that one recovery round and self-asserted review receipts fail closed;
proof that `rendered_unreviewed` cannot create an accepted scientific/visual/RC successor.
No worker may mark R2, RC or release complete.

## Disposition

- [x] All three declared worker commands completed on the primary route.
- [x] Worker reports were imported and independently reviewed.
- [x] Preview-origin acceptance was integrated and verified.
- [x] Existing exhaustion/blocker contracts were reused through a minimal adapter;
  the parallel worker implementation was rejected.
- [x] Scientific review receipt contract and schema were integrated, deduplicated
  against host receipt types, and strengthened with actual artifact-byte verification.
- [x] Formal Gate passed.
- [ ] Wire the verified review receipt into the B/C runtime scientific-state
  transition; until then R2 remains open.
- [ ] Rebaseline stale preview/acceptance fixtures and remove excluded PDF/HTML-PPT
  tests from the active release collection without deleting their source code.
