# Task 8.7 PPT Master 作业合同验收记录

状态：已通过 Codex 独立验收（仅限 Task 8.7 作业控制合同）

本记录接受 PPT Master 作业控制合同、类型化运行时、JSON Schema、持久化与恢复拒绝逻辑；不接受 A/B/C PPTX 成片，不接受原生 PowerPoint 或逐页视觉结果。生成器最多把作业推进到“待独立验收”，不得自行写入“已接受”。

## 接受对象

- 作业架构合同：`docs/architecture/format-contracts/pptx-master-job.yaml`
- 类型化运行时：`src/ci_workflow/application/ppt_master_job.py`
- JSON Schema：`schemas/ppt-master-job.schema.json`
- PPTX 格式合同入口：`docs/architecture/format-contracts/pptx.yaml`
- 中文操作指引：`docs/acceptance/runs/8.7/ppt-master-job-operator-guide.md`
- 测试向量：`tests/fixtures/pptx-master-job/contract-vectors.json`
- 合同一致性测试：`tests/contract/test_ppt_master_job_contract_vectors.py`
- 运行时正负测试：`tests/contract/test_ppt_master_job.py`
- Trellis 任务记录：`.trellis/tasks/08-31-phase-8-task-87-ppt-master-job-contract/`

## 合同覆盖

| 领域 | 已记录的约束 | 代表证据 |
|---|---|---|
| 快照锁 | 报告、版本、快照摘要、声明/证据快照、coverage 集锁定后不可变 | `snapshot_lock`、A/B/C 正例 |
| 阶段链 | 九阶段、每阶段一份收据、收据链驱动下一阶段 | `stages.order`、C 九收据正例 |
| 串行 | 全局 `ppt_master_global`，最多一个活动作业和阶段尝试 | `serial_execution` |
| 可恢复 | 仅从最新已提交收据的下一阶段恢复，不看文件修改时间 | `resume_job`、A/B 正例 |
| 失败关闭 | 过期、错序、跨报告、前置产物缺失或变化均在下一阶段前拒绝 | 运行时负例与 `rejection_codes` |
| 持久化 | 作业清单以临时文件写入、同步并原子替换 | `PptMasterJobStore` |
| 串行执行 | A/B/C 共用一个原子执行锁，不同报告之间也不能并行 | `PptMasterLeaseStore` |
| 独立验收 | 生成器最多进入 `ready_for_acceptance` | C 正例和 `editable_pptx` 边界 |

## 代表性测试

- 通过：A 暂停于内容策略与设计锁定后，下一阶段为逐页 SVG。
- 通过：B 已完成前三阶段，下一阶段为质量检查。
- 通过：C 九阶段全部提交后进入待独立验收。
- 拒绝向量：租约过期 → `RECEIPT_EXPIRED`。
- 拒绝向量：跳过逐页 SVG → `RECEIPT_OUT_OF_ORDER`。
- 拒绝向量：B 作业携带 C 快照 → `REPORT_MISMATCH`。
- 拒绝向量：前置产物摘要漂移 → `ARTIFACT_DIGEST_MISMATCH`。

已执行：

```text
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/contract/test_ppt_master_job.py \
  tests/contract/test_ppt_master_job_contract_vectors.py -q
20 passed

uv run ruff check src/ci_workflow/application/ppt_master_job.py \
  tests/contract/test_ppt_master_job.py \
  tests/contract/test_ppt_master_job_contract_vectors.py
All checks passed!
```

相关格式合同、设计合同、包清单和能力预检一并复跑，共 `45 passed`。根目录与安装包内的 PPT Master JSON Schema 内容完全一致。

## 验收边界

本步已经实跑创建、锁定、九阶段提交、暂停恢复、过期拒绝、错序拒绝、跨报告/跨快照拒绝、前置产物缺失或变化拒绝、收据篡改拒绝、原子持久化和 A/B/C 全局串行锁竞争。Task 8.8、8.9、8.10 的 PPTX 生成、OOXML、原生 PowerPoint、逐页视觉验收和四格式覆盖仍不属于本记录。
