# R212–213：来源、计算与综合判断不再混用

沿现行W03/W07修共享生产合同，不另建服务/数据库/审批步骤。owner负责共享
类型与版本；211书目执行只写独立恢复目录，210临床判断复核已终态。开发合同
由实际类型/SQLite/不可变快照/定位复测验证，不把这些当独立医学接受。

## 生产修正与实际测试

ResearchClaim的综合声明须显式AI文字、方法与标记；直接来源/确定性计算不得
混入综合字段，计算必须有可复算材料。方法或类型变化产生不同内容版本；
直接证据的旧序列化及旧内容身份保持不变。真实SQLite验证幂等、版本隔离、
前快照字节不变和不切current，方法保存在锁定闭包中。

登记locator生产者输出精确`$.`路径，和持久化来源重提取一致；历史裸路径ID
可只读重开，不改历史身份。缺点号、双点号、数组前误加点号、前导零索引、
通配符与根定位不得误过。严格JSON校验未放松。

旧测试把纯文本标为application/json，现仅修测试的真实媒体类型或结构化源；
负向引文断言保留。另在当前负向测试副本补综合声明披露，让测试实际抵达
被篡改source_text分支；原AD夹具、历史回执和哈希完全不改。

| 实际批次 | 结果 | 私有回执 |
|---|---|---|
| 声明新族RED | 6FAIL/4PASS | red.xml |
| 首次邻接 | 102PASS/5FAIL，107例 | green.xml，保留 |
| 新定位桥RED | 2FAIL/3PASS | locator-red.xml |
| 完整邻接v2 | 112PASS/59.92s | green-v2.xml |
| 严格路径族RED | 4FAIL/8PASS | locator-boundary-red.xml |
| 完整八文件邻接v3 | 119PASS/64.63s | green-v3.xml |

v3包括fragment_locators、research_claim_semantics、review_r07_ingestion_invariants、
source_to_claim_chain、scientific_review_transition、reviewed_source_fact_acceptance、
w07_ctgov_capture_bridge、c_source_lineage。静态局部Ruff七文件/strict三源通过。
不是每行宽门。最终一次quality-only门实际终态exit0：Ruff全src/tests/tools、
strict-mypy全src/tools271文件、1117活跃unit/contract、20保留兼容smoke、7分层
与旧路径纯文本依赖检查通过。不是全integration/科学/浏览器/发布门。
stable-gate-v1.log SHA `8ec07875a67f2532d52491cc97120a2f4ba6ff400069f44c330b79af4f2c4439`。
小型checkpoint-v1.json绑定当前三生产源、测试、候选、包和安装，不依赖统计文字。

## 新安装而非继承旧包

私有目录 `.artifacts/r24-212-claim-semantics-20261004/`。
新HTML-only候选包390作者文件+清单；391安装记录逐hash/size/mode相同。
安装内隔离解释器真实验证新综合合同、负向拒绝、JSON路径重放及213全部
228事实/80声明类型。帮助、包核验及隔离合同三检查通过，外部包清单验真通过。
首轮probe遗漏package verify必需--root，rc2留在v1；v2修探针命令而非产品，
重新三检查通过。不以最后一条命令的rc0掩盖前probe失败。

仅清理本次安装独有runtime/cache，uv报1376缓存项/183.4MiB（非实测物理磁盘
释放）；391安装记录/hash/size/mode、安装元数据和入口再次核对不变。缓存可
重新下载；原件、失败、快照、源码、Agent会话/数据库与历史材料均未清理。

| 当前实物 | SHA-256 |
|---|---|
| production/source_research_service.py | `1451d634c58e0cb74e8f77951d742a883e58bc34d82855129f6f77f3c9288cf2` |
| production/fresh_research_ingestion.py | `09e776070060e63030cd393dd2e298754cc7ddc9f9ec62e8048edc46ec68259a` |
| production/ingestion/locators.py | `83b6b8184032eb53a3afc3cb55405c5a0aa6c022dae5c0e22dfd01b0ba15a3f9` |
| green-v3.xml | `9640b5e90e9b36f1627daa3072b511d2fc2e87a88e6e9c6de2d1d80197c469e4` |
| ci-r24-212-development.tar.zst | `d6b3481c94b9461fcf18372716ab559428e73acf6655a1b9e6d343309ae13da7` |
| bundle manifest | `7e07f31d5481ecaad4657412e62090049b8f9bf030e50ab6537187eb32afaab7` |
| fresh-install-v1/installation.json | `82879c8fe2423aa2a6dabc88f95b972f4ff35e80700aab8e323e0759b19b25f4` |
| installed-contract-v1.json（真实失败） | `97212033b50cea532ede587a07400818a5e5f06608a86ec8d7d3dfdc71dae85c` |
| installed-contract-v2.json | `cc5ddab91bfaf72c0b1e9852679fa8911a794e6a76f4a00f42fe6a64bf7c1f69` |

## 论文候选，仍未采用

210同会话独立变更复核终态REVISE，294.843s/10调用/native grok-4.7-build/
high请求/no fallback。ROC原子自己引用不含应答定义，不能把跨段Methods支持
误写入该原子的直接endpoint。213只收窄该endpoint，定义仍由独立Methods事实
及绑定综合声明表达；0.77与原始引文不变。另修17个裸零计数单位，不合成百分比。
76综合声明显式保存AI标记/方法，4直接声明不变。全228精确原文重放及全部类型
实核，零HTTP。不是新医学PASS；旧210/209/199与原论文字节保留。

`.artifacts/r24-213-paper-production-claim-shape-20261004/candidates-v1.json`
SHA `e4d4a0c36e2d7f4a6b0ac1723ccd441de597690b4afc2b286233acc98cf561c5`；
manifest-v1 SHA `a95cad63accb37e69c41ddfcc3215e9cf8512a54db1cd8693d2193774a044b45`。
它仍是CRSwNP DUBHE，不是AD。正式生产上下文receipt、期刊公开可得日期资格、
当前候选独立接受、完整来源/宇宙、浏览器、24门户、三宿主全部模式、恢复及RC
开放。Grok结果不改标OMP。Ego/资料政策原Ask待答，仅阻断其依赖项。
