# Codex Execution Review: ci-r2-autonomous-research-contract-20260905

## Verdict

ACCEPTED_WITH_CODEX_REDESIGN. 四个隔离 worker 均完成且提供了有效实现或审计
输入，但其产物不直接取得验收权。Codex 没有照搬 worker_01 的大型状态模型、
worker_02 的泛型包直写方案或 worker_03 的平行进度真源，而是收敛为一个类型化
宿主研究任务、一个严格审计信封和 A/B/C 专属科学载荷的字节绑定提交边界。

## Worker Outputs

- `worker_01`：采纳来源计划、报告专属完成条件和一次性 Yaozh 选择语义；将
  1200 行候选实现压缩为 239 行，并复用现有合同。
- `worker_02`：采纳不可变提交、摘要绑定和幂等恢复目标；拒绝把泛型
  `ResearchPackage` 直接写入 A/B/C 专属加载路径，改为审计信封绑定专属载荷。
- `worker_03`：采纳 publication/manual、网络失败、宇宙闭包和恢复必须可审计的
  要求；拒绝新增 453 行第二状态真源，继续以现有模型和提交 manifest 为准。
- `worker_04`：审计发现的严格 package 绕过、schema/model 漂移和 bundle 闭包
  已修复；自然语言入口留在宿主 Skill，不重复建设自然语言 CLI。治理 sidecar
  精确 allowlist、源码 checkout 宿主 smoke 和真实三宿主自主执行留在 R4/R5。

## Manager Assessment

本执行包未配置 manager，由 Codex 直接处理四个独立输出。最终设计遵循
YAGNI：CLI 只提供确定性 `research submit`，宿主 Skill 负责自然语言理解和原生
Ask；产品 `project run` 必须看到已验证 submission manifest，不能再用松散
`report-data.json` 或未绑定的专属包完成产品运行。当前只闭合单报告产品执行；
多报告联合编排和 Yaozh 选择持久化被明确保留为下一小切片，未静默降级。

## Boundary

本次只在当前新工程及四个隔离执行副本中工作；没有 reset、checkout、clean，
没有访问旧工程、真实凭据、生产发布位置或受保护 Codex session/database。
候选 bundle 只在一次性临时目录构建、安装、验证并删除；未创建 RC commit。

## Hermes

本执行包最初由 live guard 声明 Pi/openai-codex/gpt-5.6-luna:max；新版 runner
重签回执时按已登记的非高峰变体为 worker 01-03 选择 ZCode，worker 04 的 ZCode
输出未满足完整执行报告门后使用声明的 Pi/Luna fallback。Hermes 未被声明且未
参与本次 artifact production。Hermes 的真实安装与入口一致性仍属于 R4/R5
三宿主矩阵，本轮不将其缺席写成通过或失败。

## Codex Independent Verification

- `pytest tests/integration -q`：441 passed。
- `bash tools/gate.sh`：Ruff 通过；strict mypy 207 files；v1 active 917 passed /
  20 deselected；retained compatibility 20 passed；layer audit 7 passed；legacy
  scanner 通过；`GATE_OK status=quality-only steps=6`。
- 聚焦 package/入口测试：12 passed；目标 Ruff 与 mypy 均通过。
- `audit-execution`：四份 runner receipt v2 与最终报告 SHA-256、角色和声明路线
  全部闭合，无 warning/error。
- `research submit --help`、仓库 package manifest 校验均通过。
- 隔离候选 bundle：322 files，SHA-256
  `ce37489be87d7a1fa9b5ed50f5e5b1d656bcc644986601849e045822118f4795`；
  archive final-content、fresh-install、安装后 package 校验和隔离 import closure
  均通过。候选包已删除，不是 RC。
- Publication 语义根因已修复：只有 `source_type=publication` 可使用论文分类，
  其他来源必须为 `not_applicable`；Pydantic 与 JSON Schema 同步。

未主张：多报告联合执行、Yaozh 回答落盘、三宿主真实自主研究、24 门户、真实
浏览器视觉矩阵、clean RC、恢复冻结或发布。

## Cleanup Decision

review gate 和 execution audit 通过后，将本执行包移入 `archives/execution/`，
删除四个已完成 APFS 克隆。保留精简 worker 报告、route/context、review、metrics、
canonical 文档和测试；约 49.5 MB 原始 stdout 由 guard 归档后可压缩，不触碰
Codex session/database、科学原始证据或其他恢复点。
