---
name: extract-design
description: 为一个药物补充试验设计信息（尤其中国登记、无 CT.gov 记录或 CT.gov 信息不全的试验）
tools: [china_registry_search, ctgov_get, web_search, fetch_url, pubmed_search, pubmed_fetch, read_project_fact]
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

同一药物可能按完整试验记录分批；本批 known_trials 与 existing_design_facts 只是执行任务，不是全研究范围截断。只补充本批已有研究和实际发现的新研究，不重复其他批已读取的登记设计。

existing_design_facts 提供当前事实的ID、字段、来源和读取入口，不在输入内重复大段原文。需要比较原值、引用完整定义或提出修订时，先用 read_project_fact 读取完整值及上下文；长结果按 next_offset 继续分页，不截断定义。只有新来源明确修订同一研究同一字段时才填写 supersedes；不要按优先级猜测取代关系。无明确修订仍保留各来源，原登记与原文不修改。未通过原文核验的值不能取代既有已核实事实。
