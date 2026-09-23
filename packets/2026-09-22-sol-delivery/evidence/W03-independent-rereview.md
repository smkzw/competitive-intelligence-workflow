# W03 返修后二次独立只读复审

- 日期：2026-09-22
- 模式：`MODE=CONFERENCE`
- 角色：W03 返修后的第二次独立只读复审者
- 请求模型：`gpt-5.6-sol:medium`
- 运行时模型/effort 身份：**UNVERIFIED**（本会话没有可核验的运行时回执）
- 唯一审阅工程：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`
- 决策：显式独立复审，且涉及临床语义、数值投影及来源重提取，采用 conference；不派执行节点或子代理。

## 结论

**总体：FAIL**

| 严重度 | 数量 |
|---|---:|
| P0 | 0 |
| P1 | 4 |
| P2 | 2 |
| P3 | 0 |

逐项结论：

| 项 | 结论 | 摘要 |
|---|---|---|
| F01 | PASS | 当前生产分母查找要求完整 rich identity 与显式关系；标题/后缀/唯一候选只在显式历史只读 adapter 内可达。 |
| F02 | FAIL | A 保留 typed 安全语义，但 B 的受控语义投影不消费 `term_key`，且门户 payload 又按粗粒度 family 重建并降级为 `generic_ae`。 |
| F03 | FAIL | A 图表主消费已转为 `numeric_projection`；B 的所谓 typed matrix 可由任意 JSON Mapping 直接伪造 `plot_value/unit/facet_key/size_basis`，且单位/size 一致性未校验。 |
| F04 | FAIL | 实例模式本身支持多 primary 及 group/cohort/period/window 配对；但新包可自行声明 `legacy_readonly_v0` 绕开 `outcome_id`，没有历史快照身份或可信迁移入口隔离。 |
| F05 | FAIL | 真实 PNH C 的 258 条 locator 可逐条精确重提取；真实 PNH A→B 当前链路却因 A builder `NameError`、既有 A payload 缺 `source_field_path` 而无法进入 B/W01。 |
| F06 | FAIL | 指定 86 项全绿，但未覆盖上述三个旁路及真实 A→B 构建失败；C 浏览器截图的冻结 `report.js` 字节未保留，不能独立重绑。 |
| R01 | PASS | 未绑定/未知 arm label 的 intervention 生成显式 blocking 行，Fresh C 包验证会阻断，不再静默丢弃或回退 arm1。 |

本结论仅表示 **W03 工程风险合同未通过**。它不构成正式科学判断、医学接受、产品接受、RC/发布批准；这些范围本轮均为 **UNVERIFIED**。

## 冻结身份与独立执行证据

- Git `HEAD`：`2df24bb441e555f20b233ad2011b4ffd3610655b`；工作树非 clean。
- `git diff --binary` SHA-256：`166a8c697f159d1227bb5d41a8b3565382a330380685765db780f3b6616567d7`。
- `git status --porcelain=v1 -z` SHA-256：`56e5763cc62b71c43b591a63039d8abdce947143d2878cdf3071a7a8cdb85357`。
- 关键当前文件 SHA-256：
  - `report_a.py`：`a35238aa067712d16093b877ad8a14321696d7ae7bbda0168a0d8ebec63ac3ce`
  - `report_b.py`：`31ed9e61b4ec18164741b4798e9b19c6062a12ea80ec27ea68e49495fa18046f`
  - `safety_denominator_crosswalk.py`：`3534488b24468cd522be412694f1923d3bb98e51b06eef784efb116d18963b32`
  - `fresh_c_research_package.py`：`69271a48ae4be81aa973056f57d9dc302dd916bd4518b45371a60a20eef7541c`
  - `endpoint_instances.py`：`26889c84eba0b23a318298192938d58115284cb9861e6558eeb657ce87ccff25`
  - PNH A/B/C builders：`7bf6961e...` / `159dc27f...` / `b4bf0164...`
  - W03 production closure test：`1beea8951ea50da1f3460bbe8f48ff7197538e6a697c126977546ee3076072bd`
- 按 `W03-result.md:269-283` 原样执行 86 项集合，固定 `PYTHONDONTWRITEBYTECODE=1`、`-p no:cacheprovider -q --tb=short`：**86 passed in 5.20s，exit 0**。
- 四张保留截图 SHA-256 与实现报告一致：A `a5adc7...`、B `6ac4a4...`、C endpoint `3de793...`、C arm `092b33...`；已直接检查截图及 Playwright YAML 内容。

## P1-01 / F02：B 未真正消费 typed 安全语义

**结论：FAIL（P1）**

- A 的 `SafetyRow` 已保存 polarity、grade set、seriousness、TEAE、relatedness、parent/children、count basis，见 `src/ci_workflow/renderers/portal/report_a.py:169-219`；PNH A 调用 `describe_safety_concept` 并写入字段，见 `packets/2026-09-11-pnh-vertical/build_pnh_a_payload.py:531-612`。该段为 PASS。
- B `_semantic_projection(domain="safety")` 的候选字段仅含 `clinical_concept/standardized_concept/.../family/safety_family`，没有 `term_key`，见 `src/ci_workflow/renderers/portal/report_b.py:1024-1053`。
- `_project_record` 虽把 `term_key` 和 typed 属性复制到输出，见 `report_b.py:2308-2317`，但受控 `clinical_concept` 已由上面的粗粒度候选产生。
- PNH B 在组装门户 payload 时又从 `family` 重建 `term_key`，不认识的 typed 概念统一变成 `generic_ae`，见 `packets/2026-09-11-pnh-vertical/build_pnh_b_audit.py:1118-1154`，尤其 `:1129-1134`。
- 直接反例：向当前 `_project_record` 输入 `term_key=absence_sae, polarity=negative_presence, teae=False`，实际输出：

  `B_SAFETY_SEMANTIC absence_sae safety:participantswithoutsaes negative_presence False`

  typed 字段虽被携带，但 B 的受控概念键未使用 `absence_sae`，故筛选/分组语义没有贯穿消费者。

最小修复：B safety 投影优先消费并验证 `term_key`；扩充受控概念表以覆盖 `absence_sae/non_serious_teae/grade_specific/composite_ae` 等现有 typed key；门户组装直接保留 `r["term_key"]`，不得按 family 逆向猜测。加入 builder→B payload→过滤/表格的端到端反例。

## P1-02 / F03：B typed matrix 仍有任意 Mapping 与单位旁路

**结论：FAIL（P1）**

- A 受影响图表主路径只读 `numeric_projection`：疗效见 `src/ci_workflow/renderers/portal/assets/report-a.js:772-852`，矩阵见 `:988-1035`；不可绘制投影、对照 facet 不一致及 size 缺失会被拒。A 本项定向 PASS。
- B 的 `_project_record(domain="matrix")` 确实拒绝普通 Mapping，见 `src/ci_workflow/renderers/portal/report_b.py:2079-2090`；但真正入口 `ReportBPortalData.matrix_view` 会把外部 JSON Mapping 直接解析为 `TypedMatrixView`，见 `:1293-1317`。
- `TypedNumericProjection` 只接收调用者已经计算好的 `plot_value/plot_unit/facet_key`，没有原始 value/unit/formula/provenance，见 `:1250-1261`。`TypedMatrixComparison` 只比较治疗/对照的 facet 字符串并检查 kind，未重算 facet，也未核验 treatment/control 的 kind、unit、direction、window、estimand，未强制 safety=`%`、size=`人`、正整数或非空批准的 size basis，见 `:1263-1285`。
- `_matrix_records` 无条件把上述值输出为“可比较”，见 `:2838-2866`。
- 直接反例：在真实 `fixtures/positive/b-pnh/inputs/report-data.json` 上替换 `matrix_view` 为 shape-valid Mapping：治疗 `10 g/L`、对照 `1 %`、伪造相同 `facet_key`、安全 `30%`、size `40 %`。当前 `ReportBPortalData.model_validate` 接受，输出：

  `B_FORGED_MAPPING_ACCEPTED 9.0 g/L 40.0 % %`

这同时证明“无任意 Mapping 旁路”和“size/unit 一致”未满足。

最小修复：矩阵边界必须接收可重算的原始投影身份，或仅允许内部不可伪造的构造结果；validator 至少重算 canonical facet，并强制 treatment/control 的 kind、unit、direction、window、estimand 一致，safety 单位为 `%`，size 单位为 `人`、值为正整数、`size_basis` 为批准且非空。负例必须从 `ReportBPortalData` 实际 JSON 入口测试，不能只测 `_project_record(domain="matrix")`。

## P1-03 / F04：C 历史 fallback 由新包自行开启

**结论：FAIL（P1）**

- `instance_v1` 的逐实例校验本身有效：每条 endpoint/timepoint 必须有 outcome/role/group/cohort/period/window，见 `src/ci_workflow/reports/c/endpoint_instances.py:82-165`；多 primary 与组、期、窗错配的定向测试通过。
- 但 `FreshCResearchContent.endpoint_identity_mode` 对任何调用者开放 `legacy_readonly_v0`，见 `src/ci_workflow/application/fresh_c_research_package.py:184-203`。legacy 分支只限制不得混入 `outcome_id`、每角色 1:1，见 `:300-361`；没有不可变历史 snapshot id、来源签名、存储迁移上下文或只读入口验证。
- 直接反例：使用当前 Fresh C 完整内容 fixture，将模式改成 `legacy_readonly_v0` 并移除全部 endpoint/timepoint `outcome_id`，当前模型接受：

  `C_NEW_LEGACY_FALLBACK_ACCEPTED legacy_readonly_v0 32`

因此“新包强制 outcome 实例、历史 fallback 隔离”未满足。

最小修复：从新建 Fresh C 内容 schema 移除 legacy 模式；若必须保留，只能由受信存储/迁移层基于不可变历史 snapshot 元数据开启，不能由 package 自报。`run_service` 增加新提交声明 legacy 也必须失败的集成反例。

## P1-04 / F05-F06：真实 PNH A→B 链断裂，86 项未覆盖真实生产入口

**结论：FAIL（P1）**

- C 正证据：生产 C `_row` 同时写精确 `field_path` 与来源标量，见 `packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py:63-118`；原始 CT.gov bytes 从 CAS 读取，见 `:205-240`；arm/outcome 使用真实数组索引路径，见 `:340-455`。在临时输出目录执行当前 C builder 后得到 258 条 observation，逐条调用 W01 `extract_locator_quote(source_locator, source_text)`：

  `C_REAL_PNH_EXACT_REEXTRACT rows 258 mismatches 0`

  因此真实 PNH C locator 子项 PASS。
- B 当前真实入口失败：直接执行当前 PNH B builder 读取仓库现有 `pnh-a-payload.json`，在 `packets/2026-09-11-pnh-vertical/build_pnh_b_audit.py:402-467` 的 `:464` 访问 `row["source_field_path"]` 时得到 `KeyError: 'source_field_path'`。现有 A payload 的 519 条 safety 行中 519 条均缺该字段。
- 继续尝试从当前源码重建 A 时，又在 `packets/2026-09-11-pnh-vertical/build_pnh_a_payload.py:450` 得到 `NameError: name 'page' is not defined`。外层循环变量是 `page_no`，见 `:193-196`。
- 所谓 production closure test 实际只组装一个 study 的合成 payload/少量行，见 `tests/contract/test_w03_production_consumer_closure.py:80-144`；它没有执行真实 A builder `main()` 后再把全量结果交给 B/C/W01，所以 86 项绿灯没有发现上述真实失败。
- F06 浏览器证据方面，四张截图文件存在且哈希匹配，但实现报告宣称与 C 截图绑定的 `data/report.js` SHA-256 `46e3c647...` 在当前仓库没有对应文件；除 `W03-result.md` 自述外也没有该哈希命中。因此截图可视觉检查，不能独立证明当前源码/载荷字节绑定。

最小修复：

1. A builder `:450` 使用正确的 `page_no`，并保证每条将被 B 消费的 safety/efficacy 行携带精确 `source_field_path` 与对应 `source_text`。
2. 在受控临时输出中执行真实固定 CAS 的 A→B/C 全链，再把全量 B/C 行送入 W01 ingest 与 manifest-only restore；不能用手工合成一行代替。
3. 将该真实链加入测试，并保留生成站点的 manifest、`data/report.js` 及哈希，使浏览器截图、console 与当前候选字节可重绑。

## F01：分母关系旁路复验

**结论：PASS**

- 生产 `lookup` 要求 study/module/group/measure object/analysis population/window/source version 全部非空，见 `src/ci_workflow/reports/b/safety_denominator_crosswalk.py:90-112`。
- 仅允许同 module+group 的直接关系，或带非空 mapping id 的 `source_declared/audited_mapping`，见 `:113-136`；标题仅能否决候选，不能创建关系，见 `:137-140`。
- 缺任何 rich identity 直接返回 `None`，见 `:149-152`。
- 标题、词元、唯一候选及跨期逻辑只存在于 `_legacy_readonly_lookup`，见 `:154-215`，并只通过显式 `LegacyReadOnlyAtRiskCrosswalkAdapter` 暴露，见 `:262-269`。
- PNH A outcome safety 只用自身发布分母，不再制造 AE↔outcome 边，见 `build_pnh_a_payload.py:548-553`。

定向负例与 86 项中的 F01 合同测试均通过；未发现无标题/后缀/唯一候选的生产分母旁路。

## R01：未绑定 intervention 阻断复验

**结论：PASS**

- 缺 `armGroupLabels` 生成 `missing_arm_labels, blocking=True`；未知 label 生成 `unknown_arm_label, blocking=True`，见 `src/ci_workflow/reports/c/arm_interventions.py:7-42`。
- C builder 把未绑定关系写成显式 observation，不回退 arm1，见 `build_pnh_c_audit.py:354-380`。
- Fresh C 完整内容验证检测 `relationship_blocking` 并抛错，见 `src/ci_workflow/application/fresh_c_research_package.py:288-298`。

当前严格大小写/空白匹配会把近似 label 阻断，而不是误绑；这符合本项 fail-closed 要求。

## P2-01：86 项仍包含过时的 C“至少两条路径”合同

**结论：P2**

- 当前实现结果称单项证据完整研究可形成一条先例路径，见 `W03-result.md:214-215`。
- 但 HTML-PPT 锁定合同仍写 `c-path-1` 为“路径 ≥2”，并固定 `c-path-2`，见 `docs/acceptance/runs/8.5/projection-contract.md:128-136`；测试仍断言 `C_min_design_paths == 2` 及三个 design-patterns slides，见 `tests/html_ppt/test_projection_contract.py:192-220`；可见文案仍称“至少两条”，见 `src/ci_workflow/renderers/html_ppt/projections/c_pages.py:265-275`。
- 因此 86 项的“相邻合同闭包”部分依赖一个与当前单先例产品合同不一致的旧 HTML-PPT 断言。它没有证明通过缩小 HTML 门户 catalog 来过关：门户 catalog 未被该投影文件修改，A/B `non_portal_responsibilities` 也只影响 HTML-PPT coverage 计算，见 `test_projection_contract.py:88-119`。本轮未发现该兼容同步直接改变 HTML 产品运行代码。

最小修复：明确 HTML-PPT 是保留旧的双路径演示，还是同步当前单先例合同；若同步，修改锁定合同、断言和观众文案，并单独回归 HTML-PPT。不要把这一兼容测试作为当前 HTML 产品语义已闭合的证据。

## P2-02：浏览器证据缺少可重绑的冻结站点字节

**结论：P2**

四张截图视觉内容与实现报告描述相符，且文件哈希一致；但当前仓库无法找到声明的 C `data/report.js` 哈希 `46e3c647...`。因此截图只证明当时画面，不足以证明画面来自本报告冻结的当前源码/载荷。最小修复为保留站点 manifest、关键 JS/data 文件及哈希，或提供可重复构建并逐字节复核的浏览器旅程。

## 工程风险与正式接受边界

- **工程风险合同：FAIL。** 四个 P1 中任一项都阻止 W03 进入风险合同已接受状态。
- **确定性局部正证据：** 86 项测试全绿；F01、R01 通过；真实 PNH C 258 条 locator 精确重提取通过；四张截图可读取且哈希匹配。
- **不能据此声称：** 完整真实 PNH A/B/C 链通过、全部 24 门户通过、全 gate、全 viewport/全页视觉通过、v107 数据接受、正式科学判断、医学负责人批准、产品或 RC 接受。
- 请求模型/effort 身份没有运行时回执，保持 **UNVERIFIED**。

本复审未修改产品、测试、`STATUS`、首轮报告，未派子代理，未提交、推送或清理；唯一写入是本报告。
