# R2 终态恢复、独立复核回执与发布边界检查点（2026-09-05）

## 状态

本检查点为无损续接状态，不代表 R2、RC 或发布完成。

- B/C 门槛失败仍先进入 `recovery_required`；只有当前阻断对象与既有
  `DoubleExhaustionRecord` 完全一致时，才复用唯一
  `build_and_write_blocker_package` 进入 `evidence_blocked`。
- `rendered_unreviewed`、`recovery_required`、`evidence_blocked`
  均不能产生视觉或真实来源接受后继。
- 新增 `scientific-review-v1` 不可变回执合同，复用既有宿主可执行文件、
  会话和外部进程证据类型，并在授权时重开审阅产物核验实际 SHA-256。
- 独立回执尚未接入 B/C 运行时科学状态迁移；包内 `reviewer_id` 仍不是
  宿主可验证的最终授权。下一安全动作必须先关闭此边界。

## 会商与取舍

治理执行：`ci-r2-terminal-recovery-review-boundary-20260905`。

- worker 01 的平行穷尽模型整体拒绝：重复已有 `gates.exhaustion` 和
  `gates.blocker_audit`，不符合 YAGNI。
- worker 02 选择性采纳并收敛：删除重复宿主证据模型，注册双份 Schema，
  增加实际审阅产物字节核验；运行时接线保持开放。
- worker 03 接受：预览态发布隔离经独立复核与定向测试通过。
- 路线审计 `audit-execution` 最终 `ok=true`，无 fallback、无 redispatch；
  三份 runner 日志和报告已归档到
  `archives/execution/ci-r2-terminal-recovery-review-boundary-20260905/`。

## 验证证据

- 发布边界定向：17 passed。
- 终态/回执/发布边界及 B/C 相关联合回归：200 passed。
- `tools/gate.sh`：
  - Ruff：通过；
  - strict mypy：203 个源文件通过；
  - unit/contract：919 passed；
  - legacy scan：`LEGACY_REF_OK`。
- `ci-workflow package verify --root .`：`PACKAGE_OK`。
- Schema 两份副本字节一致；`git diff --check` 通过。
- 全量 pytest 如实记录：2,765 passed、1 skipped、20 failed、25 errors。
  失败集中于已排除的 PDF/HTML-PPT 测试、旧预览 fixture 的快照合同、
  旧真实验收根以及两项与“禁止分母回填”冲突的 B 抽屉旧断言；不能宣称
  全仓测试通过。

## 关键文件摘要

- `src/ci_workflow/application/acceptance_boundary.py`:
  `c7b14107d027460e8fb06a424f17ca9fd323e42c4f607750689ce5b2428b8bf4`
- `src/ci_workflow/application/terminal_recovery.py`:
  `8d8049b72ca404c55b56e087e4988c88ff0bb998f5a56a95e68c18cb69975a79`
- `src/ci_workflow/qc/review_receipt.py`:
  `70a1c658e1a40a863c45d0c6163eef8e58874132ffac7f0f12eefcb95fd823b9`
- `schemas/scientific-review-receipt.schema.json`:
  `a1cfb03f5df95572f09c779e9f738be9b545e3e8093161b3c184f5406d0332be`

## 清理

已删除三个完成的隔离 APFS 克隆（清理前逻辑占用约 5.6G、5.6G、5.5G）
以及可再生的 pytest/Ruff/mypy/bytecode 缓存。未删除源码、规范证据、执行
归档、历史测试材料或 Codex 会话状态。

## 下一安全动作

建立一个受控运行时接线切片：

1. 由真实 Codex/Hermes/OMP 外部会话签发 `scientific-review-v1`；
2. 从当前候选、Gate、coverage 和 source refs 重建
   `ScientificQcCurrentContext`；
3. 只有 `require_verified_review_receipt`、实际产物字节核验和
   `bind_receipt_to_production_context` 全部通过，才产生
   `scientifically_reviewed_rendered_candidate`；
4. 重基线旧 preview fixtures 与 HTML-only pytest collection，保留非 HTML
   源码但不让已排除轨冒充 v1 验收。

