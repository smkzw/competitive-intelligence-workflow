# 第 5.2 步独立复核第 3 轮

继续同一个 Luna 验证会话，保持只读，不修改仓库。第 2 轮的 REVISE 已由原执行会话修复；当前报告为 `runs/execution/ci_phase5_task52_execution/worker_03_round3.md`，但仍以代码与可运行反例为准。

Codex 本地复跑：166 个第 5.2 单元、257 个 A 类联合、474 个关键证据交叉、105 个合同/快照测试通过；目标 Ruff 与 strict mypy 通过。

请原样重跑你第 2 轮所有 ACCEPTED 攻击，并新增检查：

1. `analysis.report_ready=False` 时 8 个 build 和 8 个 authoritative 入口是否全部拒绝；分析/日志对象本身仍可存在。
2. locked 的 sha/path/byte_size/snapshot_id、manifest contract_version/data_cutoff、project contract 版本/截止时间任一篡改均拒绝；确认校验重算和 store.read 没有循环信任。
3. model_copy/model_construct 伪造 AProjectContract、ApplicableUniverseSnapshot、GateEvidenceBinding、RegistryResultsPostedEvidence、ScientificLineageRegistry/AtomicFactVersion/fragment 后，公共构建器是否真正使用重新验证返回值，而不是验证后继续用原对象。
4. AV04–AV08 所有展示值与原子事实规范串不一致时拒绝；疗效/安全数值、单位、分母等不一致时拒绝。尝试合理空格、NFKC 与日期格式边界，判断是否误拒绝真实等价值或接受语义漂移。
5. 当前 registry 已有 AV04–AV08 事实时，dossier/专项视图漏传任一记录或重复同一 fact_version_id 必须拒绝；registry 没有对应事实时合法空模块是否可生成，不得无条件强迫非适用扩展信息。
6. EARLY_DECISION 必须有 trial entity 的 study_role 事实并只映射 SPECIAL_CORE；OTHER_ELIGIBLE 必须有独立“其他适格”事实；缺证据默认排除。
7. 两个 event_id 复用一个事实、一个事实原文与事件类型冲突均拒绝。
8. 用户文本 Gate/BackendState/back-end/零宽/全角/model-copy 拒绝；合理医学英文与 aggregate 等非工程词通过。检查中文文本 NFKC 后展示是否被意外改变到不自然。
9. `compute_locked_snapshot` 与 `SnapshotStore._lock/read` 的正向输出完全一致；现有快照兼容性和确定性不回归。

输出 PASS 或 REVISE。若 REVISE，仅列真实可运行 P0/P1/P2 反例：符号、构造、实际、预期、未捕获原因。若 PASS，列出实际执行的关键攻击及拒绝结果。不要修改文件。
