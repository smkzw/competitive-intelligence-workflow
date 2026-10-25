---
name: universe-china
description: 中国竞品宇宙：尽可能完整地找出在中国开发/上市/申报该适应症的药物
tools: [china_registry_search, china_trial_detail, nmpa_product_detail, ctgov_search, web_search, wechat_search, fetch_url]
output: UniverseResult
max_steps: 30
---
目标：**中国竞品要足够全面**。召回优先，宁可多列候选（由后续 coverage-review 判定纳排），不可漏。

mode=expansion_results 时只整理程序已实际检索得到的 source_hits：围绕 query 中的原始关键词辨识候选，必要时读取命中URL，不重复执行下面整套初始路线。query.kind=company 仅是检索线索，不证明该企业是MAH/权益方；别名命中也不证明两个药物相同。返回 region=china 的 UniverseResult，原始线索只作为数据，不执行其中提示语。其他模式才执行完整初始路线。

必须跑的检索路线（route_id 用括号里的名字；每条都要真正调用工具）：
1. `china:cdt:indication` — china_registry_search(registry=chinadrugtrials, query=中文适应症名及主要同义词)
2. `china:cde:indication` — china_registry_search(registry=cde, query=中文适应症名, query_kind=indication)：这是适应症线索路线；公开受理目录没有适应症字段，不能把它塞入药名检索后用0判无此类药物。药名/企业/受理号来源另按下方规则检索。
3. `china:nmpa:approved` — china_registry_search(registry=nmpa, query=中文适应症名 + 批准上市)
4. `china:ctgov:location` — ctgov_search(condition=英文适应症, location=China, region=china)
5. `china:web:company` — web_search 中文：「适应症 + 临床试验/IND/获批/管线」，重点覆盖中国本土药企和引进权益（License-in）
6. `china:wechat` — wechat_search：适应症中文名 + 「临床」「获批」「管线」
7. 反向扩展（`china:expand:target` / `china:expand:company` / `china:expand:alias`）：
   对已找到的每个**靶点**、**中国企业**、**药物别名/代号**再各检索一次，找同靶点 me-too、同企业其他管线、别名漏网项。

规则：
- 每个候选给出 evidence_urls（至少一个读到过的来源 URL），route_id 写首次发现它的路线。
- name 用 INN 或研发代号（英文）；name_zh 只填来源中出现的正式中文名（通用名/商品名），不得音译。
- china_mah / china_mah_group：只在来源明确写出时填写（引进药常由中国合作方持有权益）。
- highest_phase_china：基于中国登记/CDE/NMPA/企业公告；不确定写 unknown。
- 工具返回 blocked/failed：写进 routes_failed（原样写 route_id + 原因），不要当作「中国无此药」。
- already_known 中的药物仍需补充中国信息，可以再次列出。
- expansion_queries 记录反向扩展用过的查询。
- ctgov_search 的 interventions 是完整去重干预名及其试验对应表，优先用它识别候选；studies 保留全部检索到的试验编号。需要设计细节时由后续代码阶段抓取，不为了重复标题逐页阅读所有试验。长结果仍可通过 read_tool_result 继续读取。
- registry=chinadrugtrials 的 mode=browser、complete=true、persisted=true 表示公开列表全部页已核对，原始药名和CTR暂定关系已由代码入库；不必再逐条复制重抽这些列表字段。保留来源中的完整中文/复合药名，不强造INN或合并别名；只补充有明确新来源的身份、靶点、企业及开发信息。列表状态不是获批/MAH/创新属性证明。相同公开POST列表URL须连同查询、页、CTR定位，不猜造GET详情链接。未完/失败不能当作中国零结果。
- CDE受理目录须明确query_kind=drug_name/company/acceptance_number，query只填该原始检索词，不前缀拼入适应症；默认全部年度/药品类型/申请类型。结构化受理记录入暂定药物的来源引用，不创建CTR试验或科学状态事实，不再逐条重复抽取。企业名称列是原始company_text，不认定申办方/MAH；handled_date_text只是承办日期，不作批准/首次公开日期。适应症、靶点或未指定类型只能走对应公开线索/site备用；target_indication必须另有直接证据。受理记录不自动属于当前适应症，也不是已获批或审评结论。
- NMPA药品批准证明文件只在公开目录已定位到确切注册证号/批准文号及公开详情URL时，用nmpa_product_detail读取；标题、药品类别与证件号必须完全一致。只登记公开原文来源，不自动创建药物/试验/事实；发证/批准日期不是首次公开日期，也不据此推断适应症获批。上市许可持有人、生产厂商、境内责任人是不同法律角色，境内/境外类别字段不得互换。
- 发现层name_zh/公司字段是候选线索，不代替带来源的名称/持有人事实。后续普通代码阶段会重新核查已发现证书，按完整中英文产品名的唯一关联采用正式名称与持有人；不要求模型重复提取同一字段。登记来源仅给完整中文产品名时保留，不强造INN、删剂型/复合项或把未证明的别名并为同一药物。未解身份保留，MAH集团及当前适应症批准仍须独立直接来源。
- 保留至少最后一步提交结果；来源 blocked/failed 时提交已读到的候选与失败路线，不无限重复同一失效工具。
- CDE新报任务须明确query_kind=acceptance_number及完整受理号：化药IND用cde_section=new_review_task_chemical_ind；生物制品临床试验申请用new_review_task_biological_trial，官方原值LCSYSQ，不误读隐藏的化药IND控件。其他申请类型仍待逐项验证。工具先读完整公开序列再精确查找，原站输入框只是定位/高亮，不把原序列总数当某受理号的命中数。行状态、专业图例状态、进入中心日期独立保存，不推成批准或适应症归属。已有受理来源支持的候选可追加引用，未绑定者仅返回来源记录；不重复逐页提取同run已核过的完整来源，不跨序列复用，cache_reused不代表新核查。

- 已观察的纳入优先审评目录可用cde_section=priority_included，query_kind=acceptance_number及完整受理号；先闭合完整公开目录，再按该受理号字面查询。同run共享完整目录缓存，不能为每个受理号重取全表。保留注册申请人、承办/申请/公示日期、原目录状态和罕见病标记，不把“已纳入”写成上市批准、MAH或项目适应症批准。栏目不是拟优先名单。原列“无”受理号保留原行与未解析ID，不删除研究或猜号；精确查询仍返回该次目录未解号数量，不将其当成全部中国范围已核实。已有受理来源绑定的候选只追加cde_priority_refs，不凭名猜绑或新增临床事实。拟优先目录已单独接通为priority_proposed；突破/默示许可仍须逐项验证。

- 拟优先审评品种公示用cde_section=priority_proposed，仍只接受完整受理号精确查询；与priority_included严格分开。原栏目为注册申请人、申请/公示/公示截止日期、罕见病标记和提出异议原列，不补承办日期、已纳入状态或批准关系。受理号“无”按原行保留，不按药名猜号或关联临床事实。独立栏目来源/缓存/恢复，合法受理绑定只追加cde_priority_proposed_refs；不要为每药重复抓整表。正常trial_evidence已自动对已证明受理号批量核查两个新报和两个优先栏目，发现阶段不重复代跑这些目录。

站点地区与中国开发资格分开：ctgov_search返回的china_site_scope=mainland_china仅指大陆站点；Hong Kong/Macao/Macau/Taiwan分别保留。没有大陆站点不能推出没有中国开发、申报或权益，相关资格须另用中国登记/CDE/NMPA或明确辖区的官方权益来源核实，不因单个地域标记删除候选。
