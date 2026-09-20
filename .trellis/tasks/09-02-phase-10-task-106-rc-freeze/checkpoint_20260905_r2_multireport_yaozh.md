# Checkpoint — R2 多报告联合执行与 Yaozh 项目状态（2026-09-05）

## 状态

本切片代码、合同、集成、隔离安装包和受治理执行审计已通过；过程归档将在本
checkpoint 后完成。Goal 与 R2 保持 active，不输出 RC、发布、24 门户或三宿主
通过信号。下一安全动作是修复渲染中断留下部分目录后的可恢复事务边界，再把
Yaozh 项目回答接入可选来源规划。

## 本次完成

- 严格提交可在同一项目运行中携带多个报告载荷；A/B/C 分别进入既有科学门和
  渲染链，生成独立门户和独立状态，不建立融合首页。
- 完成节点由单一键索引改为“节点键 → 输入摘要 → 结果”，避免共享节点把某一
  报告载荷的完成状态误复用到另一载荷；resume 只复用摘要一致的完成节点。
- 多报告运行聚合每类报告状态、格式状态、快照、artifact manifest、review request
  与 blocker；已完成报告在另一报告等待恢复时保持字节稳定。
- 新增项目级 `yaozh answer`：初始回答仅为 `available`、`unavailable`、`skipped`，
  原子写入封闭记录；同值重放不改字节或 mtime，改答、篡改、跨项目、损坏文件和
  软链接失败关闭；CLI 不接收账号、密码、Cookie 或 token。
- 修复 fresh B/C 双重穷尽终态：先闭合 `report_evidence`，再发布 blocker；运行
  manifest 可按对应报告 research-package 摘要校验并重复 resume。
- 修复已有数值但来源等级不足时的缺口状态转换：保留合法穷尽状态，不把
  `reported_value` 填入封闭缺口枚举。
- package command catalog 从 9 项同步为 10 项，bundle final-content 纳入 Yaozh
  模块；公开 Skill 和三份 canonical 计划/设计文档同步当前能力及未完成边界。

## 会商与实现裁决

- 采纳 worker_01 的逐报告复用框架，但不接受其隔离副本中的 `git stash/pop`
  操作作为项目方法；主工作树始终保留用户脏树。
- 采纳 worker_02 的封闭项目记录和独立命令，拒绝其无必要 JSON 全文件格式重排；
  只合并 catalog 的语义变化。
- 采纳 worker_03 的 D1/D2/G3；D1/D2 已修复并用动态端到端测试钉住，G3 已由
  输入摘要索引闭合。D3 单列下一切片，未用手工清目录或放宽覆盖保护绕过。
- `session_expired` 作为后续已登录浏览器路线的访问失败回执，不是不可变初始
  Ask 的回答值。

## 决定性证据

- 双重穷尽终态聚焦集合：6 passed。
- 多报告/Yaozh/相邻项目与包合同：99 passed。
- `pytest tests/integration -q`：461 passed。
- `bash tools/gate.sh`：Ruff OK；strict mypy 208 files；v1 active 917 passed / 20
  deselected；retained compatibility 20 passed；layer audit 7 passed；legacy scanner
  OK；`GATE_OK status=quality-only steps=6`。
- 临时候选 bundle：323 files，SHA-256
  `2c937684f1c8b531797c188a702143627fbdceab11ae702b879bd4e1fd2ff053`；
  required-v12 final-content 通过；fresh-install 9 passed、1 个真实宿主显式跳过。
- 三份 worker runner receipt 均为 v2，含最终报告 `output_sha256`；
  `audit-execution` 与 `review-gate --require-verification` 均通过，无 warning/error。

## 保留缺口

- Yaozh 项目回答尚未被 capability/source planner 消费，也未实现真实已登录浏览器
  路线及 `session_expired` 回执。
- 渲染器在写出部分目录但未发布 `html.manifest.json` 时中断，resume 仍可能被
  “拒绝覆盖”保护卡住；必须做事务性修复，不能要求用户手工删除。
- 多报告中“一个证据终态 + 一个继续运行/完成”的更完整组合矩阵仍需随下一恢复
  切片扩展；当前已覆盖全完成和 A 完成/B 等待恢复。
- 逐对象 GateSpec、publication/manual 完整状态机、宇宙/缺失整体闭包、真实
  三宿主、24 门户、浏览器视觉矩阵、clean RC 和恢复冻结均未完成。

## 磁盘卫生与恢复点

guard 已把过程材料归档到
`archives/execution/ci-r2-multireport-yaozh-20260905/`，共 10 个文件、118,744
bytes。三个隔离副本删除前分别显示 5,871,420、5,858,084、5,856,960 KiB
逻辑大小；一次性 bundle 目录为 1,980 KiB，审计探针为 8 KiB。上述五个精确
目标均已删除并复核不存在；APFS 克隆逻辑大小不等于实际物理释放量，因此不做
相加释放声明。保留代码、测试、规范文档、review、metrics、checkpoint 和归档，
不清理 Codex session/database、科学原始证据、fixture、其他检查点或用户工作树。

## 下一安全动作

以 TDD 构造渲染器在目录创建后异常的真实中断，允许仅未发布、未绑定、无完成
事件的候选目录安全重建，同时保持任何已有 manifest/接受绑定严格不可覆盖；完成
后将 Yaozh 三态映射进来源规划与非阻断回执。
