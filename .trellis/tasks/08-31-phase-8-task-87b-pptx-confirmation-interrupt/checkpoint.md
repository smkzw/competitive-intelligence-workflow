# Task 8.7b 检查点

## 当前状态

2026-08-31 按用户要求无损暂停。Task 8.7 作业控制合同已经完成；Task 8.7b 的来源包和八项确认合同已由前两名执行者完成，第三名执行者已写入适配器与图测试，但在完成报告和 Codex 验收前被用户暂停。

同日用户把首次全量交付范围调整为“站点式 HTML 优先，首版可暂不集成 PDF/PPT 导出”。因此本任务转入**首版后续能力**，暂停现场、文件和会话全部保留，不再阻断首版进入 Phase 9。此范围调整不代表本任务完成，也不得进入原计划 Task 8.8。

## 已完成且有执行者证据

- worker_01，会话 `01a056aa-ef83-7000-83bb-430c249ab8e9`：
  - `src/ci_workflow/renderers/pptx_master/source_pack.py`
  - `schemas/pptx-source-pack.schema.json` 及包内副本
  - `tests/renderers/test_ppt_master_source_pack.py`
  - 执行者报告记录 `6 passed`、mypy 与 Ruff 通过。
- worker_02，会话 `01a056c3-326f-7000-812e-5a4266f80e10`：
  - `src/ci_workflow/renderers/pptx_master/confirmation.py`
  - `schemas/pptx-confirmation.schema.json` 及包内副本
  - `tests/renderers/test_ppt_master_confirmation.py`
  - 执行者报告记录与既有合同组合 `24 passed`、mypy 与 Ruff 通过。

## 暂停中的执行者

- worker_03 同一会话：`01a056d3-c835-7000-816c-758c6673fc83`。
- 已写入但尚未由 Codex 接受：
  - `src/ci_workflow/renderers/pptx_master/adapter.py`
  - `tests/graph/test_pptx_confirmation_interrupt.py`
- runner 管理的 `worker_03.md` 仍为 `PENDING`；本次通过 Ctrl-C 中止 runner，未清理会话、提示、日志或工作区文件。
- 暂停时没有运行新的 Codex 独立测试、治理审计、归档、PPT Master、SVG 或 PPTX 生成。

## 暂停时关键摘要

- `source_pack.py`：`78bcb48a7586fc944dbe41eb3594c983383f9be1786f14e7b0badfb3a71b49bb`
- `confirmation.py`：`ec0dac2b6d209a82e3d9f87bf884007a1d932a46ca5dbb1e52b68d4641242101`
- `adapter.py`：`fbc1be6e0692d2e49399d0a86a582c6b384b5184636641e899591a35c104c702`
- `test_pptx_confirmation_interrupt.py`：`e273d7ca68604b7d722488e4b48bbb03cea38ce2a6268305f2a80159e60067c5`

## 后续恢复时的下一安全动作

1. 先核对上述摘要未漂移。
2. 使用原 worker_03 会话 `01a056d3-c835-7000-816c-758c6673fc83` 继续，不创建替代会话；让其完成集成、目标测试和 runner 报告。
3. Codex 独立审阅三名执行者改动，复跑来源包、确认合同、图/CLI 集成和相关回归。
4. 只有治理审计通过后才关闭 8.7b；不得提前进入逐页 SVG 或真实 PPTX 生成。

## 首版当前动作

- 不续跑 worker_03，不启动替代会话。
- 按 `docs/decisions/0013-site-first-v1-delivery-scope.md` 继续站点式 HTML 的宿主、修订刷新、候选包和真实浏览器验收。
