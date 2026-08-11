规定场景全部通过。以下为最终复核报告（runner 持久化至 `runs/pi_ci_phase2_task26_ingestion_locators_followup2.md`）。

# Task 2.6 最终同 session 修复复核

## 结论

**PASS** — 建议接受。机械检查 6/6 真实重跑通过，规定对抗场景全部按预期拒绝，**P0=0、P1=0、P2=0**。上一轮残余 P2（PDF 顶层 `table_name`/`column_name` 未入 locator_id 承诺）已完全修复并实证；累计三轮全部缺陷闭环，无新缺陷。本会话早前已全文读取 `/Users/smkzw/.hermes/SOUL.md`（267 行，含此前显示截断的 §12 尾部），本轮继续遵守其委托合同。

## 运行证据

读取：`locators.py`（589 行）、`test_fragment_locators.py`（316 行，含 `tampered_table_name`/`tampered_column_name` 断言）。`stat` 确认两文件 mtime（1786466511）与上轮修复轮一致——无新变更落盘，磁盘状态即上轮已验证的修复态。

| 门 | 命令 | 结果（本轮重跑） |
|---|---|---|
| 1 | `uv run pytest tests/unit/test_source_classifier.py tests/integration/test_fragment_locators.py -q` | **5 passed in 0.04s** |
| 2 | `uv run pytest -q` | **178 passed in 5.60s** |
| 3 | `uv run ruff check src tests` | **All checks passed!** |
| 4 | `uv run mypy --strict src` | **Success: no issues found in 40 source files** |
| 5 | `uv run ci-workflow package verify --root .` | **PACKAGE_OK version=0.1.0a0** |
| 6 | `git diff --check` | exit 0 |

## 唯一复核目标：PDF 顶层 table_name/column_name 入 locator_id

**代码核对**：`create_pdf_table_cell_locator` 与 `reopen_pdf_table_cell_locator` 两侧 `stable_id` 均承诺 `(kind, source_version_id, content_sha256, page_number, table_name, row_number, column_name, evidence_locator_json)`；重开先重算身份，不匹配即抛"PDF 定位器身份校验失败"，再进入取值解析。

**规定场景对抗探查**（同页两张合法表 `表 3 安全性汇总`/`表 4 疗效汇总`，各 3 列；locator_id 保持不变）：

| 攻击 | locator_id 是否未变 | 结果 |
|---|---|---|
| 仅篡改顶层 `table_name`→`表 4 疗效汇总`（同页合法兄弟表） | 是 | **读取任何值前抛"PDF 定位器身份校验失败"** |
| 仅篡改顶层 `column_name`→`安慰剂组`（同表合法列） | 是 | **读取任何值前抛"PDF 定位器身份校验失败"** |
| 篡改为不存在的表名/列名 | 是 | 同样在解析前以"身份校验失败"拒绝 |
| 合法定位 | — | 仍返回原单元格 `3.0%`；攻击后重复重开仍 `3.0%`；`表 4` 合法定位 `-0.8%` 正常 |

辅助证据：4 种表/列组合的 locator_id 全部不同（`ids distinct: True`），证明 `table_name`/`column_name` 实际参与承诺计算，非仅校验路径。

## 缺陷

无（P0=0、P1=0、P2=0）。三项累计缺陷（首轮坐标静默改指、同页重复表名迟拒、本轮目标 PDF 顶层字段）全部闭环。

## 剩余边界

1. **Task 2.7 事实/声明链未实现**："定位器重开值 == 片段原文"的最终闸门必须由 ER01–04 实现；Task 2.6 内无无定位器写值路径，本轮未提前接受也未误判。
2. **结构定位合同 ≠ 真实 HTML/PDF 抽取质量**：真实抽取器须产出满足本合同（页/表名唯一/行列规范）的快照，其质量属后续任务。
3. **身份校验是完整性而非密码学防伪**：`stable_id` 可被知晓代码者重算，防管线漂移/意外损坏/随手篡改，与威胁模型一致。
4. **未跟踪文件**：摄取模块与两个新测试仍为 `??`；磁盘状态已全门通过，提交由 Codex 完成。
5. red.txt 历史 RED 无法在当前树复核（只读、无对应提交）；GREEN 已独立机械重跑，未依赖构建者自评。
