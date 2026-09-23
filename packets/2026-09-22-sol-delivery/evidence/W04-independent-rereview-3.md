verdict: FAIL

# W04 第三次 FAIL 返修后第四次独立只读复审

## model / effort

- 请求运行时：`gpt-5.6-sol:medium`。
- 核验结果：**UNVERIFIED**。本会话没有可核验的 runtime model/effort 回执；未猜测、未静默替换。
- 边界：全新上下文、单一只读复审者；只在英文工程执行命令，唯一持久写入为本报告；未联网、未派子代理、未进入 W05，未修改产品、测试、既有证据或 STATUS，未执行 commit/push/add/reset/checkout/clean/delete。

## 总结

第三次 FAIL 后的两项主修复均有实质进展：

1. `ActiveFactBinding` 已覆盖 report/collection/row、product/drug、trial/registry、group/arm/cohort/period、endpoint/event、statistical form、measure object、unit/normalized unit、source version/pointer、original-row digest；A/B/C 在创建 staging 前统一复算并严格比较。既有 stale row、同 row 异 product/drug/trial/group/arm/cohort/period/event/form/unit/source/digest、跨报告错绑反例均失败关闭，且失败保持 selector、generation 与公开输出不变。
2. `reports/current.json` 已改为稳定无 revision 协议描述符；generation 先 file/directory fsync，随后由 SQLite `synchronous=FULL` 的单事务 committed selector 发布。生产源码未发现直接解析旧 revision pointer 的旁路；generation/DB/event/journal 普通故障保持旧 selector，提交结果无法分类时使用显式 indeterminate 错误，不再依赖覆盖后 rollback pointer。

但 W04 仍不能通过，原因不是 W05 视觉密度，而是两项 W04 证据/来源合同缺陷：

1. C 原 builder 在投影用户修订时把用户值重新写成 `source_text`，并把完整 canonical source locator 字符串塞进 `source_locator.field_path`。v5 DB 中原 evidence fragment 仍是“至少16分”及原 ClinicalTrials.gov locator；最终 C 门户却把用户修订 `<=18.0分` 标成 ClinicalTrials.gov 的“登记原文，未译”，且 A/B/C 受影响页面均未显示“用户修订，未独立复核”。这是实际来源显示污染与错误归因，不是单纯文案问题。
2. v5 evidence manifest/verifier 未把三份 `state/user-fact-builder-inputs/report-*-data.json` 列为 source/artifact，也未校验 generation 中声明的 `builder_input_sha256`。不落盘内存篡改 A builder 输入的 `indication` 后，v5 verifier 仍返回 `error_count=0`；同一篡改由生产 canonical reader 正确拒绝。因此“13源/39工件/verifier 0 error”尚不能证明冻结 builder 输入未漂移，现有 tamper probe 只改 manifest 第一项 artifact SHA，覆盖不足。

本 FAIL 仅否定 W04 工程风险闭包；不扩展为全 gate、24 门户、W05 四视口、三宿主、科学/医学/产品/用户或 RC 结论。

## 缺陷表

### P0

0。

### P1

#### P1-01 — 用户修订被写成并展示为登记原文，来源定位同时被破坏

- 文件:行：`src/ci_workflow/renderers/portal/report_c.py:2013-2037,2049-2064`；`src/ci_workflow/renderers/portal/active_fact_projection.py:172-175,178-217`；`packets/2026-09-22-sol-delivery/evidence/W04-remediation-real-portal-v5-final/runtime-journey-browser.json:6-28,39-43`。
- 复现：
  1. v5 DB 只读查询显示 base 与 user_modified 两个 `fact-c-threshold` 版本继续引用同一原 fragment；fragment 内容为 `入选标准阈值为至少16分。`，locator 的 `field_path` 为 `protocolSection.eligibilityModule.eligibilityCriteria`，source version 为 `ctgov-nct04178967-20230524`。
  2. 浏览器旅程把该值从 `>=16.0 分` 改为 `<=18.0 分`，只重建 C（runtime journey 第 6–14 行）。
  3. 最终 `report.js` 的同一 observation 变成 `source_text="inclusion_criterion：<=18.0 分。"`，而 `source_version_id` 仍是原 ClinicalTrials.gov 版本；`source_locator.field_path` 变成整段 canonical locator JSON 字符串。
  4. 最终 `inclusion-criteria.html` 的 evidence view 将该文本作为 `original_text`，截图 `04-c-original-consumer-easi-18.png` 的抽屉明确显示来源版本 ClinicalTrials.gov、值 `EASI ≤18.0分`、并标注“登记原文，未译”。该页面中 `用户修订`、`未独立复核`、`user_modified` 三个提示的出现次数均为 0。
  5. 源码原因是 C projection 用用户修订构造 `narrative` 后直接写入 `source_text`，并执行 `locator["field_path"] = fact.source_locator`；后者不是原 field path，而是 `canonical_source_pointer()` 产生的完整 locator JSON 字符串。
- 影响：用户修订值被错误归因给原登记来源；原始 quote/locator 虽在 DB 内未变，却在真实消费者和来源抽屉中被合成值替代。receipt/DAG 只记录“命中了正确原行”，没有阻止输出端把 user_modified 伪装成 source original。违反 PRD“来源原始值保留、用户修订未独立复核明确展示”、W04 图/表/叙事/来源指针同步及“不能再发生合成事实污染”。
- 建议：投影层分离 `displayed_user_value`、`review_state/user_edit provenance` 与不可变 `source_text/source_locator/source_version`；不得改写 evidence view 的 `original_text`。C 页面同时显示用户修订值、`用户修订，未独立复核`、原登记原文及原定位。B 的 evidence-view 投影也应复核 `original_definition`/locator 是否被用户 narrative 覆盖；A/B/C 增加 portal-level 反例，断言来源原文和 locator 字节保持原值。

### P2

#### P2-01 — v5 verifier 对未绑定 builder 输入可产生假阴性

- 文件:行：`tools/build_w04_v5_evidence.py:31-45,273-312`；`tools/verify_w04_v5_evidence.py:97-115,141-167,219-264`；`src/ci_workflow/application/latest_delivery.py:187-197,414-439`。
- 复现：对 `.../w04-project/state/user-fact-builder-inputs/report-a-data.json` 仅在内存中把 `indication` 改为 `TAMPERED-UNBOUND-BUILDER-INPUT`，SHA-256 从 `8460ff9a...b503b3` 变为 `d5ffc7a4...4f8e94`。调用同一 `verify()` 返回：

```text
verifier_error_count=0
errors=[]
```

  对同一内存篡改调用生产 `read_current_delivery()` 返回：

```text
ValueError: 当前交付builder输入绑定不一致
```

  原因是 build manifest 的 13 个 source inputs 和 39 个 artifacts 都不含三份 builder 输入；verifier 虽读取 builder 输入重算目标 binding，却不比较 `CurrentReportDelivery.builder_input_sha256`，因此不影响目标行身份的任意输入漂移可绕过清单。现有 `--tamper-check` 只把 manifest 第一项 artifact SHA 改成零，不能覆盖该缺口。
- 影响：v5 清单无法完整绑定实际 builder 输入，`checked_artifacts=39 / error_count=0` 可能在输入字节已漂移时仍成立。产品 canonical reader本身能失败关闭，但当前证据 verifier 不能独立证明这一点，W04 frozen evidence chain 不闭合。
- 建议：把 A/B/C builder input 作为 artifacts 或 source inputs 纳入 manifest；verifier 对每个 delivery 校验 `builder_input_relative_path`、`builder_input_sha256`、路径边界和实际字节，再重算 binding。新增“非目标行/indication 漂移”和“目标行漂移”两种不落盘 tamper probe，二者都必须失败。

### P3

0。`/api/import` 仍为 404；未把 W05 宽屏与纵向密度列为 W04 缺陷。

## 原三次 FAIL 缺陷 closure

| 历史缺陷 | 判定 | 第四次独立结论 |
|---|---|---|
| 首轮 P1-01：shadow/overlay，原 A/B/C 消费者未更新 | **关闭原缺陷** | v5 运行路径重建原 report.js/search/HTML/source consumer；无 `user_fact_revision` overlay，且事实分别只重建 A/B/C。新 P1-01 是来源原文/locator 被 user value 污染，不是旧 shadow 链复发。 |
| 首轮 P1-02：pointer 发布后普通失败可暴露新 revision；无效 mixed pointer | **关闭** | 稳定 descriptor + immutable generation + SQLite committed selector 替代可变 revision pointer。普通故障保持旧 selector；commit 结果不确定显式区分。 |
| 首轮 P1-03：three-way 字段不完整/未持久化 | **关闭（本范围）** | 字段并集、三值、presence、lineage、withdrawn、resolution options 和 DB 持久化继续通过相关批次。 |
| 首轮 P2-01：events count 被错误套用 n<=N | **关闭** | `crude_rate + participants` 才施加 n<=N/自动重算；events、person-time、adjusted rate、LS mean 均未回归。 |
| 首轮 P2-02 / 二次 P2-01：浏览器与 manifest 未绑定 | **部分关闭** | DOM/console/截图/current/selector/generations/DB summary/event/journals/transactions/receipts 已进入 v5 39工件；但 builder inputs 未绑定且 verifier 可假阴性，见本次 P2-01。 |
| 首轮 P3-01：`/api/import` 同义入口 | **关闭** | 生产只接受 `/api/save`，import 回归为 404。 |
| 二次 P1-02：partial JSONL、raw pointer 伪原子 | **关闭** | event 尾记录恢复与 immutable selector 协议通过；无可变 raw revision pointer。 |
| 第三次 P1-01：row_id-only 可错绑 product/trial/arm/event/form/unit/source/digest | **关闭目标绑定缺陷** | 20项 binding 完整、严格、pre-staging；stale/同row异身份/跨报告反例失败关闭。来源输出层仍有本次新 P1-01。 |
| 第三次 P1-02：fsync + rollback 双故障普通失败暴露新 raw current | **关闭** | 新协议不再覆盖 raw revision pointer或依赖 rollback replace；generation 故障只留不可见 orphan，selector 不前移。 |

## W04 acceptance 逐项

| 验收项 | 判定 | 证据与边界 |
|---|---|---|
| 1. typed target identity / expected_revision / request_id；完整消费者身份与 pre-staging fail closed | **PASS** | binding 字段覆盖指定身份；严格相等比较，无 unknown skip；stale、同 row 异身份、cross-report 均在 staging 前失败。 |
| 2. append-only 事实版本、旧 accepted/fragment 保留、user_modified、undo 追加 | **PASS（存储层）** | DB 中 base accepted 与 user_modified 共存、同一原 fragment 保留。门户未正确展示该 provenance，计入 P1-01。 |
| 3. n/N、时间、单位、C threshold；统计对象边界 | **PASS** | 116 项相关批通过；events/person-time/adjusted/LS mean 未被 participant crude-rate 规则覆盖。 |
| 4. impact DAG/receipt 记录已验证身份和 original-row digest | **PASS（身份绑定）** | receipt 与 transaction 记录完整 binding/original-row digest，并由 builder 实际产生。它不能抵消来源展示被覆盖，故整体 W04 仍 FAIL。 |
| 5. 仅受影响报告重建 | **PASS** | v5 A/B/C report revision 为 `1/2/3`；三次保存分别只重建 A、B、C。 |
| 6. immutable generation + SQLite FULL selector；故障/重启/双故障 | **PASS（本次检查）** | descriptor 稳定、generation 先 durable、selector 单事务；普通故障不前移，commit uncertainty 显式 indeterminate；未发现生产直接读旧 current revision 的旁路。 |
| 7. three-way refresh | **PASS** | 字段并集、conflict/converged/withdrawn、三值与 resolution 要求均通过并持久化。 |
| 8. loopback/API/security | **PASS（本范围）** | `/api/import` 404；Host/Origin/session/CSRF/JSON/size/path/symlink 回归通过。未做 DNS rebinding 专项渗透。 |
| 9. v5 13源/39工件、verifier、tamper、DOM/console/screenshots | **FAIL** | 原 verifier 与简单 artifact SHA tamper probe按声明通过，截图非白、console 0/0；但 builder input 未绑定导致独立 tamper 假阴性，且 C 截图实际固化了错误来源归因。 |
| 10. 来源原值、用户修订状态与真实消费者一致 | **FAIL** | C 门户把 user value 当登记原文；A/B/C受影响页面未明确显示“用户修订，未独立复核”。 |

## 实际命令与结果

### 1. 完整 W04 相关批

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/integration/test_w04_user_fact_edit.py \
  tests/integration/test_correction_service.py \
  tests/integration/test_correction_flow.py \
  tests/integration/test_incremental_refresh.py \
  tests/integration/test_latest_delivery.py \
  tests/unit/test_render_transaction.py \
  tests/integration/test_sqlite_migrations.py -q --tb=short

116 passed in 41.21s
```

结论：既有断言全部通过，但没有断言 user_modified 不得覆盖 evidence drawer 的 `original_text`，也没有断言 verifier 必须绑定 builder input，因此不抵消本报告反例。

### 2. v5 verifier 与既有 tamper probe

```text
checked_sources=13
checked_artifacts=39
error_count=0

--tamper-check:
error_count=1
tamper_rejected=true
```

既有 probe 只证明列入 manifest 的第一项 artifact SHA 被改时能拒绝；不能证明未列入清单的 builder inputs 受保护。

### 3. 独立来源污染反例

```text
DB original fragment:
  content_text = 入选标准阈值为至少16分。
  source_version_id = ctgov-nct04178967-20230524
  field_path = protocolSection.eligibilityModule.eligibilityCriteria

Rendered C evidence view:
  original_text = inclusion_criterion：<=18.0 分。
  source_version_id = ctgov-nct04178967-20230524
  source label = ClinicalTrials.gov
  user_modified disclosure text count = 0
```

### 4. 独立 builder-input tamper probe

```text
tampered_path=.../state/user-fact-builder-inputs/report-a-data.json
original_sha256=8460ff9a1931d9527d18921bbefa1a714df905651d8928a8af3a6ab881b503b3
tampered_sha256=d5ffc7a4b152c66c72e25429d3863f5b2cc24fb286fd75d10c7b7fe0204f8e94
v5 verifier: error_count=0
canonical reader: ValueError 当前交付builder输入绑定不一致
```

该 probe 仅在进程内替换 `Path.read_bytes()` 返回值，未修改磁盘文件。

### 5. 生产旁路与视觉核验

- `rg` 未发现 `src/ci_workflow` 中 canonical reader 之外直接解析 `reports/current.json` 的生产读者；`read_latest_delivery()` 在用户 current 存在时拒绝 `latest.json` 旁路。
- 四张 v5 截图均独立目视，非白；A 显示 67%，B 显示 30/24/80 及来源抽屉，C 显示 `EASI ≤18.0`。C 截图同时直接支持 P1-01：抽屉把该修订值展示为 ClinicalTrials.gov 登记原文。
- W05 宽屏利用率、纵向/窄屏密度与四视口未评判。

## source / artifact identity

- Git：`main`，`HEAD=2df24bb441e555f20b233ad2011b4ffd3610655b`；工作树已有大量 W00–W04 及其他用户修改。本复审未把 HEAD 当作完整 dirty source identity，未改动这些文件。
- 三份既有独立 FAIL SHA-256：
  - `W04-independent-review.md`：`ae71fd6ae67e4d3e12045a978a2cf0729ad5578bdefdc2671e1740f0ffd6eecd`
  - `W04-independent-rereview.md`：`37c7cc732d3b8b67196972e798eca7037b4496a89dba8f7dd9beb0bbcc6b2e90`
  - `W04-independent-rereview-2.md`：`eb846e42233001b3924b130b8ce691e1274484ecebc0aa7a8173929396dbeb98`
- 当前 `W04-result.md`：`d449eeae676965788fc17007ccb81bfd7a09ca7822a870175224522e46d678f0`。
- v5 `evidence-manifest.json`：`c9e350ca23b88261c60694a8fb328694522672567d8d7b57e7816f8576c0c86d`；声明 dirty source digest `02a11de46e1896a66bd290c307b475718870a27f67b492216260504f94c29c32`、13 source inputs、39 artifacts、selected generation `fdc7e66cd866d56b13c942ee8356530e8cff0cdf217a45bd356cf4e6c682bba3`。
- 关键当前源码 SHA-256 与 v5 manifest 一致：`active_fact_projection.py=82466e86...615c2`、`report_a.py=58592858...ec54`、`report_b.py=07ea70f5...238a`、`report_c.py=19ced8b5...e978`、`latest_delivery.py=4b92789f...8f9c`、`user_fact_edit.py=a8e3a98b...1af8`、`build_w04_v5_evidence.py=651eb3c8...5185`、`verify_w04_v5_evidence.py=1e939d32...1f64`。

## 最小修复序列

1. 先修 C（并审计 B/A）来源投影：用户修订只能改变当前显示值；原 source quote、source locator、source version 必须原样保留并在抽屉同时可见。门户明确显示 `用户修订，未独立复核`，不得把用户值标成登记/论文原文。
2. 增加 portal-level deterministic test：保存 C `>=16 → <=18` 后，表/图显示 18；evidence drawer 仍显示原 `>=16` 原文和原 field path，并单列 user_modified value/provenance。对 B 原始定义/locator、A 来源字段做同类断言。
3. 将三份 builder input 纳入 v5 manifest；verifier 校验 delivery 声明的 builder input path/hash，再重算 binding。扩展 tamper probe 覆盖目标行和非目标字节两类漂移。
4. 只重跑受影响的 W04 测试、真实 A/B/C 浏览器旅程和升级后的 manifest/verifier；保留 W05 未验边界，再交新的全新上下文独立只读复审。

## 未验证范围

- runtime model/effort：**UNVERIFIED**。
- 全 gate。
- 8适应症 × A/B/C 的 24 门户。
- W05 四视口视觉门：1440×900、1024×1366、390×844、320×568；宽屏利用率、纵向/窄屏密度、首屏信息密度均未验，未作为本次 FAIL 理由。
- 三宿主真实安装、入口、失败恢复与语义一致。
- 全量真实生产资料 A/B/C 重建、W05/W06/W07 完整集成。
- 正式科学、医学、产品、用户与 RC 接受。

本次 FAIL 仅针对 W04 工程风险闭包；未进入 W05，也未改变其他工作包状态。
