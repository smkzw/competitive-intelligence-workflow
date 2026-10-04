# R216：恢复时也要核对声明的科学身份

现行W01/W07/W08的最小完整修复，不新增数据库、审批或恢复平台。共享科学
合同由owner单独维护；215来源关系独立审阅只读另外冻结源，未碰其输入。

## 实际缺陷与修正

恢复路径原来直接写claim closure，能接受AI方法缺失/被改、类型变化、声明ID
变化、内容版本错、支持事实缺失/包外事实、manifest声明集合错等八个反例。
成族RED真实复现八项；第九FAIL是测试把SQLite tuple当dict，单列为测试错误，
不冒充产品RED。red-v1.xml原样保留。

ResearchClaim的scientific_version_id成为摄取和恢复共同算法；直接/计算旧身份
不变，综合方法/标记仍进入新声明内容版本。恢复先验证类型、支持事实映射、
科学ID及声明集合再写隔离区；失败不发布目标。历史快照只读，不自动补签或升级。

七文件相关批47PASS/6.46s，包含新恢复族、声明语义、trust_snapshot_closure、
review_r07_ingestion、recovery_artifact_validation、verified_candidate_recovery与
snapshot_identity。Ruff四文件/strict-mypy三源通过。完整修改稳定后仅一次
quality门实际exit0：Ruff全src/tests/tools、strict271源/tools、1117活跃unit/
contract、20保留兼容smoke、7分层、旧路径纯文本检查通过。不是全integration/
科学/浏览器/24门户/终验门。

## 真实候选与安装实核

私有`.artifacts/r24-216-claim-recovery-20261004/`保存真实228事实/80声明，全部仍
candidate。只读213冻结输入和187原XML，0HTTP；生产摄取后只凭manifest恢复到
空目录：source_versions、evidence_fragments、fact_versions、fact_evidence、
claim_versions、claim_facts、source_acquisition_attempts七DB表完全一致。
195片段、198声明支持关系、228精确引文重放、76显式AI方法、原始字节与锁定
快照相同。改方法但保留旧ID的实际负向资料拒绝，目标不存在，原项目不变。

v1核验探针误把已移除row_ref的科学材料当成消费者合同，真实失败保留；v2
只读接回原候选的消费者提示以解析类型，不往科学材料写row_ref，不回退身份
分层。原脚本/项目/失败不覆盖，后继audit_recovered_paper_v2.py只读重开实物。

新d3900…b2fa8开发包390作者文件＋manifest，外部require-final-content验真，
391安装记录逐hash/size/mode相同。独立安装解释器真实恢复同228/80快照并拒绝
方法漂移；入口帮助、包核验、隔离合同/恢复三检查PASS。不是三真实模型宿主。

仅清本次私有安装runtime/cache，uv报1376缓存项/183.4MiB，不声称实测物理释放。
391安装字节/模式、元数据和入口再核不变；缓存可再生成。原始来源、失败、
快照、其他安装、用户工作树、会话及数据库未清理。

| 实物 | SHA-256 |
|---|---|
| source_research_service.py | `f1726782e41a655f5574f3df0431e4c1acb33307ba44eabed7faa506fb134863` |
| fresh_research_ingestion.py | `4fe0f4a0609b52f0cc316817ac6236e092f418dc719923cb514beeb6e5d7374b` |
| snapshot_store.py | `223b853b336509f8b8601389c652b1b5557aac64c01160ad2e48d9952060a677` |
| red-v1.xml（八真RED＋一测试错误） | `97fb70e8d0edf752879c9535780da93b3260d48ccb8cce50f20dd77e79520583` |
| green-v1.xml | `29000ea0df00ade0036d6666517cd040e9ed60226b4ce535753c85e67ada2939` |
| stable-gate-v1.log（终态） | `2bfcd526b4526b0761957db4edcc02bc0082855ec2f9dc9073d7a3f03bb1f77f` |
| 真实锁定恢复快照 | `f54c0a65ec14202499c98889c7dfeba659b337e874366f532e5258763a3e47ec` |
| real-paper-recovery-v2.json | `2d01226a5bbd03366772584da07587d0cc03d385e9ba063c31936dd3b047e63b` |
| ci-r24-216-development.tar.zst | `d3900dc91d9bcb59de90ab99528474418fc017fc6626d2d73811a8cf629b2fa8` |
| bundle manifest | `2b4bd14b13fb290f11bfebbf8f487c8c21716853f913a5a0a1cf9a437d5278a9` |
| installation.json | `33f3badd332957054958de138c1e5dad6374a124863c47869d26b7a46d2ab53b` |
| installed-contract-v1.json | `a3b279bf94e2505ed3ee74caf22a9b0f40fd2105bc427c5f941061115d2c3a36` |
| owned-cache-cleanup-v1.json | `b8adab5b2d807c39546bd03eb3234431090d0e8a68c8167b6eefd66b7d32e034` |

当前HEAD仍c129a575a403ea39027e112c1acd80ca77b43117，脏树保留，无提交/push/
current晋级。来源恢复不是整项目resume/刷新/重建验收，更不是文献日期资格、
独立医学接受或专业批准。新216不继承212包/门，213原未接受状态不变。
Ego/资料政策Ask仅阻断相应项；科学/宇宙/24门户/全部宿主模式/视觉/分享/
整项目恢复/RC继续开放。215只kernelEXIT后核，不重等旧终态或重复全页会商。
