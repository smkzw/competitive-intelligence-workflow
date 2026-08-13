# Task 3.7 最终独立续审（沿用同一 Luna 会话）

继续同一 Luna 会话，只读，不新开会话，不读取执行者材料或主代理结论。

上轮剩余 `P0=1; P1=2`。请攻击当前差异：

1. 普通调用者能否经任何公开 EventStore/GraphExecutor API签发或追加 `scientific_qc.authorization.issued`；攻击者计算完全正确的 payload、boundary_proof_digest、event_id、idempotency_key 后，公共 append 也必须在存储前拒绝。真实 `apply_scientific_qc_verdict` 路径必须通过。说明 Python 私有符号不是敌对进程安全边界，本任务只验公共 API 溯源正确性。
2. 授权是否一次性消费并绑定 scientific_qc 入口代次：精确同请求重放通过；恢复后用新 request ID 重用旧授权拒绝；检查点/全量重放一致。
3. 生产边界是否按打包 Draft202012 Schema → Pydantic → 语义校验顺序真实执行；嵌套 SourceRef locator 重复/错绑、语义 ID 重复、精确定位缺失均须在授权写入前拒绝。
4. wheel 是否真实包含 `ci_workflow/schemas/scientific-qc-verdict.schema.json`，隔离安装后生产解析器能加载；根目录合同与 wheel 副本逐字一致。
5. 重新确认此前已关闭的候选完整摘要、GateSpec/criteria 版本、三路径矛盾、无草稿/无下游产物、typed output。

运行精确攻击、关联 event/gate/graph/replay、Ruff、strict mypy、package/schema、wheel 隔离验证、diff、全量 pytest。不得修改文件。

首行严格为 `PASS; P0=0; P1=0; P2=<n>` 或 `FAIL; P0=<n>; P1=<n>; P2=<n>`。P0/P1 阻断，P2 不阻断。给精确行号与复现结果，返回完整执行报告。
