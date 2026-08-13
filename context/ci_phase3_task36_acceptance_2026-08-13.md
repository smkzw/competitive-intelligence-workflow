# Task 3.6 验收锚点

日期：2026-08-13
实现提交：`3dda306`
结论：`PASS；P0=0；P1=0；P2=0`

## 已实现

- `project run` 与 `fixture run` 共用同一类型化运行服务；fixture 只从唯一 catalog 读取，经 schema、确定性日期、逐输入摘要与案例摘要校验后运行。
- `no-draft-a-empty` 真实进入 A 类空创新药宇宙路径，只生成中文证据不足说明，不生成报告、HTML、coverage projection 或格式任务。
- 首次运行、失败后恢复、终态未变化恢复均生成当前 run、事件、检查点和 manifest 绑定；失败/中断节点与下游重跑，完成节点只在 `--resume` 时按输入摘要复用。
- 恢复会自动重绑项目内规范证据输入；证据变化要求显式重新打开，不能用旧结论覆盖新证据。
- 本轮新产物和复用材料分开记录；路径、SHA-256、字节数、精确 `mtime_ns` 与终态决策事件逐项校验。恢复前后篡改均失败关闭。
- 用户主界面文案为中文医学工作语境；内部机器状态只保留在 stderr、事件和 JSON。

## 决定性验证

- Task 3.6 四文件：11 passed；含真实 CLI：15 passed。
- 全库：458 passed。
- Ruff、strict mypy、JSON Schema、catalog、package verify、wheel 新模块成员、`git diff --check`：通过。
- 真实命令：fixture 首次运行 exit 4；`project run --resume` exit 4；当前恢复运行含 5 条节点复用事件、1 条终态决策事件、检查点和两份复用材料摘要；无报告/HTML/coverage projection。
- 恢复前修改阻断说明：exit 2，事件与 manifest 字节不变；恢复原文件后正常恢复。恢复后修改阻断说明：manifest 重验证失败。
- 隔离 Pi/OpenCode-Go 最终复验：PASS，P0=0、P1=0、P2=0。Cursor/Grok 前一轮已确认 P0/P1 清零；其 P2 项随后全部关闭。

## 边界与后续

- Task 3.6 的 wheel 检查只证明两个新 Python 模块进入 wheel，不声明该 wheel 已是可安装工作流包。
- schema、policy、migration、asset、fixture 等完整数据资源打包和隔离安装运行是计划 Task 9.5 的强制验收项。
- 下一步：Task 3.7 独立科学质控接受/否决；后续渲染任务接入时恢复 `reports/` 产物收集路径。
