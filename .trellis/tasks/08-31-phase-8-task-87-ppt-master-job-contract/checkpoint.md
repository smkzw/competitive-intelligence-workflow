# Task 8.7 检查点

## 当前状态

Task 8.7 已完成并通过 Codex 独立验收。类型化合同、JSON Schema、原子作业存储、全局串行锁、阶段收据、暂停恢复和失败关闭均已落盘并实跑。本检查点不宣称 PPTX 成片、PowerPoint 或逐页视觉通过。

## 本次补充工件

- 架构合同：`docs/architecture/format-contracts/pptx-master-job.yaml`
- 中文操作指引：`docs/acceptance/runs/8.7/ppt-master-job-operator-guide.md`
- 正负测试向量：`tests/fixtures/pptx-master-job/contract-vectors.json`
- 文档/向量一致性测试：`tests/contract/test_ppt_master_job_contract_vectors.py`
- Trellis 记录：本目录的 `prd.md`、`design.md`、`implement.md`、`task.json` 与本检查点。
- 类型化实现：`src/ci_workflow/application/ppt_master_job.py`
- JSON Schema：`schemas/ppt-master-job.schema.json` 与安装包内同名副本。
- 运行时测试：`tests/contract/test_ppt_master_job.py`

## 合同覆盖

- A/B/C 三个正例：暂停恢复边界、已锁定快照、九阶段完成后待独立验收。
- 四个负例：租约过期、阶段错序、跨报告快照污染、前置产物摘要漂移。
- 固定九阶段：初始化 → 内容策略与设计锁定 → 逐页 SVG → 质量检查 → 备注 → 收尾处理 → 原生导出 → 可编辑性核验 → 原分辨率逐页视觉检查。
- 严格串行：全局 PPT Master 锁最多一个活动作业和一个活动阶段尝试；A/B/C 不因报告不同而并行。
- 恢复前置校验：作业/报告/快照身份、合同版本、收据链、前置产物摘要、租约和活动锁全部核对；恢复不依赖文件修改时间。
- 生成器只能到 `ready_for_acceptance`，不得自行写入 `accepted`。

## 已执行检查

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

同时复跑相关格式合同、设计合同、包清单和能力预检，共 `45 passed`；根目录与安装包内 Schema 完全一致。未运行 PPT Master 成片生成、PowerPoint、Office、原生渲染或视觉验收。

## 证据边界与下一步

本步仅接受作业控制层。下一步为 Task 8.8：依据已锁定报告快照，按 A → B → C 严格串行生成可编辑 PPTX；Task 8.9 再进行 OOXML、原生 PowerPoint 和逐页视觉验收。不能把本记录外推为 PPTX 或 PowerPoint 接受。
