# R211–214：书目候选与实际获取见证

211实际kernelEXIT/rc0后核验：PI/zai/glm-5.3/high请求，fresh session
01a1045b-4744-7000-9f74-480ee8ce3ea0，无fallback，4691.123s；原生assistant
身份集仅zai/glm-5.3。382独立原生工具启动，runner计1585不是去重调用数。
父线程只启动确认/内核等候，无进度轮询。不是独立医学接受。

全58 reference_id/原始引用/登记定位与冻结输入相同，46BACKGROUND/12RESULT
原标记保留；RESULT不等于主要结果。486原始回执filename/SHA/size全核，
3,653,206B（不是模型自报约4.7MB）。worker状态22书目候选、1歧义、11引用
不匹配、11非PubMed未定位、7官方host线索、3URL失效、3访问部分失败，全部是
未接受观察。会议/后来论文、图书版次、量表版本与dataset年份不能只凭题名合并。

owner发现1不存在回执指针、1DOI混备注且与其NLM原生DOI不符，以及每HTTP
URL/时间计算后未真正落档。生成时间/mtime不能补造实际获取时间。原PMID27417017
的own DOI为10.1016/j.jaad.2016.05.046；原错误候选保留，不从备注猜测清理。
Broken首轮/全部错误与原件保留。211结论REVISE，只接受资料作为书目候选线索。

214使用生产PubMed精确UID检索+EFetch取得7/7原生PMID；25Crossref own-work
DOI当前真实GET成功。新CAS保存实际URL/UTC时间/原生字段，原211时间仍未知。
这是公开metadata，不是期刊/商业全文、不扩全文获取政策、不制造首次公开日。
零HTTP重开全部27页，生产PubMed parser/type、25作品的原生ID/对象/hash/size/
时间/URL一致，错ID和错hash两个实际篡改拒绝。新资料仍保留全部58引用/候选/
歧义，不first-wins。旧7247身份集3已有/4未有（21834600/21967117/32246968/
40539960），建议并集7251但未写入/采用，不以数量为完整性目标。

| 私有实物 | SHA-256 |
|---|---|
| 211 recovery/recovery-ledger-final-v1.json | `bc5eb696bdd97b060817a9414abdf8637d1e4d6c4f4e15842d29fb02ab5ceaea` |
| 211 owner-terminal-audit-v1.json | `e70b82f9ac68f7605a385224cb21ded5c6ec33f16141394c38985fa28dea25af` |
| 211 terminal report | `6ed0f9b08576700a2252b96def46308f1231629d91ad52dc3471f7b27f822638` |
| 211 private runtime | `5dab641dec73a89b2f341b994538e0eb8ebbcdf4261bd2da209f0b7af1917421` |
| 214 current-metadata-v1.json | `dd8a9ee51579a552be1fb2700f731144dd0777190a71818fe838c4555dfed80a` |
| 214 pubmed-fetch-v1.json | `1ab6898b3a1ce7ca9e6cb4f39d7beea0f389cef49122e9608175186f7abec738` |
| 214 verified-reference-candidates-v1.json | `b561f5a61b0595bfba0dcf76527b08223ef31d71b9b4b9633f2bb57c388984db` |

私有目录：`.artifacts/r24-211-unidentified-reference-links-20261004/` 与
`.artifacts/r24-214-current-bibliographic-witness-20261004/`。exclusive-create脚本
不可覆盖重跑；候选原文不进Skill包/公开Git或分享。生产未变，不为metadata重跑
212全仓门。下一步现行W07独立核对文献—试验关系与角色，核心必需论文才进补件
门；58无PMID不能叫58主要论文缺失。科学/全文/宇宙/24门户/三宿主全部模式/
浏览器/恢复/RC均仍开放，无来源采用/current晋级/新暂停。
