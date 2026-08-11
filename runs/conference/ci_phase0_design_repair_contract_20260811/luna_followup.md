FAIL

P0

1. `contracts/kangzhe/design_specs/track_pptx.md:842-857` 放宽了 `core.md §0.7` 与 `project_profile.md:62-67` 的角色边界，允许 10.5 pt “辅助说明”；该例外只能用于表体/坐标轴标签。  
   可复现：保留 `project_profile` 原文，直接按 `track_pptx` 将流程辅助说明降至 10.5 pt；现有测试仍通过。  
   最小修复：删除“辅助说明”，并用机器规则校验 `data-density=ultra`、18 行/18 px 行高/4.5:1 对比度/原图可读/detail-ref 全部条件；参考文献单独处理。

2. `tests/contract/test_design_contract_hashes.py:134-142` 只检查字符串，未机械验证 `project_profile.md:77-83` 的当前 run、真实摘要、独立身份、旧 mtime/收据/截图和自签拒绝。  
   可复现：删除“渲染摘要”或“独立验证者身份”的约束，同时保留测试检查的几个短语并更新 runtime digest，测试仍可通过。  
   最小修复：增加 runner-owned manifest/verdict schema 及 stale artifact、mtime 重写、旧收据、伪验证者、自签的失败 fixture；本 Task 仍只验合同，不接受报告成片。

P1

3. `project_profile.md:69-75` 仅以 prose 声明 typed source-pack 与 notes 绑定；项目包没有对应 schema、token validator 或 notes 抽取测试。  
   可复现：移除 `audience_fact` 的分母/locator要求，或让 `aside.notes` 不参与重算，现有 6 项合同测试仍可通过。  
   最小修复：加入机器 schema 和负例：互斥 token 类别、稳定 ID/locator/角色/单位/分母，以及 notes 与 slide/claim/图/表/PDF/PPTX 的一致性检查。

4. `manifest.json:17-29` 的 `source.design_specs_files` 未被 `tests/contract/test_design_contract_hashes.py` 校验。  
   可复现：把其中任一源文件 SHA 改为错误值，保持 `stable_collection_sha256` 和 runtime 不变，当前测试仍通过。  
   最小修复：重算并校验源快照逐文件清单，明确其与项目 runtime digest 分离且不可静默改写。

5. `contracts/kangzhe/design_specs/tests/test_package_load.py:73-81` 实际只读取项目自己的 `design.md`；`manifest.json:11-15` 只是自报四个通用 stub 摘要，未验证真实 stub 内容或第二正文不存在。  
   可复现：在项目入口保留“非全文”字样并加入未含 `MUST` 的第二规则块，测试仍可通过。  
   最小修复：固定入口允许的精确结构/目标并加入第二正文负例；同时明确通用版仅为历史来源，不再作为运行检查对象。

6. `project_profile.md:3` 声称与已批准 v1.2 冲突时“以本文件为准”，可能覆盖报告范围；而测试未验证 `ROUTER.md:24-30` 的门户非幻灯片画布、原生 PDF、PPT Master 及四格式负例。  
   可复现：将门户改为继承 1280×720，或将 `track_pptx.md:725` 改为允许 `python-pptx`，更新 runtime digest 后现有测试仍可通过。  
   最小修复：固定优先级为 v1.2/用户当前指令高于 project profile；加入门户画布、非原生 PDF、截图替代、绕过 PPT Master 的失败断言。

7. `docs/decisions/0002-kangzhe-contract-reconciliation.md:3` 仍写“等待上游验收并请求确认”，与同文件 `§16:234-242` 及 `0005` 已内化的项目自有权威相矛盾。  
   可复现：不同执行者按标题会错误停止在旧 Task 0.3 门前。  
   最小修复：将旧 ADR 标为 superseded/historical，并把 `0005` 作为当前项目-owned 决定的唯一入口。