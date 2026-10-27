# STATUS（整块替换）

**2026-10-27 17:11 CST｜用户要求无损暂停；Goal API实读paused；整体未交付**

当前唯一接续说明：[完整暂停/复盘/HANDOFF](handoff/PAUSE_2026-10-27.md)。用户解除暂停前不新增研究或模型调用。

## 合同与发布
- 依据PRD、DECISIONS、PLAN及EXECUTION_PACK；直接执行，共享浏览器/发布指针由本线程持有。只用确定性规则与crosscheck，不恢复旧会商/资格链。
- 本轮产品代码CI=427c006b135c4e2208f01b64a13d27c448cafb17，已推codex/ciw-v2-trunk；工作台=1945b82357958086e69393ebbf4d9f988da2ee66，已推feat/ciw-release-adapter。
- 暂停说明另作后续文档提交；恢复查实际HEAD。旧main不变，不强推；两个archive标签未发现，历史清理不宣称完成。
- D16已批准当前C行接studio，保留选择/评价；不再询问。

## 进度（不合并不同候选的PASS）
|项|已证实|剩余|
|---|---|---|
|M0基础|附件新ciw、独立环境、GitHub干净clone169测试及Ruff通过|10个既有长函数未达PLAN长度约定，详见handoff；未做历史清理|
|M1主链|真实CT.gov255项，普通CLI出A/B/C，旧候选audit40零错|最新带模型同候选覆盖与实屏|
|M2工作台|隔离默认关闭的只读身份；T1六张1440/1920截图；宽度空栏已修|新论文/事件current后的再验|
|M3中国来源|CDE59详情/75登记；公司7+公众号3篇；NMPA四药9详情|7许可详情连接失败；未发现本品CRSwNP登记，不虚构|
|M4模型|deepseek/qwen/glm真实返回；私网DNS修正，目录与论文真实调用通过|新事件schema整轮暂停；20事件零错与<15%尚未通过|
|M5论文|3篇明确关联摘要；CROWNS2双模型12结果，4差值/CI可绘；N未知|另2篇、统一release与B实屏；17检索503|
|M6泛化/studio|PNH新release+audit40+三页1920实屏；studio旧160行选择重开已测|最新C集合重读与再验；PNH不代表完整竞品宇宙|

## 当前运行资产
- CRSwNP current=rel_ffa0d97f4ca5f9e7：330研究/149核心/39产品/1690结果/371问题/265比较/9许可事件。该轮模型DNS失败，论文采用0；不能当新切片已发布。
- 该轮44队列：10文档抽取失败、26属性抽取失败、1属性冲突、3论文失败、4未归类。它不代表修正传输后的新一轮结果。
- PNH current=rel_ecb40216e04426de：149研究/68核心/7产品/1410结果/248问题/34比较，audit40/errors=[]；56未归类+6论文未抽取保留。
- studio项目p20261027_86fa32仍读rel_87dc2fc802b3fc41/160行；取消/恢复并重开保存5条已测，未调用AI评价。
- 论文最终切片stages/publication-live-slice-final.json：NPS总体-2.3[-2.6,-1.9]、亚组-2.5[-2.9,-2.1]；NCS总体-0.7[-0.9,-0.5]、亚组-0.8[-1,-0.6]；未并入current。

## 暂停与恢复
- 新整轮在事件extractor_b等待QwenHTTP响应时因用户暂停退出130；无新release，current不变。54 DeepSeek+54 Qwen+18 GLM=126已完成响应保留；未返回的一次答复未保存，恢复需补调用。
- 两工作区SQLite一致性备份均integrity=ok；CRSwNP408源/408CAS/127采集，PNH171源/171CAS；全部579CAS哈希匹配。清单/备份在库外stages/pause-20261027.*，studio压缩备份同目录。
- API18931、Vite15186自建服务已停；Ego替代空间49保留，无升级/清缓存/登录改动。不要等旧PID/40空间。
- 恢复：核对HEAD/manifest/current→普通CLI --offline --with-models复用原件缓存→新候选20事件/比例与audit→B论文和A/C实屏→studio最新C集合及选择重开。
- 不重做CDE59详情、10篇正文、已完成属性与论文缓存；不按代码hash失效；未解外部503/连接错误有新证据才重试。

## 验证与复盘
- CI169 passed（1.27s）；GitHub干净clone169 passed（1.67s）；Ruff通过。工作台适配器/studio10 passed，开发身份pytest10 passed，前端构建成功。
- 一条扩展unittest命令误拼额外模块导致失败；前7模块49测试/20skip无用例失败。纠正后误用unittest跑pytest文件为0tests，最终正确pytest10通过；不把错误命令改记PASS。
- 数值audit不能验证日期/臂/人群语义；旧19事件原文检查发现发稿日、品牌重复和旧结果误判，已修规则但新整轮未验。
- 登记臂名与干预关联真实冲突，保留原件按明确名称绑定；中国登记不填国家数1，摘要无N不补0。
- PNH实屏等待ECharts动画结束后目视，三页实际1920无横向溢出；旧1908图不冒充1920。
- 原件/数据库/响应/运行图不入Git，T1特许小截图除外；未触碰旧中文工程。备份是同盘恢复点，不是跨机器灾备。
