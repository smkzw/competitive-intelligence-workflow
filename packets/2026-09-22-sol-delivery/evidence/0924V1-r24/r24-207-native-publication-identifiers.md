# R207：原生论文编号保留，不借用参考文献身份

沿用 W07。普通生产 PubMed EFetch 解析现在保留 DOI/PMC/其他原生编号
候选及精确节点路径。仅从本记录直接 PubmedData、书籍直接 BookDocument /
PubmedBookData 的 ArticleIdList 读取，不下钻 Reference 或整本 Book。
重复、冲突、空值照实保留，不 first-wins。缺 IdType 按 DTD 默认 pubmed；
显式空类型不冒充有效类型。无编号材料不增加序列化字段，旧输入可读。
这些只是全文查找线索，不是临床角色、身份裁决、日期或来源采用。

方法依据：[NLM ArticleIdList](https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/el-ArticleIdList.html)、
[ArticleId/default IdType](https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/el-ArticleId.html)、
[PubmedData](https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/250101/el-PubmedData.html)。
PubmedBookData 单页 web timeout 保留，ArticleIdList 官方父元素列表与现存
BookDocument 原始结构仍支持本次限定位置；不假装所有远程参考都取得。

owner 直接执行：这属于确定性的原生字段保全，原件路径/节点重放能验证，
不需要再派医学意见模型。先6个真正RED，最小完整修复后7文件104 PASS / 2.15s，
Ruff 两文件 / strict-mypy 一源通过。未逐行全仓或每字段重派三路会商。
R205论文审阅不读此文件/输出，其冻结204与 scientific definitions 不变。

## 当前实物

| 实物 | SHA-256 |
|---|---|
| 当前 pubmed.py | `3ae825433dbd3a96e90d7300ae86873a6f369a376166d3466190dd5513cb430f` |
| 新成族测试 | `7dd91c2da9a7b5f10924afc9207f3361b31944aae0a979dd171cf01f2d630b04` |
| RED XML（私有206目录，未覆盖既有） | `3f94ebfbfd4a1bb76fa43644d7b6e111900054d522dda9fd8c8d9db8b1bcaedf` |
| GREEN XML（同目录） | `59c87bc88b608374d9d1d772555b0226fcc017572070e5f1eeab21be99a8d4c5` |
| 新 metadata-v1.json | `227cdbad71a8da04e73a9f260e8cb9085bce1a2c0cc09656cbf6c27cdef0a2bb` |
| 113 原始页集合 | `3f5872fc0ddb0ed9943a92c30c9e9639a4cdf1e57349fa49da191fdf1eb4db32` |

私有 `.artifacts/r24-207-pubmed-identifier-candidates-20261004/replay_identifiers.py`
确定性重开203/204已固定元数据与113页原件/hash/size。7247记录精确身份集合不变；
每个新增编号从实际节点再核类型/值/路径。去掉新增候选字段后的原 typed digest
与旧记录逐条相同，不修改旧摘要/回执。所有采集日期仍原值，零新 HTTP。
结果保留7247 pubmed、6596 doi、2358 pmc、4074 pii、9 bookaccession 等原生
编号出现次数；不是6596篇唯一 DOI 或2358份已获取全文。原旧manifest前后 hash不变。
新输出已有路径禁止覆盖；旧包不能读取新增字段就不能冒充当前支持。

## 界限与下一步

登记中58个无PMID引用已全量按原始页/研究索引/引用hash重新打开。
其中有书籍、网页、会议摘要及登记标RESULT的背景题名，不能全称为“缺失主要论文”，
也不能仅凭 RESULT 当成该试验的主要结果。原待核58条保留，不用数量或猜测编号闭合。
后续以这些自身编号作可核验的全文获取/匹配候选，再结合研究关系和逐论文
独立判断；冲突时不默认第一项。当前未做该科学筛选、全文下载、采用或current晋级。
207新源不继承202安装/宽门；206+207组合稳定后已集中验当前门/新包，见下节。
Ego空间12真实复查仍NOT_FOUND；不新建/换浏览器，新实屏仍NOT_RUN。
Goal active，24门户/三宿主全模式/科学视觉/宇宙/恢复/RC仍未完成。

## 当前字节的集中开发门与独立安装

一次 `bash tools/gate.sh` 实际 exit 0：Ruff 全 src/tests/tools，strict-mypy
全 src/tools 271 文件；1117 活跃 unit/contract、20 保留格式兼容 smoke、7 分层
以及旧路径引用检查通过。准确范围为 quality-only，不含全 integration、医学、
浏览器或发布终验。206 的147项与207的104项邻接测试另有实际回执。
门日志 `stable-gate-v1.log` SHA-256：
`27d38b154a38e4e9825a0e8484ec29b0928060d78b9cb4ac98c92f3931f024ec`。

本次私有目录 `.artifacts/r24-207-pubmed-identifier-candidates-20261004/`：

| 当前实物 | SHA-256 |
|---|---|
| bundle/ci-r24-207-development.tar.zst | `5e7214b1877229356682ec1de8c1dcb3f979391b5dda33bd728c2f71aba9e8c5` |
| bundle manifest | `3a7fe6e15b52ecc57b450abf7a578d707f2d85154964801fd129ad7378290210` |
| fresh-install-v1 安装元数据 | `3ef0aac9984967c1417a5f535c52d7fed42acaaf758e76b5ca4fc9a7629e1455` |
| installed-probe-v1.json | `dfb09e3b878b3f751e1415e2b0cb226bcb70618185cb752ae2258263d9eee2e2` |
| installed-source-paths-v1.json | `191c4c228ccc807735a32e124454a761ac5ca2409d63fe0db6d3fe3e98ecd7a9` |
| owned-cache-cleanup-v1.json | `4128dd3fd090ad203da1402b62d8f6711077d07a392f78251aab0cd2c8e2a723` |

390作者文件+清单，实际新安装391记录逐hash/size相等；安装内 help、包验真、
合成替身的阻断→恢复→HTML→严格回执通过，不冒充三真实宿主。额外隔离安装解释器
重验精确JATS单元格/粗行拒绝与自身DOI/参考文献不借用四断言，实际 exit 0。
包不含原论文、原始运行证据、凭据和缓存。

只清理本次 fresh-install-v1/runtime/cache 的私有下载缓存，uv 报告1376文件/
183.4MiB；这不是实测物理磁盘释放（可能有硬链接）。清后391记录hash/size/mode、
安装元数据不变，入口复跑 exit 0；缓存可重新下载。原件、失败、历史证据和工作树
完整保留。新5e721包/当前门只替代旧3fba包的开发与安装证据，不继承科学/视觉验收。
