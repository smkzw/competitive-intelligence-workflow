# Execution Output:

## Boundary And Context Check

- **任务**：Task 3.3 第二轮修复（repair2），关闭 Codex 发现的 10 项 P0/P1 假绿。
- **硬边界已遵守**：未 commit；未改 Trellis/context/review/metrics/prompt/runner 报告（`runs/pi_ci_phase3_task33_repair2.md` 未用工具写）；只改任务范围内源/schema/三份测试/包导出；未动 Task 3.1/3.2 与 Task 3.4+ 面；未做安全测试、无 OCR/联网/UI。
- **本 turn 复核**：精确三文件命令仍 **3 passed**；工作区恰为允许交付文件（2 修改 + 4 新增，含先前的 `package-manifest.json` 登记），无漂移。

## Work Performed

1. **F1 真实 GateSpec**：删除 `GateSpecInput`；`create_request` 接收真实 `GateSpec`，从批准 YAML 重载并校验 `spec_id`/`spec_fingerprint`/`report_kind` 与每个单元的 `blocking_level=critical`；B spec 用于 C、修改过 spec、`non_blocking`、扩展单元、未知单元全部在写请求/目录/列表前失败。
2. **F2 类型化守卫**：`gap_still_open`（False 拒绝）+ `expected_to_close_units`（非空、关键、须覆盖所缺字段）——"主文/登记/监管已足够则不再请求"的机械形式。
3. **F3 身份**：请求身份含报告/产品试验/文档角色/DOI-PMID-登记+标题/附件链接/排序关键单元/spec 指纹；同参重建返回既有记录（状态/时间戳不变、列表单条）；同 ID 身份漂移经 `_save_request` 身份字段比对失败关闭；同试验同缺口不同文档身份不同。
4. **F4 attempt/事件**：模型新增 `attempt_number` 并纳入全部事件 event_id/幂等键/守卫；`re_request` 写声明迁移事件并递增；`mark_not_required` 改走 `_transition` 声明守卫路径；两次同字节坏下载产生不同 attempt 事件，attempt 内重放经 EventStore 去重。
5. **F5 多文件分支**：修复原未覆盖分支；逐文件校验/识别，无效/错误页按摘要隔离；恰一合法目标→接受；多合法→全部按歧义隔离；合法+登录页无需删文件即可恢复；无合法目标时声明 `awaiting_user→needs_re_download`。
6. **F6 规范化匹配**：NCT 大写、DOI casefold+去尾标点、PMID 数字形式；精确 DOI 唯一足够、DOI+NCT 强、NCT/PMID 单独需有义标题片段；扫描器自动比对其他活跃请求（不依赖调用方候选列表）。
7. **F7 PDF/一致性**：`_pdf_text_and_metadata` 真实解析并合并标题/主题/关键词+页面文本，解析失败即不可读；`publication_pdf` 必须真实 PDF（HTML 拒绝）；`detect/match/accept` 全部强制文件名/媒体类型/内容一致，`text/plain` 字节命名 `.pdf` 在直接 API 上被拒；假接受测试换成真实 reportlab PDF + HTML 拒绝 + 直接 API 拒绝回归。
8. **F8 作业/归档**：`_append_re_extraction_job` 按 job_id 幂等且冲突感知（同 ID 同内容 no-op、异内容失败）；接受幂等短路防崩溃重放重复；规范归档预存按摘要校验（漂移拒绝复用）；模型+schema 对 matched/accepted 强制匹配标识符、作业 ID、项目相对路径。
9. **F9 列表重生成**：`logs/download_requests.md` 从物化请求原子重生成，只列活跃待办、每请求一次；已接受/不再需要消失；无待办显示"当前无需补充资料"；无内部状态/GateSpec/✓。
10. **F10 死代码**：删除重复 `_download_list_line`（grep 计数 0），保留 `_request_list_line`；为每项 finding 添加直接回归。

## Artifacts And Evidence

- 修改：`src/ci_workflow/ingestion/manual_inbox.py`（重写）、`src/ci_workflow/ingestion/__init__.py`（去 `GateSpecInput` 导出）、`schemas/download-request.schema.json`（+`attempt_number`，强化 accepted 守卫）、`package-manifest.json`（先前登记）。
- 重写三份测试（每文件恰 1 顶层节点）：`test_download_request_transitions.py`、`test_manual_inbox_recovery.py`、`test_user_filename_auto_rename.py`。
- 实测：真实 reportlab PDF 经 `publication_pdf` 接受；小写 nct/DOI 尾标点规范化唯一匹配；规范文件名含角色/摘要、原文件名仅元数据；隔离按摘要消歧路径；下载列表无待办显示"当前无需补充资料"。

## Commands And Observations

- 精确三文件命令：**3 passed**（本 turn 复核仍 3 passed）
- Task 3.1/3.2 回归 + 合同（trio+quartet+manifest/replay/content-store）：**245 passed**
- 全库 pytest：**432 passed**；Ruff `src/ tests/`：All checks passed；strict mypy `ci_workflow.ingestion`：Success 6 files
- Schema：持久化记录含 `attempt_number` 通过 `download-request.schema.json`；accepted 缺 `matched_identifiers` 负例被拒；`ci-workflow package verify`：PACKAGE_OK 0.1.0a0；`git diff --check`：clean
- 10 项 finding 回归映射 grep 全 PASS；`_download_list_line` grep 计数 0。

## Blockers Or Missing Environment

无阻塞。残留边界（Codex 验收点）：登录/错误标记为策展语境清单（新措辞登录墙可能漏检，无 OCR）；`re_request` 递增 attempt 并写事件但不清理已隔离文件（用户需放新文件）；PDF 依赖 pypdf 文本层/元数据，纯图像 PDF 按不可读隔离（无 OCR 范围）；多合法目标隔离后的中文措辞建议 Codex 对照产品合同复核。

## Rerun Requests Or Next Step

- **重跑请求**：无。精确三文件 3 passed 已复核，交付完整。
- **下一动作**：Codex 审查三份测试与 `manual_inbox.py`，对真实 publication/supplement 页面验证登录墙检测与标题/DOI 匹配，运行 Phase 3 正式命令；验收后 commit（建议信息：`fix: repair task 3.3 manual inbox (round 2)`）。
