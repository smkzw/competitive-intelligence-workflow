# Task 3.1 无损暂停记录

日期：2026-08-12
状态：暂停，未接受，未提交；Phase 3 与父任务均保持 `in_progress`。
下一阶段：不得进入 Task 3.2，先关闭本记录中的两项 P0 并完成原会话复验。

## 当前完成面

- A/B/C 版本化证据规则、闭合宇宙、逐对象完整矩阵、逐试验比较/单臂、B 逐组疗效与安全、C 登记充分边界、只收紧覆盖和不可变父结果均已实现。
- 已关闭前三轮发现的零组比较、效应量无终点、提高阈值失效、漏聚合、事实链路缺失、跨产品/试验/终点拼接、任意不适用、角色集合漂移等关键假通过。
- 当前独立机械证据：Task 3.1 精确套件 `141 passed`；全库 `329 passed`；Ruff、strict mypy、`ci-workflow package verify --root .`、`git diff --check` 均通过。
- 工作树仍为有意未提交状态，保存全部实现、测试、prompt、runner 报告与验收反例；没有写 Task 3.1 接受记录。

## 最终独立验收结论

来源：`runs/codex-subagent_ci_phase3_task31_acceptance_followup3.md`
结论：`FAIL; P0=2; P1=0; P2=1`

### P0-1：批次实例可用 model_copy 绕过校验

- `GateEvaluationBatch.model_copy(update={...})` 不重新运行 Pydantic 校验。
- 伪造 `batch_key` 或嵌套修改单元结果事实链路后，`aggregate_report_gates` 直接信任模型实例并可返回通过。
- 恢复时新增 `test_aggregate_rejects_model_copy_tampered_batch_key_or_unit_results`；聚合入口必须对批次内容、键、嵌套结果重新做显式完整性验证，不能依赖对象曾经构造成功。

### P0-2：导出构造器可重新盖章脱离结果

- `GateEvaluationBatch.from_evaluation(spec_b, snapshot_b, unit_results_from_a)` 会给旧结果计算新批次键。
- 对象矩阵相同时，旧快照结果可贴到新快照；同版本但阈值已提高的规则也可接收旧阈值结果并通过。
- 恢复时新增 `test_public_batch_constructor_rejects_detached_unit_results_from_changed_snapshot_or_spec`。
- 不能只重新计算批次键。修复边界应为：批次构造与单元评估成为不可分的评估器原子路径，公共 API 不再接收脱离的 `unit_results`；或给每个单元结果加入由规范指纹、快照摘要和评估内容共同生成且不可重新盖章的来源证明，并在聚合入口重验。

### P2：上下文外报告值对象不知道规范成员关系

- `ReportGateResult` 单独反序列化时，没有 `GateSpec`，因此同报告类型的未知单元标识无法由值对象自身判断。
- 正式批次/聚合路径已有规范成员校验。该项保持 P2，后续持久化加载服务必须携带规范校验；不要在无上下文值对象中伪造已证明的成员关系。

## 原会话恢复锚点

- worker_01 Pi：`019ff237-531d-7000-945e-d3919ca0e6c3`
- worker_02 Pi（下一步优先恢复）：`019ff262-8ff4-7000-8709-4589a92be55c`
- worker_03 Pi：`019ff26d-e8dd-7000-ac05-a594bd8999e2`
- Cursor 管理者：`d9ad2f85-a8ff-4a9a-9e80-1711b8bbf417`
- Luna/max 独立验收：`019ff27d-3370-7202-92ce-003822c8d38e`

同一会话继续时按最新全局 AGENTS 的日夜间路由执行；可在原会话切换有效模型，不废弃或新开会话。先 preflight 新 follow-up prompt，再长等待；不得因延迟 fallback。

## 推荐恢复顺序

1. 重读最新 `/Users/smkzw/.codex/AGENTS.md`、本记录、Trellis `implement.md` 和最终 Luna 报告。
2. 在原 worker_02 会话先写两个 exact RED，设计并实现“评估器原子批次”边界；不要用隐藏/改名代替真实来源约束。
3. 独立运行精确套件、全库、Ruff、strict mypy、package verify、diff check，并攻击 model_copy、脱离结果、快照/规则漂移、阈值提高与父结果不可变。
4. 恢复原 Cursor 会话做整合复核；P0/P1=0 后再恢复原 Luna 会话。
5. 只有 Luna `PASS; P0=0; P1=0` 后，才写 `docs/acceptance/runs/task-3.1/`、完成 reviews/metrics、更新 Trellis、清理过程文件并提交 Task 3.1。
6. Task 3.1 接受后才进入 Task 3.2。

## 保留与清理

- 保留 `runs/`、`logs/`、`prompts/`、`reviews/`、`metrics/` 与所有第三轮/最终验收报告；它们是恢复和否证证据。
- 本次仅清理可再生 `.pytest-tmp/`；不归档执行证据、不删除旧会话、不提交失败状态为“已完成”。
