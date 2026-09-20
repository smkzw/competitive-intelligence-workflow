# Checkpoint — R2.3 Publication 与人工补件产品门完成

## 结论

R2.3 已完成并通过受控执行、独立会商修订、Codex 文件/测试复核和全仓开发门。
Publication 的正式裁决、登记关联论文检索回执、单快照单次人工补件、错文件恢复、
扫描件 OCR 交接、不可得分流及多报告局部暂停均已进入真实产品运行链。

本结论只覆盖 R2.3，不代表真实出版商/付费墙访问、24 个门户、三宿主、浏览器视觉或
RC 已验收。

## 实现与合同

- `PublicationRecord` 是研究包内唯一正式 publication 裁决；综述与普通 ad hoc 默认
  排除，必需但未取得的论文须有至少两次、跨两个 `route_family` 的类型化获取尝试。
- 分歧/边界裁决须绑定独立 reviewer、干净上下文和候选摘要，生产者自审失败关闭。
- 每个已声明纳入的试验须有唯一 `PublicationSearchReceipt`；即使未发现关联论文，
  也须保留查询摘要、两类路线、尝试和无发现诊断，禁止静默省略 publication 搜索。
- research-package 提交按已批准 GateSpec 校验阻断单元；accepted replacement 仅在补件
  回执、来源和 publication 裁决一致后允许，并在替换前归档旧审计包、报告和 manifest。
- 每个审计快照只有一个用户门和一份用户可见 `manual-supply-request.md`。错文件隔离后
  可在同一 gate 接受正确文件；原文件 inode/字节不变，规范重命名、哈希和重抽取任务
  均有回执。无文本层 PDF 进入 `ocr_required`，不被误判为普通文本 PDF。
- 文件接受后产品返回诚实的 `recovery_required`（exit 7）；Agent 根据重抽取任务形成
  新严格包、重新提交并恢复受影响报告，不把待处理状态伪装为成功运行。
- 用户一次确认无法取得后，官方证据足够的受影响门户每一页显示限制；不足时不生成
  该报告门户，只生成简洁证据不足状态并进入 `evidence_blocked`。不受影响报告继续。
- 图状态覆盖 `awaiting_user`、`recovering` 和 `evidence_blocked`；用户文案不暴露内部
  快照摘要或本地定位字段。

## 独立审阅与修订

- 三名受控只读执行 worker 完成 publication/package、manual-inbox/run-service 和负向
  矩阵审计；`audit-execution` 通过，无路由漂移、fallback 或缺失角色。
- Grok Build `grok-4.6:high` 独立会商完成一轮，提出 D1–D10。Codex 逐项对照当前
  字节复核并关闭：错文件恢复、接受后恢复语义、producer 越权状态、限制可见性、唯一
  用户门、GateSpec 字段、产品负向覆盖、路线家族、逐试验检索回执和图状态/文案。
- 会商 `validate-conference` 与执行/会商两份 `review-gate --require-verification` 均通过。
- `--official-evidence` 在本阶段记录用户一次性不可得响应后的分流，不新增未经批准的
  自动充分性评分器；最终科学 QC 仍须检查该分支是否有足够来源支撑。

## 决定性验证

- publication / research-package / product 聚焦与负向测试：通过；其中产品链覆盖错文件
  后正确文件、扫描 PDF、重复运行、严格包替换、限制继续、证据不足和 gate 篡改。
- manual-inbox 恢复套件：4 passed。
- 全 integration：510 passed（121.26 s）。
- bundle / fresh-install：17 passed、1 skipped；跳过项为尚未进入本阶段的真实宿主 smoke。
- 最终全仓开发门（代码及治理修订后重跑）：
  - Ruff：通过；
  - strict mypy：211 个源文件通过；
  - v1 active：942 passed、20 deselected；
  - retained compatibility：20 passed、942 deselected；
  - layer audit：7 passed；
  - legacy reference scanner：通过；
  - `GATE_OK status=quality-only steps=6`。

## 边界、磁盘卫生与下一动作

- 本任务没有使用真实出版商、付费墙、药智账号或用户真实补件，不据此声明真实来源
  联调完成；也没有执行门户的物理浏览器视觉验收。
- 调试目录 `tmp/debug-publication-gate` 在确认真实路径后精确删除，释放 2,288 KiB；
  未执行广泛 cache、Git 或用户文件清理。
- 执行/会商的规范报告、review、metrics、上下文和恢复证据保留；runner 过程文件按 guard
  精确归档，不删除受保护会话状态。归档中的三份可再生 stdout 以 `gzip -9` 原样压缩，
  该任务执行归档由约 7.3 MiB 降至 824 KiB，释放约 6.5 MiB。
- 下一安全切片从正式执行计划重新读取 R2.4，聚焦完整医学语义归并与确定性冲突边界；
  不提前进入门户重构、三宿主、24 份真实报告或 RC。
