# Checkpoint — R2 核心能力矩阵执行门

日期：2026-09-05  
状态：本切片 accepted；R2 与 RC 均未完成

## 完成内容

- 产品运行每次首次执行和 `--resume` 都重新运行能力预检；preflight 节点不复用，
  同一 `RuntimeCapabilityProbe` 的上一 flight 缓存也不会被当作新观测。
- 当前矩阵由唯一应用层边界原子保存到 `capabilities/preflight.json`。规范回执目录、
  文件软链接或非普通目标失败关闭；读取缺失回执不创建目录。
- 研究必需能力缺失时，在来源研究任务生成前以 `capability_blocked`、退出码 5 和
  中文执行环境说明安全停止。恢复能力后可从同一项目继续。
- 仅 HTML 浏览器验收能力缺失时，研究可继续并保留已形成事实，但 format 不生成
  门户且不能标记为完成。药智登录是可选辅助能力，单独缺失不阻断核心链。
- CLI、fixture 与直接运行测试使用显式能力注入；生产默认仍使用真实运行时探针。
  能力阻断、关键证据不足和普通技术失败保持不同结局。

## 独立执行审阅

- 三个只读 worker 分别审阅 run-service 插入点、原子持久化/重放安全、负向恢复及
  CLI/宿主语义；均一轮完成，runner 报告 SHA-256 分别为：
  - `477d358706765350e37f9743a01343ada5c79bf3cbe45d3a6e1f6cc7e3616bb3`
  - `2f1c75e6af2e43d9c495b700c6c30965a009f1b5fd14585fe3bacb3de6060d25`
  - `343229fc86e12f1f30caec110919266f251114da004d12b4b333800bd773a90e`
- Codex 只采纳在最终源码与测试中可复现的结论。worker_02 发现的读取副作用和
  runtime probe 跨 flight 缓存均已关闭；并发演进期间的过时观察未当作验收事实。

## 决定性证据

- 能力/CLI/宿主/恢复聚焦集合：38 passed。
- `pytest tests/integration -q`：499 passed。
- `tools/gate.sh`：Ruff OK；strict mypy 209 source files；v1 active 940 passed / 20
  deselected；retained compatibility 20 passed；layer audit 7 passed；legacy scanner
  OK；`GATE_OK status=quality-only steps=6`。
- 隔离 bundle：324 files；SHA-256
  `60af99a93a9a47da27da00b41b1721323a73d8841194bcbda856723696e76ecb`；
  required-v12 final-content 通过；fresh-install 9 passed、1 个真实宿主测试显式跳过。
- 当前 Codex CLI：`codex-cli 0.153.4`。

## 尚未完成

- 真实药智浏览器适配器、登录态/验证码/访问受限的封闭诊断。
- R2.2 竞品宇宙全量 closure、完整 Publication/manual gate、逐对象 GateSpec 和
  blocker audit。
- Codex/Hermes/OMP 真实入口实跑、八适应症 A/B/C 24 门户、完整浏览器/科学验收、
  clean release source set、恢复演练和 RC 冻结。

## 磁盘卫生与下一安全动作

一次性候选 bundle 目录 `tmp/r2-capability-bundle.0IZ3lK` 的逻辑大小为 1,988 KiB；
其文件数、SHA-256、final-content 和 fresh-install 结果已记录，并在治理
review/audit 通过后逐文件精确删除，释放 1,988 KiB，复核原路径不存在。runner
原始 stdout 由治理归档保留，不清理会话数据库、科学
证据、fixture 或其他任务证据。

下一安全切片：按执行 v3 推进 R2.2 竞品宇宙 closure 的类型化查询/回执与独立
闭包复核，或在依赖顺序要求下先完成真实药智浏览器适配器；两者都不得借本切片
的能力门绿灯冒充真实来源可用。
