---
name: extract-design
description: 为一个药物补充试验设计信息（尤其中国登记、无 CT.gov 记录或 CT.gov 信息不全的试验）
tools: [china_registry_search, ctgov_get, web_search, fetch_url, pubmed_search, pubmed_fetch]
output: ExtractionResult
max_steps: 20
---
输入：一个药物、适应症、已有 CT.gov 结构化设计的试验列表（trials_with_registry_design，不要重复抽取）。

重点补充：
- 中国登记试验（CTR 号）：期别、样本量、对照、主要终点及时间点、入排关键条件、主要研究者单位
- 论文方法学中的设计细节：随机比例、分层因素、设盲、主要终点定义、多重性控制、关键入排阈值

字段：design.phase / design.sample_size / design.allocation / design.masking / design.control /
design.primary_endpoint（value 写 {"measure":..., "time_frame":...}）/ design.key_inclusion / design.key_exclusion /
design.stratification / design.multiplicity。

规则同 extract-results：先读取原文，quote 逐字复制，找不到写 gaps。
