# Phase 2 独立科学数据验收（第二次修复复核）

## 结论

**FAIL。P0=0，P1=6，P2=0。**

正式机械证据和正向 fixture 链均通过，但仍存在可执行的科学数据合同绕过，因此不满足 PASS 条件。

## 执行证据

- 指定最小套件：**39 passed in 0.15s**。
- 父 Codex 提供：Phase 2 套件 60 passed、全库 187 passed、Ruff、strict mypy、包校验均通过。
- `git diff --check`：未发现 diff 错误；本隔离环境仅产生 macOS `xcrun` 缓存权限警告。
- 未进行安全测试，未修改文件。
- `source_to_claim_chain` 正向 fixture 测试通过；父 Codex 提供的官方 API 核对与 NCT02912468 fixture 数值一致。

## 逐项反例结果

1. **路线尝试与来源回执可不一致 — P1**

   `RouteProgress.complete()` 仅按 receipt ID 与 attempt ID 集合对应，未校验对应的 `result_class`。构造“尝试结果为未找到、来源回执为其他结果”的不一致组合仍可完成路线。

   位置：[planner.py:61](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/planner.py:61>)。

2. **恢复饱和仍可忽略技术错误 — P1**

   两个技术错误作为已完成策略单元时，原漏洞已修复；但：

   - 未完成策略单元的技术回执不会阻止 `is_saturated()`；
   - `RecoveryRound` 未强制 `receipt_ids ⊆ strategy_unit_ids`，孤立技术回执可被塞入恢复轮次；
   - 由无关的 `not_found` 单元满足饱和条件后，孤立技术回执可被包装成替代路径和穷尽证明。

   直接复现结果：`incomplete strategy + technical receipt -> is_saturated=True`；孤立技术替代回执构成的穷尽证明被接受。

   位置：[retries.py:112](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/retries.py:112>)、[retries.py:155](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/retries.py:155>)。

3. **公众号定位仍可使用非完整短句 — P1**

   当前只要求定位正文长度不少于 8 个字符且为正文子串。构造定位 `"正文中披露了第2"` 被接受；它不是完整短句，不能保证同一内容重开时的科学定位稳定性。

   位置：[authoritative_wechat.py:156](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/connectors/authoritative_wechat.py:156>)。

4. **中国自然日日期未强制北京时间 — P1**

   `calendar_day` 仅校验时间为零点，直接构造 `UTC 00:00` 的中国试验首次披露记录仍被接受。自然日截止可能因此发生 8 小时边界误纳，未满足保守日期合同。

   位置：[china_registries.py:315](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/connectors/china_registries.py:315>)。

5. **声明模型可接受调用方伪造的科学证据上下文 — P1**

   无 validation context 时已正确拒绝；空 lineage registry 的工厂路径也已拒绝。但调用方可自行构造一个伪造的 `AtomicFactVersion`，通过 `context={"accepted_facts": (...)}` 直接让 `ClaimVersion.model_validate()` 接受未注册事实。

   位置：[claims.py:117](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/domain/claims.py:117>)。

6. **Lineage Registry 可接受未经真实重开的伪造片段 — P1**

   调用方可直接构造 `VerifiedEvidenceFragment`，不经过实际 locator 重开/校验流程，然后放入 `ScientificLineageRegistry`；竞品宇宙闭合会接受该片段。因而“已登记并真实重开”的证据要求仍可被对象构造绕过。

   位置：[lineage_registry.py:47](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/capabilities/lineage_registry.py:47>)、[ontology_universe.py:273](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/capabilities/ontology_universe.py:273>)。

## 已闭合的原问题

以下反例已被当前修复拒绝：

- 单次 `not_found` 直接结束路线；
- `route_not_applicable` 或 `route_access_blocked` 遗漏政策必查单元；
- 两轮均为技术错误却直接声称科学穷尽；
- 恢复/替代路线缺少完整 `SourceVersionRecord`；
- 微信定位链接与原文链接不一致；
- 中国试验或 CDE/NMPA 使用非官方域名；
- 无科学证据上下文直接创建声明；
- 竞品宇宙使用伪造字符串片段 ID；
- 来源版本内容路径与摘要不一致；
- NCT02912468 官方 fixture 的 276、两组背景治疗、-0.45/-1.34、133/143、2019-07-25、PMID 31543428 及度普利尤单抗/糠酸莫米松边界链通过。

## 缺陷

六项 P1 均属于可执行的科学来源、恢复、定位或 lineage 信任边界缺陷，不是测试噪声，也不能由正向 fixture 通过抵消。

## 进入 Phase 3 前动作

在进入 Phase 3 前必须：

- 强制逐字段比对 route attempt 与 source receipt，包括结果类别、策略单元、实体、缺口和声明域。
- 禁止恢复轮次存在孤立回执；饱和必须覆盖每个政策必查单元，且实际完成、实际回执和结果类别一致。
- 公众号定位改为完整句/完整段落或稳定 offset 加正文哈希，不能只接受短子串。
- 将中国自然日统一解释为北京时间，或持久化明确的日期不确定区间并按保守截止处理。
- 禁止调用方伪造 `accepted_facts` validation context；声明只能从 lineage registry 的受控工厂生成。
- 让 `VerifiedEvidenceFragment` 只能由真实 locator 重开校验产生，并使 registry 能验证该来源，而不是信任可直接构造的对象。

修复后需为上述六项分别增加回归测试，并重新执行 Phase 2 套件和全库验证。当前结论**仅覆盖 Phase 2 科学数据合同，不覆盖真实全量竞品调研、Phase 3 或报告质量**。