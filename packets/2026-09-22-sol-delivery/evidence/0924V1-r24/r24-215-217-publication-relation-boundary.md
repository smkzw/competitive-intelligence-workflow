# R215–217：文献身份、试验关系与角色不能混作一个结论

现有W07的最小完整修复，沿用既有B `unclassified`，不建第四种报告或新本体。
来源共享合同由owner维护，215只读独立审阅冻结材料。Goal连续，无新暂停。

## 215独立审阅的实际结论和边界

Grok4.7/high单次新鲜上下文实际终态rc0/end_turn，732.576s，native响应
`grok-4.7-build`，19turns/modelCalls，无回退。high为请求/CLI记录，非响应
独立attestation。58原引用/30完整研究/32自身metadata全覆盖；11支持候选、
8身份矛盾、11模糊、16背景、8需原件、4无法判断。原BACKGROUND46/RESULT12
不是科学角色。000/023/041/044仍是同研究候选，尚无主要/延长期/关键安全采用。

会议报告不等于后来期刊论文，图书/量表不同版本不能混绑；APPLES的7954符合
条件者与8071登记入组量先保留语境差异，不能直接宣称数值矛盾。owner不采信
“54均非本试验结果”的概括性排除：缺NCT或不完整引文不能证明无关。

Reviewer未找到workspace相对CAS；owner在正确R214/pubmed、R214/crossref
根重开2原始PubMed见证及25原生Crossref对象、17登记母页、30研究、58原指针、
32元数据和2上游输入。hash/size/原对象完全一致、0HTTP；此处只关闭字节追溯，
不是独立全文医学接受。不改冻结材料、不为路径问题重派整轮。

权威记录：`reviews/codex_conference_ci-r24-215-citation-relations-review-20261004_review.md`
及同名metrics。私有实物位于`.artifacts/r24-215-citation-relations-review-20261004/`：

| 实物 | SHA256 |
|---|---|
| terminal-source-audit-v1.json | 2f26597417365c964ac5eaed6f09bbdf6044fb239641f96091fe74c65724be2f |
| candidate-crosswalk-v1.json | d5de39f84aeb6d6094b4558f4a17df0ecf9b527ff7bfeb37a002d437195b6180 |
| 独立报告 | 5f8abedca93a06b2d2fe0f8d894ec2675eefc6b3904eb68096817650b25cad2e |

## 217生产修复和批量验证

生产 `_classify` 不再将未匹配目标NCT解释为 `unrelated`；输出既有
`unclassified` 和中文关系未确定说明。记录、原始ID/类型/数值、母试验角色仍保留；
不能替代主要论文。参考文献中的NCT、部分编号或其他研究的ID仍不能冒认关联。
B消费者继续重算当前规则并拒绝伪造primary角色；本轮没有放宽它的验证门。
模型/独立终审仍有责任从原件作实质关联和角色裁决，规则候选不等于医学接受。

8真实RED后完成同根因最小改动，9文件123PASS/2.19s；Ruff4文件、strict-mypy
PubMed+B合同2文件PASS。修改仅当前源码/当前实现断言，不改历史fixture或SHA。
R216宽门/安装包属于旧源码，不继承为本次当前通过；本轮相关批已覆盖B真实
生产消费者。下一稳定产品里程碑集中跑宽门和新包，不为每个私有资料文件重跑。

实际0HTTP重开113原始页/7247自身记录/1758目标研究，旧typed metadata摘要、
全部ID及匹配NCT有序集合不变；6550无目标匹配记录保留待裁决。5993宽检索
子集只5507 `unrelated→unclassified`，其他364supporting/81ad-hoc/33primary/
8review候选角色不变。全7247目前角色建议6550unclassified、549supporting、
92ad-hoc、43primary、13review；43是规则建议，不是43主要论文已接受。
另7当前元数据逐hash核验，4新记录只独立提案，不就地合并或采用；40539960
无NCT仍unclassified，32246968的APPLES关联来自正文显式NCT，不来自会议题名。

v1真实探针FAIL：历史捕获顺序与inventory顺序不同，导致有序匹配ID比较失败，
是探针输入错误，非产品RED。原v1脚本与失败记录保留；v2使用原capture顺序并
核对两套目标集合完全一致。原件/旧摘要/当前项目未改。

私有实物：`.artifacts/r24-217-pubmed-relation-boundary-20261004/`。

| 实物 | SHA256 |
|---|---|
| pubmed.py当前源 | 80d7dd3df37482aee0ea500ba1ea555f86e7b28a8637bc1878a9089de409c5ce |
| red-v1.xml | 7801401de4de6b2af456d511190c0428927a1315605bfa2daa6b20c94a9ca860 |
| green-v1.xml | 43344c9a460e7f37c7b6ced2be4e75c0867cd991a78ca16a95146a76442a8fda |
| real-relation-replay-v2.json | 496f3bab1720a239b9022343746c3065f3db6d2b3df5407ccadf633036aa2c5a |

## 下一步与禁止夸大的结论

215/216/217所有handles终态，无在途节点或需要重复等待。下一工作单元应推进
普通入口研究/门户的完整操作链及A/B/C桌面组件，不继续整篇论文/逐标签循环。
Ego原空间12不可达的原生Ask仍待答，不能擅开空间或用别的浏览器称实屏通过。
药智/论文公开见证等既有Ask只影响相应项，不阻断其他授权工作。

主要论文全文和资格、竞品宇宙、全球/中国当前来源、当前独立科学接受、新实屏、
24门户、三宿主全模式、当前离线分享/整项目恢复/RC均尚未完成；没有current
晋级、正式接受receipt、提交/push或旧工程接触。历史证据原样保全。
