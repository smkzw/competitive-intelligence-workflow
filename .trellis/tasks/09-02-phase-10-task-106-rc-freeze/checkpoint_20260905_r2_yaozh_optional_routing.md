# Checkpoint — R2 药智可选路线与三态接线（2026-09-05）

## 状态

药智项目三态已接入来源政策、类型化自主研究任务和能力预检；运行期会话状态有
独立无凭据访问回执。Goal 与 R2 保持 active，不输出真实药智访问、三宿主、24 门户、
RC 或发布信号。

## 本次完成

- 项目回答类型仅允许 `available`、`unavailable`、`skipped`；`session_expired` 不再
  能通过模型或读取入口伪装成第四种永久回答。
- `available` 增加 `required=false` 的 `yaozh-optional-browser` 研究路线；另外两态
  在任务中形成非阻断 `not_applicable`，不创建虚假科学来源、尝试或完成回执。
- `source-policy-v1` 升至 1.1，新增 `yaozh_enterprise`；不属于全球/中国必查来源，
  无任何 `direct` 权限，疗效/安全和基线仅 `lead_only`。
- `selection_from_project` 消费一次性回答。可选 `login_browser` 仍被探测和记录，
  但不进入核心研究、HTML 交付或全链恢复依赖；失败时中文提示用户自行登录并说明
  其他来源继续。
- 运行期 `YaozhRouteAccessReceipt` 把 `ready`、`session_expired`、
  `tool_unavailable` 与项目回答分开，绑定回答字节摘要且不允许凭据字段。
- 首次生成的来源研究待办可在回答后按同一项目/合同原子更新；损坏、跨项目、
  非普通文件和软链接均拒绝覆盖。同字节重放不改写。
- 修复独立 Astra 审阅发现的悬空软链接漏洞：悬空记录不再被当作缺失并替换。

## 会商与裁决

- 三个受治理只读 worker 分别核查来源权威、可选能力依赖和测试/文档矩阵；
  runner receipt v2 与 `audit-execution` 均通过。
- 用户指定的 `gpt-6-astra:high` 一次性阶段审阅通过 Codex CLI 0.153.4 兼容路径
  完成。原生 guard 目录仍错误限制为 low/medium，因此保留 admission 失败证据且
  未替换模型。
- 采纳 Astra 的三态分离、悬空链接、依赖分离、来源权威和任务迁移建议；不建设
  第二状态库、账号中心、Cookie 导出、自动续登、后台监测或通用商业数据库框架。
- run service 目前仍只把核心 capability matrix 计算为节点输出摘要，尚未持久化并
  将必需能力 blocked 作为执行门。此项保留为下一安全切片的 P1，不因本次药智
  非阻断接线而隐藏。

## 决定性证据

- 药智持久化与运行期回执：19 passed。
- 药智/自主研究/能力/来源/入口聚焦集合：25 passed；项目运行：4 passed。
- `pytest tests/integration -q`：489 passed。
- `tools/gate.sh`：Ruff OK；strict mypy 209 files；v1 active 940 passed / 20
  deselected；retained compatibility 20 passed；layer audit 7 passed；legacy scanner
  OK；`GATE_OK status=quality-only steps=6`。
- 最终隔离 bundle：324 files，SHA-256
  `ae6f90bd498edc81ed8f05ab7ba5eecc4c59224629d0354e195dce68e237a2d5`；
  required-v12 final-content 通过；fresh-install 9 passed、1 个真实宿主显式跳过。
- Astra review SHA-256：
  `40b32b1f4dd42f2f690cd8cd9bbdf9a2e5395b0549782e274aaae042ead1223e`。

## 保留缺口

- 真实药智浏览器适配器、实际登录态/验证码/访问受限分类与封闭错误诊断尚未实现；
  当前空白 Chromium smoke 不能证明药智会话有效。
- 核心 preflight blocked 状态尚未成为 run service 的持久化执行门。
- Publication/manual gate、宇宙闭包余项、逐对象 GateSpec、真实三宿主、24 门户和
  浏览器视觉矩阵仍未完成。
- 渲染事务已记录的孤儿 snapshot 小型治理项不在本切片扩展。

## 磁盘卫生与恢复点

- 受治理执行材料已归档到
  `archives/execution/ci-r2-yaozh-routing-20260905/`，共约 6000 KiB；worker 报告、
  runner stdout receipt v2 和 cleanup manifest 均保留。
- 两个一次性候选 bundle 目录共 3968 KiB，已在记录最终文件数、SHA-256、
  final-content 和 fresh-install 结果后精确移入系统废纸篓，并复核原路径不存在。
- Astra prompt 与只读审阅正文保留在 `prompts/`、`runs/conference/` 作为本阶段
  用户指定模型/effort 的独立证据；不清理任何 Codex session/database、科学证据、
  fixture、其他检查点或用户工作树。

## 下一安全动作

先把核心 capability matrix 持久化并接入 run service 的选择性执行门：必需能力
缺失时按受影响报告/交付阻断，药智可选能力仍只降级；为测试和宿主入口提供显式、
可重放的 probe 注入，避免用忽略 preflight 的方式维持旧集成测试。随后进入真实
药智浏览器适配器的封闭诊断合同或 R2.2 宇宙 closure，按依赖评估择先。
