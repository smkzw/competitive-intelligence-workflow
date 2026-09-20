# Codex Execution Review: ci-r2-capability-execution-gate-20260905

## Verdict

ACCEPT 本次“实时能力矩阵 → 研究/HTML 选择性执行门 → 同项目恢复”合同切片。
本结论不接受真实药智浏览器、三宿主实跑、竞品宇宙闭包、24 门户或 R2 整体完成。

## Boundary

只评审当前新工程中的能力矩阵、产品运行选择性阻断、CLI/fixture/宿主合同、恢复
行为及其测试和规范文档。未访问其他工程，不运行真实账号，不执行生产或发布写入，
不接受真实 Codex/Hermes/OMP 三宿主、门户视觉或临床科学最终验收。

## Worker Outputs

- worker_01 准确定位了 run service 丢弃矩阵、恢复复用 preflight、研究和 format
  无执行门的问题。其建议已落实为显式 probe/host 注入、每次重检、研究前阻断、
  format 前阻断和独立退出码 5。
- worker_02 在实现并发落地后重新审阅，确认应用层原子写和软链接拒绝已成立，
  并发现读取会建目录以及复用同一 `RuntimeCapabilityProbe` 会沿用缓存。两项均已
  采纳并增加实证测试。其早期关于 CLI 仍绕开唯一 writer 的观察已因当前 CLI
  默认项目路径使用 `persist_capability_matrix` 而失效；任意显式 `--json` 仍是
  用户指定导出文件，不是项目规范回执。
- worker_03 的最小负向矩阵用于核对研究阻断、交付阻断、可选药智、恢复重检、
  中文状态与 CLI/宿主语义。没有扩展成重复测试层。
- 三份 worker 报告均由 runner 保存，worker 未写产品代码或自行宣称验收。

## Manager Assessment

当前 live route 不配置独立 Hermes execution manager，由 Codex 直接处置三个独立只读 worker。
worker 输出形成时工作树仍在演进，因此仅采纳可在最终字节和测试中复现的发现；
早期快照判断未被直接当作当前事实。

## Codex Independent Verification

- 聚焦能力/CLI/宿主/恢复集合：38 passed。
- `pytest tests/integration -q`：499 passed。
- `tools/gate.sh`：Ruff OK；strict mypy 209 source files；v1 active 940 passed / 20
  deselected；retained compatibility 20 passed；layer audit 7 passed；legacy scanner
  OK；`GATE_OK status=quality-only steps=6`。
- 隔离 bundle：324 files；SHA-256
  `60af99a93a9a47da27da00b41b1721323a73d8841194bcbda856723696e76ecb`；
  required-v12 final-content 通过。fresh-install 9 passed、1 个真实宿主测试按现有
  边界显式跳过。
- 负向边界覆盖：研究必需能力阻断在来源任务前；仅浏览器验收阻断不生成门户；
  药智登录单独缺失继续核心；恢复时不复用 preflight；软链接不替换外部字节；
  缺失回执读取无副作用；运行时 probe 跨 flight 不复用缓存。

## Cleanup Decision

review gate 通过后归档 process files，不删除 worker 报告。一次性 bundle 在摘要和
SHA 已进入 checkpoint 后精确删除；不触碰用户工作树、科学证据、fixture、会话
数据库或其他任务材料。
