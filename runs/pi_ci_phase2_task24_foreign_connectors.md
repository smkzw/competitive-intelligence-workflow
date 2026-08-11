全部验证完成。最终报告如下（不写入 runner 报告路径，由 runner 持久化）。

我确认已完整读取 `/Users/smkzw/.hermes/SOUL.md` 全文（读取器仅对结尾 768 字符做了展示截断，非跳过），并按其约束执行了只读验收。

---

# Task 2.4 独立验收

## 结论

**PASS**（机械检查全部真实通过；P0=0，P1=0，P2=3）

P2 缺陷不涉及竞品漏纳、错配或当前指南错选，全部为覆盖门与谱系校验的防御性缺口，均给出最小修复建议。文件存在、构建者自评或 `green.txt` 记录均不作为验收证据；以下结论只基于本次实际重跑输出与代码/测试逐行核对。

## 运行与读取证据

| 检查 | 本次真实输出 |
|---|---|
| 组合（7 项）`uv run pytest tests/integration/sources/{test_ctgov,test_pubmed_cross_reference,test_regulators}.py -q` | `7 passed in 0.05s` |
| 全库 `uv run pytest -q` | `166 passed in 5.36s` |
| `uv run ruff check src tests` | `All checks passed!` |
| `uv run mypy --strict src tests/integration/sources/test_*.py` | `Success: no issues found in 37 source files` |
| `uv run ci-workflow package verify --root .` | `PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4` |
| `git diff --check` / `git status --short` | `DIFF_CHECK_OK`；变更仅为新增连接器、schema、测试与任务材料，`package-manifest.json` 的 M 只是把 `schemas/guideline-basis.schema.json` 加入 `components.schemas`（diff 已核对） |

读取范围：ADR 0006/0007、spec v1.2（§1–10 及任务相关部分）、`{prd,design,implement}.md`、`evidence.py`/`ids.py` 全文、三个连接器全文、`guideline-basis.schema.json`/`package-manifest.schema.json`/`package-manifest.json` 全文、三个测试文件全文、`red.txt`/`green.txt`。`cli.py:176-233` 确认 `package verify` 校验清单 schema、版本一致性、Skill 绑定与组件存在性（不校验 guideline-basis schema 本身，该项由 `test_regulators.py` 用 `Draft202012Validator` 对 4 个实例实测通过）。

## 登记与论文攻击

- **NCT 身份不混入全局实体身份**：连接器只生成 `source-study`/`source-version`/`registry-observation`/`publication-cross-reference` 命名空间 ID（`clinicaltrials_gov.py`），`grep` 确认连接器目录无任何 `stable_id("entity"…)`；NCT 号仅作为来源内身份与标识证据保留（ADR 0007）。✓
- **分页令牌编码/替换**：`build_next_page_url` 先剔除旧 `pageToken` 再 `urlencode` 追加；实测 `NEW/TOKEN=` → `pageToken=NEW%2FTOKEN%3D`，旧令牌被替换且仅出现一次。✓
- **versionHolder 不冒充单试验更新**：`registry_posted_version_date`（`lastUpdatePostDateStruct.date`）与 `platform_version_holder`（`versionHolder`）为独立字段；`_scientific_record_digest_input` 从版本摘要中剔除 `versionHolder`。测试证明：仅 `versionHolder` 变化 + 次日采集 → `source_version_id` 相同；真实日期变化 → 版本不同（`test_ctgov.py` 首测）。✓
- **原文不可被外部字典篡改**：`raw_record_json` 在构造时快照，`raw_record` 每次返回新解析副本；实测构造后篡改输入 dict、篡改 `raw_record` 返回值，重新抽取仍得原值（`test_ctgov.py` 二测 + 独立探查）。✓
- **字段保留精确 API 路径与登记链接**：`_walk_leaves` 生成 `protocolSection.eligibilityModule.eligibilityCriteria`、`resultsSection.outcomeMeasuresModule.outcomeMeasures[0].classes[0].categories[0].measurements[0].value` 等精确路径，locator 含 `document_role` 与 `record_url`；设计/结果声明域正确分流（`test_ctgov.py` 二测）。✓
- **引用类型不冒充论文角色**：`platform_reference_type` 原样保留（RESULT/DERIVED），`publication_role` 恒为 `unclassified`，角色判定明确留给论文分类器（`test_ctgov.py` 三测）。✓
- **PubMed 只取 `MedlineCitation/PMID`**：`parse_pubmed_efetch_xml` 仅遍历 `PubmedArticle/MedlineCitation/PMID`，`CommentsCorrectionsList` 嵌套 PMID 41442029 被排除（`test_pubmed_cross_reference.py` 首测）。✓
- **协议/事后/亚组/综述不判为主要报告**：分类顺序为 unrelated→review→ad_hoc→protocol(supporting)→primary；协议论文即使含随机分期+主要终点也判 supporting；primary 需随机+主要终点+结果三信号齐备，偏保守（`test_pubmed_cross_reference.py` 首测，角色断言 `[primary_report, ad_hoc_analysis, review, supporting_publication, supporting_publication]`）。✓
- **论文方案字段不能替代登记字段**：`assess_key_field_coverage` 对 `trial_design` + `primary_publication` 贡献直接拒绝；论文-only 时 `supplement_state="required"`（`test_pubmed_cross_reference.py` 二测）。✓ 但存在 P2-1 缺口（见缺陷）。
- **关键字段齐全时不强制 supplement**：无缺失 → `not_required`，测试断言通过。✓

## 监管与指南攻击

- **监管文件不越声明域**：`allows_claim` 精确匹配；`create` 强制至少一个 scope、禁止重复域；实测 `regulatory_status` True / `efficacy` False（`test_regulators.py` 首测）。✓
- **草案/撤回/已替代不驱动当前默认**：`can_drive_current_default = (final and active)`，模型校验器强制一致；draft、withdrawn、superseded 均 False，最新 final+active 为 True（`test_regulators.py` 二测）。✓
- **替代链悬空/单向被拒**：`validate_guideline_lineage` 校验后继存在、双向一致、predecessor 必须已 superseded（`test_regulators.py` 二测）。✓ 但存在 P2-2/P2-3 缺口（见缺陷）。
- **schema/Pydantic/包清单一致**：4 个 `GuidelineBasis` 实例 `model_dump(mode="json")` 过 `Draft202012Validator`；schema 的 allOf 条件（draft→const false、superseded/withdrawn 约束）与模型校验器一一对应；`guideline-basis.schema.json` 已入包清单且 `package verify` 通过。✓

## 缺陷

- **P2-1 覆盖门：补充材料可覆盖方案字段**（`pubmed.py:assess_key_field_coverage`）。仅拒绝 `trial_design + primary_publication`；实测仅凭 `supplementary_material` 贡献即可使 `design.eligibility_criteria` 被覆盖、`supplement_state="not_required"`，且 rationale 会称"登记结果、主要论文或监管材料已覆盖…方案字段"——与实际来源不符。与 ADR 0006/0007「论文不替代登记平台的方案/统计设计字段」及「补充材料不需要的前提是登记结果/主要论文/监管材料已覆盖」存在偏差；若 Task 2.7 把论文附件补充材料喂入设计字段，将构成来源错用。最小修复：对 `trial_design` 仅接受 `clinical_trial_registry`/`regulatory_material`（把 `supplementary_material` 一并拒绝），或给 `EvidenceContribution` 携带分类角色并按其门控。当前被 Task 2.7 未接线所掩盖，故判 P2 而非 P1。
- **P2-2 替代链不检测环**（`regulators.py:validate_guideline_lineage`）。实测构造 a→b→c→a 三方循环通过全部双向校验（cycle_detected=False）。后果是安全失败（环内无 active，`select_current_guideline_basis` 返回空，不会选错指南），但校验声称"双向一致"而实际允许结构性环。最小修复：沿 `superseded_by_version_id` 做环检测（拓扑序或 DFS），或要求每 series 恰有一个 final+active。
- **P2-3 同一 series 可同时存在多个当前默认**（`regulators.py:select_current_guideline_basis`）。实测同 series 两个 final+active（无替代关系）时返回两者（按日期倒序），未强制每 series 单一当前默认；若下游取 `[0]` 则新者胜出，但旧者仍持 `can_drive_current_default=True`。最小修复：`validate_guideline_lineage` 增加「每 series 至多一个可驱动当前默认」约束，或选择函数遇多个当前默认时抛错/明确去重。

**观察（非缺陷，供 Codex 知情）**：带 PMID 但缺引文的登记引用会抛 `ValueError` 并整页失败（实测确认）——与"响亮失败"的解析边界一致，但真实 API v2 偶有缺引文引用，属健壮性取舍；`EvidenceContribution` 无角色字段，论文角色（`can_replace_primary_report`）与贡献来源的接线在 Task 2.7，连接器已暴露门控信号，本任务不提前验收该接线。

## Codex 仍需确认

1. P2-1 的裁决：补充材料是否允许覆盖方案字段——若按 ADR 严格读，应拒绝，建议随 Task 2.7 接线前在 `assess_key_field_coverage` 修补。
2. P2-2/P2-3 是否在本任务内修补（均可在 `regulators.py` 一处完成），还是并入 Task 2.7 的谱系持久化一并处理。
3. 带 PMID 无引文引用的策略（严格失败 vs 保留空引文建边）需 Codex 拍板，避免未来真实抓取被整页阻断。
4. 结论基于离线录制形态与代码核对；实时连通性（green.txt 记录）只作诊断，未在本轮重做，不构成验收依据。
