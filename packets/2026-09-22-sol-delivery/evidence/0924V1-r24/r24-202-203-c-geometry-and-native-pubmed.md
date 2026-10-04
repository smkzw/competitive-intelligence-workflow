# R202–203 前端独立执行与真实 PubMed 漏读修复

## 继续实施的边界

HEAD仍`c129a575a403ea39027e112c1acd80ca77b43117`，Goal active，唯一英文根。
当前来源/schema/事实采用由owner负责。R199临床候选执行不读/改在途输出；
R202独占共享图形与C作者资产单元，不接触来源/临床/数据库或镜像。
既有PRD/DESIGN/桌面范围/HTML-only不变；本回执不是另一套产品权威。

## R200 真正全量原子重放已终态

18060实际exit0，安装解释器生产获取桥/原子解析/ResearchFact构造重放全部1758研究；
123165原子、210583直接事实候选、515个missing范围问题，0整研究提取失败。
域：AE75887、疗效46119、biomarker385、免疫原性278、PK/PD496。
没有将缺失补0、采用候选、生成报告或晋级current。
结果`.artifacts/r24-200-ad-current-research-20261004/atomic-source-inventory-v1.json`，SHA
`bd8f2a0205fc1b3b47942dd7eed90c186e6c922e639bcffd90fe927709e4562e`；
私有确定性重放脚本SHA`9768e7910ab52240b2006cdd1ac405f0081153ef25b56f33420f4497ed0d1ebf`。
大批候选数不是临床接受/创新完整性。固定原18页/source-set和逐研究提取SHA可重建，
不另复制几十万条原始文本形成第二套数据。原source/current未改。

## R201 实际网络恢复后，R203发现真正的解析缺陷

8479当前源码实际exit0：5993检索ID，5984解析记录，旧逻辑报complete_with_attrition。
30检索/30EFetch/1摘要页，89,299,728原始字节；原回执SHA
`b4f0600c4e4c663ed85c9e9482a7be819b4a8cc119e04e418adebaf912f21ade`，
获取起点2026-10-03T22:19:35.066285Z。原429失败和此回执均不覆写。

owner重开原生XML发现九条所谓未获取标识**全部存在于EFetch正文**，节点均为
PubmedBookArticle；publication status均ppublish。不是源缺失、不是网络无法下载。
当前解析器只枚举PubmedArticle，漏读书籍/专著，并用出版状态错误解释为不可获取。
原始九PMID：41587291、41337631、32809396、35679442、35289989、35816599、
27977093、27280278、20722164。原生类型八Review/一Study Guide，保留原类型，
不默认升级主要结果论文。精确源页hash/path保存在重放清单。

[NLM PubmedBookArticle](https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/el-PubmedBookArticle.html)
和[BookDocument](https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/el-BookDocument.html)
明确定义原生形状：自己的PMID、可选章节题名/BookTitle、直接PublicationType/Abstract。
出版状态不构成EFetch不可获取证明；仍缺少标识必须保持incomplete与来源诊断。

R203 owner direct客观源完整性修复，未做临床裁决。生产解析共享原抽象/身份规范，
支持BookDocument但不搜嵌套引文PMID；获取器保留summary状态，却不因状态字符串
自动放行遗漏。complete_with_attrition枚举仅为历史兼容保留，新缺失不借其闭合。
现行旧测试的“在处理/非PubMed字符串即证明不可获取”断言已迁移为保持缺口，
原回执/RED/hash不改，不是为绿灯删掉真实功能。

首次RED八失败中七为真实断言，一为混合fixture缺第三个兜底响应引起StopIteration，
后者单独记录、不冒充产品RED；明确补合成诊断响应后与整族最小修复合批。
六文件98PASS/2.17s，Ruff四文件/strict两个源通过。RED XML SHA
`06afe5fd980185774f22861c0ff48bd8161248e917b55135e9e262c796cf3f41`，GREEN
`abcbe28b25eebe764051f056e2ecdbb153df5ba97b08c72d81b034a9dfcc42f4`。
新pubmed.py SHA`bb0e743be74b53674a935d0a62bffa0719882ca0a189f2fcba395c87877f94df`；
pubmed_fetch.py SHA`c7109a2adae6f96b7bd3264c2f6762531cc6eb29af8205bbdb138817423162ec`。

## 原件零新HTTP重放成功

63445实际exit0，核61页hash/size/原取得时刻、5993检索ID精确并集，当前生产parser
重新提取全部5993：5984期刊+9书籍，缺少集合为空，无重抓/伪新鲜度/旧回执重写。
候选角色：5507未匹配、364支持、81ad-hoc、33primary、8review。
这些是既有启发式**候选**，并非医学裁决；未匹配NCT不证明论文与AD无关，
全部5993保留，不能按这组候选标签自动删文或取代全相关/必需论文识别。

工件`.artifacts/r24-203-pubmed-native-records-20261004/current-pubmed-reparse-v1.json`，SHA
`4566cacdb7e07526c137af9a9e5fbaa4ab4bf217e28f931be1ba9f540d7130ef`；
source-set`ce4aa36f45db060bf2acdbb515736312c11a4492633499eac8ea7e60f52cdcf2`，
完整typed-record集合`64fb8ea77c2cad12eba83101af345b8af1107da1dcbb6fcdc3a0e4e85906fb46`。
确定性脚本`replay_current_pubmed.py` SHA
`72cd74006a1eeeb494c2ea9fe068358ca86e35306cecdcccb9c7a13d1d63b688`。
每记录含自己的原生节点定位/源页hash/类型/元数据digest及未采用标记，原文不再复制。

重放命令（英文根）：`uv run python .artifacts/r24-203-pubmed-native-records-20261004/replay_current_pubmed.py`。
输出独占，已有结果重跑须指定新版本，不覆盖原证据。源集合、取得时间、脚本和
提取器版本共同界定证据；不继承81ad旧包/1117门，更非临床或当前门户接受。

## R202 实际独立前端执行

当前C renderCChart仍绕过PresentationPlan用360..1800px固定下限，CSSmin300。
已有用户D1及Kangzhe要求共用布局决策；只修C矩阵/时间图几何与空/筛后状态，
不把C长条款横比变成数值热图，不回退A/B事实/科学坐标。
owner已实际核上游Kangzhe SKILL SHA`f1a47790…6ab`及16个当前owner文件全等项目
v6-site副本，仍KZ6-0929-A04。初次guard因外部read-set拒绝，尚未派发；改为实际
核相等的既有本地规范后preflightPASS，不绕guard或另复制一套规格。

单E03 route primary CodeBuddy/deepseek-v4.1-flash:max实际启动52892，runner65883/
native66087，仅三作者资产、新test_r24_c_shared_presentation_plan.py和新202私有证据
可写；128turns/7200s/no fallback。核native启动不等于最终模型身份/成果通过。
kernel NOTE_EXIT18004单一事件等候，无进度轮询/在途QA。镜像与manifest为owner-only，
终态再集成/同步并做一批相邻/命中区检查。Ego工作区Ask仍待答，不能伪称美学通过。

## 接续

R199终态后冻结source-first候选并安排一次独立科学复核；R202终态后核完整代码/
真实RED与批次，源/前端均稳定时一次quality门及新HTML-only包/安装。继续AD登记绑定
论文扩展/中国来源/创新资格与独立闭包。24门户、三宿主全部模式、视觉/分享新浏览器/
完整恢复与RC仍开放；未暂停/提交/push/正式current晋级。
