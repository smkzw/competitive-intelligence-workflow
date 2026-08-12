# Task 3.2 接受与续接锚点

日期：2026-08-12

## 当前结论

- Task 3.2 已接受：`PASS；P0=0；P1=0`。
- 修复与接受提交：`f02dff4 fix: close task 3.2 audit false greens`。
- Phase 3 仍为 `in_progress`；Task 3.3—3.7 尚未实施或接受。
- 下一安全动作：严格按批准计划 Task 3.3，先建立下载请求、manual-inbox 自动识别/规范命名/归档/续跑的首轮 RED 合同。

## 不可退回的不变量

- 关键证据不足不得产生正式、草稿或占位报告，不得创建报告快照、覆盖投影、格式/渲染作业或产物记录。
- 技术访问失败与科学上未列示/未公开分开；用户中断前必须完成多路径恢复、连续两轮信息增益饱和和独立遗漏复核。
- 每个适用路线仅一条摘要，允许汇总多条实际回执；回执、尝试次数、访问方式和最终结果类别均从实际证明派生。
- A/B/C 空宇宙分别建模；B/C 必须绑定闭合快照，A 真正零产品不伪造快照。
- 阻断时唯一用户产物是 `blockers/<report>/<version>/{audit.json,audit.md}`；文字使用原生中文临床语境，不展示内部状态、日志或提示词。

## 最终机械证据

- Task 3.2 精确套件：98 passed。
- Task 3.1 回归：143 passed。
- 全库：429 passed。
- Ruff、strict mypy、JSON/Schema、包校验、`git diff --check`：通过。
- 主会场已真实重放重复路线、最终结果类别伪造、空宇宙跨 GateSpec、B/C 缺快照和空宇宙多资格缺口攻击；全部失败关闭。

## 独立验收与路由记录

- 实现会话：`019ff262-8ff4-7000-8709-4589a92be55c`，最终使用 `Pi/opencode-go/deepseek-v4-flash:max`，同会话完成六轮修复，无 fallback。
- 独立验收会话：`019ff5e4-2a7d-7000-82c3-9ba2b770687c`，`Pi/opencode-go/deepseek-v4-flash:max`，修复后实际复测 98/143/429，最终 PASS。
- Grok Build 会话 `b3833cab-e55a-42b0-aa7e-3e5ac463c644` 连续三次在工具调用前 cancelled，最终出现 `Resident session actor ... DeadFailed`；按声明链切换。
- 备用验收会话：`d1708553-1dc7-4f2f-b63a-4b742285162f`，`Cursor/cursor-grok-4.5-high`，修复后静态合同复核 PASS；Shell 被宿主拒绝，未把其静态结论当作机械执行替代。

## 当前内容摘要

- `schemas/blocker-audit.schema.json`：`36d0d2af5a9bbeda72cea4346e4acfce7559a6d1ad921bbd3212740bd1c3ff96`
- `src/ci_workflow/gates/exhaustion.py`：`b29b8321e8761d8ed6c14bd3fa76013c6c38face21919d198f6f6cafed0a520b`
- `src/ci_workflow/gates/blocker_audit.py`：`264e3fd5dc84b1e5503bdf00ff0a81f8955fe28e98ffca9307eed9ffd87a9301`

## 非阻断后续观察

- Task 3.3/3.4 的真实恢复图需明确同路径重试与恢复轮次的展示口径，避免把重复尝试误当信息增益。
- 正式 Graph 入口必须从事实与规范原子求值，不接收调用方自报的 GateResult。
- 科学质控完整门户、关系图实体复核和锁快照仍属于 Task 3.7，Task 3.2 只接受否决路径与零下游不变量。
