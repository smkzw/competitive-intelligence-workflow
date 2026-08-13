# Task 3.7 独立复审第二次续审（同一 Luna 会话）

继续你自己的既有 Luna 会话，不新开会话。仍然只读，不读取执行者提示词、执行者报告、日志、会议记录、主代理结论。

上一轮你判定 `FAIL; P0=3; P1=2; P2=1`。请直接检查当前差异是否真实关闭：

1. 科学质控授权现在是 `scientific_qc.authorization.issued` 图事件，迁移消费并在重放时核验。必须主动攻击：普通调用者能否直接调用公开签发方法或自行追加一条形状正确的授权事件，再完成伪造迁移。如果所谓“边界签发”仍只是换了一个公开自填入口，判 P0；如果公共执行接口能机械区分边界发行与普通调用，则验证其项目/运行/对象/from/to/evidence digest/一次性或重放语义。
2. `ReportGateResult` 是否绑定当前候选快照完整内容摘要并纳入 result_key；同 ID、同 universe_summary、内容变化必须拒绝。
3. 科学质控标准版本是否与产生 GateResult 的 GateSpec 版本绑定；错配必须拒绝。
4. accepted/recoverable/exhausted 三路径所有矛盾组合是否失败关闭。
5. JSON Schema 与运行时语义校验是否诚实覆盖语义唯一、精确定位与跨数组引用，是否实际进入正式验证路径，而不只是存在一个未调用的帮助函数。
6. P2 文档路径：核验仓内 `docs/specs/competitive-intelligence-workflow-design-v1.2.md` 是批准设计书的锁定副本；实施计划若确实由工作区外的批准计划驱动，路径缺失只作非阻断记录，不把它误判为产品功能缺陷。

重新运行上轮攻击与新攻击、精确测试、关联 gate/graph/replay 回归、Ruff、严格 mypy、schema/package、diff、全量测试。不要修改文件。

结论首行严格：
- `PASS; P0=0; P1=0; P2=<n>`
- `FAIL; P0=<n>; P1=<n>; P2=<n>`

给出复现命令、观察结果、精确行号。任何 P0/P1 阻断，P2 不阻断。返回完整执行报告，不要只给计划。
