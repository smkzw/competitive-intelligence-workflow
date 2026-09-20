# Checkpoint — R2 自主研究与严格交接合同（2026-09-05）

## 状态

本切片已通过代码、合同、安装包和受治理执行审计；Goal 与 R2 继续保持 active，
不输出 RC、发布、24 门户或三宿主通过信号。下一安全动作是补齐多报告联合执行
和 Yaozh 一次性选择持久化，再继续 R2.2-R2.4 闭包。

## 本次完成

- 项目首次进入来源研究等待态时生成类型化自主研究任务，而不是模糊占位说明；
  任务绑定项目/适应症/报告/截止日，并显式列出全球、中国、别名、靶点、企业、
  试验反向扩展及 A/B/C 专属路线和完成条件。
- 新增确定性 `research submit`：通用 v1.3 审计信封以规范路径和 SHA-256 绑定
  A/B/C 专属科学载荷，先校验身份、截止日、来源、宇宙、路由和独立复核，再
  原样写入不可变文件，最后发布 submission manifest；精确重放幂等。
- 产品 CLI 必须加载并复核 submission manifest；松散 `report-data.json` 或未绑定
  专属包不能完成产品运行。测试/fixture 兼容路径暂以显式内部参数保留。
- 公共 Skill 已改为“宿主自主研究 → 严格提交 → resume”的可执行说明；普通
  用户不需要手填内部 schema，自然语言理解和原生 Ask 不重复下沉到 CLI。
- package command catalog 从 8 项同步为 9 项，bundle final-content 纳入自主研究
  和严格提交模块。
- 修复 `ResearchSource` 科学语义：只有 publication 使用论文分类；登记、监管、
  附件、公司、会议和二级来源必须为 `not_applicable`。访问状态独立保存，不能
  把可访问登记来源伪装成主要结果论文；Pydantic 与 JSON Schema 已同步。

## 会商与实现裁决

- 采纳四个执行者提供的来源计划、完成条件、不可变提交和边界审计目标。
- 拒绝新增 1200 行自主任务大模型、453 行平行进度真源和把通用包直接写入
  A/B/C 专属路径；以 239 行任务合同和 282 行双层绑定提交服务完成最小根因修复。
- worker_04 提出的自然语言 CLI 不采纳：公开 Skill/宿主负责理解和原生 Ask，
  CLI 只负责确定性项目及提交边界。bundle sidecar 精确清单、源码 checkout
  host smoke 和真实三宿主自主研究留在 R4/R5。

## 决定性证据

- `pytest tests/integration -q`：441 passed。
- `bash tools/gate.sh`：Ruff OK；strict mypy 207 files；v1 active 917 passed / 20
  deselected；retained compatibility 20 passed；layer audit 7 passed；legacy scanner
  OK；`GATE_OK status=quality-only steps=6`。
- Publication/提交聚焦集合：12 passed；目标 Ruff 与 mypy 通过。
- `research submit --help` 和仓库 package manifest 校验通过。
- 临时候选 bundle：322 files，SHA-256
  `ce37489be87d7a1fa9b5ed50f5e5b1d656bcc644986601849e045822118f4795`；
  final-content 校验、fresh-install、安装后 package 校验和隔离 import closure 通过；
  该候选仅为可删除验证件，不是 RC。
- 新版 runner receipt v2 对四份最终 worker 报告做 SHA-256 字节绑定；
  `audit-execution` 与 `review-gate --require-verification` 均通过，无 warning/error。

## 保留缺口

- 当前严格提交可同时校验 A/B/C，但产品 runner 暂时只允许单报告项目；多报告
  合同会明确失败，不静默漏跑。
- Yaozh Ask 已进入任务合同，但一次回答尚未落入项目持久状态和公开命令。
- 逐对象 GateSpec、完整 publication/manual 状态机、宇宙/缺失整体闭包、真实
  三宿主、24 门户、浏览器视觉矩阵、clean RC 和恢复冻结均未完成。
- bundle 治理 sidecar 精确排除和安装后真实宿主 smoke 仍按 R4/R5 验收。

## 磁盘卫生与恢复点

临时候选 bundle 已在命令退出时精确删除。受治理过程文件在 review/audit 通过后
由 workflow guard 移入 `archives/execution/ci-r2-autonomous-research-contract-20260905/`；
随后删除四个已完成 APFS 隔离副本并复核不存在。保留精简 worker 报告、route/
context、review、metrics、canonical 文档、测试和当前工作树；不清理 Codex
session/database、科学原始证据、fixture 或其他恢复点。APFS 逻辑大小不等于
实际释放物理字节，不据此夸大空间收益。

执行结果：过程文件已归档，归档共 12,331,599 bytes（约 12 MB）；四个隔离
副本删除前各显示约 5.6 GiB 逻辑大小，均已按精确路径删除并复核不存在。
不把四者逻辑大小相加宣称为实际磁盘释放量。

## 下一安全动作

先以 TDD 把已提交的多报告 A/B/C 载荷逐份进入独立运行/门户链，并将 Yaozh
一次性选择绑定项目和幂等恢复；完成聚焦、全量 integration、quality-only gate
及独立审计后，再判断 R2.1 是否可关闭。
