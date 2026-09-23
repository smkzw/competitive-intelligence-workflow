verdict: FAIL

# W04 第二次 FAIL 返修后第三次独立只读复审

## model / effort

- 请求运行时：`gpt-5.6-sol:medium`。
- 核验结果：**UNVERIFIED**。本会话没有可核验的 runtime model/effort 回执；未猜测、未替换。
- 边界：全新上下文、单一只读复审者；仅写本报告；未联网、未派子代理、未进入 W05，未执行 commit/push/add/reset/checkout/clean/delete。

## 总结

第二次 FAIL 后的返修取得了实质进展：旧 `user_fact_revision` overlay 已退出运行路径；active facts 确实进入 A/B/C 既有 builder，原 `report.js`、search index、HTML 和来源字段发生变化；event 半条 JSONL 尾记录可在同 request 重试中恢复；v4 manifest 的 13 源、19 工件、dirty digest 算法及篡改失败关闭均可独立复算。

但 W04 仍不能通过，原因不是 W05 视觉问题，而是两项 W04 生产风险：

1. builder 只凭调用方提供的 `report + collection + row_id` 覆盖原领域行，不校验 trial/product/arm/endpoint/statistical form/source identity。v4 证据实际把合成 `20/80` 人数粗率写入两个语义完全不同的真实 SAE 计数行：A 从 `8例/40` 变成 `30% (24/80)`，B 从 `9例/25` 变成 `30% (24/80)`；C 也把原本已写明 `Hgb ≤9.5`、来源版本为 `ctgov-pnh-page-2` 的观察，改绑到合成 `source-v1`。receipt/DAG 来自 builder 的实际执行，但实际消费的是错误目标，因此仍属自证式绑定，不能证明“正确原消费者”闭包。
2. 单故障顺序已修好，但 post-replace directory fsync 失败且 rollback replace 再失败时，`_atomic_write_pointer()` 返回 `OSError`，raw `current.json` 已是新 revision。故“任何返回失败 raw current 必须保持旧字节”仍不成立，且这种双故障正是本次指定要检查的伪原子边界。

本 FAIL 仅否定 W04 工程风险闭包；不扩展为全 gate、24 门户、W05 四视口视觉、三宿主、科学/医学/产品/RC 结论。

## 缺陷表

### P0

0。

### P1

#### P1-01 — active fact 与原领域行仅按 row_id 绑定，可覆盖无关医学对象

- 文件:行：`src/ci_workflow/renderers/portal/active_fact_projection.py:21-26,52-58`；`src/ci_workflow/renderers/portal/report_a.py:1862-1945`；`src/ci_workflow/renderers/portal/report_b.py:4700-4795`；`src/ci_workflow/renderers/portal/report_c.py:1988-2053`；`tools/build_w04_rereview_evidence.py:138-197`。
- 复现：`ActiveFactBinding` 只有 `report/collection/row_id`。三 builder 命中唯一 row_id 后直接覆盖值、单位、分子分母、叙事和来源字段，没有核对原 row 的科学身份。v4 工具把合成事实 `25% (20/80)` 绑定到：
  - A `safe-1`：`iptacopan / NCT04820530 / 严重不良事件组别汇总计数 / 8例 / 8/40`；rev2 变为 `30% / 24/80`。
  - B `bsafe-safe-298`：`eculizumab / NCT05886244 / 严重不良事件组别汇总计数 / 9例 / 9/25`；rev2 变为 `30% / 24/80`。
  - C `row-nct04469465-inclusion_criterion-1`：base 原文已含 `Hgb ≤9.5`、`source_version_id=ctgov-pnh-page-2`；合成 base fact 却是 `<10 g/dL/source-v1`，rev2 将该真实观察改写为合成来源。
- 影响：stale、错误或被污染的 `consumer_bindings` 可把一个事实写到无关试验/产品/组别/统计对象；图、表、叙事、索引、来源绑定和 receipt/DAG 会一致地证明错误结果。当前 v4 浏览器截图证明“发生了原生重投影”，但不能证明“重投影到了正确消费者”。这违反 W04 的完整目标身份、无关事实不联动和来源绑定要求。
- 最小建议：为 binding 加入并校验不可漂移的原消费者身份（至少 report/collection/row_id + product/trial/group/arm/cohort/period/endpoint or event definition/statistical form/measure object/unit/source version/original-row digest）；builder 在写入前逐项比对，不一致失败关闭。v4 证据应使用与 A/B/C 原行真实同源、同语义的事实，增加 stale row_id、同 row_id 异身份、跨统计对象错绑反例；receipt 记录并绑定验证后的原行身份摘要。

#### P1-02 — fsync/rollback 双故障仍可“返回失败但 raw current 已前移”

- 文件:行：`src/ci_workflow/application/latest_delivery.py:120-161`；提交顺序见 `src/ci_workflow/application/user_fact_edit.py:752-766`。
- 复现：对 `_atomic_write_pointer()` 注入第一次 `current.json` replace 成功、随后 directory fsync 失败、回滚 `os.replace` 再失败。实际输出：

```text
returned_failure = OSError: injected rollback replace failure
raw_changed = True
raw_revision = 1
calls = [initial replace, directory fsync failure, rollback replace failure]
```

- 影响：调用方收到失败，但任一 raw pointer 读取者已看到新 revision；这正是伪原子状态。仓内单故障覆盖了 pre-fsync、replace、DB、event、journal、post-fsync 成功回滚和 partial JSONL，但没有关闭 rollback 自身失败。
- 最小建议：不要把“覆盖唯一 pointer 后再以第二次 replace 回滚”作为失败原子性的唯一保证。采用可判定 committed generation 的单一事务真源/双槽 pointer + durable commit record，或在 rollback 失败时进入明确的 indeterminate recovery 状态并阻止普通失败返回；恢复必须依据已持久 DB/event/ready journal 决定前滚或回退，并以 raw bytes 为准。增加 post-fsync + rollback replace、post-fsync + rollback fsync 双故障反例，要求不会以普通失败返回同时暴露新 pointer。

### P2

0。第二次报告的 v4 manifest 缺口已关闭；见下方 closure 与 hash/manifest 核验。

### P3

0。`/api/import` 已关闭；W05 宽屏利用率和纵向/窄屏密度仅列为未验证，不作为 W04 功能失败。

## 第二次报告缺陷 closure

| 第二次报告缺陷 | 判定 | 第三次独立结论 |
|---|---|---|
| P1-01：overlay/shadow 链，原 builder/消费者未变 | **未完全关闭** | shadow/overlay 本身已关闭：运行路径调用 A/B/C 原 builder，删除 revision metadata 后原 payload 仍与 base 不同，search/HTML/source 字段也变化，旧 `_PAGE_RULES` helper 未被生产调用。但新链只按 row_id 信任 binding，v4 证据实际错绑无关 SAE/设计行；因此“正确原消费者闭包”仍未成立。见本次 P1-01。 |
| P1-02：raw current 伪原子、partial JSONL 不可恢复 | **未完全关闭** | event before/partial write、request DB、journal、pointer replace、pre-fsync、单次 post-fsync 等单故障已保持旧 raw bytes并可同 request 恢复；partial JSONL 可截尾且保留有效历史。仓内未发现生产代码直接读取 `reports/current.json` 绕过 canonical reader。但 fsync + rollback replace 双故障仍返回失败并暴露新 raw pointer。见本次 P1-02。 |
| P2-01：v3 manifest 未绑定 runtime/current/DB/event/journal，dirty digest 无算法 | **关闭** | v4 明确定义 Unicode 路径排序及 `path + NUL + sha256(raw bytes) + LF`；13 源、19 工件、3 journeys、raw current、DB summary、event、3 journals、rev3 transactions/receipts、DOM/console/4 screenshots 全部绑定。verifier 为 0 error；内存篡改 raw current 副本后失败关闭。 |

## W04 acceptance 逐项

| 验收项 | 判定 | 证据与边界 |
|---|---|---|
| 1. typed target identity / expected_revision / request_id / rationale；幂等、漂移、并发 | **FAIL** | 保存命令和事实版本身份本身通过；但跨门户消费者目标仅有 row_id，无完整科学身份，真实 v4 样本已发生错绑。 |
| 2. 追加事实版本；旧 accepted/source quote/evidence 保留；user_modified；undo 追加 | **PASS** | DB summary 显示旧 accepted、两类 user_modified 和 supersedes 链均保留；undo 为 revision 3 新版本。 |
| 3. n/N、时间、单位、语义、C threshold；统计对象范围 | **PASS** | 95 项批次覆盖 participant crude rate 才约束/重算；events、person-time、adjusted rate、LS mean 和无关同值事实不联动。 |
| 4. impact DAG 来自真实 receipt/consumer identity | **FAIL** | receipt 确实由 builder 实际执行产生，不再是 `_PAGE_RULES` 固定 overlay；但它只证明指定 row_id 被改，未证明该 row 与 fact 是同一科学对象，v4 已实证错绑。 |
| 5. staging、hash/reference closure、唯一 raw current、故障恢复/同 request | **FAIL** | 普通故障、partial JSONL 与精确重试通过；fsync/rollback 双故障仍伪原子。 |
| 6. typed three-way refresh 与持久化 | **PASS** | base/user/source 字段并集、presence、lineage、撤回及显式 resolution 均在相关批次和 DB summary 中成立。 |
| 7. loopback/API 安全边界 | **PASS（本范围）** | 服务仅接受 `/api/save`；`/api/import` 404，multipart save 415；Host/Origin/session/CSRF/大小/路径/symlink 回归通过。未做 DNS rebinding 专项渗透。 |
| 8. 真实浏览器与 v4 证据 | **FAIL（数据绑定）** | DOM/console/截图/字节绑定均真实，console 0/0、四图非白；但旅程展示的是错绑到真实行后的结果，不能接受为正确功能闭包。W05 视觉密度不参与本判定。 |
| 9. 防自证、fixture 漂移、生产旁路、过度声明 | **FAIL** | overlay 与 latest/current 旁路已关闭；但 v4 用合成事实覆盖无关真实行，且 receipt 无语义身份校验，是自证样本与生产约束同时不足。 |

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

95 passed in 37.03s
```

结论：既有断言全部通过，但未覆盖本报告的消费者语义错绑和 fsync/rollback 双故障，因此不抵消独立反例。

### 2. 原领域 payload / search / receipt 字节检查

- A/B/C rev2 的 `data/report.js` 删除/不存在 `user_fact_revision` 后仍分别与 base 不同；三份均 `overlay_present=False`。
- A、B 原 safety 行分别从 `8例/8÷40`、`9例/9÷25` 被改成 `30%/24÷80`；C 原 observation 的阈值、source text/source version/review state 被改。
- rev2 search index 含新值；三份 receipt 含对应原页面和 chart/table/narrative/index/source consumer；`integrate_fact_revision()` 生产调用为 0，旧 `_PAGE_RULES` 只留在 forensic helper。
- 这些检查既证明原 builder 链已接通，也直接复现 P1-01 的错绑。

### 3. 故障反例

- 现有批次：event-before、partial event write、request DB、journal、pointer replace、current file fsync、单次 directory fsync 均保持旧 raw pointer，并在同 request 重试后到 revision 1；partial JSONL 保留先前有效事件且只追加一条保存事件。
- 新独立反例：post-replace directory fsync 失败 + rollback replace 失败，返回 `OSError`，但 raw pointer 为 revision 1。结果见 P1-02。
- 生产直接读取旁路搜索：未找到 `src/ci_workflow` 中直接解析 `reports/current.json` 的其他读者；canonical `read_current_delivery/read_effective_delivery` 为现有入口。此结果不能消除文件系统层 raw pointer 的双故障问题。

### 4. v4 verifier 与篡改失败关闭

```text
checked_artifacts=19
checked_sources=13
error_count=0
schema_version=4.0
```

不落盘篡改测试将 `reports/current.json` 的读取字节追加一个字节后复用同一 verifier：

```text
error_count=1
artifact mismatch: .../reports/current.json
```

因此清单对该工件能失败关闭。`git diff --check` exit 0。

## hash / manifest

- `W04-independent-review.md`：`ae71fd6ae67e4d3e12045a978a2cf0729ad5578bdefdc2671e1740f0ffd6eecd`。
- `W04-independent-rereview.md`：`37c7cc732d3b8b67196972e798eca7037b4496a89dba8f7dd9beb0bbcc6b2e90`。
- 当前 `W04-result.md`：`38d792ba22c37b5050b1bd1837e0f2aa9c7e7b4cbe5c7364d881756ed5cc0d89`。
- v4 `evidence-manifest.json`：`bce5c414ca4ea00d6f375f5994b969a34b8cc65532ffedfe508fa9f0241359ff`。
- dirty source digest：`9c5d95e88c75aef771c116e87b54a45d96b5369d8efa06c465991f4ff44918ce`；13 个输入的当前 hash/size 全匹配。
- raw `reports/current.json`：`c762eeea2cdc7b2d9c5858139e6436c057974e395f0f5e82c9619719f383b5c1`，revision 3。
- event stream：`023d1ffbc4ca13af748e03de6cb670409f9696269da7d57c3b09890bfb128922`。
- readonly DB summary：`14c37d826ced613d1d4d9b5582ffebbab4dcfd1726da6c52a605cfbf00c0668f`。
- 19 个 manifest 工件、3 个 ready journal、A/B/C rev3 transaction/consumer receipt、3 个 runtime journey、DOM/console 与 4 张截图均匹配当前字节。

## 三方比较、统计对象与 API 回归

- three-way：**PASS**。字段并集、user-only/source-only/converged/conflict/withdrawn、base/user/source 三值、lineage、source version、resolution options 与 DB 持久化均有覆盖。
- 统计对象：**PASS**。`n<=N` 与自动重算只用于 `crude_rate + participants`；events count 可大于人数，person-time、adjusted rate、LS mean 不被粗率逻辑覆盖。
- `/api/import`：**PASS（已关闭）**。生产服务仅接受 `/api/save`，import 返回 404；未发现回归别名。

## 最小修复

1. 先修 consumer binding：增加原领域行完整科学身份/原行摘要并在 A/B/C builder 写入前严格核对；不匹配必须失败关闭。用真实同源事实替换 v4 合成错绑样本，增加三类 stale/mismatched binding 反例，并让 receipt 记录验证后的身份摘要。
2. 修 current 双故障协议：不能依赖覆盖后 rollback 的第二次 replace 才维持“失败=旧 pointer”。设计可恢复 generation/commit marker 或单一事务真源；对 rollback replace/fsync 失败给出确定前滚/回退恢复，避免普通失败与新 raw pointer 同时出现。
3. 重跑受影响最小批与真实 A/B/C 浏览器旅程，升级 manifest/source digest 后再交全新上下文独立复审；不得进入 W05。

## 未验证范围

- runtime model/effort：**UNVERIFIED**。
- 全 gate。
- 8适应症 × A/B/C 的 24 门户。
- W05 四视口视觉门：1440×900、1024×1366、390×844、320×568；宽屏利用率、纵向/窄屏密度、首屏信息密度均未验证。本报告没有把旧视觉差判成 W04 功能失败。
- 三宿主真实安装、入口、失败恢复与语义一致。
- 全量真实生产资料 A/B/C 重建、W05/W06/W07 完整集成。
- 正式科学、医学、产品、用户与 RC 接受。

