# Checkpoint — R2 A/B/C 渲染事务恢复（2026-09-05）

## 状态

A/B/C HTML 的未发布中断恢复已完成代码、测试、全仓门、隔离 bundle 和受治理
执行审计；Goal 与 R2 保持 active，不输出 RC、三宿主、24 门户或发布信号。
过程归档在本 checkpoint 后完成。

## 本次完成

- 新增共享 `UnpublishedRenderTransaction`：每个报告版本先在 run 级 staging
  渲染，完成后原子换名为 `html/`，再原子写 `html.manifest.json` 作为提交点。
- A/B/C 产品 artifact builder 均接入同一事务；站点摘要和 mtime 在 staging 上
  计算，换名后保持一致。
- resume 只清理当前项目、当前报告、当前版本内可证明未发布的 `html/`、staging
  和 manifest 临时文件；未知文件、软链接、越界路径均失败关闭。
- 版本根产物清单、coverage projection、artifact store、当前运行清单或科学复核
  状态只要精确绑定目标站点/manifest，即使目标 manifest 被删除也拒绝覆盖。
- 原始 A/B/C site renderer 仍用于纯渲染测试，但全仓生产调用只通过事务 staging；
  它们不是产品发布入口。

## 会商与裁决

- 采纳 worker_01 的共享事务和 A 接入，采纳 worker_02 的 B/C 对称接入；不引入
  第二状态数据库或复杂 journal。
- worker_02 曾在主工作树短暂截断未跟踪 `report_b.py`，随后从操作前备份恢复。
  Codex 对照备份确认当前差异仅为事务接入及必要格式化，并恢复了一段被误删注释；
  该 Python rewrite/临时恢复方式不符合本项目常规编辑纪律，不作为后续方法。
- 采纳 worker_03 关于科学复核与当前运行绑定的风险并即时补强。格式完成事件缺少
  report version，不能按报告类型粗暴拦截所有新版本；版本精确保护由 manifest、
  run/review 路径绑定和 artifact store 共同承担。
- 快照在 manifest 提交前锁定可能留下孤儿快照；它不覆盖既有快照且不授予发布权，
  当前记录为后续小型治理项，不为此扩大事务状态机。

## 决定性证据

- 事务聚焦集合：43 passed。
- `pytest tests/integration -q`：481 passed。
- `bash tools/gate.sh`：Ruff OK；strict mypy 209 files；v1 active 940 passed / 20
  deselected；retained compatibility 20 passed；layer audit 7 passed；legacy scanner
  OK；`GATE_OK status=quality-only steps=6`。
- 临时候选 bundle：324 files，SHA-256
  `cbe06b136e90b416943eb9c7087fec0ce4709dda0872e43b6018d8b105c81e77`；
  required-v12 final-content 通过；fresh-install 9 passed、1 个真实宿主显式跳过。
- 三个执行会话均一轮完成；runner receipt v2 绑定最终报告字节；
  `audit-execution` 与 `review-gate --require-verification` 均通过，无 warning/error。

## 保留缺口

- 项目运行仍依赖单写者；同一项目同一版本的跨进程并发不是本切片承诺。
- 中断前已锁定但未被产物引用的孤儿 report snapshot 尚未自动回收。
- Yaozh 项目回答尚未接入来源规划和已登录浏览器路线。
- 真实三宿主、24 门户、浏览器视觉矩阵、R2.2-R2.4 整体闭包、clean RC 和恢复
  冻结均未完成。

## 磁盘卫生与恢复点

guard 已把过程材料归档到
`archives/execution/ci-r2-render-transaction-recovery-20260905/`，共 10 个文件、
7,097,267 bytes。一次性 bundle 目录删除前为 1,984 KiB；worker_02 的 3 个操作前
备份与 3 个机械修复脚本已按精确路径删除，上述 7 个目标均复核不存在。保留源代码、
测试、规范文档、review、metrics、checkpoint 和归档；不清理 Codex session/database、
科学原始证据、fixture、其他检查点或用户工作树。

## 下一安全动作

把 Yaozh 三态项目回答接入来源计划：available 只启用已登录浏览器辅助路线，
unavailable/skipped 明确记录非阻断不适用回执，session_expired 作为技术访问状态
提示用户自行登录；任何凭据仍不得进入项目、提示词、日志或 bundle。
