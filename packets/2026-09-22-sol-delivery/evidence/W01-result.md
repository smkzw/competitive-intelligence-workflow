# W01 实施与验证证据

日期：2026-09-22  
工作包：W01 候选信任、逐事实原文与快照闭包

## 执行身份与源身份

- 用户请求模型/effort：`gpt-5.6-sol:medium`。
- 运行时回执：本会话没有可核验的 model/effort receipt；模型与 effort 身份记为 **UNVERIFIED**，不据此作已验证声明。
- 工程根：仅 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`。
- 分支/HEAD：`main` / `2df24bb441e555f20b233ad2011b4ffd3610655b`；实施结束前 HEAD 未变化。
- W00 的 13 个 tracked 修改及既有未跟踪证据均保留；本包没有 commit、push、git add、reset、checkout、clean 或删除。

## 改动范围

生产与合同：

- `migrations/0011_candidate_lineage_closure.sql`
- `schemas/evidence-snapshot-manifest.schema.json`
- `src/ci_workflow/application/fresh_research_ingestion.py`
- `src/ci_workflow/application/research_package_submission.py`
- `src/ci_workflow/application/run_service.py`
- `src/ci_workflow/application/scientific_review_transition.py`
- `src/ci_workflow/application/source_research_service.py`
- `src/ci_workflow/storage/snapshot_store.py`
- `src/ci_workflow/storage/source_derivation.py`

测试：

- 新增 `tests/integration/test_w01_trust_snapshot_closure.py`。
- 更新 `test_fresh_a_research_package.py`、`test_review_issuer.py`、`test_review_r07_ingestion_invariants.py`、`test_scientific_review_transition.py`、`test_sqlite_migrations.py`。
- 没有另造验收框架；新增反例和端到端旅程落在现有 pytest integration/migration 层。

## 合同实现

1. **候选与接受分权**：研究提交与摄取只产生 `candidate` 事实/声明及 `candidate_unreviewed` 授权状态；兼容入口也转入同一候选摄取实现。发布转换要求生产 `review_issuer` 留存的签发记录，并校验 receipt digest，嵌入包内的旧 reviewer 字段、伪时间或只换 digest 不能授权。
2. **逐事实原文**：对持久化来源字节执行无通配符精确 JSON path 或唯一文本锚点重提取，并与 `original_text` 逐字相等；根路径、URL/页码单独定位、粗字段、生成文本和不同来源字节均失败关闭。规范值作为派生记录，不替代来源原文。
3. **内容身份与冲突**：事实版本身份覆盖完整 `ResearchFact` 科学字段、来源版本和逐事实 fragment；只改科学 context 也产生新版本。同逻辑 fact ID 出现新内容时建立显式开放冲突集。source version、acquisition attempt、idempotency request 分别持久化并独立寻址。
4. **传递闭包**：v2 evidence manifest 和返回 lineage 包含采用事实关联的全部 source、source/fact fragment、fact、claim、derivation、attempt 和 receipt。新增 manifest-only restore，可在空目录重建数据库/CAS/快照并复核不可变快照身份。
5. **历史兼容**：manifest v1 字节与身份算法不补字段、不重签；迁移只扩展新列/表。既有 issuer、review transition、snapshot store、source derivation 与 migration 链被复用。

## RED 批次

命令：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/integration/test_w01_trust_snapshot_closure.py tests/integration/test_review_r07_ingestion_invariants.py tests/integration/test_source_capture_precision_ingestion.py tests/integration/test_source_to_claim_chain.py tests/integration/test_research_source_binding.py tests/integration/test_review_issuer.py tests/integration/test_scientific_review_transition.py tests/integration/test_research_package_submission.py -q --tb=short
```

结果：`13 failed, 138 passed in 4.64s`。其中 8 个为集中加入或强化的 W01 反例（候选状态、粗定位、伪原文、科学 context 身份、fragment 闭包、空目录恢复、提交授权状态、attempt/request 分离）；另 5 个为现有签发夹具固定有效期随当前日期过期，已改为确定性远期有效期，显式过期用例仍单独覆盖。

## GREEN 与决定性检查

- W01 合并批次（同上命令，最终重跑）：`152 passed in 4.82s`。
- 迁移、manifest 闭包、历史 manifest 与快照身份：
  `16 passed in 0.26s`。
- A 类产品兼容入口：`2 passed in 0.69s`。
- Ruff（W01 生产文件与相关测试）：`All checks passed!`。
- mypy `--strict`（5 个核心生产文件）：`Success: no issues found in 5 source files`。
- `git diff --check`：通过。

源到接受的新增集成旅程实际执行：真实 source bytes → research submit → SQLite candidate/derivation/attempt → v2 snapshot → 空目录恢复 → 生产 issuer 签发 → scientific review transition 接受；同旅程同时断言未签发候选不能接受。

## 关键产物 SHA-256

- migration 0011：`66d78eba168abacd0a4f8e0915820f6a9d1e29b13e7694a2a67db8cd787052f9`
- manifest schema：`8993705ab64b73950c10b173abff769a9986501bb79446fe55398e07468e52d3`
- fresh ingestion：`424ebe4c8248d28bd8b9a77603048cb37e95ee3b006a786798538ae7eb9d697e`
- review transition：`9b5d199fd9a60f30fc90ab23109d0a963538320d2f2313af8372c47064afda5b`
- snapshot store：`fe30e536beedd12d34f33733da1da952cc4ae4be74cc711526c0ac3f85180177`
- source derivation：`ac0263bbe1132b66a3495b983fa4f306d169e92e70d11d5a8b2e7a3bcc09e068`
- W01 集成测试：`85537cd4315fc46f02b006773b6de10ee6435d472570916567779104d4d4bdcd`

## 限制与未解决项

- 按工作包边界未运行全 gate、24 门户、完整浏览器、三宿主或恢复矩阵；这不是 RC、视觉、科学或产品最终接受。
- 额外兼容探测 `test_multi_report_product_run.py` 中 3 个 B/C 路径失败：旧合成夹具把 `application/json` 来源保存为非 JSON 文本，并用粗 locator/生成的“来源原文”。新生产合同按设计拒绝，未通过放宽精确定位来制造 GREEN；后续 B/C 夹具及其生产输入须改为真实可重放来源字节与逐事实 locator。
- `source_research_service` 的历史接受实现仍作为 return 后不可达代码保留供源码考古；活动兼容入口已唯一委托共享候选摄取，不能再铸造 accepted。后续可在独立清理包移除不可达历史体，不影响本包运行合同。
- 请求模型/effort 缺少运行时回执，保持 **UNVERIFIED**。

下一安全动作：并行进入 W02/W03；W07 可基于本包的新来源/片段/快照闭包开始真实来源链。B/C 生产旅程进入相应工作包前，先替换上述不可重放合成来源。
