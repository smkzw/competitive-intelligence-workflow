---
name: extract-design
description: 为一个药物补充试验设计信息（尤其中国登记、无 CT.gov 记录或 CT.gov 信息不全的试验）
tools: [china_registry_search, china_trial_detail, ctgov_get, web_search, fetch_url, pubmed_search, pubmed_fetch, read_project_fact]
output: ExtractionResult
max_steps: 20
---
输入：一个药物、适应症、已有 CT.gov/中国登记结构化设计的试验列表（trials_with_registry_design，不要重复抽取）。

重点补充：
- 中国登记试验（CTR 号）：期别、样本量、对照、主要终点及时间点、入排关键条件、主要研究者单位
- 论文方法学中的设计细节：随机比例、分层因素、设盲、主要终点定义、多重性控制、关键入排阈值

字段：design.phase / design.sample_size / design.allocation / design.masking / design.control /
design.primary_endpoint（value 写 {"measure":..., "time_frame":...}）/ design.key_inclusion / design.key_exclusion /
design.stratification / design.multiplicity。

规则同 extract-results：先读取原文，quote 逐字复制，找不到写 gaps。

公开方案/SAP或论文方法PDF可用fetch_url读取完整文本及页码范围，长文按offset继续；引用实际source_id与quote，不能从文件名/下载时间猜历史公开资格。扫描或解析失败保留处理缺口，不把失败当成无设计内容，不自动调用OCR或请求凭据。

known_trials中detail_tool=china_trial_detail的CTR研究，使用该工具读取中文登记详情；不猜详情URL，不从列表题目推断期别、人群或申请人角色。完整中文入排、组别及终点内表均保留在可分页结果中；计划/已入组/实际总人数分别照录，空缺不是0。登记申请人不是自动核实的MAH；健康人药代研究仍按实际人群和测量保留，不写成患者疗效。

普通trial_evidence已按原中文临床表确定性采用的研究也在trials_with_registry_design内。不要重抄或重写同一表格；只补原表未提供、实际新来源支持的设计内容。条件性PK、原始强度/规格关系和全部组别保持原文，不用登记适应症替换健康受试者人群。原文内不一致保留并记录gaps，不自行纠正剂量。

每条事实优先填写本次工具返回的source_id及source_url。同一公开详情URL可对应多个CTR和来源版本，必须逐事实指定实际读取的版本；宿主仍核对本次读集、项目及URL，错误/未读取的ID不能落成已核实来源。source_id不是接受许可，quote/数字/科学上下文核验仍照常执行。

china_trial_detail优先给出精确来源和完整source_text；quote从该原文逐字复制，不抄JSON数组的引号/逗号。只有工具包明确status=paged时才用顶层64位result_id和next_offset调用read_tool_result；网页内部32位detail_id不是分页ID。未出现分页标记不能自行宣称文本被截断。登记原词、计划/实际与未知状态照录，未读取的后续内容不能补造。

样本量的 enrollment_type 只在原文明确时填写 ESTIMATED（计划）或 ACTUAL（实际入组），未知留空。计划与实际、不同组、分析人群或访视是不同观察，不互相 supersedes。新来源明确修订同一科学上下文时才能取代原值；保留来源限定，不从人数大小猜测类型。

同一药物可能按完整试验记录分批；本批 known_trials 与 existing_design_facts 只是执行任务，不是全研究范围截断。只补充本批已有研究和实际发现的新研究，不重复其他批已读取的登记设计。

existing_design_facts 提供当前事实的ID、字段、来源和读取入口，不在输入内重复大段原文。需要比较原值、引用完整定义或提出修订时，先用 read_project_fact 读取完整值及上下文；长结果按 next_offset 继续分页，不截断定义。只有新来源明确修订同一研究同一字段时才填写 supersedes；不要按优先级猜测取代关系。无明确修订仍保留各来源，原登记与原文不修改。未通过原文核验的值不能取代既有已核实事实。

文献按工具返回的实际内容层级使用：content_level=pubmed_record只证明已读取PubMed题录/摘要，不证明已读全文；pmc_full_text才是取得并核对文章身份的PMC正文。请求full_text=true不等于取得全文。full_text_status=not_in_pmc只表示本次题录无PMC副本，metadata_unresolved表示题录元数据未解；都不能写成论文不存在或结果未公开。PMC访问/解析失败保留失败记录，必要时可显式另取PubMed记录，但不得把这种后续记录称作全文。仅引用实际取回的页段/文本，不能补造未读表格、附录或方案。
