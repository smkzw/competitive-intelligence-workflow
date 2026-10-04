# R24-165｜原生统计条款接普通 C；仍在实施

记录时间2026-10-04 CST；HEAD `c129a575a403ea39027e112c1acd80ca77b43117`。只操作英文工程根，用户及历史脏树完整，旧中文工程零接触。共享源/消费者由主线程执行，一位新上下文审阅者挑战临床解释；另一执行者只拥有范围账本新目录。不是暂停、发布或全流程接受。

## 实际实现与边界

新增 `tools/materialize_c_pdf_extension.py`，复用原摄取、CAS、快照、C模型及消费者注册。锁定原登记85观察及四份官方PDF的64精确原文，再把37条明确统计字段映射为候选C观察：分析人群9、比较逻辑2、统计模型9、缺失与敏感性16、样本量依据1。其余27条保留完整原文/ID/定位和暂缓原因，不伪造关键N、终点、时间点或整体人群。保留未决冲突和限定作用域；首次公开日仍未知，仅本次官方取得证明当前可得，不倒推更早历史。

新候选122观察/33来源/122合法消费者，科学接受0，实际current不切。原85观察逐字节数据一致，原64引文及旧候选不改。新工具先验输入hash、真实源与当前获取回执，拒绝错误锁定、未来时间、早于取得的截止及既有输出；普通入口生成14页，不另造展示demo。C渲染器原统计字段门有8种，页面只路由5种：本轮接齐sample_size_assumptions、estimand_intercurrent、missing_data_sensitivity及中文标签和无访视语义，37新行完整可达。来源未知组别明确显示“适用范围见原文”，不写成整个人群。

## 冻结材料

相对路径均基于唯一英文工程根。

- 新候选 `.artifacts/r24-165-c-native-statistical-extension-20261004/candidate-manifest.json`，SHA `bd3e991c5f7b3ca9979c1dcc250936c3d89831b2609a80e340f572cebb6eb74a`。
- 普通页数据 `review-portal-data.json`，SHA `5d4f6911ac31bf9c681a01dff7b982b493ba4b0db66066a2a32d1ac6e77cc236`；普通统计页 `project/reports/C/review-candidate/html/sample-analysis-statistics.html`。
- 工具SHA `102d89439a51624fcafbe119b0c58e3781fcee3d6cbb6427a1fc1b1bbf9f09ce`；C渲染器SHA `351103047b8774535f4f5b5b2e1a738b7e0c1fc5803966de2b13b873d1141229`。后续改源码不继承旧门。
- 输入登记manifest `c345223662b9174f183400772552e5e799eae4bb6f5e58ff0496d0968fd3a04c`；当前PDFmanifest `176e5ab3e7fd339fc483203cfa183b6644a1a1c11b693e5653572ade97e3c83d`。

## 测试的真实经过

七条真实输入集成初始缺功能RED。第一邻接批17通过2失败：外部边界空白与既有摄取规范不一致，以及普通页漏路由的下游问题。只清外部空白，原PDF/proposal内文和字节不变；随后37通过1失败暴露统计路由真实缺陷。接齐同族3字段后扩大到邻接及原C浏览器检查，123通过10失败/102.11s。新原生接通族通过，十项尚未关：八项把否定说明“不生成唯一最佳方案”当作推荐；两项禁止所有英文但报告保留必要的原文与别名。先补能检测真实推荐/标题中文和原文保存的浏览器行为，再退出旧字符串断言；不得删原文、隐藏说明或把旧FAIL改PASS。

原XML保留：`.artifacts/r24-165-c-pdf-extension-20261004/green.xml` SHA `ab156494823ac6c723e4206228ffc09538bbd96b25945b9ecc1814d8d5ea3f1f`；`green-v2.xml` SHA `0b166faf5ed3e45a2673e99c281d27d0c86441614bae6f4996b3fd499f547883`。新行为替代批尚待终态，不算PASS。新增源码使R164一次宽门和387文件安装包仅对164版本有效，165未跑宽门/新包。

## 在途与未运行

### 后继测试与W06共享隐私根因（R166，仍实施）

四项行为替代先通过，XML `behavior-replacement.xml` SHA `28e04b49c6480997e708731ea4e02ba1bcc8a95b43d58e4c79011705a0955af4`。随后19通过/2FAIL31.69s：四宽八页面族已关；治疗页还保留旧轴图“研究简称”断言。其余通过真实研究ID、中文标题与无截断检测替代，保留原XML `migrated-family.xml` SHA `11ab2f25b1118eea5833843acdeb1c05e9bfbc5848845357cf3fb1d20d24e7e8`。

W06生产分享此前仅检查页面/数据，漏扫JS/CSS/SVG私有路径和凭据样式。初始12RED/1对照，其中伪token夹具格式不正确；保留初始XML，修夹具为明确非真实但合法格式后12有效RED/1对照，`share-privacy-red-v2.xml` SHA `6d911bc0ee4ecd4cf30de79afeca69b5a6b0ed9fda11cabb55613a17598975b2`。共用资源检查现覆盖所有资产，严格数据规则不降级，资产裸`file://`说明仍合法，真实`file:///`路径不合法。`share_export.py` SHA `4ede6a3e1155f23a1848de6f825f6fb4b6b273b9270f1db9bd2b85328a24eb93`。不声称模式检查可识别任意未知凭据。

邻接最初23通过6FAIL/207.67s，失败全在旧测试直接点击折叠内导出按钮；不回退默认紧凑页面。先新增ABC真实键盘展开/导出3通过，XML `personal-disclosure-replacement-v2.xml` SHA `9aa229d9fcfde641d5485da54a0ac6d7167c204524479a1a8ca5a90ff3523da8`；再使旧测试沿真实summary展开再操作，未改导出内容/版本/防坏配置/跨页断言。最终同族及邻接32通过/32.00s，`share-and-treatment-green-v2.xml`；旧失败XML `share-and-treatment-green.xml` SHA `89832e4673018151c1e8363b48b450702998d121fd5f59c1df8cfa195645ad52`保留。相关Ruff8文件/strict-mypy3生产定义实际通过，非全门/科学/美学/真实三宿主。

下一共享根因：C原文关键词与研究列选择未在个人导出/跨页复用中保留，统计文本也不能和样本量一起转数值条图；成族生产复现后修复，固定165科学审阅材料不改。实际新候选实屏仍待Ego Ask，旧包不继承新代码。

R165 C03已预检通过、单次启动handle93499，请求codebuddy/deepseek-v4.1-flash:max及manifest允许fallback；真实模型/effort须终态回执再核。只读上述固定候选、37条数据/普通页及四原始PDF，不给执行者推理，不改产物。R163scope-v2同一实际pi/zai/glm-5.3/high会话handle24457仍在途；两节点不固定轮询、读在途输出、重派或强杀。

Ego Lite实际报space12不存在。按其规则已发原生选择题请求恢复方式，未答前不擅自创建空间/浏览器。新候选实屏NOT_RUN，旧161的34图不能证明165视觉。R143独立代码路线Ask也未决；只阻断相应接受，不阻断其他构建。

继续：关上述测试合同冲突，实际Ego可用后验新统计先例页；定向科学审阅终态后处理真实问题，必要时另建v2而不改固定材料；真实current编辑/清除/undo/合法扇出与离线分享、来源宇宙/Publication、A/B/C各物理页四宽四态、24门户/三宿主/最终恢复/RC仍开放。Goal active，无阶段暂停/清理/提交/最终接受。
