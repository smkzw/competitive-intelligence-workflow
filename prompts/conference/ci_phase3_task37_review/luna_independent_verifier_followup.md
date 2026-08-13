# Task 3.7 独立复审（同一会话续审）

继续你自己的 Luna 独立验证会话，不要新开会话，不要读取执行者提示词、执行者报告、日志、会议记录或主代理结论。上一轮你判定 `FAIL; P0=4; P1=2`，实现已针对这 6 项及其相邻绕过路径修补。

请直接检查当前未提交差异和以下验收锚点：

- `2026-08-10-competitive-intelligence-multiskill-workflow-design.md` 中科学质控、证据门槛、无草稿与图状态约束；
- `2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` 的 Task 3.7 与 Phase 3 停止条件；
- `src/ci_workflow/qc/scientific.py`
- `src/ci_workflow/capabilities/scientific_qc.py`
- `src/ci_workflow/graph/guards.py`
- `schemas/scientific-qc-verdict.schema.json`
- Task 3.7 与关联图测试。

必须重新执行你上一轮的攻击，并主动寻找相邻绕过：伪造摘要、跨快照 GateSpec、跨报告类型/版本/对象、伪造标准或覆盖、生产者与审查者同一身份、空或重复来源/定位/问题片段、接受与否决结构矛盾、已穷尽否决缺少或错绑记录、裸布尔或普通字符串绕过、否决后出现任何报告下游产物。特别核验新增 `ScientificQcCurrentContext` 是否让这些字段形成一个不可漂移的当前边界；Phase 3 尚未承诺数据库持久化身份权威，不要把后续阶段能力当成本任务缺陷，但若当前接口本身仍可自相矛盾或跨对象授权，必须判为 P0/P1。

运行精确测试、关联图回归、Ruff、严格 mypy、JSON Schema 负例、package verify、diff check；全量测试若环境允许则运行。只读，不修改文件。

结论首行必须严格为以下之一：

- `PASS; P0=0; P1=0; P2=<n>`
- `FAIL; P0=<n>; P1=<n>; P2=<n>`

随后给出复现命令、观察结果、精确文件行号、仍需修复项。P2 不阻断 Task 3.7；任何 P0/P1 均阻断。返回完整执行报告，不要只给计划。
