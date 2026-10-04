# R24-164｜官方当前可得证据、真实候选、恢复与隔离安装

记录时间为 2026-10-03 UTC / 2026-10-04 CST。这是继续实施记录，非暂停或发布验收。HEAD仍为 `c129a575a403ea39027e112c1acd80ca77b43117`，用户及历史脏树保留；旧中文工程零接触。主线程拥有共享日期/摄取/快照，执行节点提供有界新连接器，独立科学接受仍不由本记录代替。

## 已完成的最小完整改动

用户裁决已写入现行 PRD §4.2 / DESIGN / ACCEPTANCE：官网本次真实公开获取可证明当前可得，不伪造首次公开日，不能倒推更早历史截止日。R159 helper 实际终态为获准 fallback `zcode/zcode-live-bigmodel/GLM5.3Flash:max`，身份/effort已核，1070.088s，session `sess_d767230d-d0fa-498c-9939-946eab663047`。执行者原始两文件先CAS保留；报告中的测试声明不代替主线程实际复验。

主线程发现原 helper 仅返回内存 witness，缺少持久回执；补充完整 GET 起止时间、实际PDF字节匹配、CAS JSON回执及重开校验，拒绝未来/倒序时间、重定向、错误正文、错误来源、错误摘要、伪造回执。复用既有 stdlib 网络、Pydantic、CAS、摄取和恢复事务，无新平台/依赖/日期角色/事实身份规则。SourceCapture 的可选字段在省略时不改变旧序列化；A/B/C 时间门共用当前可得规则，摄取前实际重开 proof，恢复时在既有 staging 内核验。

`tools/materialize_pdf_scope_candidate.py` 可选消费 pinned 官方获取清单，默认历史离线行为不变。四文件集合、原始字节和回执在新输出创建前核验；不会将 source_clause 直接当作 C 关键观察、科学接受或合法消费者。

## 实际证据与边界

| 层 | 实际结果 | 不能扩大为 |
|---|---|---|
| 相关集成 | 当前证明族8项功能RED；最终邻接156 passed/59.63s。材料化族4项缺功能RED；最终60 passed/6.27s，集合有重叠不得相加成216独立用例 | 全集成/医学/发布通过 |
| 真实官网获取 | 四份官方 Protocol/SAP 完整 GET，起止UTC、200、PDF原件摘要、CAS回执全部重开；cutoff `2026-10-03T16:24:32.197087+00:00` | 首次发布日期、此前已可得 |
| 原文候选 | 64条引文、31物理页、4原件、64/64精确重开；与R153完全相同科学来源版本及事实版本 | 64条科学接受、关键C绑定或完整宇宙 |
| 恢复 | 仅由新 evidence manifest 恢复至全新目录；同快照摘要、31来源回执实际重开 | 三宿主/全产品灾备 |
| 开发宽门 | Ruff `src tests tools`；strict-mypy全268源；活跃单元/合同1071通过20 deselected；保留兼容smoke20通过1071 deselected；分层7通过；旧路径检查通过，`GATE_OK status=quality-only steps=6` | 所有非HTML格式真实渲染、医学、视觉、24门户或RC |
| 当前包 | HTML-only白名单构建387文件，archive验证 `BUNDLE_OK`；独立安装、实际installed CLI、包验证、解释器/导入源验证均0退出；全部发行/作者字节匹配，排除路径0 | 三宿主真实执行、正式分发、RC |

中间失败记录保留：首次相关GREEN里56通过/1失败是主线程调用了不存在的恢复API，随后读真实定义改用 restore_evidence_manifest；材料化工具类型标注和Ruff修复后才运行最终宽门。没有改断言掩盖功能失败，没有清历史资料。

## 受控材料与摘要

所有相对路径均以唯一英文工程根为基准；大原件在本地CAS，不进入公开安装包。

- 官方获取：[availability-manifest-v1.json](../../../../.artifacts/r24-164-current-official-pdf-20261004/availability-manifest-v1.json)，SHA `cd9926139bb9527d691e7455062337761852d1f54da6a763a4abcce7b706ebf0`；可重放脚本 `capture.py`。原件日期未知不变，取得的新证据是本次获取，不是重写 v7 历史缺口。
- 新候选：[candidate-manifest.json](../../../../.artifacts/r24-164-current-native-pdf-candidate-20261004/candidate-manifest.json)，SHA `176e5ab3e7fd339fc483203cfa183b6644a1a1c11b693e5653572ade97e3c83d`。
- 快照 `evidence-snapshot_96ff5dd3044fe18458633cb6`，SHA `6c387a08bc8721f90a5a14e8eadb949dc9d3f31d3974aa61aa6001e21e0901c9`；原与恢复根 `.artifacts/r24-164-current-native-pdf-{candidate,recovered}-20261004`，accepted=0，bindings=0。
- 邻接156结果 `current-proof-green-v2.txt` 在 R162 artifact，SHA `e9b2dc8006466199862cb045625cbbd73bba829c03de42765ca4de66db1ef909`；材料化60结果 `materializer-green.txt` SHA `0c0afc8b250962272ecd058272f6b72168297364481b93bed92587569c1eb277`。
- 本轮宽门 `milestone-gate.txt` SHA `73b4484d2c493d0ac91239974722d3bf2ade0561481156ea4a6efe047aefb459`。当前-source-set快照及各installed命令/输出在 [installed-runtime-v1.json](../../../../.artifacts/r24-164-current-official-pdf-20261004/installed-runtime-v1.json)，SHA `6a07e60f8064b182fe8e22d555aa9243665309fd2179504ea1a9e9a473d7a420`；其文件范围为src/tests/tools源码，不含文档或临时数据。后续改源码不可继承此门。
- 新包 `.artifacts/r24-164-current-html-bundle-20261004/ci-r24-164-development.tar.zst` SHA `259353d5711be6c69099ce5dd7f30c6dbfe420ac6e5a92bcb9d4b0de88ba87ac`，external manifest SHA `0756d6c09b94e7566f9054f15f1c1421cae7211bbe2daa95c410047fbc21a16a`；isolated安装根 `.artifacts/r24-164-fresh-install-20261004`，安装回执 SHA `d95d7f71de2e4c1544c0916428cc43a50e3a875b811c3efc9736dd1fb7e789c6`。安装器实际建立独立锁定依赖环境，未借开发venv冒称独立，未修改用户Agent入口。PDF阅读依赖属于输入能力，不是PDF输出。

## 继续实施

R163唯一在途节点仍为同pi/zai/glm-5.3/high会话的scope-v2账本续接24457；不读取在途输出、不重派。R151/R156/R159/R160均已终态，不沿历史段落重新等待。B/C34张主线程全目视，视觉结论仍REVISE而非美学通过。R143独立代码路线Ask尚待答，不阻断其他明确授权实现。

下一有界整族：从原始方案/SAP生成合法类型化 C 观察，保留原文/作用域/限定数量/未决关系，接既有事实摄取和消费者、普通检索横比页。不能以generic source_clause伪填主要终点/时间点/样本量门；12未决关系和7历史缺口保留。随后同源合法编辑/clear/恢复/undo与实际current分享、来源宇宙和论文闭包、所有物理页面四宽四态/跨浏览器、24门户、三宿主、安装恢复和独立验收。Goal active，不建阶段性暂停点，不切实际current/清理/提交/RC。
