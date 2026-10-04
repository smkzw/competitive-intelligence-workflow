# R200–201 当前 AD 来源与公开接口恢复

## 边界与真实身份

唯一英文根，HEAD `c129a575a403ea39027e112c1acd80ca77b43117`；既有脏树保留。
Goal active，未暂停/提交/push/切换正式current。新项目仅位于
`.artifacts/r24-200-ad-current-research-20261004/project`，project ID
`project_cc6ce532c5262738530990af`。普通入口实际建立特应性皮炎 A/B/C、HTML项目；
截止日2026-10-04为本次默认日，`cutoff_was_user_supplied=false`，不是历史还原。
药智路线原生Ask待答；公开接口先行，不替用户声称有账号或沿用旧会话。

重要纠正：owner曾口头将另一条 R199 DUBHE 论文称为 AD，这是错误描述。
原题名为“An anti-TSLP monoclonal antibody for uncontrolled CRSwNP: the DUBHE
randomized clinical trial.”，PMID41022848/NCT05324137，研究CRSwNP，不属于AD。
R199实际冻结输入没有绑定AD，候选未采用；两分支不混用。不能把该登记号不在
AD检索集合中当遗漏，也不能因CM310/CM326相似而合并。

## R200 安装内真实获取

使用已核验390作者文件包 `81ad355c4d32aff60fb96b2d233acf8fe8fbf23a9b2e0570714f8e04ec16058a`
的fresh-install-v3公开入口，查询 `("Atopic Dermatitis" OR "Atopic Eczema")`，
page-size100/max-pages1000，不做Top-N截断。真实2444终态exit0：1758条/18页，
2026-10-03T22:07:00.093963Z至22:07:16.359821Z；51,101,465原始分页字节。
`pagination_complete=true`，`universe_closed=false`。收件全量并非创新竞品闭包。

不可变获取回执：项目相对
`evidence/raw/sha256/8a/8a5edacb1f521ab7fb858a9fefa89eaa168fb29c997564dfb5ba0be698a7b586.bin`，
SHA同文件名。既有 `tools/build_ctgov_source_inventory.py`（开发工具，不在安装包）
由安装解释器运行，输出上层 `source-inventory-v1.json`，SHA
`859532dffad88e2a0eaa9625f0854e5e6b7c815cdf240dcb04a02ff5460f9455`；
固定source-set `978f9b574699a696679f666ab1f7feac72000e56823b41d42062f2487cf351e5`。
重开18页及1758原记录身份/字节，不改原件。

清单：1131登记药物候选研究；1116建议创新候选、464建议非药物、15建议标准/对照、
163创新属性未明；366含resultsSection，17未载人数；463别名建议、65冲突。
这些是全量保留后的候选提示，不是接受的药物同义关系或正式研究纳入判断。
中国来源、别名/靶点/企业反向扩展、创新资格、Publication和独立复核仍未闭合。

安装内1758原记录的生产原子提取重放18060在途，输出仅
`atomic-source-inventory-v1.json`：逐研究capture/hash、候选计数/域/问题及科学提取digest，
失败逐研究记录，不把解析失败写成无数据。私有脚本不做采用/报告/current。
初次25817因私有digest不支持嵌套Pydantic对象TypeError退出；属核验脚本错误，
不是登记缺数据。明确序列化BaseModel后重新运行；另一次启动误写安装目录exit127
亦单独保留，不算产品失败/成功。不为这些脚本细节跑全仓。

## R201 PubMed 真实限流与最小修复

安装内9172实际exit7；检索声明5993篇，保存七ESearch页后429，尚无EFetch记录。
回执SHA `4b09914cd39d4426363b8087dc4242c8dcb4d2c328a98e60ca43fde7c794bbea`
保留于同项目CAS。`rate_limited`不等于0篇/分页完整，也不证明每个429都由本程序造成。
检索是疾病MeSH/中英文名对应英文同义名，加临床试验类型或随机/延长期/phase线索；
仍需登记绑定论文反向恢复，不宣称此一检索式覆盖全部相关论文。

NCBI官方规则：[同IP无key全部E-utilities合计每秒3次](https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/)。
生产默认transport原来没有请求节流。owner inline，客观接口根因，不增加模型会商、
账号、API key、重试平台或依赖；使用stdlib monotonic/Lock/sleep，共享进程内
ESearch/EFetch/ESummary请求起点至少0.35s。慢请求不另加固定等待，失败也占请求额度。
IP上别的进程仍可能429，已有明确失败/恢复合同保留，不隐藏重试。

成族实际2RED/1PASS，集中五文件邻接批90PASS/2.15s；Ruff两文件、strict-mypy
一个生产文件通过。RED XML `98987f1d99de5432e200d30f803e48d207460be5e368b428d50e3b984496f486`；
GREEN XML `7037f9472ec7595d79ec22ded4d067396d4ea9974b42e3656572c64e2e295602`。
新pubmed_fetch源码SHA `9876f5cb09507d591f8ce9f7d2b2df94da755fa263489cffcd09fb13b0cbbca9`。
首次Ruff发现test zip缺strict参数，最小修正后Ruff通过；不抹失败。
R201产物/回归在 `.artifacts/r24-201-pubmed-request-pacing-20261004/`。

当前开发源码普通CLI8479重跑同一真实检索在途；实际模块origin已核为英文工程src。
不是对旧81ad包的通过证明；新源码不得继承旧包/稳定门。冻结/重打包在完整单元后一次做。

## 下一安全动作

读取本地18060/8479终态与确切结果，保留失败；R199仅kernel退出后核候选，
再安排一位source-first独立科学复核。新Ego空间/药智/C论文策略Ask待答，不静默代选。
24门户、各宿主全部模式、完整宇宙、科学/视觉、分享实浏览器和完整恢复/RC仍开放。
