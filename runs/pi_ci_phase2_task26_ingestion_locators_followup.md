复核完成，结论明确。以下为最终报告（runner 持久化至 `runs/pi_ci_phase2_task26_ingestion_locators_followup.md`）。

# Task 2.6 同 session 修复复核

## 结论

**FAIL** — 首轮两项 P2 中一项完全修复、一项仅部分修复；残留 1 个 P2 直接违反本轮回合目标 1，按本轮硬性标准（机械全过且 P0/P1/P2=0 才可 PASS）判定 FAIL。计数：**P0=0、P1=0、P2=1**。机械门 6/6 真实重跑通过（详见 §运行证据），缺陷判定基于对抗探针，不采信构建者自评。

## 运行与读取证据

读取：`locators.py` 全文（585 行，与上一轮逐字节一致）、`test_fragment_locators.py`（316 行，与上一轮一致）。`stat` 确认两文件 mtime（1786466136 / 1786466098）与上一轮完全相同——自上次派发后**无新修复落盘**。

| 门 | 命令 | 结果（本轮重跑） |
|---|---|---|
| 1 | `uv run pytest tests/unit/test_source_classifier.py tests/integration/test_fragment_locators.py -q` | **5 passed in 0.04s** |
| 2 | `uv run pytest -q` | **178 passed in 5.65s** |
| 3 | `uv run ruff check src tests` | **All checks passed!** |
| 4 | `uv run mypy --strict src` | **Success: no issues found in 40 source files** |
| 5 | `uv run ci-workflow package verify --root .` | **PACKAGE_OK version=0.1.0a0** |
| 6 | `git diff --check` | exit 0 |

## 原缺陷逐项证据

**原 P2-1（同快照内篡改坐标静默改指）——部分修复。**
- 登记定位器：4 种篡改（`field_path` 改指、`locator_id` 伪造、`evidence_locator.url`、`evidence_locator.document_role`）全部在读取值前抛"登记定位器身份校验失败"；合法重开返回 `'two'`。**已修复**（locator_id 承诺版本+摘要+完整 evidence_locator canonical JSON）。
- 网页定位器：5 种篡改（`heading_occurrence` 3、`paragraph_number` 1、`evidence_locator.heading`→其他、`paragraph` 标签、`field_path`）全部抛"网页定位器身份校验失败"；合法重开返回 `'p2'`。**已修复**（出现次序+段落+JSON 均入承诺）。
- PDF 定位器：`page_number`→2、`row_number`→2 及 4 种 `evidence_locator` 字段篡改均抛"PDF 定位器身份校验失败"。**但顶层 `table_name`→`表 2` 实测 OPENED 返回 `'9.9%'`（静默改指同页兄弟表），顶层 `column_name`→`行` 实测 OPENED 返回 `'a'`（静默改指行标签列）**。原因：`locator_id` 只承诺 `page_number`/`row_number` + evidence_locator JSON，而 `reopen_pdf_table_cell_locator` 的**取值解析用顶层 `table_name`/`column_name`**——这两个字段既未被承诺、又是读取值的权威输入，承诺字段与解析字段不一致。**未修复**（即上一轮报告 §7 的 P2 #1，mtime 证明本轮无修复落盘）。

**原 P2-2（同页重复表名迟拒）——已修复。**
- `PdfPage._table_names_are_unique` 在快照创建时校验；实测 `表 3` vs `表  3`（空白规范化碰撞）在 `PdfDocumentSnapshot.create` 抛"PDF 同一页内表名不得重复"；同页合法不同表名（`表 1`/`表 2`）继续正常工作。新测试 `test_fragment_locators.py` 已覆盖该断言。

## 新缺陷

无新发现。当前唯一 P2 为上述 PDF 顶层字段残留（上轮已报，本轮复核仍存在）：

| # | 级别 | 证据 | 最小修复建议 |
|---|---|---|---|
| 1 | P2 | PDF 顶层 `table_name`/`column_name` 未纳入 locator_id 承诺，篡改后静默改指（`表 2`→`'9.9%'`、`行`→`'a'`，同快照同摘要实测）。`evidence_locator` 内对应字段被承诺但重开时不被用于解析。 | `create_pdf_table_cell_locator` 与 `reopen_pdf_table_cell_locator` 两侧 `stable_id` 各追加 `str(table_name)`、`str(column_name)`（与 `page_number`/`row_number` 同构）；或重开改为仅用 `evidence_locator.table`/`column` 解析并删除顶层字段。两行改动。 |

## 剩余边界

1. **身份校验是完整性而非密码学防伪**：`stable_id` 可被知晓代码者重算，防管线漂移/意外损坏/随手篡改，非对抗性攻击者——与威胁模型一致，需 Codex 确认此边界。
2. **无法重开的数值绕过事实层无法正面闭合**：事实/声明链（ER01–04，Task 2.7）未实现；Task 2.6 内无无定位器写值路径，但"重开值 == 片段原文"闸门必须由 Task 2.7 实现，否则本 P2 残留可携带错误值进事实层。本轮未提前接受也未误判后续任务。
3. **结构定位合同 ≠ 真实 HTML/PDF 抽取质量**：本轮只验证快照结构合同；真实抽取器质量属后续任务，未验收。
4. 摄取模块与两个新测试仍为 `??` 未跟踪；red.txt 历史 RED 无法在当前树复核（只读、无对应提交），GREEN 已独立机械重跑，未依赖构建者自评。
5. 建议 Codex 在应用上述两行修复后重新跑本复核探针（`table_name→表 2` 与 `column_name→行` 必须转 `身份校验失败`），即可满足 P2=0 的 PASS 条件。
