# 0924V1 R235–239：C 研究先例身份、完整来源候选与恢复

仍执行 W03/W04/W05C/W07/W08，未新建产品权威。Goal active，旧中文根零接触。
保留全部用户脏树、失败和历史快照，无当前发布/commit/push/RC。

## 实施与真实验证

235 明确 C product_id 必填但可 null，缺字段不等于明确未知。复用 StudyRow，
A TrialRow 与 A/B 已绑定事实要求不放宽。首次四真实 RED→四 focused PASS。

236 派一个 E03 执行节点，仅 design/pages/endpoint_instances 与新身份测试，
owner 同时处理合同/来源/渲染/消费者，写域不重叠。实际211.242s，OMP会话
01a10541-2a2f-7000-8b6e-cb34c18e8580，kernel23791 NOTE_EXIT 后收33717终态，
无回退。cursor/default 是动态 selector，不是已验证底层 model/effort。Worker
五 RED/一原 PASS→六 GREEN/116 邻接。owner合并43 PASS/11.04s；九 scoped-mypy
FAIL 与混合 null/string 诊断排序 TypeError 如实保留并修，不用 cast/ignore。
已知产品的三条身份锚保持不变；未知关联使用研究命名空间，不存 fake product。

237 来源消费者只接受 C observations 的 product_id/drug_name 同时明确 null；
missing/半未知/已知-未知漂移拒绝。原源版本、定位、原文、快照闭包、append-only
与幂等不松绑。真实85固定来源候选登记/导出/恢复/幂等复跑已通过，源事实和
两端 current 不变。最终恢复邻接61 PASS/60.39s（非全仓）。XML
`06eb0d1ea6b6730b0d8194bb20da95df351a451b8265c952ac7dc6bfbbfda046`。

238 普通原源预览、模板和实际生产 JS 过滤五真实 RED：混合身份错误排序；
纯待核/混合研究无法预览；产品二次显隐盖过完整筛选；空筛选重画全图。
一组完整修复后44邻接 PASS/9.27s、strict10源 PASS、最终 scoped-Ruff PASS。
真实源入组0/未知/计划仍分开。模板不产生 data-product-id="None"。作者与镜像
report-c.js 同 SHA `1469da0974273cf01da298385d573f33114e079e5040e8d78a43112e1f015130`。
初次 Ruff13FAIL 与后续两格式FAIL保留，未改科学/交互断言；格式收口后通过。
RED XML `323e9c8ae717e76ae09a18b7321ecf7d88778b6a536caa2cb9545b0ee1b334b5`；
GREEN XML `c6ffde76f5d4fa03553568cb2205177381931a2317fd37716142d71215e1f8c1`。
Node/最小DOM并非浏览器/审美通过。Ego既有12空间本次再次真实 NOT_FOUND，
既有选择题仍待答，不换空间/浏览器，不重问或继承旧截图。

## 239 完整 PN 来源集：普通 C 候选和恢复

唯一私有 `.artifacts/r24-239-full-pn-c-study-candidate-20261004/`，235MiB实际。
源母回执 `861ffe73c6248f3cea9aadd858b81a2c4492c1bb8abdcfaef5245afdcc57cf20`。
54真实登记研究、3289设计原子→2254候选设计观察/2254精确来源消费者，普通
C生成66物理页/110113990bytes。819未支持原子、313未决原子、326可选路径缺口
原样保留，不猜产品或臂；全部产品明确未绑定，不意味着54都是创新治疗。
52研究终点实例成对；NCT00532519/NCT04776694缺终点实例覆盖，仍保留研究，
正式门不被绕过。候选只能待复核阅读，不能初始化正式 current。

两次 owner 探针失败保留：v1 把普通Enum的str当序列化candidate，登记前失败，
无项目写入；v2 用午夜报告截止替代合同当地日终，登记前原子性拒绝。已有证据
项目保留，v3用现有合同精确截止恢复，仅追加新摘要快照，不覆写旧快照/原源。
v3实际38023 exit0。v4实际15171 exit0：66页/2254观察图表原文与来源身份逐条
核对可达；导出2254绑定，钉固manifest后恢复到新空目录，全部事实版本/状态/
科学内容与源端相同；幂等恢复成功，两端 current 无创建，站点字节不变。
没有科学采用、实时重新检索、当前用户编辑、离线分享或浏览器实屏结论。

| 固定实物 | SHA256 |
|---|---|
| C site |70efa7b418a5c47c39239b8fe08c858c0d78cc38ce6a9ffe6a39bebb07e64334|
| c-portal-data-v1.json |e93e36084b2fb7d02a14f78ef9e25a0d0d3c176980d2c3675d10e29d9021fb2a|
| c-projection-v1.json |ea0b6e9c865b9a03c807917796e1c771a86f9e54011b42f9265dff7cfaf339a1|
| c-source-inputs-v1.json |0085f6bae897083db5687030a8db44da409040e1aaf5e3138ea0d56bd5948051|
| replay-pn-c-v1.json |0e1fd897581cb14e9f4f841386cb457258375bfdd80112d8e5dbec55958f591c|
| source-checkpoint-v1.json |43d922fb094b5f4a21ae43e890d8254a4fca741a2c5b2e50fac7321add51b016|
| c-recovery-manifest-v4.json |be86b7f6d6438b6f5b89d7322db0dbf470a766fa1c8a176c262f6d3433600ae3|
| audit-recovery-v4.json |ed80d0f579e5c8f5520e250fc9a572482bdb6644a09b99845faca4bfb34555b6|

候选科学内容摘要 da2dc1848df56a809c05f49c98e9b8170f84298863d4d4bc37b3444c157befaf。
大站点不入Git，但现有私有站点/SQL/CAS/恢复包均受控可取；恢复命令为 v4 helper，
只能对全新输出运行，不重跑已存在目录、不清理唯一材料。

## 下一工作单元与验收边界

四旧 AD 审计失败已有 R230 同字节证据，不继承历史PASS。240一个 E03 当前测试
oracle迁移已实际启动：必须以原始路径/语义独立预期保留负例，不能改魔数掩盖；
精确写域为原测试与一个新测试，产品/源码/历史fixture只读，owner持其他代码。
初始化不算结果，终态后才核字节/初始RED/实际GREEN；不在途QA或进度轮询。

完成真实B完整观察池/创新与中国来源/必需论文与方案/正式科学上下文、当前保存
分享和桌面实屏；再集中一次质量与安装候选门，不按私有资料/小改重复宽门。
24门户/三宿主全模式/恢复与RC仍为交付门，未缩范围、未假称全部完成。
