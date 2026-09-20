# Task 8.3 实施清单

- [x] 从 Task 8.2 不可变 PDF 哈希建立 Task 8.3 Trellis 恢复点。
- [x] 建立 `src/ci_workflow/qc/pdf.py` 只读验收合同（执行者已完成，待 Codex 集成复核）。
- [x] 扩展 `tools/verify_pdf.py`：逐页文本、原始页图、contact sheet 与哈希绑定（执行者已完成，待 Codex 集成复核）。
- [x] 新增 `tests/acceptance/test_pdf_outputs.py`，覆盖计划要求的全部结构和证据条件（执行者已完成，待 Codex 独立复跑）。
- [x] 对 A10/B24/C20 全部 54 页执行当前渲染与机器检查（执行者报告全绿，尚未构成最终接受）。
- [x] 在标准 PDF 阅读器中验证打开、中文选择/检索和书签导航。
- [x] 完成隔离视觉审阅、缺陷修复复测与 Codex 逐页终验。
- [x] 更新 Phase 8 检查点并可恢复清理 Task 8.3 临时缓存。
