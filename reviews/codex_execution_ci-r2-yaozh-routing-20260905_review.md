# Codex Execution Review: ci-r2-yaozh-routing-20260905

## Verdict

ACCEPT 本次“项目回答 → 来源计划 → 可选能力 → 运行期访问状态”合同切片。
本结论不接受真实药智浏览器访问、三宿主或 R2 整体完成；这些仍需后续实测。

## Boundary

只评审当前新工程中的药智合同、来源政策、研究任务、能力预检、运行接线及相邻
测试/文档。未访问其他工程，不处理真实账号，不进行生产写入，不修改已封存任务，
不接受真实浏览器、Hermes/OMP/Codex 三宿主或发布完成。

## Worker Outputs

- worker_01 正确指出旧来源政策没有药智条目、自动研究任务不消费回答，以及
  `session_expired` 错误混入项目回答类型。已采纳：来源政策升至 1.1 且药智无
  `direct` 权限；项目回答收窄为三态；自动研究任务按回答生成可选路线或明确
  `not_applicable` 状态。
- worker_02 正确复现旧 `login_browser` 会阻断全部研究/交付。已采纳最小依赖
  分离：该能力仍被探测和记录，但 `required_by=()`，不进入核心研究与 HTML
  依赖；恢复后也不会重排整条产品链。宿主 receipt 因 matrix 保持 `ready` 而不会
  将仅药智失败分类为全局 `capability_blocked`。
- worker_03 的正负/恢复/幂等/秘密测试矩阵已用于 TDD。未采纳其“四个新测试
  模块”的文件拆分建议；相同合同用现有相邻测试文件即可闭合，避免无必要扩散。
- 三份 runner receipt 均为 v2，分别绑定报告 SHA-256；`audit-execution` 通过，
  无 route drift、缺报告、pending 或错误。

## Manager Assessment

该路线按 live policy 不配置独立 Hermes manager，由 Codex 直接复核。另按用户明确要求，
以 CLI compatibility 运行一次 `gpt-6-astra:high` 全新只读阶段审阅；本机 CLI
`0.153.4` 实际启动记录明确显示 model=`gpt-6-astra`、reasoning effort=`high`。
旧 workflow guard 仍仅允许 Astra low/medium，因此 native admission 失败；未静默
降级。审阅正文 SHA-256 为
`40b32b1f4dd42f2f690cd8cd9bbdf9a2e5395b0549782e274aaae042ead1223e`。

Astra 提出的七项 P1 中，本切片已关闭项目三态、悬空软链接、任务迁移、可选
依赖和来源权威五项；“run service 尚未把核心 preflight blocked 状态作为执行门”
保留为下一切片的现存 P1；“真实浏览器异常需封闭诊断”作为浏览器适配器硬门，
本切片没有虚构尚不存在的抓取器。Publication/manual gate 和运行完成文案保持
既有 R2 后续项，不在此切片冒充完成。

## Codex Independent Verification

- TDD RED 实际捕获：任务不接收回答、登录能力错误阻断、项目选择不消费回答、
  来源政策缺药智、模型接受第四态、悬空软链接被覆盖、缺运行期访问回执。
- 聚焦 GREEN：药智持久化 19 passed；药智/自主任务/预检/来源政策/入口合同
  25 passed；项目运行 4 passed。
- `pytest tests/integration -q`：489 passed。
- `tools/gate.sh`：Ruff OK；strict mypy 209 source files；v1 active 940 passed / 20
  deselected；retained compatibility 20 passed；layer audit 7 passed；legacy scanner
  OK；`GATE_OK status=quality-only steps=6`。
- 最终隔离 bundle：324 files；SHA-256
  `ae6f90bd498edc81ed8f05ab7ba5eecc4c59224629d0354e195dce68e237a2d5`；
  required-v12 final-content 通过；fresh-install 9 passed、1 个真实宿主明确跳过。
- 科学边界：`yaozh_enterprise` 不属于全球/中国必查来源，无任一声明域为
  `direct`；疗效/安全与基线仅 `lead_only`。`unavailable/skipped` 不创建虚假
  科学尝试或证据片段。
- 恢复边界：首次待办可在一次性回答后原子更新；旧待办必须可按同一项目/合同
  解析，否则拒绝覆盖。相同任务字节直接返回，不改写。
- 秘密边界：项目回答、任务和访问回执均为 `extra=forbid` 封闭合同；运行期回执
  只绑定无凭据回答字节摘要，不接受 Cookie/token/header/browser storage。

## Cleanup Decision

执行包通过 review gate 后归档，不删除 runner 证据。两个一次性 bundle 目录在记录
最终 SHA 和 fresh-install 结果后精确删除；不触碰会话数据库、科学证据、fixture、
其他任务归档或用户工作树。Astra 阶段审阅保留为本阶段独立会商证据。
