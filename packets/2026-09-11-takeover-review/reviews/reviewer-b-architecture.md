Trellis SessionStart ✓

已按只读边界完成评审。说明：本会话 Bash 被拒（非交互模式无审批通道），因此所有行数用 `Grep -c` 精确取得，字节级哈希无法计算；凡未经我实测的数字均标注来源。旧中文工程零接触。

---

## 结论

引擎骨架（domain/gates/graph/storage/application，共 115,247 行 / 192 个 py 文件）是真实、失败关闭的工程，但**产品的科学内核是双份的**：`reports/b/*` 约 12,000 行的科学视图层只有测试在调用，真正出 HTML 的 `renderers/portal/report_b.py` 自己重算了一遍裁决逻辑——这是"完整医学语义"目标的真正阻塞点。最大三个风险：**① 权威科学视图层未接线（P0）；② 除 CT.gov 单条件查询外零真实取数，24 门户矩阵无通往真实的路径（P0）；③ 1,220 条未提交改动且无已验证里程碑，恢复成本不可测（P1）**。优先行动顺序：先补"渲染器不得自行裁决"的红测与类型化接缝（1→2），再补一条可执行真实路线与 `not_applicable` 适用性证据（7→8），最后才接通语义提案链并跑 PNH 竖向验收（5→6→9）——**在此之前不做 source-set 收敛、不做任何提交**。

---

## 清单逐条裁决

### 1. 巨型文件 / 科学-渲染耦合 — **部分成立，且比清单描述更严重**

行数全部精确核实：`report_b.py` 4199、`run_service.py` 3938、`reports/b/pages.py` 3757、`safety.py` 3333、`efficacy.py` 3316。

清单说"renderer 内仍持有裁决逻辑"，这是对的，但**真正的问题不是文件大，而是权威层没人用**：

- `renderers/portal/report_b.py:310` 起是自带的临床别名表 `_CLINICAL_CONCEPT_GROUPS`（310–744），另有 `_canonical_arm_role`(:815)、`_canonical_statistical_form`(:771)、`_time_band`(:835)、`_semantic_group_key`(:2771)、`_cross_trial_groups`(:2861)、`_groups_for_page`(:2961)。这些确实是医学裁决，不是排版。
- 但 `reports/b/efficacy.py:build_efficacy_views`(:2938)、`safety.py:build_safety_views`(:3060)、`pages.py:build_matrix_view_state`(:3537)、`efficacy.py:build_endpoint_basis_set`(:1443) 在 `src/` 内**除自身模块外零调用者**；唯一调用者是测试（`tests/reports/b/test_efficacy_views.py:88`、`test_safety_heatmap.py:96`、`test_matrix_states.py:319`）。
- 出报告的唯一路径是 `run_service.py:732` → `build_report_b_artifact`，它从不触碰上述视图层。
- 更关键：`report_b.py:2748` 的 `_project_scientific_groups` 拿 `semantic_row_digest` 校验"页面观察属于完整科学视图"，看起来是正向约束——但 `scientific_groups` 本身来自 `report_b.py:3690` 的 `_groups_for_page(...)`，**是渲染器自己产出的**。这是渲染器对自己做一致性校验（循环），不是对科学视图层的一致性校验。

**修正意见**：拆分不是第一步。把一个持有科学层副本的 4,199 行文件切开，只会让同一套规则出现第三个家，之后更难删。最小安全路径是四步，顺序不可换：

1. 把 `ReportBPortalData` 的 `efficacy_views/safety_views`（`report_b.py:1165–1176`，当前是 `Any | None`）改成类型化字段；
2. 让 `_groups_for_page` 消费 `EfficacyViewSet`/`SafetyViewSet`，删掉本地 `_semantic_group_key` 的初分桶；
3. 让 `_project_scientific_groups` 的 `groups` 来源改为科学层而非 `3690` 行；
4. **此后**才按域拆文件，且拆出来的语义助手归 `reports/b`，不是留在 `renderers/`。

### 2. 双份资产手动同步 — **部分成立，风险方向被清单说反了**

- 重复的 5 个文件：`charts.js`、`portal.css`、`portal.js`、`evidence-drawer.js`、`evidence-drawer.css`。我用行数+首尾行采样比对，5 份当前一致（未做 SHA，Bash 被拒）；仓库内的护栏做的是 SHA。
- 护栏覆盖**不全**：`tests/browser/test_portal_shell.py:455–479` 只覆盖 `portal.css`/`portal.js`（+ logo 的 brand↔module），`tests/browser/test_evidence_drawer.py:192–205` 只覆盖 `evidence-drawer.js/css`。**`charts.js`（63,109 字节 / 1,822 行）没有 portal↔module 字节相等测试**，它只被 `cli.py:_verify_asset_manifests`(:163–185) 用 `manifest.json` 的 sha 校验——而那校验的是 **repo 根副本**，运行期消费的却是**模块内副本**（`builder.py:144–170`，module-first）。
- `report-a/b/c.js/css` 只存在于模块内，不在任何 allow-list、不在 manifest.json、task44 fixture（`tests/fixtures/task44-chart-table-sync/render_fixture.py:188–203`）还故意混用两处来源。

**修正意见**：不要引入"构建期复制"。安装包是**源码 allowlist**（`tools/bundle_contract.py:360–398`，第 382 行含 `src/ci_workflow/renderers/portal`），模块内副本才是发货副本。正确收敛是：保留模块内为唯一运行来源，把根 `assets/portal/` 降级为**被校验的镜像**——把已有的字节相等测试扩到全部 5 个文件（约 20 行），或直接删掉根副本、让 `cli.py` 对模块内字节校验 manifest。加构建步骤只会新增一个失败模式、零收益。

### 3. 大规模脏树 — **成立**

- HEAD 已核实：`.git/refs/heads/main` = `bb27ec9d750cf02fb64da5dfe665b2f4b262922d`，与清单一致。脏树条目数我无法实测（Bash 被拒）；会话环境自报 1,220 条，作为参考而非我的实测结论。
- 已有机制齐备且够用：`tools/check_clean_tree.py`（失败关闭、支持精确路径豁免）、`tools/verify_rebaseline_source_set.py`、`tools/rebaseline_snapshot.py`、`tools/gate.sh --require-clean/--source-set`（gate.sh:108–114）。
- v5 P7 第 1 条要求的"受控 source-set 逐文件纳入、保全原脏树"，**机制已经存在**，不需要新造。

**修正意见（与清单的疑问直接相关）**：**不要做中间里程碑提交。** 理由不是"禁止推测性历史提交"这条纪律，而是实质性的：当前树的科学链已知未接线（第 1 条）、真实取数只有单查询（第 6 条），此时提交会把一个**未验证的科学身份**固化成 provenance 锚点；v1.4 §14（第 255 行）要求身份同时绑定代码+证据+页面，而这三者现在都还不成立。事后验收要么继承一个假锚点，要么公开否弃它。

降恢复成本改用不落 git 的方式：立刻产出一份**脏树内容寻址清单**（路径 + sha256 + 字节数，不 stage），使任何丢失可被检出、且可用现有脚本重生成。若用户坚持要检查点，唯一安全形式是**仓库外的 tar 归档 + 哈希**，不是 commit。

### 4. 导航 / 元数据漂移 — **成立，且是"三处权威互相矛盾"，比清单更严重**

- `docs/specs/README.md:3`：**"当前唯一批准的完整产品设计是 `...-v1.3.md`（2026-09-04）"**；:7 称 v1.3 为 canonical。
- `docs/specs/competitive-intelligence-workflow-design-v1.4-review.md:1` 标题"完整设计 v1.4（待审定）"；:3 明确"本文件不代表Goal已设置，也不是实现完成或发布声明"；:38"本文中的新技术设计是审定候选，不冒称用户逐条批准"。
- 项目 `AGENTS.md` 仍写 v1.3 是 approved product contract。
- `README.md:3` 仍在宣传四种输出（站点式 HTML、原生 PDF、HTML-PPT、可编辑 PPTX），`:5` 还写"当前状态：Phase 0 基线建设"——与 v1.4 §1.2（第 23 行，首版仅 HTML）和 `package-manifest.json:11`（`formats: ["html"]`）直接冲突。

**修正意见**：注意——**不能据此把 v1.4 升为权威**，它自己声明未审定。正确做法是让权威索引**机器可检**：`docs/specs/README.md` 保留为唯一索引，加一条合同测试断言"只有一个 spec 文件声明权威"且"README 的格式清单 == `package-manifest.json.formats`"。`tests/contract/test_approved_spec_hash.py` 已存在，扩它，不要新建机制。然后修正 `README.md` 为 HTML-only 并删掉 Phase 0 那一行。

### 5. 语义提案链未闭环 — **成立；但清单对 P3.2 的判断有误**

- `SemanticGroupingProposal`（`reports/b/semantic_grouping.py:34–61`）的 `status: Literal["proposal"]` **在 schema 层面就无法表示"已批准"**，也没有任何 review/issuer 字段。测试还把这个当特性验证（`tests/reports/b/test_semantic_grouping_proposals.py:97` 用 `model_copy(update={"status":"accepted"})` 期望抛错）。
- 生产者：`src/` 内不存在。唯一构造点是测试（同文件 :31–36，`producer_id="synthetic-model"`）。
- 消费者：`report_b.py:2883` `proposed_semantic_buckets(...)`，渲染器是唯一消费者。
- `review_issuer.py:330` `issue_review_receipt` 与 `scientific_review_transition.py:646` `promote_rendered_candidate` 作用于**整个已渲染门户**（回执绑定 `ScientificQcCurrentContext`），**不作用于提案**。没有任何函数做 proposal 的 candidate→approved 迁移。
- 已有正确形状但无人生产：`SemanticAdjudicationReceipt`（`reports/b/semantic_contract.py:106–118`）带 `model_id`/`independent_review_id`/`independent_context`，grep 显示仅在本文件内被引用。

**对清单的修正**：P3.2「版本化时间政策未实现」**不成立**。`TimepointCompatibilityPolicy`（`reports/b/contracts.py:619`，含 `version` + `policy_id` + `_time_policy_id_text`）与 `EndpointCompatibilityPolicy`（:497）确实存在，从 YAML 加载（:791–804），并且**已被疗效视图层消费**（`efficacy.py:895–914`、`1254/1279`、`1443/1457`）。缺口不是政策，而是**渲染器的 `_time_band`（`report_b.py:835`）自己做单位换算、从不读该政策**——又一次双份。

P3.1 完整临床单元：**确实缺失**，`clinical_unit` 在 `src/` 内零命中。
P3.3–P3.5：**部分**。`unknown` 是哨兵字符串 `"not_reported"`（`semantic_contract.py:77–86`）+ `semantic_value_is_unknown`；`SourceApplicability.NOT_APPLICABLE`（`sources/policy.py:36`）与 `RouteCompletionState.NOT_APPLICABLE`（`sources/planner.py:15`）只存在于**路线层**，临床事实层没有 `not_applicable`。"不适用≠未知"在路线层被强制，在观察层没有。

**最小接通路径与顺序**（顺序不可换）：

1. 给 `SemanticGroupingProposal` 加显式状态迁移 + `review_receipt_id`，并**复用** `SemanticAdjudicationReceipt` 的既有字段形状，不要造第二种回执类型；
2. 新增生产者 `capabilities/semantic_review.py`，接到图的 `semantic-review` 节点（v1.4 §4.1 第 66 行），确定性 `compare_clinical_constructs` 保留为否决；
3. 让签发路径给提案签回执（复用 `review_issuer` 的身份/上下文绑定）；
4. 最后才让 `_groups_for_page` 消费已批准提案。

**不要从 P3.1 开始**——它是更大的数据模型改动，且它的缺失并不阻塞 1–4。

### 6. P2 来源链缺口 — **成立，且比清单更严重**

- 全仓**唯一**网络实现：`sources/connectors/ctgov_fetch.py:62–77`（`urllib.request` + 禁跳转 opener）。
- 查询形状**只有一种**：`query.cond=<condition>`（`ctgov_fetch.py:125–127`）。无 by-sponsor / by-intervention / by-NCT / by-target。
- 其余五个连接器全部是**纯校验/URL 构造，无网络代码**：`clinicaltrials_gov.py`(353) 记录构造器+分页 URL；`pubmed.py`(300) 仅 URL 构造(:104) + XML 解析(:125)；`regulators.py`(348)、`company.py`(168)、`china_registries.py`(672)、`authoritative_wechat.py`(248) 全为校验。
- **必需路线被声明但无执行器**：`policies/sources/source-policy-v1.yaml` 标了 `clinicaltrials_gov` required_global_baseline、`cde`/`chinadrugtrials`/`dxy_drug_assistant` required_for_china；但 `sources/planner.py` 是状态机模型类（`RouteProgress`、`assess_historical_source`），**不是 planner**。真正的强制点在 `domain/research_package.py:1019–1031`，而它只检查 `closure.global_route_ids`/`china_route_ids` 里记录的 `result_class` 是否落在允许集合内——**它不执行路线**。
- 时间：`ctgov_fetch.py:93–94` 硬编码 `universe_closed: Literal[False]`、`temporal_scope: Literal["current_records"]`；`cli.py:528` 自写限制串。
- OCR：`src/` 内零命中。浏览器适配：不存在，`application/yaozh_access.py`(439) 只持久化"是否有访问权"。
- 无任何产物证明真实端到端：CT.gov 测试全部用合成 transport（`tests/integration/sources/test_ctgov_fetch.py:23–33`）；各适应症 fixture 全是随包 JSON（如 `fixtures/positive/b-pnh/inputs/report-data.json`）。

**对清单的修正**："竖向样例优先还是横向铺开优先"这个二选一是错的。在语义链未接线的前提下，竖向样例**无法验收**（它需要尚不存在的独立科学复核路径）；而横向铺开等于把一条未验证的管线复制 24 份，产出 24 份没人能科学接受的产物。正确顺序：**① 先补一条真实可执行路线**（PubMed 最便宜：`pubmed.py:104`+`:125` 已有 URL 构造与 XML 解析，只缺一次 fetch+parse 调用和一个仿 `_research_fetch_ctgov_handler` 的 CLI handler）；**② 闭合提案链（第 5 条）**；**③ 再跑一个 PNH 竖向端到端作为首次真实验收**；**④ 最后才铺 8×3**。

### 7. 测试体系 — **部分成立**

- 规模核实：`tests/**/test_*.py` 约 250 个，分布在 12–13 个顶层根（acceptance / application / browser / contract / graph / hosts / html_ppt / integration / migration / pdf / renderers / reports / unit）。
- "gate 是 quality-only"**成立且是明示设计**：`tools/gate.sh:101–106` 只跑 ruff / mypy / v1-fast-tests(tests/unit+tests/contract) / retained-compat-smoke / v1-layer-audit / legacy-references，`:123` 自报 `GATE_OK status=quality-only`。科学门、真实浏览器门、包装/三宿主门、恢复门、RC 门都不在其中——v1.4 §14（第 251 行）要求它们**分别留证、不互相替代**，所以这不是疏漏。但它意味着"gate 全绿"对产品零含义，且现有的分层审计（`tests/contract/test_v1_test_layering.py`）只守**格式分层**，不守科学分层。
- 对"页面=科学视图投影"的覆盖：形状对、但**循环**。`_project_scientific_groups`（`report_b.py:2748–2768`）确实用 `semantic_row_digest` 拒绝页面行与完整视图不一致——但"完整视图"由 `report_b.py:3690` 自己产出。它证明的是渲染器自洽，不是与 `reports/b` 一致。

**缺失的关键负向合同**（每条都便宜、可立即补）：

- **a.** 没有测试断言渲染器不得自行裁决。最强可执行形式：断言 B 运行在缺少 `efficacy_views`/`safety_views` 时**失败关闭**。今天这两个字段是 `Any | None`（`report_b.py:1165–1176`），缺失被静默容忍。
- **b.** 没有测试能发现 `reports/b/*` 的视图构造器是死代码。
- **c.** 没有测试断言 `charts.js` 两处副本一致（第 2 条缺口）。
- **d.** 没有测试断言 README 格式清单与 `package-manifest.json.formats` 一致（第 4 条缺口）。
- **e.** `tests/browser/*` 覆盖了 shell/autoescape/drawer，但没有测试断言 v1.4 §11（第 219 行）的四视口 × 双引擎矩阵是**验收必要条件**，只证明了它可以被记录。

---

## 新发现

**F1（P0）科学视图层在生产路径上是死代码。** `build_efficacy_views`/`build_safety_views`/`build_matrix_view_state`/`build_endpoint_basis_set` 在 `src/` 内无外部调用者，只有测试调用（`tests/reports/b/test_efficacy_views.py:88`、`test_safety_heatmap.py:96`、`test_matrix_states.py:319`）；而 `run_service.py:732` 走的 `build_report_b_artifact` 从不触碰它们。这是对 v1.4 §9（第 183 行）最大的偏离，也是第 1 条的真实内核。

**F2（P1）`ReportBPortalData` 有未类型化逃生口。** `report_b.py:1165–1176` 的 `efficacy_views: Any | None`、`safety_views: Any | None`、`views`/`view_states: Mapping[str, Any] | None`、`matrix_view(s)` 五个 `Any` 字段，正是科学层本该接入的接缝。产品合同的技术形态是"Pydantic + 应用自有类型化控制图"（v1.4 §4.1 第 54 行），而这些 `Any` 使视图集 schema 漂移在边界上完全不可检。

**F3（P1）`src/ci_workflow/reports/b/__init__.py` 缺失**，而 `reports/a`、`reports/c`、`reports/common` 都有。`ci_workflow.reports.b` 是隐式命名空间包——这恰好是产品科学内核所在模块，且是把它作为整体导入/打包的前提。修复成本极低。

**F4（P1）路线结果 `not_applicable` 在闭包门被无证据接受。** `domain/research_package.py:1019–1031` 的允许集合包含 `"not_applicable"`，但该处**不要求任何适用性依据**。`sources/policy.py:36` 定义了 `SourceApplicability.NOT_APPLICABLE`，门却不查它。后果：一个"不适用"字符串即可让闭包门变绿，与 v1.4 §6.1/§9（"不可访问不是不适用"、"明确不适用与未知是不同状态，必须有适用性依据"）直接冲突。

**F5（P2）缺少科学分层的合同审计。** `test_v1_test_layering.py` 守的是 HTML-only 格式分层（`LEGACY_RUNTIME_IMPORTS`、`RETAINED_FILES`），很有价值；但没有等价的"渲染器不得裁决"合同。这是当前可得的最便宜的结构性护栏。

**F6（P2）`README.md` 是发货文件，却宣传被排除的格式。** `README.md:3` 列出原生 PDF/HTML-PPT/可编辑 PPTX，`:5` 写"Phase 0 基线建设"；而 `README.md` 同时被 `tools/bundle_contract.py:362`（allowlist）和 `:406`（`FINAL_REQUIRED_CONTENT`）要求进包。即**发货包自带的 README 与 `package-manifest.json:11` 和 v1.4 §1.2 冲突**。

**F7（P2）单查询取数可满足闭包门的验收完整性风险。** `cli.py:487–540` + `package-manifest.json:125` 暴露 `research fetch-ctgov` 为用户可见命令；结合 F4，一次 `query.cond` 查询的回执有路径满足闭包门，唯一的拦截是回执自带的限制串（`cli.py:528`）。这不是代码 bug，是验收完整性风险。

**F8（P3）模块内 13 个资产里 6 个未被 manifest 覆盖。** `assets/portal/manifest.json` 只列 6 个文件；`report-{a,b,c}.{js,css}` 仅存在于模块内，无 allow-list、无 digest 固定。一旦它们被 `resolve_portal_asset` 加载，既无 repo 回退也无摘要校验。

**F9（P3，正向发现）latest 指针实现是失败关闭的，可作为范式保留。** `application/latest_delivery.py`：拒绝回退与同时刻覆盖（:84–88）、`BEGIN IMMEDIATE` + compare-and-swap（:90–95）、发布前重验产物清单（:96）、fsync + `os.replace`（:97–103），且 `read_latest_delivery` 是**重开已接受链校验**而非信任标签（:58–64）。这正是 v1.4 §12（第 235 行）要求的。无需动作。

**F10（P3）延后能力的 bundle 排除是对的，但是人工维护点。** `renderers/pdf`、`pdf_native`、`html_ppt`、`pptx_master`、`qc/pdf.py` 留在开发仓（符合 v1.4 §1.2"代码留开发仓"），并由 `tools/bundle_contract.py:100–119` 的 `_V1_DEFERRED_PATHS` + `_assert_not_deferred`(:131–133) 失败关闭地排除。正向发现，无需动作。但排除是**按路径前缀**做的，任何新增在已允许前缀下（例如 `src/ci_workflow/application/`）的延后模块必须手工加入该集合——这是个维护点。

---

## 建议的下一步

按依赖顺序，每条都是最小可验收单元：

1. **补齐资产漂移护栏**：把 `tests/browser/test_portal_shell.py:455–479` 的字节相等断言扩到 `charts.js`，并把 manifest sha 校验对象从 repo 根副本改为**模块内副本**（第 2 条 / F8 的一半）。约 20 行，不动 `src/`。
2. **补"渲染器不得裁决"的负向合同**：断言 B 运行在缺少 `efficacy_views`/`safety_views` 时失败关闭（第 7a 条 / F5）。**这条现在会红——这正是目的**：把第 1 条从意见变成红灯。
3. **统一权威索引**：加一条合同测试，断言 `README.md` 格式清单 == `package-manifest.json.formats`，且只有一个 spec 文件声明权威；随后把 `README.md` 改为 HTML-only、删除 Phase 0 行（第 4 条 / F6）。扩 `test_approved_spec_hash.py`，不新建机制。
4. **补 `reports/b/__init__.py`，并把 `efficacy_views`/`safety_views` 从 `Any` 改为类型化字段**（F3 / F2）。先类型化、后强制必填——仅类型化就会立刻暴露 schema 漂移。
5. **给 `SemanticGroupingProposal` 加显式状态迁移 + `review_receipt_id`**，复用 `SemanticAdjudicationReceipt` 既有字段形状（第 5 条步骤 1）。
6. **新增 `capabilities/semantic_review.py` 作为生产者**，接到图的 `semantic-review` 节点（v1.4 §4.1 第 66 行），保留 `compare_clinical_constructs` 为确定性否决（第 5 条步骤 2）。
7. **补一条真实可执行的 PubMed 路线**，复用 `pubmed.py:104` 的 URL 构造与 `:125` 的 XML 解析，加一个仿 `_research_fetch_ctgov_handler` 的 CLI handler 与合成 transport 测试（第 6 条步骤 1）。这是证明"路线机制真会执行、而非只是被声明"的最便宜方式。
8. **收紧闭包门**：`not_applicable` 的路线结果必须附适用性依据（F4）。改动小、杠杆高，且与 5–7 相互独立。
9. **只有 5–8 全绿后**，才跑 PNH 竖向端到端作为首次真实验收（fixture 已存在于 `fixtures/positive/b-pnh`），再决定 8×3 铺开节奏（第 6 条步骤 3–4）。
10. **在 9 通过前，推迟 P7 source-set 收敛与任何提交**；期间只产出一份脏树内容寻址清单（路径 + sha256 + 字节数，不 stage），使恢复成本可测量（第 3 条）。

**未验证项声明**：脏树条目数（1,220）来自会话环境自报，非我实测；两处资产副本的一致性为行数+首尾采样结论，非字节哈希；`tests/**/test_*.py` 计数为约 250（Glob 全量枚举），非精确到个位。以上三项不影响任何裁决的方向性结论。