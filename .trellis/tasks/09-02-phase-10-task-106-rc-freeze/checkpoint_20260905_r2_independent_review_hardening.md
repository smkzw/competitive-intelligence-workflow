# Checkpoint — R2 独立复核信任根加固（2026-09-05）

## 状态

本切片已完成并通过独立执行审计；Goal 与 R2 仍保持 active，不输出 RC、发布或
真实三宿主验收信号。下一安全动作是继续 R2.1-R2.4 未闭合项，而不是续跑旧
Task 10.6 RC 流程。

## 本次完成

- 已执行一次 `gpt-6-astra:high` 只读阶段审阅和一次独立 CodeBuddy 会商；
  Codex 对共同 P1 逐项裁决并启动四 worker 隔离执行。
- 新增安装包内 `review issue`：绑定已发布 request，真实启动外部复核进程，
  将 host/session/process/formal verdict 字节写入 `scientific-review-v1` receipt
  与同源 issuance record；只有两者、request 和当前生产上下文共同闭合才可晋级。
- A/B/C 统一为 post-format 两阶段状态机：HTML manifest/站点真实字节先绑定，
  无回执为 `rendered_unreviewed`；研究包自审不再授权 A 报告。
- 晋级时重新检查 receipt `issued_at` 与 verdict `valid_until`；未来、过期、
  同身份、同会话、伪回执、替换记录、跨候选和门户漂移均失败关闭。
- A 摄取使用 package review 时间建立确定性快照；生产上下文和 review request
  对其他候选不可覆盖。
- 等待回执和晋级后允许任意次纯复用 resume；真实来源验收沿
  `run.node.reused` 来源图闭合，不再错误限制为两个 run。
- bundle 纳入 `review_issuer.py` 与完整 scientific review import closure；
  package CLI catalog/schema 同步。retained non-HTML 仅为 2 文件/20 断言的
  bounded compatibility smoke，不属于 v1 release gate。
- canonical v1.3、roadmap、execution v3 和 Task 10.6 design/implement 已同步
  本地信任模型及 R4/R6 延后项。

## 决定性证据

- `bash tools/gate.sh`：Ruff OK；strict mypy 205 files；v1 913 passed / 20
  deselected；retained compatibility 20 passed；layer audit 7 passed；legacy
  scanner OK；`GATE_OK status=quality-only steps=6`。
- `pytest tests/integration -q`：438 passed。
- R2 聚焦：91 passed；C 类额外端到端签发/晋级测试通过。
- `python -m ci_workflow package verify --root .`：`PACKAGE_OK`。
- 临时候选 bundle：320 files；SHA-256
  `e77e87ebfb3007a052707f4237de81fcd7c5351e9208bda7b0dff2af9ae3282a`；
  final-content verify 返回 `BUNDLE_OK`。此包仅为可删除验证件，不是 RC。
- `audit-execution`：4/4 worker route/output/stdout 闭合，无 warning/error。
- execution review gate：通过。

## 会商裁决

- 立即采用：真实签发记录、post-format 晋级、门户字节绑定、A/B/C 对称、
  晋级时有效期、多次 resume、bundle 信任根和准确测试口径。
- 延后：R4 验证实际 screenshot bytes；R6 绑定 expected run identity。
- 拒绝：PKI、中央签名服务、OS attestation、nonce registry、第二套 receipt、
  重新激活 PDF/PPT 产品轨。
- 本地 v1 不声称抵抗拥有项目目录写权限的恶意同一 OS 用户；它保证普通公开
  API 路径不能用手写自洽 JSON、无关历史或漂移字节取得科学晋级。

## 保留阻断与未完成

- 三宿主真实签发/fresh-install、R4 所有物理页面浏览器与 screenshot-byte
  验收、24 门户、clean RC、恢复冻结均未执行。
- 三个旧外部 A/B/C 验收项目仍因旧 `package_digest` 被当前门正确拒绝，
  按计划在 R5/R6 用当前候选重新生成，不修改旧证据冒充通过。
- R2.1-R2.3 与逐对象 GateSpec / blocker audit 尚未整体闭合。

## 磁盘卫生与恢复点

四个 APFS worker 克隆与临时 bundle 仅在本 checkpoint、worker reports、stdout、
review 和 metrics 全部落盘且 audit/review gate 通过后删除。保留 prompts、
runner 证据、canonical 文档、测试、receipt 合同和当前工作树；不清理任何
Codex session/database 或其他受保护运行时状态。

执行结果：过程文件已由 workflow guard 归档到
`archives/execution/ci-r2-independent-review-hardening-20260905/`（13 files，
约 152 KiB）；四个隔离克隆原显示各约 5.6 GiB、临时 bundle 约 1.9 MiB，
均已逐目录删除并复核不存在。APFS 克隆的实际物理释放量可能小于显示逻辑
大小，不据此夸大释放空间。

## 下一安全动作

从 R2 剩余合同做一次差距审计，优先选择可独立验收的 GateSpec/blocker 或
入口研究链小切片；继续使用 guard 声明执行/会商，完成后再更新本阶段状态。
