# R205–206：整篇独立复核与精确 XML 重放（连续实施）

## 合同和实际路由

沿用 W03/W07，不新增医学本体或平台。R199 的 204 条 DUBHE CRSwNP
候选未采用，不归入 AD。原文、候选、全部上下文材料保持冻结。独立科学判断
交给一位新鲜 reviewer；owner 自行补确定性的生产定位接缝，二者不修改共同输入。

R199 实际 terminal rc0，最终 PI/zai/glm-5.3 native session
`01a103cc-599f-7000-954b-ecb6132326cd`，runtime receipt 实际观测该模型，
high 为请求 effort；729 reported tool calls / 2786.021s。外层 CodeBuddy/DS 标签
不是最终身份。原 no-fallback 文字错误，原可执行 manifest 实际允许回退；
review/metrics 已纠正，不改原失败或日志。

R205 已实际启动 Grok/grok-build/grok-4.7/high，session
`f3eff662-a6f9-476a-8711-64b767e60e4a`，runner PID73188/native PID73190，
终态仅由 kernel watcher41151 通知。请求身份不等于已观测响应身份。
两时段任务 manifest 的 fallback 均为空。排除实际 GLM 执行者及近缘变体。
reviewer 先看整篇原始 JATS，再看 lossless 全204，不读执行者/owner 说服性分析。
不进度轮询、在途 QA 或因迟延重派。初始化不是派发，模型报告不是最终采用。

## R206 已实现范围

`storage/source_derivation.py::extract_locator_quote` 现在对 XML 调用有界
JATS 索引重放，而不是用标题/行名 OR 匹配整行 XML。支持同一 canonical article
路径的合法单文章包装、明确一基节点序号、单元格、段落和原注释；段落继续使用
现有排除浮动表/图的规范化。粗表/行、根、通配符、属性查询、未知包装、多篇文章、
实体展开、缺失节点、空文本和越界全部拒绝。不偷偷回退到 URL/相邻段落。
只证明精确来源文本，不证明临床解释、身份/日期政策、可得性、采用或跨报告绑定。
原 `linked_jats.py` 与 reviewer 所读 ResearchFact/ResultContext 定义未修改。

先建立整族 18 例：16 真正 RED / 2 原 PASS；最小完整改动后五文件81 PASS，
最终九文件147 PASS / 8.37s。Ruff 两文件、strict-mypy 一源通过；导入排序初次
FAIL 保留，格式化后已修。没有逐行全仓或安装/三宿主重跑。

## 实物与 SHA-256

| 实物 | SHA-256 |
|---|---|
| 原始 JATS | `71d3916d36ad1a398581231fae764dab806bbf03f9692ba7469cbf1066341a26` |
| 冻结 candidates.json | `5706c42979ac37fc9e0ee6ba95c0396e59edf06d982695dd22a215bc1fc190d6` |
| R199 manifest.json | `93b09e6b11dec90b667f8c28ac93e93ca61e519f80d124cbf8ebb6a301434fab` |
| lossless review material | `27fcaea627243c632f36615d4c49aafadf0f1133726d68e8e84c1d2da8790043` |
| 当前 source_derivation.py | `59d3f2979f19e9d4760d95ce832d54df2b7ad4674dd3a998d77943782da09eb9` |
| 新定位测试 | `61a954038a94cffa0ee5a3294641fa8ebe55b499f796087eb2ccdf8f832159dd` |
| 整族 RED XML | `184943cbe88478fbf624ba1164546d460e7cdecdf2a0d739b13940a8b3782a46` |
| 最终邻接 GREEN XML | `19365912ad919341ba292951118617458881968cdd5293a82af6e52fadd1918a` |
| 生产真实路径重放回执 | `42d9f7e59190d9a94f2762f5a2ea1fb3c0d115fcd6fda9912fb24720cc509078` |

私有 `.artifacts/r24-206-jats-exact-replay-20261004/replay_frozen_paths.py`
可从固定原件/候选确定性重放；已有输出禁止覆盖。真实离线全204路径：
37 精确原文相等、0 quote mismatch、167 粗定位拒绝；没有新 HTTP/采用/当前晋级。
这里的167是生产精度拒绝（表行/整体表等），不是167个错误临床数值。
原文/候选摘要在运行前后相同。逐事实结果在同目录生产回执，不只留下统计文字。

## 下一安全动作与未完成

等待 R205 kernel 退出后读取完整返回/工具覆盖/原始反例/响应模型身份，评估
根因及最小后继修复；不改冻结199工件。若修订候选，另建后继版本后验受影响族。
论文当前获取见证扩展 Ask 尚未裁决，不能仅因全文存在就采用或倒推历史公开日期。
Ego 空间恢复 Ask 未答，新实屏仍 NOT_RUN。147 PASS 只属于精确来源重放及邻接层。
R206 新源码不继承 R202 的3fba安装/宽门；等连贯模块稳定后集中重跑当前门/包。
24门户、完整竞品宇宙、Publication 资格/科学、四桌面四状态、离线新浏览器、
三宿主全模式、恢复及 RC 未完成。Goal active，无暂停/current晋级/提交/push。
