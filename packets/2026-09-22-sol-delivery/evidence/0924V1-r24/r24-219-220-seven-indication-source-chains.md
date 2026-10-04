# R219–220：另外七个适应症的登记原件与有界缺口恢复

现行 W07/W09 来源准备，不把来源数量当创新竞品数，不以六份登记清单代替24门户。
219一个E07执行节点承担独立公开获取；owner负责共同来源身份和实物核验。
220是确定性资源缺口，inline复用已有生产参数；不增加恢复平台或审批步骤。

## 执行及 owner 实核

219 runner1989/93483已实际终态rc0。kernel14887 NOTE_EXIT后才读全报告/资料。
native PI/zai/glm-5.3、UUID01a104cd-6ed7-7000-b446-b20fa3036ac6，high为请求，
1517.947s，无回退。170模型调用/170唯一工具启动，runner675不是唯一工具数。
PI内部循环由runtime管理，请求128不能声称原生硬上限。获取实际仅约5.5分钟；
后续同类机械工作用一次批处理，避免模型逐页重复检查。native费用是估算非账单。

七个普通CLI项目创建A/B/C/html，未指定历史cutoff，药智未回答，未伪造preflight。
生产fetch-ctgov真实逐页查询；六条完整，RA触128MiB上限exit7，保留37页/3700项
且不派生“完整集”。网络/资源失败不解释为科学缺失；其他六项继续完成。

owner只读0HTTP重开123原页、全回执和8355规范研究捕获：hash/size、原生ID、
请求游标、平台版本、原始精确JSON切片（保留数值字面值）、selector、摘要与
获取时间/自然日精度全部一致。原始文件未变；不是医学判断、历史重建或闭包。
第一owner探针误传包装层media_type进入严格study模型，真实失败保留；v2分别
核包装字段/科学study字段后通过。未改生产合同，也未更新历史SHA。
worker重放脚本会覆盖原stdout/closure，不再运行；后继输出均独占新名字。

## RA有界恢复

生产API已支持每查询max_total_bytes。owner只对该次恢复设160MiB，在新项目
重放原37页、最多两次官方尾页请求，不改默认预算/全局路由/产品代码。实际仅
一个新请求取得最后87项，38页/3787完整；135389164原始字节，正向投影3787。
原37页、获取时间、失败回执及原manifest完全不变；本次是“原前缀＋新尾页”
同查询恢复，不能冒称现在全量重新在线核查，更不能倒推历史截止日。
owner逐页/逐研究精确投影复核，两个真实selector/提取器篡改拒绝。合法源清单
由既有build_ctgov_source_inventory生成；创新、别名、药物类型均仅候选。

| 本轮查询 | 页数 | 查询记录 | 来源准备状态 |
|---|---:|---:|---|
| Asthma（宽于重度哮喘） |53|5293|分页完整、严重程度/创新纳排待核|
| Rheumatoid Arthritis |38|3787|有界恢复完整；旧37页失败不重写|
| Ulcerative Colitis |20|1910|分页完整、创新纳排待核|
| Nasal Polyps OR Chronic Rhinosinusitis |7|623|分页完整、CRSwNP相关性待核|
| Prurigo Nodularis OR Chronic Prurigo |1|54|分页完整、创新纳排待核|
| IgA Nephropathy OR Berger Disease |3|285|分页完整、创新纳排待核|
| Paroxysmal Nocturnal Hemoglobinuria |2|190|分页完整、创新纳排待核|

七条件合计12142，不是跨适应症去重后的竞品宇宙。先前AD1758属于R200自身
获取窗口/来源集合，不继承为本次重新核查；八条件合计13900也不是13900竞品。
六新清单＋RA新清单逐研究保留臂关系/别名歧义/缺N/纳排建议与原始定位，
无accepted=true/current/门户发布。未因unknown、传统治疗或无结果删掉原始研究。

## 可恢复实物

219私有根 `.artifacts/r24-219-seven-indication-sources-20261004/`；
220私有根 `.artifacts/r24-220-ra-pagination-recovery-20261004/`。
每份source inventory携带母回执、固定分页/hash、source_set_sha256、缺口和
可重建入口；大原件不入Git，现有CAS完整保留。当前代码未变，不跑另一开发门/包。

| 实物 | SHA256 |
|---|---|
|219/source-manifest-v1.json|fb5303c9c247e7c8d4289cead7edf5cc757d2f8a7f3c8f4b04d202c4c23345d6|
|219/closure-verification.json|b88b1c70f6668478a3ca9627822cc5fb25b4f16420574828cd5559f931f0b6b9|
|219/owner-audit-v2.json|9aefbcb71660dccfa76464991106697d43205ca16194c778488982aa1414eeef|
|219/candidate-inventories-v1.json|f7ffee2fc0dfade27766663ab3d14ac73c1b5ac58ce989d969c45c694f023d25|
|220/recovery-v1.json|43c2b4fa243b9da0580ee8e9766dfc875ca7ccc5ed1282e0b23560b841da8e00|
|220新捕获回执|f208489a5e9e9fd668817f9ed099eae7b801cb27bee2c150fed43eeb1c6887db|
|220/owner-audit-v1.json|d7d3d168f8b3ab223f77457c7ee4048255b47e91727c4114e7d03c6cabf88e2f|
|220/source-inventory-v1.json|eeda0361f6f568fd18771fce251cd561cc36705d0c98522d800b4fd9935b2222|
|220/source_set_sha256|3fc87b76fcfe978d44fc4bd2e3379dc00c8304e57a80809a655670d37733b17c|
|219原生runtime回执|003dbabd63583d1736f38febf073e1247f030b9450bba0fa5467d4cb0676b3a4|

两个私有根约854MiB（571M+283M实测），仍低于该收集/恢复1GiB预算；不新增
无限原子副本，也不为腾空间删除唯一原件/失败/数据库。可再生安装缓存此前已清。
219/220所有handle终态，无需要重复等待的节点；主模型身份仍未独立attestation。
下一步沿W07正常研究包完成相关性、创新/别名、全球中国/论文来源与独立遗漏复核，
再推进三门户实际操作链和24矩阵。Ego/商业访问/全文政策原Ask只影响对应项。
科学/新实屏/全宿主模式/分享新浏览器/整项目恢复/RC未过；Goal连续、无新暂停。
