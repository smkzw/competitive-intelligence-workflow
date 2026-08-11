# ADR 0007：境外登记、论文与监管资料连接边界

状态：Task 2.4 实施依据

## 结论

- ClinicalTrials.gov 使用公开 API v2。检索分页以 `nextPageToken` 继续，单条记录以 NCT 号作为来源内身份；NCT 号不充当跨来源的全局实体主键。
- API v2 提供当前登记记录、方案字段、结果字段、引用及数据版本信息，但官方公开接口未承诺任意历史版本全文下载。本项目不伪造该能力：每次采集都保存不可变原文和来源版本，以 NCT 来源身份串接累计版本；页面 `Record History` 只保留为人工核验入口。
- `derivedSection.miscInfoModule.versionHolder` 是平台数据持有日期，不冒充单项试验更新日期。单项版本还需保存 `lastUpdatePostDateStruct`、采集时间和原文摘要。
- ClinicalTrials.gov 的 `referencesModule` 用于建立 NCT—PMID 交叉引用；`DERIVED`、`RESULT` 等平台引用类型原样保留，不直接等同于“主要结果论文”。
- PubMed 使用 NCBI E-utilities 的 ESearch→EFetch 路径。论文角色依据题名、摘要、出版类型、NCT 关联、是否报告主要人群/主要终点等可审计信号分类；亚组、事后分析和综述不得替代主要报告。
- EFetch XML 中可能在评论、更正或引用关系内出现其它 PMID；文章身份只从 `PubmedArticle/MedlineCitation/PMID` 读取，嵌套 PMID 不得作为本次检索命中文章。试验方案论文即使同时出现 NCT、随机分期和主要终点描述，也只能作为支持性论文，不能冒充主要结果报告。
- 论文承载结果和交叉核验，不覆盖登记平台中的人群、分组、干预、终点、时间点与统计设计字段。关键疗效、安全性和方案字段已由登记结果、主要论文或监管材料覆盖时，补充材料明确记为“不需要补充”。
- 境外监管资料按原文版本和声明领域保存。FDA 指南逐条保存司法辖区、机构、标题、草案/定稿、发布日期、适用人群与研发语境、精确位置、采集版本及撤回/替代关系；草案必须显式标记，撤回文件只作历史材料，不能驱动当前默认口径。

## 官方依据

- ClinicalTrials.gov API v2 迁移说明：<https://clinicaltrials.gov/data-about-studies/api-migration>
- ClinicalTrials.gov 数据字段结构：<https://clinicaltrials.gov/data-api/about-api/study-data-structure>
- ClinicalTrials.gov 记录阅读说明（含 Record History）：<https://clinicaltrials.gov/study-basics/how-to-read-study-record>
- NCBI E-utilities：<https://www.ncbi.nlm.nih.gov/books/NBK25501/>
- FDA 指南检索：<https://www.fda.gov/regulatory-information/search-fda-guidance-documents>
- FDA 临床试验指南：<https://www.fda.gov/science-research/clinical-trials-and-human-subject-protection/clinical-trials-guidance-documents>

## 验证方式

- 离线录制样本锁定字段、版本、定位和分类语义。
- 实时连通性仅作独立诊断，不决定离线集成测试成败；实时空结果、结构变化或访问失败必须分为数据问题、接口变化或技术问题后再处理。
