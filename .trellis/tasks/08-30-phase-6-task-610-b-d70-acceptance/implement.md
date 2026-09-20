# Task 6.10 实施清单

## 合同与 RED

- [x] 盘点当前 fixture runner、B 视图/渲染、manifest 与浏览器验收接口。
- [x] 新增精确 D70 三案例注册/摘要/状态测试并保存 RED 证据。
- [x] 新增 fresh PNH 与四项目当前运行绑定验收测试并保存 RED 证据。

## 输入包与执行闭环

- [x] 构建 `fixtures/positive/b-pnh/` 和三个独立 D70 输入包，更新唯一 catalog 和 schema 兼容面。
- [x] 实现或修复 B 运行适配、基线门槛、恢复快照、处置缺失与分母语义所需的最小代码。
- [x] 清理或归档同名旧验收目录；确认四个项目根在运行前新建且为空。
- [x] 串行运行 fresh PNH 与三个 D70 命令；任一异常先诊断后继续。

## 确定性与浏览器验收

- [x] 运行 Task 6.10 目标测试、B 类测试、Phase 6 精确退出集合和 A 类回归。
- [x] 生成当次验收站点、manifest、摘要和全路由截图。
- [x] 在 Chromium/WebKit 的 768/1024/1440 视口检查全部路由及交互。
- [x] 验证 PNH 关键事实、研究/论文角色、终点依据、基线门槛、非阻断处置、分母语义和缺失状态。

## 独立审阅与修复循环

- [x] 分别对 Minimax、Cursor Grok 4.6 medium、CodeBuddy hy3-x 做真实连通性测试。
- [x] 三路以真实医学经理角色审阅站点、截图、科学完整性、中文与视觉；独立科学审阅另行验证关键事实。
- [x] 按 P0/P1 优先修复并重复目标测试、浏览器截图和同会话复核，直至无 P0/P1 或形成真实技术阻断。
- [x] Codex 重新打开最终受众运行时，完成最终科学、浏览器和视觉接受。

## 记录与阶段收口

- [x] 更新 `docs/acceptance/report-b.md`、本次 `docs/acceptance/runs/task-6.10/`、Phase 6 PRD/实施清单和任务 checkpoint。
- [x] 保存源文件与关键产物哈希、运行起点、命令结果、截图索引、审阅结论和下一安全动作。
- [x] 只清理明确属于本任务且不再使用的缓存/旧测试产物；不删除旧工程，不发布 Phase 6，不启动 Phase 7。

## 持久化包补充记录（worker_03）

- 已生成持久化包：`output/acceptance/task-6.10/phase-6-acceptance-package-20260830/acceptance-package.json`。
- 包摘要：`1e00bb8b8d091366c25e4b2309b9dca21f6fcb1efac1c17d9a13f6cba6c87e13`；四个案例逐案确定性摘要和当前文件路径均写入包清单。
- 四个运行均从独立空项目根开始：PNH 与 D70 恢复/处置案例锁定 B 快照并停在 `quality_check`，D70 基线缺失案例停在 `evidence_blocked` 且只保留阻断审计文件。
- 包级重算验证通过；15 项 fresh/状态链/注册测试、518 项 Phase 6 B 确定性集合和 74 项 A 类回归均通过。
- 本补充不执行视觉接受，不将 `quality_check` 推进为 `delivery_ready`，不标记 Phase 6 接受，不启动 Phase 7；等待 Codex 绑定最终真实视觉裁定。

## Codex 最终视觉与状态收口

- [x] 将第一轮会商发现的 768 表格、搜索聚焦和 Escape 语义转为双引擎 RED；修复后 16 项全部通过。
- [x] 生成新候选 `f1b37ba4745997df319485fb6e929e24ed1153d0304376f6740c45fda3800381`，覆盖 144 个渲染目标和 150 张截图。
- [x] 同一独立会商 session 第二轮复测七域全部接受；Codex 查看代表截图并绑定正式视觉签收记录。
- [x] 写入不可变接受清单 `artifact-manifest-accepted_002bad11c24551a833c5ce39.json`，原清单保持 `quality_check`。
- [x] 运行 317 项聚焦回归及 612 项 Phase 6/A 类回归；均通过。
- [x] 写入 `acceptance-package-final.json` 并关闭 Phase 6；Phase 7 尚未启动。
