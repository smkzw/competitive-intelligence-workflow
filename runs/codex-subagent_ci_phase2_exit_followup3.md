# Phase 2 独立科学数据验收（最终窄复核）

## 结论

**PASS。P0=0，P1=0，P2=0。**

本结论仅表示 Phase 2 科学数据合同可接受，不覆盖 Phase 3、真实全量竞品调研或报告质量。

## 执行证据

- 父 Codex 可写环境正式 Phase 2 套件：**61 passed**。
- 全库：**188 passed**；Ruff、strict mypy、包校验、`git diff --check` 均通过。
- 本隔离只读环境执行指定命令：26 passed，8 个 `tmp_path` 测试因临时目录不可写而在 setup 阶段失败；原因是环境权限，不是科学断言失败。
- 不含临时目录依赖的合同、路线、微信和中国来源测试：**22 passed**。
- 未修改文件，未进行安全测试。

## 六项反例结果

1. **路线回执与尝试逐字段不一致：已闭合**

   使用相同回执 ID，分别篡改 `result_class`、策略单元、实体、缺口和声明域，五种情况均被拒绝，错误为“路线尝试内容与来源审计回执不一致”。

   位置：[planner.py:68](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/planner.py:68>)。

2. **技术错误伪造恢复穷尽：已闭合**

   - 未完成策略附技术回执：拒绝；
   - 恢复轮次夹带未声明孤立回执：拒绝；
   - 技术回执作为已声明策略执行时，`is_saturated` 为 `False`；
   - 因此不能借无关 `not_found` 单元包装为两轮科学穷尽。

   位置：[retries.py:104](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/retries.py:104>)、[retries.py:155](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/retries.py:155>)。

3. **公众号短子串定位：已闭合**

   定位必须等于已保存正文中的完整非空段落；短子串测试被拒绝。原始微信链接、身份、正文摘要和账号角色约束仍有效。

   位置：[authoritative_wechat.py:156](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/connectors/authoritative_wechat.py:156>)。

4. **中国登记自然日时区：已闭合**

   `calendar_day` 使用 UTC `00:00` 的构造被拒绝；只有北京时间 `+08:00` 零点可接受。

   位置：[china_registries.py:319](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/sources/connectors/china_registries.py:319>)。

5. **声明绕过科学证据注册表：已闭合**

   - `context={"accepted_facts": (...)}` 被拒绝；
   - 空注册表不能接受伪造事实；
   - 声明工厂要求受控 `ScientificLineageRegistry`；
   - 候选事实只能通过 `accept_candidate_fact()` 进入注册表。

   位置：[claims.py:117](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/domain/claims.py:117>)、[lineage_registry.py:102](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/capabilities/lineage_registry.py:102>)。

6. **伪造重开片段或注册表：已闭合**

   直接构造 `VerifiedEvidenceFragment` 或 `ScientificLineageRegistry` 均被受控构造令牌拒绝。正式重开路径会从 SQLite 重读片段、来源版本和内容寻址正文，并拒绝正文中不存在的伪片段；父环境正式测试已通过。

   位置：[extraction_normalization.py:43](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/capabilities/extraction_normalization.py:43>)、[lineage_registry.py:21](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/capabilities/lineage_registry.py:21>)、[content_store.py:331](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/storage/content_store.py:331>)。

## Phase 3 边界

六项 P1 均已闭合，当前无 Phase 2 科学数据合同阻断项。后续 Phase 3 仍需独立验收真实全量调研、报告生成和用户-facing 质量；这些不属于本次 PASS。