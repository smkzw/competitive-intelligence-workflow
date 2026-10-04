# R224–226：完整来源挑战、普通 A/B 候选与设计缺口隔离

现行 W03/W05/W07 实施，不新增产品权威。R224独立科学语义挑战；owner独占
共享schema和摄取/渲染。R226已裁决的缺失不推断语义采用成族RED后最小修复，
相关集成批次后仅在R223+R226稳定接口集中跑一次质量门。

## R224 已终态，不再等待旧 handles

kernel68766 EXIT后收98541 exit0。真实模型grok-4.7-build/grok-build，UUID
a3304c0d-76dd-44db-ba23-5ea734b6d2d5；768.507s、22模型调用/22turns、无回退。
high为请求和runner配置，不冒充独立server effort证明。
完整报告214行；owner另重开8索引hash、54研究身份、33引用、26自身metadata。
实际引用分布为14研究有引用、40无登记引用；早先18表述不准确，原记录不改。
reviewer54标签40direct/10mixed/1subtype/1healthy/2context均实际存在，但不等于
每个语义判断已获批准。独立报告是挑战证据，不是生产ScienceReceipt/医学批准。

关键纠偏：登记条件不能覆盖真实人群；DRUG不是小分子、BIOLOGICAL不是mAb；
剂量/制剂不另造分子；破损MG-K10/placebo关系与ICP322/332保留冲突。主论文
与亚组/量表/PK论文分开：PRIME37142763、OLYMPIA1 39602139、OLYMPIA2 37888917、
vixarelimab两部分36816342/41405882。PMID41051123自身内容冲突，不因登记号匹配
就通过。原源取值不重算，缺号不误排除。R221仍REVISE，后续全包修订不自签。

| 实物 | SHA256 |
|---|---|
|实际R224报告|49b960ac7a7b45d88ea8d0739ef0f26667762752f1f24dd28dfd0c7f7a1ab880|
|实际runtime|3ef75d3d02b9b4df54261d108b563daaa9b4f37727742a955bd6beec72911682|
|owner终态核验|7a95e49a7238b730154be4abc10e4a949c0546e38d791be03525e7034ed3078a|

## R225 普通入口真实接入，尚不完整

新私有根 `.artifacts/r24-225-pn-normal-entry-20261004/`，273MiB；无新HTTP。
完整PN母回执861ffe…cf20输入原有通用tools/build_a_payload.py，别名map为空，
不采信执行者建议等式。但构建器自身旧名称规则仍待修，不宣布37个已审定分子。
实际37候选产品、44研究、3538疗效行、185安全行、48其他域行；10无药物表
研究遗漏保留明确ID，原完整54未删，不能以44替代完整B相关研究池。

3771行逐原始值/定位核验；3538疗效/181安全可匹配、4安全缺口与7来源问题保留。
4个no_exact_match是缺收集时间窗来源与builder占位文字不一致，未用假时间补齐。
普通materialize实际15677 exit0：17有数值来源、4200候选事实、3767声明，
793疗效+31安全A编辑消费者登记、181 B安全来源视图。非全部科学采用，也未
登记B编辑消费者。生成A48页/14860121B，B101页/188445637B；C仍设计来源准备，
不伪称已生成第三个完整门户。B大体积/重复载荷是后续需要测量的产品成本。

自身探针第一次误用trial_id KeyError、第二次把小写内部id直接比大写登记号
AssertionError；均保留，非产品FAIL或GREEN。v3用display_id并验证其与内部id
精确casefold对应，未改原报告/来源字节。B摘要的site_directory_digest返回
`[sha256,bytes]`，字段名site_sha256误称单hash；实际按tuple解释，不更新旧摘要。

| 实物 | SHA256 |
|---|---|
|build-summary-v3.json|8ec3d76715cb634ae745f4cf09d4d8aaf0f03d852b526a549420e0279d5774cc|
|source-map-audit-v3.json|cf4e7b7bd52128e4687bc9827aa21f3425440c05c664b76bebefa41a7333281a|
|materialization-v3.json|249739e2d911fc3daf453331a80db83414bb60c5dacebfa0ce2d84b5a0d6ff55|
|b-render-v3.json|fe130a2e133f953aad9f5cf8d151dd3075c39f7bc7f191405835c9eee3e6d3eb|
|A实际site|fb06e2cb5d8fff4c601871f60a5893b9002e80b21a7bd1f39d42188fd0393dcc|
|B实际site|7d3985579db422b680801e11a44914f2cbe9f497cbe25fe1da2986cfe240609d|

## R226 同实例终点时间缺失不再中断全部研究

六个primary/secondary × absent/empty/null真实RED：生产源提取器整体抛异常。
最小修复是缺失时间窗记录精确absent路径，保持其他原子；非文本错误仍拒绝。
设计投影将相关定义/说明原子记missing_outcome_timeframe未决，不借用同试验
其他终点时间、不产生空时间图或把整研究丢掉。未决带factID/path，原原子引文
保持可取；并未声称这些未决已进入最终C门户。旧“缺timeFrame必须整包抛出”
属于实现断言，迁移为“非文本timeFrame拒绝”，其他源篡改/重复身份门继续保留。

完整八文件邻接145PASS/26.27s；Ruff四文件PASS、strict-mypy两源PASS。
真实PN54旧C候选0HTTP重放：3289事实/326缺口与原产物完全相等，源字节不变，
新parserhash另记，不更改原R222源码hash或继承旧版本回执。

R223+R226稳定接口一次tools/gate.sh真实exit0：全src/tests/tools Ruff、strict271，
活跃1117PASS/108.71s、保留兼容20PASS/.72s、分层7PASS/.23s、旧路径纯文本lint。
受检源码前后稳定；这是quality-only，不覆盖全部集成/报告/浏览器/正式科学/
fresh-install/三宿主/24门户/RC。没有为每个私人来源产物重跑宽门或安装包。

| 实物 | SHA256 |
|---|---|
|当前ctgov_design_atoms.py|efe4a1211f4532ad35de0fc09e75e7d17001fdaf01dafa6825af9178f6f7aecc|
|当前ctgov_c_design_projection.py|50bb6ac2671eac788491b07ad70d7ebce0ba9f8a579b6b9f4c069083d6947631|
|red-v1.xml|aed7b49f39df9a3dda5be72dfb3e13999e709e4cf88e76826b3c5f5fc2a26acc|
|green-v1.xml|1503220b58ff73a15a5f37f566a615da8dc2f3017d948e2313a2989973e2b8f0|
|真实PN重放|a5ec89bbca263abf1a590165e6e50223360214a4d89d475bc28423d6baa25329|
|quality-gate-v1.json|f17d92a7bac103f6fb095220d6de050f1688fc886a03825e35a986f0964a6f45|
|quality-gate-v1.log|5b6dac9fefb1055c1121ce632f0f3ce3c26fd781dfe5fdd7f6a94875560c2189|

新私有226136KiB。保留唯一源/候选/失败/DB，不借一般清理删除。旧R218包属于旧
资产版本，新223/226尚无安装/真实浏览器证明。Ego12选择题与其他既有Ask仅影响
对应项；没有擅自替代空间或浏览器。Goal连续，无新暂停/正式current/提交/push。
后续先全包修订并测量普通B/C完整性、绑定/保存/分享，然后集中当前包/实屏；
八适应症24门户、中国/global/reverse闭包/主论文/三宿主/恢复/RC全部仍开放。
