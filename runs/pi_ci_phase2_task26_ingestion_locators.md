全部验证完成。已读取 `/Users/smkzw/.hermes/SOUL.md` 全文（267 行，含此前被显示截断的 §12 尾部），并在只读边界内完成了全部机械门与对抗探针。

# Task 2.6 独立验收

## 结论

**PASS** — 建议接受（机械检查 6/6 真实重跑通过，P0=0、P1=0）。P2=2（均为硬化建议，不阻断；见 §7）。本验收不采信构建者自评（red/green.txt 仅作锚点），全部结论来自本会话独立重跑与对抗探针。

## 运行与读取证据

读取：ADR 0009、prd/design/implement、`classifier.py`、`fragmenter.py`、`locators.py`（全 541 行）、`evidence.py`（全 331 行）、`ids.py`、三个 schema、`package-manifest.json`、4 个测试文件、red/green.txt、`content_store.py`。

| 门 | 命令 | 结果（本会话重跑） |
|---|---|---|
| 1 | `uv run pytest tests/unit/test_source_classifier.py tests/integration/test_fragment_locators.py -q` | **5 passed in 0.04s** |
| 2 | `uv run pytest -q` | **178 passed in 5.56s**（green.txt 声称 178/5.88s，一致） |
| 3 | `uv run ruff check src tests` | **All checks passed!** |
| 4 | `uv run mypy --strict src` | **Success: no issues found in 40 source files** |
| 5 | `uv run ci-workflow package verify --root .` | **PACKAGE_OK version=0.1.0a0** |
| 6 | `git diff --check` / `git status --short` | diff check exit 0；4 个文件已修改（3 schema + evidence.py），新摄取模块与测试为 `??` 未跟踪 |

结构对照：`classify_source` 角色表 8 类与 ADR 中文标签一致；`create_document_version` 规范名 = `身份_中文角色_版本_摘要[:12]+后缀`；`IngestedDocumentVersion._supplement_keeps_parent` 双层强制父文档；三 locator 均绑定 `source_version_id` + `source_content_sha256`；`ContentAddressedStore` 路径 `evidence/raw/sha256/xx/{digest}.bin` 与 schema 的 `content_relative_path` pattern 一致。

## 分类与用户文件攻击

- **未知自动文件不被猜成已分类**：实测 8 例——`pdf/unknown`、`json/general_web`、`pdf/conference`、`docx/unknown`、`octet-stream/publication` 全部落入 `review_pending`；仅 `html/unknown`→`web_page`（通用角色，非对论文/登记/官方资料的具体猜测，符合 ADR）。`company_disclosure` 优先于 html 判定→`company_release`，family 声明域优先，正确。
- **supplement 无父文档失败**：`SourceDocumentInput` 与 `IngestedDocumentVersion` 两层均抛"补充材料必须关联主文档/保留父文档身份"，含 manual_inbox 通道；伪造分类对象绕过第一层时第二层拦截，实测通过。
- **用户文件保留原名**：`临床原始文件_最终版 v2(1).pdf` 原名逐字保留；含目录路径（`dir/evil.pdf`）拒绝；空内容拒绝；规范名 `NCT01-user-1_用户补充文件_2026-08-01_594e519ae499.pdf` 由稳定身份/中文角色/版本/摘要生成（含不安全字符替换为 `-`，稳定可逆）。
- **同内容副本**：同字节 → 同 `content_sha256`；不同 `document_identity` → 独立 `document_id`/`source_version_id`（实测 supplement vs user-file）；同身份同内容 → 去重为同一 ID（与 Phase 1 内容寻址语义一致）；同身份改内容 → 同 document_id、新 source_version_id。

## 登记、网页和 PDF 定位攻击

- **登记数组路径**：`a.b[1].v` 精确重开 `"two"`，`[0]`/`[1]` locator_id 不同；越界索引、`a..b`、`[0]` 根数组、`a[0]b`、`a[b]`、`a.b[-1].v`、尾点、int-on-dict 全部拒绝。
- **外部字典修改不影响快照**：create 后改原 payload 的嵌套值与浅层值（含带点键），`reopen` 仍返回原值，`snapshot.payload` 不变——canonical_json 为冻结字符串、`payload` 属性每次重解析，正确。
- **网页同名标题按出现次序**：3 个同名 `H` 标题中间夹其他标题，occurrence 1/2/3 全部精确定位；occurrence=0/4、段落越界拒绝；重开重新按 heading+occurrence 推导，不依赖字段路径串。
- **PDF 页/表/行/列**：同页重复数值 `81.0%`（行 1 与行 3）两个 locator 各自精确重开、id 不同、row 标签不同，无错引；跨页同名表按 page 区分；越界行/不存在列拒绝；重复列名、锯齿行宽、重复页码在 snapshot create 即拒绝。
- **跨版本拒绝**：三类 locator 全部实测抛"来源版本或内容摘要不一致"（改版本 id、改摘要、同版本伪造摘要均拦截）。
- **结构边界**：同页重复表名在 `create` 定位器时失败闭合（"未找到唯一指定表格"），归一化碰撞（`表 3` vs `表  3`）同样闭合——**无错引可能**，但快照创建未提前拒绝（见 P2-2）。

## 共享合同攻击

- **EvidenceLocator ↔ 三 schema 同步**：5 个 locator dump（网页/登记/PDF/裸 url/页+表，含空值）对 `source-version.$defs.locator`、`evidence-fragment.properties.locator`、`guideline-basis.$defs.locator` 三处 jsonschema（2020-12 + FormatChecker）**全部通过**；整文档 source-version、evidence-fragment round-trip 通过；9 键齐全（null 允许）与 Pydantic dump 一致；Pydantic 拒绝 `page=0`、空白 heading、无锚点、`page=0.5`。git diff 确认三 schema 与 `evidence.py` 的 `heading/row/column` 扩展逐字段同步（37+/5-）。
- **schema 结构差异**（非缺陷）：evidence-fragment 的 locator 内联在 `properties`，另两个在 `$defs`；字段内容一致，已实测等价。
- **无法重开数值进入事实层**：Task 2.6 范围内**无任何写值路径不带定位器+版本/摘要绑定**——`add_fragment` 强制非空原文、摘要为原文哈希、fragment_id 承诺 (版本, 定位器 canonical, 原文摘要)。但"重开值 == 片段原文"的一致性闸门不在本任务代码中（属 ER01–04），见 §8。

## 缺陷

| # | 级别 | 证据（实测） | 最小修复建议 |
|---|---|---|---|
| 1 | **P2** | **同版本+同摘要内篡改定位器坐标静默改指**：`reopen` 只校验 `source_version_id`/`source_content_sha256`，不重算 `locator_id`。实测：registry `field_path` `a.b[1].v`→`a.b[0].v` 返回 `'one'`（原 `'two'`）；web `heading_occurrence` 1→3 返回 `'p4'`（原 `'p2'`）；pdf `row_number` 1→3 返回 `'81.0%'`（原 `'3.0%'`）、`column_name`→`'行'` 返回 `'a'`。跨版本/摘要篡改仍被拦截，但记录内坐标篡改可把引用静默移到同快照另一值。 | reopen 时按 (kind, version, digest, 坐标) 重算 `stable_id` 并与 `locator.locator_id` 对比，不一致即拒绝；或由 Task 2.7 事实层强制 `reopened == fragment.original_text`（两者至少取一）。 |
| 2 | **P2** | **PDF 同页重复表名未在快照创建时拒绝**：`PdfDocumentSnapshot.create` 接受同页两个 `表 3`，定位器创建才失败闭合。无错引后果（定位必失败），但结构歧义暴露过晚，且 `_pdf_table` 依赖"每页表名唯一"的隐含不变量未在数据入口固化。 | `create` 时校验 `(page_number, table_name)` 唯一（与 `_page_numbers_are_unique` 同级）。 |

P0=0、P1=0。两个 P2 均为失败闭合方向的硬化项，不影响"数值错引/跨版本/补件丢失/无法回原文"四类高优先风险（均实测未发现）。

## Codex 仍需确认

1. **"无法重开的数值绕过进入事实层"无法正面闭合**：事实/声明链（ER01–04，Task 2.7）尚未实现。Task 2.6 内不存在绕过路径（定位器+摘要绑定、失败闭合均已实测），但"定位器重开值 == 片段原文"的最终闸门必须由 Task 2.7 实现，否则 P2-1 的坐标篡改可携带错误值进事实层。本验收既未提前接受也未误判该后续任务。
2. **结构定位合同 ≠ 真实抽取质量**：本轮验收只证明快照上的可重开结构合同成立；真实 HTML/PDF 抽取器（pdfplumber/pypdf 的表名/行/列识别、网页标题切分）必须产出满足本合同的快照，其质量属后续任务，本轮未验收、也未放行。
3. **新模块未跟踪**：`src/ci_workflow/ingestion/{classifier,fragmenter,locators}.py` 与两个新测试文件在 `git status` 中为 `??`；磁盘状态已通过全部机械门，提交由 Codex 完成。
4. **red.txt 的历史 RED 无法在当前工作树复核**（只读验收、无对应历史提交）；不影响结论——GREEN 已独立机械重跑，未依赖构建者自评。
5. `classify_source` 中 `text/html` 无条件→`web_page`（即使 family=unknown）是唯一"自动归类"路径，建议在 Task 2.7 或后续评审中确认此语义符合产品预期（本轮按 ADR 视为通用角色，非缺陷）。
