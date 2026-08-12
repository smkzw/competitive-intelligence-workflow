# Execution Output:

## Boundary And Context Check

- **任务**：Task 3.3 修复轮（Codex 拒绝后授权有界修复），14 项缺陷全修。
- **硬边界已遵守**：未 commit；未改 Trellis/context/review/metrics/prompt/runner 报告（`runs/pi_ci_phase3_task33_repair.md` 未用工具写）；未动 Task 3.1/3.2 源码测试与 Task 3.4+ 面；未做安全测试、无 OCR/联网/UI。
- **本 turn 复核**：精确三文件命令仍 **3 passed**；git 工作区恰为允许交付文件（2 修改 + 4 新增，外加先前 `package-manifest.json` 登记），三个错误命名的旧测试文件已删除，无漂移。

## Work Performed

1. **测试重构（缺陷1）**：删除 `test_manual_inbox_download_lifecycle.py`、`test_manual_inbox_content_identification.py`、`test_manual_inbox_idempotent_replay.py`；新建精确三文件 `test_manual_inbox_recovery.py`、`test_user_filename_auto_rename.py`、`test_download_request_transitions.py`，每文件 1 个顶层测试节点，子用例矩阵内聚。
2. **`manual_inbox.py` 全量修复**：
   - 缺陷2：`create_request` 即建收件目录；`logs/download_requests.md` 追加式中文清单（标题/原因/落地页+附件链接/唯一相对目录/无需重命名）；accept/not_required 更新清单。
   - 缺陷3：`scan_and_process_inbox` 真实文件系统扫描（零文件→None、隐藏/临时跳过、多文件→隔离、单合法→接受），不依赖调用方传文件名/内容。
   - 缺陷4：`stable_id` 纳入 `sorted(missing_fields)`，同试验不同缺口/文档互不覆盖；同参重建返回既有记录。
   - 缺陷5：`GateSpecInput` 绑定 spec_id/fingerprint；missing_fields 必须 ∈ critical_unit_ids；B trial-disposition、C 统计/设计扩展即使标为 blocking 也拒绝。
   - 缺陷6：事件 event_id/幂等键纳入 `effective_digest`（内容 sha256 或 request_id），新文件在 `needs_re_download→awaiting_user` 后产生全新事件，同参重放去重；`re_request` 不再写冲突事件（状态重置落请求记录）。
   - 缺陷7/14：`_append_jsonl`/`_append_download_log`/`_save_request` 全部原子读-追加-写，保留多行账本全部记录；≥2 作业/2 请求回归通过。
   - 缺陷8：accept 持久化 `source_version_id`/`canonical_relative_path`/`re_extraction_job_ids` 到请求；schema+Pydantic 状态守卫拒绝 matched/accepted 缺身份/摘要/归档元数据。
   - 缺陷9：库目录只含规范文件，原文件名仅元数据；收件副本在规范归档+事件/状态可恢复后才删除；重放不重复。
   - 缺陷10：`.pdf` 无 `%PDF` 签名拒收（HTML/纯文本字节不行）；HTML 错误/登录页不能作来源；提取 PDF 元数据。
   - 缺陷11：DOI 精确唯一即足够；DOI+试验ID 强；单标识符+有义标题足够；文件名永不参与；"Supplementary appendix" 标题的合法补件通过。
   - 缺陷12：登录/错误检测收窄到真实页面语境（"sign in to view"/"access denied"/"登录后查看"等），"measurement error"/"not found in subgroup" 不再误隔离。
   - 缺陷13：隔离文件存于摘要消歧相对路径，路径+原因持久化，一句中文可执行说明，不覆盖已接受内容，后续合法文件可恢复同请求。
3. **schema**：`download-request.schema.json` 增补 6 字段并强化 accepted 状态守卫（需 canonical_relative_path/source_version_id/jobs）。
4. **`__init__.py`**：导出 `GateSpecInput` 与新 API。

## Artifacts And Evidence

- 新增/修改：`src/ci_workflow/ingestion/manual_inbox.py`、`src/ci_workflow/ingestion/__init__.py`、`schemas/download-request.schema.json`、`package-manifest.json`（先前登记）、三份精确测试。
- 已删除：三个错误命名旧测试文件。
- 实测：任意文件名 HTML 补件被接受，规范名 `nct001-supplementary-material-v1-<digest8>.html` 进库，原文件名仅元数据；下载清单含 create+accept 条目；quarantine 摘要消歧路径+中文说明落盘。

## Commands And Observations

- 精确三文件命令：**3 passed**（本 turn 复核仍 3 passed）
- Task 3.1/3.2 回归 + 合同（trio+quartet+manifest/replay/content-store）：**245 passed**
- 全库 pytest：**432 passed**；Ruff `src/ tests/`：All checks passed；strict mypy `ci_workflow.ingestion`：Success 6 files
- Schema：`download-request.schema.json`/`event.schema.json` 对持久化记录通过；accepted 缺 `canonical_relative_path`/`source_version_id` 负例被拒；Pydantic accepted 守卫通过
- `ci-workflow package verify`：PACKAGE_OK 0.1.0a0；`git diff --check`：clean

## Blockers Or Missing Environment

无阻塞。残留边界：登录/错误标记为策展语境清单（新措辞登录墙可能漏检，Codex 需真实页面验证）；`re_request` 有意不写事件（状态重置），若 Codex 要求该迁移也落事件需另行设计按次幂等键；PDF 元数据依赖 pypdf 可用层。

## Rerun Requests Or Next Step

- **重跑请求**：无。精确三文件 3 passed 已复核，交付完整。
- **下一动作**：Codex 审查三份测试与 `manual_inbox.py`，对真实 publication/supplement 页面验证登录墙检测与标题/DOI 匹配，运行 Phase 3 正式命令；验收后 commit（建议信息：`fix: repair task 3.3 manual inbox defects`）。
