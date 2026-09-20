# Task 9.4 最终验收记录

时间：2026-09-01（Asia/Shanghai）

## 当前状态

- Task 9.4 已完成并通过治理验收。
- 三宿主薄适配器、统一 `HostReceipt`、`host-smoke-v1`、HA01–HA10 合同和源码级真实宿主调用已实现。
- 当前真实宿主调用均为源码 checkout 证据；Task 9.5 完整 `.tar.zst` Skill bundle 的 fresh-install 与三份 `path_resolved` 回执尚未执行。
- 首版真实交付范围仍只有站点式 HTML；未进入 PDF、HTML-PPT 或 PPTX 集成。

## 本轮已完成

- 独立 CodeBuddy 会商首轮发现：成功结果词汇映射、特殊方法越权、候选包布局与语义摘要边界问题。
- 已修复 runner 的 `rendered → completed` 映射，并在会商复审后继续修复 verifier 的同一映射，消除 runner/verifier 不对称。
- 已禁止宿主适配器覆写可截获共享状态的特殊方法，并加入 `__setattr__`、`__getattribute__` 反例。
- 已明确 Task 9.5 候选物为完整 `.tar.zst` Skill bundle；Python wheel 只承载 CLI，不承担完整 fixture/manifest 资源。
- 已明确 `semantic_receipt_digest` 是受整份回执自摘要保护的运行点诊断摘要，不单独作为事后真实性判据。
- 已落盘三宿主真实源码级冒烟证据：`reviews/ci-phase9-task94-host-adapters/live_host_smoke_evidence.md`。

## 已执行检查

- 修复前后聚焦集合：`115 passed`。
- 完整 integration：`347 passed`。
- 最新 verifier 对齐后的定向集合：`49 passed`。
- Ruff：通过。
- strict mypy：通过（7 个相关源码文件）。
- `ci-workflow package verify --root .`：通过，`0.1.0a0`。
- 目标差异 `git diff --check`：通过。
- CodeBuddy 同一会话最终复审：P0=0、P1=0、P2=0。

## 会商与治理状态

- Conference task id：`ci-phase9-task94-host-adapters`。
- CodeBuddy session：`fbb48d06-659c-461f-bfb7-cb98c0d19be5`。
- 首轮：`runs/conference/ci-phase9-task94-host-adapters/general_single_object.md`。
- 第一次复审：`runs/conference/ci-phase9-task94-host-adapters/general_single_object_round2.md`。
- verifier 对齐修复后的同会话最终复审已完成：`runs/conference/ci-phase9-task94-host-adapters/general_single_object_round3.md`。
- Conference review/metrics、execution review/metrics、两个 review-gate 与 `audit-execution --require-conference` 均通过。

## 下一安全动作

进入 Task 9.5：构建完整 `.tar.zst` Skill bundle，在隔离目录 fresh-install，并从 Codex/Hermes/OMP 三个真实安装入口生成三份 `path_resolved` 回执；不得把 Task 9.4 的源码 checkout 证据复用为最终包验收。

## 保留与清理边界

- 未执行任何 git reset、checkout、stash 或宽泛清理；用户与其他任务的脏工作树全部保留。
- `tmp/task94-live/` 与 `tmp/task94-wheel-inspect/` 是本任务临时目录；在 Task 9.4 证据归档和治理验收前不要删除。清理时只使用解析后的明确路径。
- 当前无后台测试或会商进程；最后一个定向测试已正常退出，退出码 0。
