# 阶段 Handoff：专家审阅纠偏执行报告（d1909b8 → 9cf65e5）

- **撰写日期**：2026-09-22
- **审阅基线**：`d1909b8`（上轮专家审阅《CI_workflow_v96_review》所固定提交）
- **当前 HEAD**：`9cf65e5`（本文件所在提交区间内的最新 docs 提交；最后功能提交 `251d613`）
- **当前唯一候选**：**abc-v102**（`runs/pnh-vertical/abc-v102`，run_018098d1826029bf12bfe7f6，A 56 页 / B 70 页 / C 18 页，三包严格校验 ACCEPTED）
- **前一候选**：abc-v97（f3ba4d3，已被 v100/v101/v102 按新工作区纪律替代；各候选独立可溯）
- **进行中**：round-7 独立复核（deepseek A r46 / B r60 / C r44）已派发、静默运行中，verdict 未回。本文所有"待复核"结论均指该轮。

本文件按 AGENT_NEXT.md §4 的 HANDOFF 格式撰写。分九节：①执行概要 ②五项用户决策状态 ③R01–R13 处置矩阵 ④round-4 会商新增缺陷处置 ⑤复核收敛轨迹（round-4→6 实证） ⑥测试与验证证据 ⑦失败/未完成/环境限制（与历史记录分开） ⑧需专家裁决的两项合同问题 ⑨下一步（按依赖与阻断）。

---

## 一、执行概要

上轮专家审阅给出 13 项缺陷（R01–R13）、7 个工作包（WP0–WP7）、36 项行为验收（ACCEPTANCE.md）。本轮按审阅 §6 的三分轨执行：

| 分轨 | 本轮产出 |
|---|---|
| 数据根因修复 | **WP0+WP1 完成**：R01–R09、R11–R13 全部落码，31 项新回归测试全绿（unit 27 + integration 4）。R10（产品闭环）未动，见第七节 |
| 独立审查 | 三轮全量复核 + 两轮对抗测试 + 两轮用户旅程（round-4/5/6，累计 15 份独立结论）；**C 报告 round-6 首个 accepted**（verdict-omp-deepseek-abc101-c-r43） |
| 产品任务闭环 | **未启动**（R10/WP2–WP6 无代码产出）——见第七节"未完成"，不与上述混淆 |

审查采用"独立 harness + 清洁环境 + 超长静默"流程：deepseek-flash(max) 三路科学复核按快照逐候选重派（快照 ID 含 project_id，结论不跨工作区继承）；grok-4.7(xhigh) 独立对抗探针（round-4 自建 73 用例 → round-5 95 → round-6 109，**不读生产者测试**）；cursor(auto) 真实浏览器用户旅程（Chromium 实机 DOM 读取，非截图判读）。每轮收包后由独立会商者（deepseek 独立上下文）逐项复验裁决（`packets/2026-09-22-conference-round4/conference-memo.md`：21 项发现全部成立，含复验探针命令）。

**专家审阅的两项预警已被实证命中**：
1. "不能以 review 轮数代替闭环"——本轮明确未把复核收敛当产品进度：五项用户决策的实现状态见第二节（全部"未实现"或"部分"）。
2. "独立复核最多负责发现问题与评价证据"——人群柱图（全 1 无辨别）未等复核裁决，已按审阅意见改为说明+同源表格（`report-c.js` criteriaCountOption `__no_discrimination` 分支）。

---

## 二、五项用户决策的实现状态（逐项：未实现 / 已接通待验收 / 验收通过）

> 按审阅要求：不重复陈述决策内容，只给实现状态、代码入口与差距。**本轮无一项达到"验收通过"。**

| 决策 | 状态 | 本轮相关产出 | 差距（阻断项） |
|---|---|---|---|
| B 全部相关研究+分面 | **未实现**（维持上轮判断） | 无新代码 | WP4B 未启动；`WorkspaceMembership→FacetPlan→NumericFrameEligibility` 闭环缺失 |
| 事实修订全报告同步 | **未实现** | R07 摄取层修复（`fresh_research_ingestion.py`：完整载荷版本摘要、同 ID 异载荷显式冲突、逐事实精确片段）是 WP3 的前置不变量，已具备 | WP3 共同修订事务（revision/局部重算/原子 publish）未启动 |
| C 设计先例库 | **部分**（输入合同松绑） | R09：删除 `candidate_paths≥2` 门槛（`fresh_c_research_package.py::_validate_design_paths`）；`_stat_notes[:8]` 裁剪删除；R05 终点实例化（`reports/c/endpoint_instances.py`，逐 outcome_id 配对校验） | C03（多组多期给药归属 arm1）未动；检索横比（WP4C）未启动 |
| 个人复用/静态分享 | **未实现** | 无新代码 | WP6 未启动 |
| A=B=C 共享证据 | **部分**（不变量层共享） | 概念词表单源 `concept_catalog.py`（A/B/C/PDF/PPT 五消费方统一）；R11 状态两字段跨报告传播（B dossier 已补） | 共同事实身份、跨报告派生传播未落实；B 仍依赖旧兼容分组主线 |

---

## 三、R01–R13 处置矩阵（不是"已修复"三个字，每项带代码+测试+证据）

| # | 处置 | 代码入口 | 回归证据 | 已知残留 |
|---|---|---|---|---|
| R01 | **已修** | `report_a.py::EfficacyRow`——三 validator 合并为唯一披露不变量（reported_zero 必须显式 0；缺失不得补 0） | `tests/unit/test_v96_review_invariants.py::sci01`（5 用例） | 无 |
| R02 | **已修，两轮收敛** | `reports/b/safety_concepts.py`——round-4 建表驱动分类器；round-4 会商 F02 证实"特定族被总体族吞"后重排为否定→特定→总体→generic；round-5 复合标题过匹配（26/28 误归停药）后引入**片段化判定**（`classify_safety_concept` 逐逗号/and 片段独立分类，≥2 概念→`composite_ae`） | sci02（6 用例）+ grok round-5/6 对抗探针；载荷概念分布 any_teae 146→117、discontinuation_ae 仅剩 2 条真停药、composite_ae=56 诚实单列 | F17（复合与否定并存的边界语义）grok 标 medium，待会商定口径 |
| R03 | **已修，两轮收敛** | `reports/b/safety_denominator_crosswalk.py`——期别入口归一（`normalize_period`，含 Period N→TPN）、期别不符一律未知禁借用、冲突显式记录、锚定词元+词元全含匹配、人时量纲互斥不挡位 | sci03/sci04（4 用例）+ grok F10–F13/F18 对抗用例全过 | F16（变体回退缺 requested_period_absent 冲突记录）low |
| R04 | **已修** | `registry_observation.py`——规范 ID 直接识别（连字符保留，F08 修复）；"提供但未知"收缩到共享规则，与"未提供"显式区分 | sci05（4 用例） | 无 |
| R05 | **已修** | `DesignObservation.outcome_id` + `reports/c/endpoint_instances.py`（逐实例配对、空白时间点不冒充已配对、孤儿双向检验、同 id 异定义冲突）；`fresh_c_research_package.py` 实例级校验；C 构建器逐条携带 outcome_id | sci06（3 用例）；实测 NCT03181633 的 9 条主终点全量配对（此前仅 1 条） | 无 |
| R06 | **已修** | `reports/c/synthesis.py::_normalize_text` 保留数值语义字符 | sci07（2 用例） | 无 |
| R07 | **已修** | `fresh_research_ingestion.py`——version_id 完整载荷摘要；查后插入+异载荷显式冲突；事实自带精确 locator 时落逐事实片段 | `tests/integration/test_review_r07_ingestion_invariants.py`（SCI08/09，4 用例，走生产 SQLite） | 存储层 append-only 触发器使"同 ID 异载荷"在存储不可达，摄取层守卫为纵深防御（测试已注明） |
| R08 | **已修** | `charts.js` 两副本——首系列标签 `series[0]` 自引用改按当前类别数 | 静态修复；浏览器验证归 UI01 待真实多系列实测 | 待 UI01 验收 |
| R09 | **部分** | `≥2` 门槛删除（C01）；`:8` 裁剪删除（C02） | v101/v102 渲染覆盖 | **C03（多组多期给药归属 arm1）未动**；检索横比未启动 |
| R10 | **未动**（明示） | — | — | WP2–WP6 为主线，见第九节 |
| R11 | **已修（代码面）** | `ProductRow.regulatory_approval_status` 与登记状态分字段；A/B 产品页两列展示 | B `products/eculizumab.html` 实测含"监管批准事实"；A r45 未再否决此项 | 权威核验接入（辖区/适应症/批准日期）待来源决策 |
| R12 | **已修（src 副本）** | `evidence-drawer.js` 恢复 scale 展示 + `isUnitShapedScale` 形状判别 | — | 根 `assets/portal/` 旧副本未同步（安装包资产同步属 ENG 任务）；三类夹具（真量表/无量表/单位）跨适应症 drawer 验收待做 |
| R13 | **已修（代码面）** | `TrialRow.sample_size: int | None` + `planned_sample_size` 分字段；构建器保留未知样本量试验（135→140）；模板/B 投影"未公开"守卫 | sci10（2 用例）；v102 载荷 5 项未知样本量试验保留 | **通用入口迁移（WP2）未动**：生产入口仍依赖 PNH 垂直包（/tmp 指针、固定截止日、TARGET_TRIALS）——审阅原文 R13 的"生产入口"部分未解决，如实声明 |

---

## 四、round-4 会商新增缺陷处置（审阅包之外，独立审查+会商发现）

会商备忘录（`packets/2026-09-22-conference-round4/conference-memo.md`）裁决 21 项发现全部成立，并归纳四层根因（概念词表分裂/守卫写成放行/投影多链路/内部键泄漏），另挖出**两个三路复核与两路测试均未覆盖的静默缺陷**：

| 缺陷 | 处置 |
|---|---|
| 原生 PDF A 安全轴整列坏死（45/45 点"未公开"） | **类别匹配已修**（`pdf_native/projections/a.py::_is_any_teae_row` 按 term_key）；**臂名语义脱节仍在**（PDF 投影按"治疗组"匹配，载荷臂名为登记原名）——PDF 管线修复登记为独立任务，未混入本轮 |
| A 安全性完整性门禁因词表脱节永不触发 | **已修**（`report_a.py` 门禁改按 term_key 判定 any_teae/any_sae 齐备）；门禁复活后被夹具正确拦截（`oral-small-molecule` 缺安全维度报错）并修正夹具口径 |

会商排期 12 项中 **#1–#7、#10、#12 已实施**（7d16cbb / 515500f / fd90fa3 / 251d613 四批）；#8/#9 按会商标注归 R10 主线；#11（构建器参数化）沿用原排期。

---

## 五、复核收敛轨迹（实证，非自述）

| 轮 | 候选 | deepseek A/B/C | grok 对抗 | cursor 旅程 |
|---|---|---|---|---|
| round-4 | abc-v97 | veto 6/3/7 项 | 62/73，F01–F09 | fail，5 项交互缺陷 |
| round-5 | abc-v100 | veto 5/2/7 项（C 均为会商明示"移交"项） | 88/95，F10–F15 | 供应商连接故障，未产出（基础设施，非代码） |
| round-6 | abc-v101 | **C accepted**；A veto 5 / B veto 2（收敛至展示层与合同深水区） | 101/109，F16–F22（多为 low/medium 边界项） | 复测通过（矩阵气泡/回归/视口，产物在 `runs/test-round5-cursor/`，其 findings 被 round-6 引用） |
| round-7 | abc-v102 | r46/r60/r44 运行中 | 未派发（本轮对抗项已收敛为 low，待 round-7 收包后定） | 未派发 |

A r45/B r59 的剩余项与 v102 修复的对应关系（供审阅核对）：
- A r45 issue-2 类目标题：根因是首轮修复把类目后缀注入 `term`（**跨报告副作用：B 侧族判定消费 term，掉落 67→243**）。v102 改为 `SafetyRow.measure_context` 独立字段（term 保持登记原貌）+ 渲染层 measure_label 组合。实测 NCT00867932 九条类目行携带独立标题。
- A r45 issue-4 组名解码未落地：根因是模板 `arm_detail or arm` 优先级——解码名写入 arm、登记名写入 arm_detail 后，模板反而显示登记名。v102 改为"解码名优先 + （登记名：原文）括注"（`templates/a/safety.html.j2`）。
- B r59 issue-2 基线影子泄漏：泄漏源为 subgroups-supporting 等未经域级过滤的页面路径。v102 收口到 `_page_records` 总出口（`_without_declared_shadow_pairs`）+ `_legacy_or_view_rows`（`_without_declared_shadow_rows`）。实测 v102 渲染产物 0 个 `-declared` 行 ID（v101 同页曾泄漏）。
- A r45 issue-6 **载荷内嵌复核声明悖论**：`build_pnh_*` 在提交时必须写入 `scientific_review.status="accepted"`，而独立复核发生在提交之后——提交格式与复核时序存在结构性矛盾。**未擅自修改，提请专家裁决**（见第八节）。

---

## 六、测试与验证证据

- **新增回归**：`tests/unit/test_v96_review_invariants.py`（27 用例，SCI01–SCI10）+ `tests/integration/test_review_r07_ingestion_invariants.py`（4 用例，SCI08/09 走生产 SQLite）。
- **全量基线**：`pytest tests/unit tests/contract -k "not slow"` → **1054 passed + 2 既有失败**。两项既有失败均为工作树脏文件所致、早于本轮（①`test_page_catalogs`：C.yaml evidence-limitations 页与冻结集不同步；②`test_bundle_scientific_closure`：隔离安装包 portal.css 摘要与未提交资产不一致）。与历史记录分开声明：**本轮零新增失败，也未把这两项写成通过**。
- **候选链**：`PYTHONHASHSEED=0` 全程；abc-v102 = project create → 证据 raw 复制 → 三个 packet builder → `build_pnh_audit.py A,B,C` → `research submit`（ACCEPTED）→ `project run`（run_018098d1826029bf12bfe7f6）。
- **产物抽查命令**（审阅可复跑）：
  ```sh
  # 载荷概念分布（诚实分类）
  python3 -c "import json,collections;d=json.load(open('packets/2026-09-11-pnh-vertical/pnh-a-payload.json'));print(collections.Counter(r.get('term_key') for r in d['safety']).most_common())"
  # B 渲染产物影子行（应为 0）
  grep -o '"row_id":"[^"]*declared"' runs/pnh-vertical/abc-v102/reports/B/v1/html/products/danicopan.html | wc -l
  # A 类目上下文进入嵌入数据
  grep -o '"measure_context":"[^"]\{0,40\}' runs/pnh-vertical/abc-v102/reports/A/v1/html/data/report.js | head -3
  ```

---

## 七、失败 / 未完成 / 环境限制（与上节分开，如实声明）

**未完成（代码层面零产出，非"待验收"）**：
1. R10 全部（WP2 通用运行入口 / WP3 共同修订事务 / WP4A/B/C / WP5 统一 ViewState / WP6 静态分享 / WP7 发布验收）。
2. R09-C03（多组多期给药各归身份，不汇 arm1）。
3. F15 残余：15 处 Python 概念字面匹配（其中约半数为 `source_research_service._outcome_report_term`、`_SAFETY_TERM_GROUPS` 等 B 门定义性规范词表——合并入 concept_catalog 属合同级重构，未在缺陷轮冒险执行）。
4. A r45 矩阵横轴单位混轴与气泡溢出（纵轴派生率已修，横轴未动）。
5. PDF 管线臂名语义（PDF 投影按"治疗组"匹配，载荷臂名为登记原名）。
6. B 含中文半翻译分面清洗（纯英文标注已修，混合残片未动）。
7. 载荷内嵌复核声明悖论（第八节，提请裁决）。

**环境/流程限制**：
1. cursor 供应商连接故障一轮（ERROR_OPENAI，round-5），已重派并复测通过；非代码问题。
2. `/tmp/pnh-proj-path.txt` 指针三次导致信封写错工作区（已写入记忆与纪律：指针必须先于 B/C 构建器）。该指针本身即 R13/WP2"生产入口依赖垂直包"的实例。
3. 工作树含大量非本任务脏文件（fixtures/policies/schemas 等），按项目规则未触碰；两项既有测试失败由其导致。

**流程教训（会商实证）**：
1. "修一处、同族复现"被证实为结构性——概念词表五处字面互不相同导致精确匹配逐层失效；`concept_catalog` 单源后 A/PDF/PPT 同族缺陷一次收敛。
2. 跨报告字段耦合两次教训：term 注入类目后缀改变 B 族判定（已回退改独立字段）；渲染层"保守回退"扩散英文（须同时补解码）。

---

## 八、提请专家裁决的两项合同问题

1. **载荷内嵌复核声明悖论**（A r45 issue-6）：`a-research-package.json` 的 `scientific_review.status="accepted"` 在提交时由构建器写入，独立复核（deepseek）发生在提交渲染之后。候选方案：a) 载荷内声明改为 `pending`（需合同允许非 accepted 状态）；b) 把该声明从载荷移至回执层（复核后签发）。倾向 b，但涉及 FreshA 合同与门禁消费方，**未擅自实施**。
2. **F17 复合与否定并存的分类口径**："Non-serious adverse events and serious adverse events" 现判 `composite_ae`（片段化判定）；是否应为 `any_sae`（取严重度子集语义）？涉及分类器语义边界，附 grok S11/S12 原始用例与当前实现（`safety_concepts.py::classify_safety_concept`）供裁决。

---

## 九、下一步（按依赖与阻断列出）

1. **round-7 收包**（进行中）：若 A/B accepted → 三报告在 v102 快照齐 accepted → 进入 accept-visual（ego lite 真实点击，四视口 1440/1024/390/320 + Chromium/WebKit）→ PNH 纵向闭环。若再 veto → 剩余项已高度收敛（矩阵横轴、含中文分面），按行级定位续修。
2. **第八节两项裁决落地**（阻断：①影响提交流程合同；②影响分类器语义）。
3. **R10 主线启动**（阻断：1、2 完成后无借口继续延迟）：WP3 共同修订事务（AtomicFactVersion/CorrectionService 已具备 R07 不变量前置）→ WP4B B 共同工作空间 → WP4C C 检索横比 → WP4A A 完整景观 → WP5 ViewState（含 BI-01 图/筛选一致性验收用例）→ WP6 静态分享 → WP7 发布验收。
4. **WP2 通用入口**（依赖 3 的 SourcePlan 合并）：消除 /tmp 指针与 PNH 专用脚本，ENG01 验收（两种适应症同一安装入口）。
5. 横向扩展矩阵（多适应症/三宿主/安装/恢复/RC）维持既定终验要求，不以本阶段小夹具替代。

---

## 附：快速复核入口

- 仓库：https://github.com/smkzw/competitive-intelligence-workflow（main，HEAD 9cf65e5）
- 关键文件：`concept_catalog.py` / `safety_concepts.py` / `safety_denominator_crosswalk.py` / `endpoint_instances.py`（新增模块）；`tests/unit/test_v96_review_invariants.py`（SCI 映射注释齐全）
- 运行记录：`packets/2026-09-11-pnh-vertical/runbook.md` 追记 65–68（每轮派发/收包/修复/验证全记录）
- 会商裁决：`packets/2026-09-22-conference-round4/conference-memo.md`
- 独立审查原始产物：`runs/pnh-vertical/abc-v10{0,1,2}/state/scientific_review/*/verdict.json`、`runs/test-round{4,5,6}-{grok,cursor}/findings.json`
