已收到更宽测试集结果。结论：**不改变 Task 10.1 的“接受（附非阻断说明）”建议**；4 个失败均不在 Task 10.1 合同范围内。

---

## 背景作业结果与 Task 10.1 关系

**全量结果：** `480 passed, 4 failed, 1 skipped`

| 失败项 | 根因 | 与 Task 10.1 关系 |
|---|---|---|
| `test_native_pdf_slice.py` ×3 | 环境缺少 `pdftotext` | **无关** — Phase 8 PDF，且 ADR 0013 下非首版阻断 |
| `test_offline_assets.py::test_html_ppt_runtime_...` | 运行时缩放公式与合同断言不一致 | **无关** — Phase 8 HTML-PPT，首版 HTML-only 不阻断 |

**Task 10.1 范围内测试（此前复核）：**
- `tests/acceptance/test_fixture_catalog.py` — 通过
- `tests/contract/test_package_manifest.py` — 通过  
- `tests/hosts/test_fresh_install.py`（含 `fixtures/acceptance` / `matrix.md` bundle 检查）— 通过

这 4 个失败**不构成 Task 10.1 当前范围缺陷**，也不推翻“18 族 / ADR 0013 / 摘要可重算 / 责任分层 / 矩阵冻结”的闭合判断。

---

## 对两类失败的简要定性（供 Codex 路由，非 10.1 阻断）

1. **PDF slice（3 项）**  
   - 性质：**环境/工具链**（`pdftotext` 缺失），非 catalog 合同问题  
   - 建议：在验收环境补齐 poppler/pdftotext，或标记为 RED 环境前置条件；**不归入 Task 10.1**

2. **HTML-PPT offline assets（1 项）**  
   - 性质：**Phase 8 实现与合同断言漂移**（`fitDeckToViewport` vs 期望的 `Math.min(window.innerWidth/1280, ...)`）  
   - 建议：由 Phase 8 / 格式恢复轨道处理；**首版 HTML-only 下非 10.1 阻断**

---

## Task 10.1 最终建议（维持）

**接受，附非阻断后续说明（accept with nonblocking future notes）**

- **当前范围（矩阵冻结）：** 已闭合  
- **未来执行（10.2 / 10.6 / 10.8 / E1）：** verifier 实现、receipt 落盘、fresh-source 与 RC 证据 — 仍属后续任务  
- **相邻仓库健康：** 上述 4 项失败应单独跟踪，**不得**作为拒绝 Task 10.1 的理由  

若 Codex 需要单一收口表述：

> Task 10.1 验收矩阵合同可接受；全库 4 失败为 PDF 工具链与 HTML-PPT 合同漂移，与 10.1 正交，建议并行修复但不阻塞 10.1 治理关闭。
