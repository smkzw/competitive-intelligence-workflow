# 新 Goal prompt v6（ZCode 接管，2026-09-11）

状态：当前生效的目标文档。产品范围与验收标准逐字继承原生 Goal（快照：`docs/handoffs/goal-snapshot-20260911.json`；原生命题于 Codex 侧 paused，本项目以该原文为最高产品依据继续，不假称恢复原任务对象）。本文件只更新三件事：执行机制（用户 2026-09-11 授权）、操作计划指针（v6）、接管 review 结论。

## 变更记录（相对 v5 / 原生 Goal 文本）

1. **执行机制**：原生 Goal 中"不使用旧执行/会商 runner"约束的旧 Codex runner 作废；用户 2026-09-11 明确要求按全局 `~/.zcode/AGENTS.md` 的执行/会商多模型协作+检查+会商 LOOP 机制推进：主线程持有分解/合同/验收，独立复核按 `~/.zcode/zcode-route-manifest.json` 派发（GLM 产物必须由非 GLM 家族挑战），packet 留痕。产品独立复核不可主线程自证的要求不变。
2. **操作计划**：`plans/zcode-execution-plan-v6-20260911.md` 取代 v5 为当前计划；P1–P7 骨架与全部产品合同不变。
3. **接管 review**：`reviews/zcode-takeover-engineering-review-20260911.md`。2026-09-08 暂停点已关闭（全部被中断验证重跑通过 + Reviewer-A 独立终审第二轮语义修复成立）；新增最高优先工程缺口为"权威科学视图层生产接线"（F1/P0）与四项 P2 语义护栏，处置顺序见 v6 计划 §2。

## 逐字保留的产品目标（原生 Goal 原文快照，未改动）

以下为 2026-09-11 从原生 get_goal 读取的 objective 全文；其"按v5计划P1–P7逐阶段推进"按上文变更 2 解释为按 v6 计划的同一 P1–P7 骨架推进：

~~~text
接管并完成 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 竞品调研多 Skill 工作流。先核验经用户审定的完整设计 `docs/specs/competitive-intelligence-workflow-design-v1.4-review.md`、完整实施计划 `plans/gpt6-execution-plan-v5-20260905.md`、当前接管检查点、工程review、实际源代码和测试状态；以最新用户裁决为最高产品依据，旧Skill、ZCode和历史交接仅作为待核验输入，不能自动恢复过时要求。
（以下各段产品合同——统一Skill套件/单入口/三门户/高密度/来源与时间/闭包/Publication/药智/医学语义/复核签发/快照刷新恢复/HTML-only安装包/24门户真实矩阵/RC与旧根零接触——见 goal-snapshot-20260911.json 与 v5 Goal prompt 全文，此处不重复转写以免转写漂移；歧义时以 JSON 快照为准。）
~~~

## 完成证据要求（不变）

- 每任务先 RED 后 GREEN、记录准确范围与源/产物摘要；审查、测试数、模型自信和文件存在不是完整接受。
- 开发候选收口后唯一 commit/source-set/包再做最终绑定验收；全部门通过、P0/P1 清零、24 门户、三宿主/安装/恢复满足后才 RC_FROZEN。
- 旧中文工程持续零接触；退役须用户再次明确批准。
- 在全部原始范围的完成证据逐项充分之前，不标完成，不将目标缩成当前可通过的测试子集。
