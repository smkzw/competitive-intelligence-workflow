# W07 真实来源链只读追踪（2026-09-23，开发证据）

判定：**未闭合**。本记录不是科学复核、全量验收或已修复回执。只操作英文工程；旧中文工程零接触。只读原生子任务提供了八组 PNH 实例，主线程独立复核了下述计数、代码断点和两个 CAS 文件哈希；其余逐个 JSONPath 尚待生产链重放，不能把子任务结论直接当正式验收。

## 三个不同分母，不得混用

- W05A v6 实际 `data/report.js` SHA-256 `e4e8c181e56fc6e9c8fbdf511226561c877279813b5ad0532d766becd979a695`：疗效 3895 + 安全 517 = **4412**；逐事实 `source_field_path` 与 `source_text` 同时/任一具备均为 **0/4412**。这是当前受审展示载荷，不自动等同于数据库或另一份中间包。
- `runs/test-pnh/evidence/library/a-portal-payload.json` SHA-256 `da36a48bb49c8afdd683290dc76a3eb00f14c4de6d119a8c3a00420cfbaa8eed`：疗效 4141 + 安全 136 = **4277**（本轮 `jq` 重算）。
- 同目录 `a-research-package.json` SHA-256 `3d9c091f1a119594b65ca9aebe2b14c9456ac9dc7d930b62ee8d64dfbc30fdec`：**4458 facts**（本轮 `jq` 重算）；其中还含非疗效/安全事实。

## 存储与断点

本轮只读 SQL 重算 `runs/test-pnh/state/project.sqlite`：`content_blobs=10`、`source_versions=10`、`evidence_fragments=10`、`source_text_derivations=0`、`fact_versions=4759`、`fact_evidence=4759`。两个按研究切片的 CAS 文件已按字节重算，SHA-256 与文件名相同：`57/5745725fe69c03ee4a145888c2f9137df00be2ffef2c17f7638b1fb491695ecd.bin`、`8c/8c7cc7ac11529a753e40705ce711e574b774eb00e239316a84bbc6b1bfed7345.bin`（均位于 `runs/test-pnh/evidence/raw/sha256/`）。

历史包装器 `packets/2026-09-11-pnh-vertical/build_pnh_audit.py` 仍使用 `studies[]` 粗定位，并把“某行的登记结果事实”构造为 `original_text`；这是占位文本，不是原始来源引文。`tools/build_a_payload.py` 未把逐事实精确路径/原文携带到最终 A 行。当前 `source_research_service.py` 可抽取结局/AE的部分精确路径，但尚无死亡汇总字段；旧 A 构建器虽读取死亡汇总，却不满足新精确摄取合同。`storage/source_derivation.py` 已有拒绝通配符、从 CAS 重提取原值的能力；`application/fresh_research_ingestion.py` 已要求事实原文等于重提取结果。主要断点是旧 PNH 构建路线绕过这条新合同，而非 CAS 全部遗失。

只读样本显示：多组、多期、真实零值、复合安全类别、LDH 多时间点的数值在 CAS 中有可追踪候选；某些分母在对应终点对象中确实缺失或跨对象来源未证实；另有 `hasResults:false` 的研究本身无结果。**不能**因为数值可找到就自动补分母、编造来源或把真实零值当缺失。尚未验证八组全部 JSONPath、组别/时间窗语义和版本绑定，也没有发现可证实的这批真实记录解析失败；“未发现”不等于全量不存在。

另一个待核科学边界：活动 AE 解析器对个别 `stats.numAffected` 缺省使用 `0`，而精确重提取无法引用不存在的字段。ClinicalTrials.gov [官方字段结构](https://clinicaltrials.gov/data-api/about-api/study-data-structure)定义该字段为整数及其含义，但本轮没有找到足以普遍证明“字段缺省=真实零值”的官方规则。生产链不得把这种推断零值当作带有精确原文的 `reported_zero`；先核对原页面/下载格式及组别语义，必要时以缺失/待核状态保留。此项为审计推论，不是已确认的 ClinicalTrials.gov 编码规范。

## 下一最小实施批

1. 选上述多组/多期/零值/缺失/多终点/复合安全小批真实 CAS；重放 `SourceCapture`，将按研究切片的来源版本和 `source_text_derivations` 持久化，禁止再用页级 `studies[]` 当事实定位。
2. 每条采用事实绑定研究、终点/事件、组、类别、时间窗、稳定身份、精确无通配符路径、重提取原文；数值/分母分别证明，派生值必须携带输入事实与公式。
3. 用真实小批在快照和 A 页面核对逐事实入口，分类记录 `source_missing`、`parse_failure`、`source_unmapped`；然后才选择唯一新的 A 载荷哈希，重新计算全量闭合分母并扩展 B/C。W05B/C 的桌面结构可以并行，不因来源暂缺而虚报终验或暂停开发。

当前请求的子任务模型/effort只有请求参数，没有独立运行时回执，身份记 **UNVERIFIED**；该报告是只读诊断，不是用户所禁止的执行/会商机制。

## 首个生产接缝（同日实施，仍非闭包）

新增 `source_capture_from_ctgov_study(project_root, study)`：消费现有 `derive_ctgov_records` 的单研究切片，重新打开原始 CAS 回执并核对 NCT 身份、标题、来源网址、`lastUpdatePostDateStruct.date`；以 `calendar_day` 而非虚构时刻进入现有 `SourceCapture`。未新增第二套来源存储。一次本机真实 CAS 探针在 `5e055f4c…bin` 的 `studies[5]` 重放 NCT04558918，精确路径 `$.resultsSection.outcomeMeasuresModule.outcomeMeasures[1].classes[0].categories[0].measurements[0].value` 重提取字符串 `68.8`，回执方法 `ctgov-study-json-v1`。该探针在临时目录运行，**尚未**把事实写入正式 SQLite、快照或页面，故 0/4412 未变。

随后在自动清理的**临时试验项目**中，使用同一真实 CAS 切片和上述精确 `EvidenceLocator` 调用现有 `ingest_research_evidence`：得到 1 个来源版本、1 个 `source_text_derivations`、1 个事实版本；SQLite 事实 fragment 的原文是 `68.8`，locator 是上述无通配符路径。临时试验项目并非当前 PNH 项目的正式数据库/快照；试验用 fact ID 和 claim 仅为接缝验证，尚未建立跨来源/排序稳定科学身份，不得用来称正式报告来源闭包。

为清除重构噪音，删除 `source_research_service.py` 中 `ingest_fresh_a_research_package` 已经 `return` 后的约 230 行不可达旧摄取代码；历史可由 Git 父提交找回，现有生产入口仍使用共享 `ingest_research_evidence`。新增接缝正/负案例及邻接日期/来源审计/研究包集成批 `16 passed`，修改模块 Ruff 与 strict mypy 通过。后续仍需把多组、多期等真实事实、分母和状态通过该接缝进入摄取与门户。

## 原子数值与分母重提取（同日后续，开发候选）

`source_research_service.py` 的登记结果解析现保留每一项原始数值字段路径；存在由人数计算比例的记录时，同时保留独立分母字段路径。新增 `extract_ctgov_atomic_results` 对既有 `SourceCapture` 的 JSON 原文按精确 locator 重提取数值与分母，返回可见值、原始 quote、组别/终点/时间以及解析/缺失问题，不把派生百分比当作来源原文。`numAffected` 缺失仍只产生“未知，待核”的问题，不产生零原子；组别汇总某一字段缺失也不再吞掉同组另一项有效统计。

真实本机 CAS 探针：`5e/5e055f4c38b521ee0b77d8d55c403955f543e6800db21245bd2d1bf36e7b4a14.bin`，SHA-256 与文件名相同；从 `studies[5]` 重开 NCT04558918 后得到 **216 个原子结果、0 个该研究解析问题**。其中 `68.8` 重提取路径为 `$.resultsSection.outcomeMeasuresModule.outcomeMeasures[1].classes[0].categories[0].measurements[0].value`，组 `OG000`；此项为来源直接报告的百分比，无单独分母 locator，不可借其他 `N` 重算。该 CAS 位于当前未跟踪运行资料，不能据此声称新安装包可复现。

定向整族：`tests/integration/test_ctgov_result_coverage_audit.py`、`test_w07_ctgov_capture_bridge.py`、`test_source_text_derivation.py` **30 passed in 55.29s**；所改模块 Ruff 与 strict-mypy（该 1 个源文件）通过。以上仅是原子重提取层：尚未形成稳定 `ResearchFact` 身份/组期关系、独立分母派生记录、正式 PNH 数据库/快照、A/B/C 页逐事实来源入口；4412 条展示事实的闭包数量仍未重算，保持 W07 FAIL。下一步用原子结果经既有 `ResearchFact` 和 `ingest_research_evidence` 摄取真实小批，验证不匹配/0/0/缺失及报告行绑定，再扩全量。

### 原子事实摄取接缝续建

新增 `ResearchResultContext`（既有事实可选字段，省略时序列化字节不变）与 `research_facts_from_ctgov_atom`：从一个有精确字段路径的结果生成原始数值事实，存在分母时另外生成一个分母事实。组别、终点、时间、类别和原始数值角色进入事实版本的科学上下文；来源报告的估计百分比仅保存其原始报告值，不把显示比例误当 n/N 派生。错误的疗效/安全行绑定被拒绝。使用已入库 AD 来源 NCT02277743，在独立临时项目中摄取一条报告百分比、一条明确零事件及其风险分母，得到 1 个来源版本、3 个事实版本与逐字段原文片段；测试同时核查数据库中的 `reported_zero`、`EG001` 和精确 locator。该测试尚未把事实映射到最终门户。

又以本机真实 PNH CAS `5e055f4c…bin` 的 NCT04558918 在自动清理临时项目中完整走过：原始分页字节→研究切片/派生回执→`SourceCapture`→216 条可解析原子→选取原文 `68.8`→`ResearchFact`→既有 `ingest_research_evidence`→SQLite 精确片段。该探针结果为 1 个来源版本、1 个事实版本、片段原文 `68.8` 与上述精确字段路径一致；首次探针只因诊断 SQL 错把 context manager 当连接而失败，修正探针后成功，未改产品数据。此处的摄取项目是临时项目，不是正式 PNH 数据库；216 是该单研究解析原子数，绝不等于 4412 条报告事实的来源闭包。后续仍须做稳定报告行交叉绑定、派生 DAG、0/0 无风险人数边界、缺失分类、快照/页面和全量重算。

### 缺失 AE 人数的跨层回归

用户确认 `numAffected` 缺失应为“未知，待核”，不能推断为零。新增以 AD 夹具中 **NCT05131477** 的真实缺口 `seriousEvents[16].stats[7].numAffected` 为输入的回归：原子结果和由它生成的事实均不得指向不存在的数值字段；问题须保留为 `missing`。另一研究 NCT02277743 的明确原文零值仍保留为 `reported_zero`，且记录事件术语与组别。首次测试误选 NCT02277743 寻找上述缺口，测试失败；定位实际来源后修正样本，未修改生产逻辑或历史夹具。W07 摄取接缝文件最终 `4 passed in 24.34s`；合并审计批的首次运行 `1 failed, 16 passed` 不能记为全绿。受改模块 Ruff、单模块 strict-mypy 和 diff 检查通过。这只是规则与小批回归，未解决 NCT05131477 原始缺失，也未闭合最终门户逐事实来源。

### 单条 A 疗效行的核证绑定（同日续建）

新增 `bind_ctgov_outcome_to_a_row`，只处理登记来源直接报告的数值，不把人数/分母推算率伪装为原文。调用时重新抽取当前来源，要求原子结果与当前字节一致，并逐项检查试验、终点、时间窗、组别标题/组号、单位和数值；既有路径、版本或引文若与来源冲突则拒绝覆盖。绑定同时返回对应的原子 `ResearchFact`，报告行记录精确字段路径、来源版本、原文及组号。结果科学上下文新增组别标题，避免仅靠宽泛“治疗组/对照组”误绑不同剂量。

真实 AD 夹具 NCT02277743 的 Placebo IGA 16 周 `10.3%` 作为首个样本，来源原文 `10.3`、路径 `$.resultsSection.outcomeMeasuresModule.outcomeMeasures[0].classes[0].categories[0].measurements[0].value`。替换内存中的单条 A 行后，真实 `render_report_a_site` 产出的 `data/report.js` 包含该路径和当前来源版本；错试验、错值、错组别、既有冲突引文均拒绝。此小批并未修改历史夹具、当前正式 PNH 项目或 4412 条最终展示事实；`source_version_id` 入页面仅证明该行链路，不代表全站来源闭合。人数/分母派生 DAG、其他 A 行及 B/C 绑定仍待实施。

改动代码 Ruff 与单模块 strict-mypy 通过，邻接来源审计、摄取和研究包提交批 `22 passed in 83.23s`；实际站点仅验证数据载荷，不是浏览器视觉/交互验收。

### A 研究包提交边界接入（同日下一批）

已将上述核验接入 `FreshAResearchContent` 的提交前验证：只要事实声明 `result_context` 且绑定到 `efficacy:` 报告行，执行器按来源版本每份重提取一次结果原子，核对结果键/精确路径/组别及完整报告行；同一行多个主事实、未绑定到当前行的事实、原文或行字段冲突均拒绝。人数计数不得借“直接报告值”路径绕过派生公式。真实 AD `10.3` 行的正确原子绑定通过定向核验；在内存构造的研究包里把该行 `source_text` 改为编造引文，实际 `FreshAResearchContent.model_validate` 在覆盖审计前拒绝。合成历史包不含新 `result_context`，此新增门不追溯重写或宣称其逐事实来源已闭合。

改动模块 Ruff、单模块 strict-mypy 均通过；摄取、A 研究包及来源覆盖邻接批 `20 passed in 84.21s`。**限制**：新门只覆盖显式原子绑定的 A 直接报告疗效；未绑定旧事实、人数/分母派生率、安全性以及 B/C 还需各自的逐事实闭包和生产路径。真实来源数值到最终 4412 条事实的分子未重算，W07 仍 FAIL。

### AE 时间窗和 n/N 小批绑定（同日续建，未闭包）

重新读取 AD NCT02277743 的原始登记 JSON，发现 `adverseEventsModule.timeFrame` 明确写到最终访视 Week 28；历史 A 安全性行却写“来源未单列时间窗”。解析器现在把该模块时间窗进入每条 AE 原子的科学上下文。显式绑定遇到历史错误时间窗会拒绝，只有把行改为当前来源原文的时间窗后才能继续；历史夹具字节未被改写或重标 PASS。

真实 `任何SAE / EG001 / Dupilumab 300 mg q2w` 小批：来源 `seriousNumAffected=7`、`seriousNumAtRisk=229`，解析展示率为 `3.1%`。`bind_ctgov_ae_to_a_row` 对试验、类别、事件、剂量组、收集时间窗、统计对象、分子/分母和展示值做同一身份核对；报告行的 `source_text` 是原始人数 `7`，不是捏造的“来源原文 3.1%”。分子和分母各成一条精确来源事实，并生成同时引用两事实的确定性计算声明。A 研究包的显式绑定验证要求这两事实和计算声明同时存在；缺分母、改原文、错行或缺计算声明均拒绝。真实站点 `data/report.js` 可见该单条 AE 的精确来源路径。

代码 Ruff 与单模块 strict-mypy 通过，来源摄取、登记覆盖及 A 包邻接批 `20 passed in 86.80s`。**仍未完成**：计算声明尚非设计合同要求的完整结构化派生记录（输入 fact *version*、规则版本、公式、输出、适用范围与快照关联）；页面尚未把人数/风险人数/计算式一起呈现给用户，且没有浏览器验收。A 其他 AE、B/C、正式 PNH 数据及 4412 条全量来源均未闭合。下一批应补共享派生记录及其页面消费，再按真实小批扩展，不可把此处的单条示例写成 S01–S03 通过。

### AE 结构化派生与安装迁移闭合（同日后续；仅小批）

对同一 NCT02277743 的 `7` 与 `229`，`CtgovAeRateCalculation` 固定规则 ID/版本、`round(100 * affected / at_risk, 1)`、输出 `3.1%` 与 A 安全性行作用域。摄取前按共同登记研究、事件、组别、时间窗、来源、原始整数及算式核对；伪造 `3.2%` 被拒且数据库来源版本仍为零。成功摄取后，`evidence_derivations` 的 `calculation` 行及不可变快照同时记录两个 fragment ID、两个 fact version ID、规则/版本、公式、参数、输出及 claim version ID；恢复空项目后计算行保持一致。同一输入重复摄取不重复增加派生。此计算来自两个原子来源值，不声称登记页直接报告了 `3.1%` 原文。

初次端到端用例发现旧 0011 表的 kind CHECK 只允许 `source_text/normalization/translation`；若使用 `INSERT OR IGNORE` 会把新 `calculation` 静默丢掉，形成“快照有、SQLite 无”的假一致。新增 0015 迁移复制旧行并重建 CHECK/append-only 触发器，改计算插入为仅对相同派生 ID 幂等，其他错误不忽略。迁移测试证实旧行保留、防修改有效与 `PRAGMA integrity_check=ok`。安装 `package-manifest.json` 原仅列 0001–0010，而实际已有 0014；现列至 0015，并让 `package verify` 比对声明与全部实际 SQL。定向 W07/迁移/包合同 **13 passed**，`PACKAGE_OK` 为开发候选；先前同界面相邻批 **32 passed**、Ruff 与 243 文件 strict-mypy 通过。上述属于不同测试时点，不合并冒称一个终验。仍缺页面消费、B/C 同源绑定、正式 PNH 数据库 4412 条闭包、浏览器和 fresh-install 验收；W07 继续 FAIL。

### AE 快照派生的 A 门户公开投影与浏览器检查（同日后续；仅一行）

新的 `project_a_calculation_evidence` 读取有 hash 保护的证据快照，按 claim version、两个 fact version、两个原文 fragment、同一 source version、报告安全行的值与精确定位逐项闭合，再给渲染器一个公开字段子集。没有 `calculation` 派生的旧行不从 `n/N` 猜测得到；缺行、错值或缺派生失败关闭。真实 AD NCT02277743 的一条 7/229→3.1% 在 A 安全页“查看数据依据”中有折叠条目、原始人数、计算式、Week 28 登记原文时间窗、双字段路径和 CT.gov 外链。直接渲染的浏览器试验只给该行一个真实来源条目并明示“此处只核对一条安全性比例，不代表全站来源闭包”；不是正式 AD 报告或独立科学接受。

第一次 1600px Chromium 实测发现长英文时间窗和 JSON 字段路径把证据区撑至 610px、超出 395px 容器；改为短摘要+完整可展开原文，专用单列栅格与长词换行后同一容器 `clientWidth=scrollWidth=395px`，可见文本不截断。截图：本机 `output/playwright/w07-calc-evidence-1600-final.png`，SHA-256 `e725a7af89616be0a9584da3f76cb2b4b7267bfb405f319ac7e447f533ac6a6e`。浏览器检查了点击打开、摘要展开、真实外链与无 console error；随后修复原有证据侧栏 Escape 不关闭/不回焦问题，最新浏览器重测：打开后焦点到“关闭数据依据”，Esc 后 `hidden=true` 且焦点回“安全性热图”触发按钮。相关 A 来源/渲染/事务/镜像测试批 **44 passed**，Ruff、strict-mypy 243 文件、JS 语法、候选包校验均通过；后续微调测试来源日期与焦点处理需随最终源码再核相邻范围。W07 仍 FAIL：仅一条 AE，小批临时项目；正式 4412 条、B/C、全桌面矩阵、fresh-install、24 门户、三宿主未完成。

### PNH 原始页批量试读与弱候选分层（同日后续；仍未形成报告绑定）

基于现有旧研究包 **10 页/190 个 NCT** 原文和 W05A v6 `data/report.js` 的 **4412 行**，本轮只读重新计数：132 个登记记录明确 `hasResults=false`，58 个有结果；当前门户引用的 50 个 NCT 全属后者，来源原文均在这 10 页。首轮复用新原子解析器时 132 个无结果记录误抛 `resultsSection 必须是对象`，另有实际 NCT00397813 在“受试者人数 0/分母 0”处抛 `ZeroDivisionError`，只剩 57 个成功研究。对此做了两项科学边界修复：明确 `hasResults=false` 且无结果模块时安全返回无原子（不得当解析失败或补零），0/0 不形成发生率，保留精确分母路径和“比例未定义”问题；声称有结果却缺模块继续失败关闭。NCT00397813 的 0/0 来自旧 PNH 原文中的 HCT 分组，不自动认为其属于报告 50 个研究。修复后对**报告实际引用的 50 个研究**重新打开原始页、生成研究切片并重提取，全部 50 个可读，得到 15,556 个原子结果、81 个 `parse_failure` 问题与 3 个 `missing` 问题；其余 140 个未在修复后重跑，不声称全 190 通过。

进一步仅用于**寻找工作量**的宽松候选计数：疗效按同 NCT + 数值约 ±0.11，3895 行中 442 无候选、1531 恰一候选、1922 至少两候选；安全按同 NCT + 分子/分母 + 数值约 ±0.11，517 行中 269/19/229。该粗筛没有核对人群、终点、组别、时间窗、类别、统计依据或来源原文，单候选也**不是**已核证绑定，歧义不能靠 first-wins 消掉。下一步把无候选按来源确实未报告、旧包装器变换/解析遗漏、第二来源与错误行身份分类；多候选按完整医学身份和精确 locator 再解歧。未形成新的唯一候选报告字节/摘要，也未把本批计入 4412 分子；当前仍为 0/4412，W07 FAIL。

相邻 AD 覆盖审计曾固定断言只有 1 个缺失，新增 0/0 识别后实为 8 个：原 NCT05131477 `seriousEvents[16].stats[7].numAffected` 缺失仍在，另有 7 个来源明确 0/0，其中 NCT03334396 1 个、NCT05131477 6 个。首次相邻批 `1 failed / 27 passed` 如实保留；测试已按精确来源位置改为分别断言上述两类问题，并把两研究的 `reported_not_projected` 保持为未闭合，不是把 0/0 改成 0%。定向审计回归 `1 passed`；最终 W07/CT.gov 覆盖/A 研究包/镜像整族 `28 passed in 103.90s`，Ruff、strict-mypy 243 文件和候选包校验通过。该测试范围不覆盖正式 4412 行、24 门户或三宿主。
