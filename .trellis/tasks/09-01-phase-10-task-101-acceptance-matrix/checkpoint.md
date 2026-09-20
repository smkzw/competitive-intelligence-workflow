# Task 10.1 完成检查点

完成时间：2026-09-01T12:20:07+08:00

## 已完成

- 建立首版站点式 HTML 的唯一机器验收目录，共 23 个场景：`full-matrix-v1`、4 个历史截止场景、批准计划中的 18 个 `required-v12` 机器族。
- 固定适应症、IANA 时区、物化数据截止、逐文件 SHA-256、稳定 case digest、预期/禁止结果、责任阶段、验证器和回执位置。
- 18 个 required-v12 族与批准计划逐项独立绑定；E1 单独标记条件不适用，其余未来阶段回执均保持待执行。
- 完成中文医学验收矩阵；PDF、HTML-PPT、PPTX 继续无损延后，不进入首版阻断条件。
- 候选包 allowlist 已包含 `fixtures/acceptance` 和 `docs/acceptance/matrix.md`。

## 决定性验证

- Task 10.1、相邻 fixture/package、bundle 与 fresh-install 聚焦套件：46 passed。
- Ruff 检查通过；目标 digest 实现与验收测试 mypy 通过。
- 独立 Pi/Cursor 会商同一会话两轮复核，最终结论为“接受，附非阻断后续说明”，无 fallback。

## 异常与恢复

- 初始执行把内部自定的 18 个语义场景误当作批准机器族；Codex 对照实施计划发现后，复用原 worker 会话改为准确的 18 个计划 ID 和子场景。
- 一次控制器机械整合错误使用了未加载项目环境的系统 Python，导致两个 YAML 暂时被 traceback 覆盖。完整输入目录未受损；worker_02 与 worker_01 在原会话依次重建 fragment 和共享 catalog，23 个 case、35 个输入/预期摘要与全部 case digest 重新核验通过。
- 该事故属于技术整合错误，不是证据缺失；恢复后未遗留 traceback、摘要漂移或旧 case 目录。

## 下一安全动作

进入 Task 10.2：按 catalog 锁定的真实 fresh-source A/B/C 场景执行站点式 HTML 验收。Task 10.1 不代表未来 verifier、receipt、RC、恢复演练或旧根处置已经完成。
