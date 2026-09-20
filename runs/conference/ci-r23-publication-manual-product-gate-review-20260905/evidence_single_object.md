I'll start from the assigned conference context and plan, then independently audit the R2.3 publication and manual-inbox product-gate implementation against the verdict, two-strategy, and evidence-insufficiency contracts.Context is loaded. Next I’ll read the R2.3 task docs and implementation sources, then check tests against the product-gate contracts.Task docs show P1 done and later phases still open; I’ll now inspect the actual product-gate code, schemas, and tests.I already see a possible dual-authority issue around the two user-facing markdown gates; next I’ll trace research-package, run_service, schemas, and tests.The run-service insertion is confirmed; I’ll now read the exact publication-package validators, submit path, CLI unavailable flow, and the gate tests.I have enough independent evidence. The report below is advisory only; Codex remains final authority.

# Conference Output: ci-r23-publication-manual-product-gate-review-20260905 - evidence_single_object

## Output

独立只读审阅结论：**R2.3 已把 `PublicationRecord` / `ManualSupplyGate` 接到 `research submit` 与 `run_project`，但产品门尚未诚实闭合。** 最高冲击缺陷是：错文件隔离后产品 resume 无法再接受正确文件；即便正确补件被接受，受影响报告也停在伪 `running`，不会重抽取、不会恢复生成。不可得→带限制/证据不足的产品路径几乎没有运行级测试，且限制说明不会进入报告。本输出不构成最终验收。

---

### 1. 范围与方法

**Evidence**

- 初始读集：`context/ci-r23-publication-manual-product-gate-review-20260905_conference_context.md`、`plans/codex_main_venue_ci-r23-publication-manual-product-gate-review-20260905.md`。
- 合同：`.trellis/tasks/09-05-r23-publication-manual-product-gate/{prd,design,implement,checkpoint_20260905_p1_audit}.md`；`docs/specs/competitive-intelligence-workflow-design-v1.3.md` §5.2。
- 实现：`src/ci_workflow/domain/publication.py`、`domain/research_package.py`、`ingestion/publication_gate.py`、`ingestion/manual_inbox.py`、`application/publication_manual_gate.py`、`application/research_package_submission.py`、`application/run_service.py`、`cli.py`、`schemas/research-package.schema.json`。
- 测试：`tests/integration/test_v13_publication_gate.py`、`tests/contract/test_v13_intake_package.py`、`tests/integration/test_multi_report_product_run.py`；`re_request` 仅出现在 inbox 孤立测试。
- 未跑测试、未改文件、未做视觉/浏览器验收。

**Inference**

`implement.md` 的 P2–P6 仍未勾选，但代码与产品测试已存在接线。应按现码审，不按勾选状态放行。

---

### 2. 合同项对照（先给判断）

| 合同项 | 判断 | 依据 |
|---|---|---|
| 正式 verdict 唯一权威 | **部分成立** | `PublicationRecord` 是研究包层唯一正式对象；PubMed/B 类仍保留另一套 `PublicationRole` 词汇 |
| 两策略获取 | **域模型成立，产品语义弱** | 未取得时要求 ≥2 个不同 `strategy_id`；不检验策略实质不同，也不强制 retryable 失败先重试 |
| 独立复核绑定 | **域模型成立** | 分歧/边界要求独立身份、上下文、候选 SHA-256；禁止自审 |
| 单快照单次用户响应 | **gate 模型成立，产品恢复破裂** | `user_response_count` 拒绝二次回答；错文件路径会把 DownloadRequest 打进无法从产品路径恢复的状态 |
| 多报告局部暂停 | **暂停成立，恢复不成立** | A 继续、B 等待已测；接受后 B 永不恢复 |
| 原地补件 | **接受路径成立** | inode/字节保持已测；错文件后死锁未测 |
| 不可得分流 | **模型层成立，产品层未证明** | `mark_publication_files_unavailable` 有单测；`run_project` 无 limited/insufficient 集成测，限制不进报告 |
| 证据不足终态 | **半成品** | 会写 `blockers/*/v1/audit.md` 且不生成门户；内部详审包与用户简页未分离 |

---

### 3. 可执行缺陷清单

严重度：`correctness` = 合同/状态机错误；`honesty` = 产品结局对用户不诚实；`coverage` = 缺负向证明；`enhancement` = 可延后。

#### D1. [correctness] 错文件隔离后，产品 resume 无法接受正确文件

**Evidence**

- `scan_and_process_inbox` 无合法目标时，若状态是 `awaiting_user`，会迁到 `needs_re_download`（`manual_inbox.py` 约 1106–1135）。
- 已声明迁移没有 `needs_re_download → file_detected`（约 45–68）。
- 再次放入合法文件时，`detect_file` 触发 `UndeclaredTransitionError`，被吞掉并原样返回（约 1087–1098）。
- `re_request()` 只在 `tests/integration/test_manual_inbox_recovery.py` 与 `test_download_request_transitions.py` 被调用；`publication_manual_gate.py` / `run_service.py` / `cli.py` 均不调用。
- P5 明确要求覆盖错文件、扫描件、登记号不一致。产品测试只有一次正确 PDF 的 happy path。

**Inference**

同一快照的“一次中断”在文件层被切成不可恢复状态。用户按清单放入错文件后再放正确文件，`--resume` 会永远 `awaiting_user`。

**Recommendation**

产品路径不要把 DownloadRequest 打进需要 `re_request` 的状态。隔离文件即可，请求保持 `awaiting_user`，直到 gate 收到唯一响应。或在 `scan_and_process_inbox` 发现新文件前自动 `re_request`，且不得新开用户 gate。加集成测试：错 PDF → 隔离 → 正确 PDF → `accepted`。

#### D2. [honesty] 正确补件被接受后，报告停在伪 `running`，不重抽取、不恢复

**Evidence**

- 接受后 `run_service.py` 约 1576–1578 把受影响报告放入 `manual_blocked_reports` 和 `manual_re_extraction_required`。
- 随后约 2520–2541：命中该集合就 `continue`，不执行 `_execute_research_*`。`manual_state` 在有 `manual_re_extraction_required` 时设为 `"running"`。
- `test_multi_report_product_run.py` 约 600–614 断言第三次、第四次 `run_project` 都是 `outcome == "running"`，且 gate 字节不再变。
- `accept()` 只把重抽取任务写入 `receipts/re-extraction-jobs.jsonl`（`manual_inbox.py` 约 1612–1631）；`run_service` 不消费这些 job。
- CLI：`running` 文案是“证据采集工作正在进行中”，exit 0（`cli.py` 约 436–438；`run_service.py` 约 3607–3611, 3626）。

**Inference**

这不是测试过严，而是实现把“已接受、待恢复”做成了终态假进度。v1.3 §5.2 与 design 要求接受回执驱动重抽取并恢复受影响报告。当前用户会看到成功接受 + 永久采集中。

**Recommendation**

接受后必须消费重抽取 job，把新来源版本绑进受影响报告科学载荷/抽取层，再走原报告门。在完成前 outcome 应为可审计的恢复态，而不是通用 `running`/exit 0。测试应从“停在 running”改为“B 恢复生成或明确 `recovery_required` 且二次 resume 有进展”。

#### D3. [correctness] 生产者可在提交期写 `official_evidence_sufficient` / `evidence_insufficient`，跳过用户门

**Evidence**

- `manual_supply_required` 仅当 `acquisition_disposition == "manual_required"`（`publication.py` 约 287–289）。
- 未取得的必需论文只要两策略尝试，就可以是 `official_evidence_sufficient` 或 `evidence_insufficient`，不必 `blocking_fields`（约 253–274）。
- `assert_gate_ready` / `assert_product_handoff_ready` 不检查 publication 获取处置（`research_package.py` 约 908–973）。
- `run_project` 只对 `manual_supply_required` 物化 gate（`publication_manual_gate.py` 约 110–114）。
- v1.3：用户一次确认不可得之后，才按官方证据是否足够分流。

**Inference**

宿主可以把“用户确认不可得”提前写进研究包，从而不询问用户、不标注限制、甚至在 `evidence_insufficient` 时仍生成报告。

**Recommendation**

提交期禁止未经过用户响应的 `official_evidence_sufficient` / `evidence_insufficient`。这两态只能由 `record_user_response(file_unavailable, ...)` 写入。包内未取得的必需论文只能是 `manual_required`。

#### D4. [honesty] “带限制继续”不把限制写进报告

**Evidence**

- `limitation_zh` 只进入 `ctx.runtime_metadata["publication_limitation_zh"]`（`run_service.py` 约 1582–1583）。
- 全仓无其他消费者（检索仅 cli/gate/run_service）。
- 产品测试没有 unavailable/limited 的 `run_project` 路径。
- v1.3：官方证据足够时“继续生成报告并明确标注限制”。

**Inference**

CLI 可记录限制并 resume，报告仍按无缺口生成。这是假完整。

**Recommendation**

limited 路径必须把中文限制写入受影响报告快照/门户可见位置，并禁止无限制文案的 HTML。补 `run_project` 测试：`publication unavailable --official-evidence sufficient` 后 B 生成且含限制；`insufficient` 后无 `reports/B/**/html`，有简洁证据不足页。

#### D5. [correctness] 用户可见门不唯一

**Evidence**

- `materialize_publication_manual_gate` 写 `logs/manual-supply-request.md`（约 198–201）。
- 同一次 `create_request` 重写 `logs/download_requests.md`（`manual_inbox.py` 约 858–859, 631–649）。
- 宿主仍从 `download_requests.jsonl` 投影 `manual_inbox_pending`（`hosts/base.py` 约 163–183）。
- v1.3 / PRD：只建立一个 Markdown gate。
- 接受后 `to_markdown()` 仍列出“请放入”，`materialize` 在 replay 时按当前 gate 重写该文件（`publication_manual_gate.py` 约 198–201）。

**Inference**

用户会看到两份清单；错文件后 inbox 列表与 snapshot 清单可能分叉。接受后主清单仍在要文件。

**Recommendation**

`logs/manual-supply-request.md` 为唯一用户权威。`download_requests.md` 改为内部派生或删除。接受/不可得后改写为“已记录一次性回答，本快照不再要求补件”。

#### D6. [correctness] `blocking_fields` 与 GateSpec 关键单元未在 verdict 层对齐

**Evidence**

- `PublicationRecord` 接受任意非空字符串；合同测试用 `"主要疗效"`（`test_v13_intake_package.py` 约 329；`test_v13_publication_gate.py` 约 65, 161）。
- 产品路径 `create_request` 要求字段 ∈ 批准 YAML 的 critical `unit_id`（`manual_inbox.py` 约 796–803）。B 的疗效单元是 `b_core_efficacy_endpoint`（`policies/gates/B-v1.yaml` 约 170）。
- `materialize` 用字段前缀猜报告，否则取 `affected_reports[0]`（`publication_manual_gate.py` 约 119–131）。
- `run_project` 只捕获 `PublicationManualGateError`，不捕获 `RequestNotRequiredError`（`run_service.py` 约 1555–1562）。

**Inference**

中文字段名可通过提交，运行时创建请求失败，且以未映射异常冒出，而不是合同错误。多报告论文若 blocking 字段无 `b_`/`a_` 前缀，可能挂到错误报告的 GateSpec。

**Recommendation**

在 `PublicationRecord` / 研究包校验强制 `blocking_fields` 为所选报告的 critical unit_id，且与 `affected_reports` 前缀一致。`RequestNotRequiredError` 必须升级为 `PublicationManualGateError`/`ContractConfigError`。

#### D7. [coverage] 不可得、篡改、错文件、扫描件的产品路径未测

**Evidence**

- `test_multi_report_product_run.py` 只有 pause + 正确 PDF + 停在 `running`。无 `publication unavailable`、无错文件、无 gate JSON 篡改、无扫描/无文本 PDF。
- `test_v13_publication_gate.py` 的 unavailable 测试手写 `state/manual-supply-gates/snapshot-1.json`，不经过 `run_project`。
- `_write_publication_evidence_insufficiency`（`run_service.py` 约 3200–3232）把短文案同时写成 `audit.json` 与 `audit.md`，与“内部详审包 + 用户简页”合同不符。

**Recommendation**

补最小负向矩阵：错文件死锁、接受后恢复、sufficient 限制可见、insufficient 无门户、gate 身份漂移拒绝、扫描 PDF 隔离。证据不足页与内部 blocker 审计分离。

#### D8. [correctness] 两策略只检查 `strategy_id` 字符串不同

**Evidence**

- `publication.py` 约 264–270：`len({strategy_id}) < 2` 才失败。
- retryable 集合（网络/限流/验证码/解析/能力缺口/截断）不必在转 `manual_required` 前重试。
- JSON Schema 对必需论文只要求 `fetch_attempts.minItems: 1`，不要求两策略（`schemas/research-package.schema.json` 约 142–150）。

**Inference**

宿主可写 `publisher-1` / `publisher-2` 两次同类失败，或两次超时后直接人工门。Schema 与 pydantic 不一致，schema-only 校验会放行。

**Recommendation**

Schema 与域对齐：未取得时 `minItems: 2` 且 `strategy_id` unique。至少要求两个 `result_class` 或两个 source family。retryable 未穷尽不得 `manual_required`。

#### D9. [coverage] 提交不强制“适格试验必须有必需论文裁决”

**Evidence**

- 有 publication 来源时，必须 1:1 绑定 `PublicationRecord`（`research_package.py` 约 733–740）——这项是对的。
- 无 publication 来源的 B/C 包可通过 `assert_gate_ready`。v1.3 §5.2：登记关联主要/延长期/关键安全论文必须检查。

**Inference**

省略论文来源即可绕过整座 publication 门。

**Recommendation**

对进入核心比较的 included trial，提交期要求 registry-linked 必需论文的逐篇 verdict，或类型化“已检索无登记关联论文”回执。禁止沉默缺席。

#### D10. [honesty] 用户文案泄漏内部快照定位符；awaiting 未写入报告图

**Evidence**

- `to_markdown()` 含 `快照：{snapshot_id}`（`publication_gate.py` 约 282）。snapshot_id 是审计包 SHA。
- awaiting 路径只写 `runtime_metadata["report_states"]`，不走 `g_report_collecting_awaiting_user`（对比 evidence_blocked 会调用 `_drive_report_transitions`）。

**Recommendation**

用户 Markdown 去掉内部摘要/快照号。受影响报告应走图上 `awaiting_user`，恢复走 `recovering`，以便清单与事件可审计。

---

### 4. 已成立、不应回退的部分

**Evidence**

- 分歧/边界必须独立复核，自审与过期 digest 被拒（`publication.py` 约 229–250；`test_v13_publication_gate.py` 约 87–140）。
- 综述/ad hoc 默认排除且不得获取（`publication.py` 约 275–276）。
- 必需且未取得必须有获取尝试与受影响报告。
- 同一 `snapshot_id` 文件 + `_gate_identity` 漂移拒绝（`publication_manual_gate.py` 约 187–194）。
- 多报告：A 生成、B 等待、二次 resume 不重问（`test_multi_report_product_run.py` 约 571–588）。
- 正确 PDF：内容匹配、原地 `os.replace`、inode 不变（同文件约 590–609；`manual_inbox.py` 约 1600–1604）。
- `file_received` 无回执不可 `accepted`（`publication_gate.py` 约 214–218, 240–244）。
- 二次 `file_unavailable` 失败关闭（`test_v13_publication_gate.py` 约 288–294）。
- PubMed `PublicationRole` 未写入 `ResearchPackage` 权威字段；来源分类必须等于正式 `publication_class`。

这些应保留。缺陷在接线与终态，不在分类器骨架。

---

### 5. 最高冲击异议

**异议：** 现有集成测试把“接受后永远 `running`”写成绿灯，会把 P4 未完成伪装成产品门完成。`38 passed` / `510 passed` 不能证明 R2.3 验收项。

**替代：** 把 D1 与 D2 定为放行阻断。在修好前，`implement.md` 不得把 P3/P4/P5 标完成，也不得发 RC。

**挑战的假设：** “DownloadRequest 六态可原样接入唯一用户门”。六态含 `needs_re_download` 与 `re_request`，与“单快照一次用户响应”冲突。Snapshot gate 应是唯一用户中断；inbox 只做文件核验/隔离/原地改名。

---

### 6. 给 Codex 的决策点

1. **接受后的 `running`：** 视为 P4 未完成（本审默认），还是故意的中间态？若是后者，必须改用户文案，且禁止 exit 0。
2. **错文件：** 保持 `awaiting_user` 只隔离文件，还是自动 `re_request` 且不算第二次用户询问？
3. **包内 `official_evidence_sufficient`：** 提交即非法，还是仅宿主预声明、仍必须过用户确认？
4. **`blocking_fields`：** 是否立即改为 GateSpec `unit_id` 合同？中文标签只出现在用户 Markdown。
5. **B/PubMed `PublicationRole`：** 本轮只保持“信号、非权威”，还是要与 `PublicationClass` 做词汇映射门？

---

### 7. 需要 Codex 回答的有界问题

1. 本审是否把 D1+D2 作为 R2.3 放行否决项？这决定后续是修接线还是先改测试语义。
2. `publication unavailable` 的 `--official-evidence` 是否允许纯操作者声明，还是必须由确定性规则对照登记/监管证据计算？当前 CLI 信任旗标，产品不能证明“官方足够”。
3. 证据不足终态是否必须沿用 `blockers/{report}/v1/audit.{json,md}` 这条既有阻断包路径？短页写进该路径会与详审包撞车。

**Safe provisional path：** 在 Codex 回答前，不宣称 R2.3 产品门完成；保留现有分类/gate 模型；禁止把“接受后 running”解释为恢复成功。

---

### 8. 类别收口

| 类别 | 内容 |
|---|---|
| **Evidence** | 上列文件:行与测试断言。未执行测试命令。 |
| **Inference** | 产品门接线存在，但恢复、不可得、唯一用户面、限制可见性未闭合。测试在奖励不完整接线。 |
| **Recommendation** | 先修 D1/D2/D3/D4；同步改测试与用户面；D8/D9 作为提交合同加固。 |
| **Uncertainty** | 未验证 live CLI catalog、fresh-install bundle、真实期刊 PDF、图状态机在 awaiting 下的 coordinator 行为。`implement.md` 未勾选与代码已接线之间的任务状态以代码为准。 |

**不宣称最终临床/监管/视觉/当前 Web 权威。Codex 保留最终验收。**
