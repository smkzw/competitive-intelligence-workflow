verdict: FAIL

# W04 返修后独立只读复审

## model/effort verification

- 请求运行时：`gpt-5.6-sol:medium`。
- 核验结果：**UNVERIFIED**。本会话没有可核验的 runtime model/effort 回执；未猜测身份，也未静默替换模型。
- 复审边界：全新上下文、单一只读复审者；只在英文工程执行命令，只写本报告；未联网、未派子代理、未进入 W05，未执行 commit/push/add/reset/checkout/clean/delete。

## 总结

返修已真实关闭 typed 三方比较、统计对象边界、`/api/import` 别名和浏览器截图真实性等缺口；91 项相关测试、Ruff、strict mypy 与 diff check 均通过，v3 保存的 A/B/C 页面也确为 abc-v106 的真实门户字节，不是旧的空白测试页。

但 W04 仍不能通过：

1. 新 revision 仍由 W04 自己硬编码页面映射并追加一套 `user_fact_revision` payload/JS/DOM 小组件；删除该新增字段后，A/B/C 原 payload 与 abc-v106 完全相同，现有 builder 和原图表/表格/叙事消费者没有重投影。receipt/DAG 的五类消费者也是该新增层自报，不是既有消费者身份。
2. `reports/current.json` 在 event/DB/journal 后段失败前已经替换为新 revision；读取函数只是依据 `prepared` journal 返回旧对象。反例中保存返回失败后原始 pointer 已从 revision 0 变为 1，而 API reader 报 revision 0，属于 journal 可见性伪原子。
3. event JSONL 部分写入后失败会留下损坏尾记录；同一 request 重试不能恢复。
4. v3 evidence manifest 的逐文件哈希可复算，但未绑定两个 runtime journey 文件、最终 current、DB、event/journal 字节，也没有定义 `dirty_source_digest` 算法；故其“source→故障→恢复→browser”证据链仍不闭合。

本结论只否定 W04 工程风险闭包，不升级为 W01–W03、W05、科学、医学、产品或 RC 结论。

## 缺陷表

### P0

0。

### P1

| ID | 文件:行 | 复现 | 影响 | 最小建议 |
|---|---|---|---|---|
| P1-01 | `src/ci_workflow/renderers/portal/fact_revision.py:23-65,105-164,182-230,260-305`; `src/ci_workflow/application/user_fact_edit.py:769-812`; `tests/integration/test_w04_user_fact_edit.py:313-345` | 对 v3 revision 2 的 A/B/C `data/report.js` 解析后删除 `user_fact_revision`，三份对象均与 `runs/pnh-vertical/abc-v106` 原 payload 相等；`rg "integrate_fact_revision\\(" src/ci_workflow` 只有 W04 service 与该 helper 两处。helper 依据 `_PAGE_RULES` 自选页面，`PortalFactConsumer.artifacts` 默认宣称 chart/table/narrative/index/source_pointer 全部存在，再生成统一小组件。截图也显示修订内容是原门户下方独立“当前事实同步”卡片。 | P1-01 没有真实关闭：事实修订没有进入既有 A/B/C builder 的领域 payload 和原消费者，原图/表/叙事可继续显示旧数据；receipt 与 impact DAG 是新增平行层的自证。把 sidecar 从 JSON 文件移入 `report.js` 并不能消除 shadow-only 数据链。 | 让现有 A/B/C builder 接受 fact revision，并重建其真实领域行/series/table/narrative/source binding；由 builder 输出实际 consumer receipt。删除通用平行图表/表格小组件及硬编码 `_PAGE_RULES` 验收替代；反例应断言原消费者数据本身改变，而不只断言新增字段/DOM 存在。 |
| P1-02 | `src/ci_workflow/application/latest_delivery.py:105-117,326-364`; `src/ci_workflow/application/user_fact_edit.py:687-732`; `src/ci_workflow/storage/event_store.py:204-242`; `tests/integration/test_w04_user_fact_edit.py:387-475` | 反例一：注入 event append 失败，`save()` 返回 `OSError`；`reports/current.json` 原始字节已改变且 raw revision=`1`，只有 `read_current_delivery()` 因 journal=`prepared` 返回 revision=`0`。反例二：令 event store 先写半条 JSON 再抛错，首次返回 `EventStoreError`、reader 仍为 revision 0；同一 request 重试再次返回 `EventStoreError: 规范事件流包含无效记录`。另 `_atomic_write` 明确吞掉 replace 后目录 fsync 错误，仓内测试反而要求该故障返回成功并暴露 revision 1。 | P1-02 没有真实关闭。“返回失败不暴露新 current”只对一个特定 Python reader 成立，pointer 文件本身已经是新版本；任一直接 pointer 消费者、不同实现或证据读取会看到新 current。event 部分写入还破坏同 request 恢复，违反 W04 故障恢复合同。 | 把唯一可见 pointer 的替换放到所有可恢复 DB/event 状态已持久化之后，或使用单一事务存储/明确 committed pointer，使原始 current 在失败时保持旧字节；event append 采用临时完整记录+原子提交、长度校验/可截断尾记录或等价恢复协议。覆盖 raw pointer、目录 fsync 和部分 event write 反例。 |

### P2

| ID | 文件:行 | 复现 | 影响 | 最小建议 |
|---|---|---|---|---|
| P2-01 | `packets/2026-09-22-sol-delivery/evidence/W04-remediation-real-portal-v3/evidence-manifest.json:1-66,312-346`; `packets/2026-09-22-sol-delivery/evidence/W04-result.md:55-94` | 13 个 `source.file_sha256`、三份 revision 2 transaction manifest、portal payload/search/custom-JS/HTML 与五张截图哈希均可复算；但 manifest 没有两个 `runtime-journey*.json` 的哈希、最终 `reports/current.json` 哈希、DB/event/journal 哈希或 receipt。`dirty_source_digest` 只有值没有算法；以 source map 的 canonical JSON、`sha256  path`/`path:sha256` 排序行等常见方法均无法得到声明值。 | P2-02 浏览器真实性已大幅修复，但 evidence manifest 尚不能不可变绑定“故障→隐藏→重试→undo→refresh”和最终 current/DB/event/journal；dirty digest 也不能独立复现。报告/STATUS 对“绑定 current 与 runtime receipts”的表述过强。 | 在 manifest 中写明 dirty digest 的精确输入集合、排序、编码和算法；加入 runtime journey、最终 current、只读 DB 摘要、event stream、journal 文件及 revision 3 transaction/portal receipt 哈希，并由一个校验命令复算。 |

### P3

0。补充复杂度审查发现的硬编码路由和并行渲染层已计入 P1-01，因为它直接造成生产消费链漂移，而不是单纯可选的代码精简。

## 原独立审阅缺陷逐项 closure

| 原缺陷 | 判定 | 独立复核结论 |
|---|---|---|
| P1-01 shadow 数据链/真实消费者未接入 | **未关闭** | 已从独立 test page/`w04-*.json` 升级为真实 abc-v106 页面中的 payload 字段和 DOM 卡片；但现有 builder/原消费者数据未变化，仍是平行修订层。见本次 P1-01。 |
| P1-02 current 原子性/故障恢复 | **未关闭** | bundle 发布前不变量检查已补；标准 reader 可借 prepared journal 返回旧对象；但 raw current 已先切换，目录 fsync 被吞，event 部分写入不可恢复。见本次 P1-02。 |
| P1-03 compare_refresh 字段全集与 RefreshService | **关闭** | `RefreshService.compare_user_fact_refresh` 对 base/user/source 字段并集计算三值、presence、source inheritance、lineage、source version、resolution options，并持久化 comparison/base/user/resolution JSON；遗漏 source 字段保留 user-only，撤回全字段进入 `source_withdrawn` 且需显式解决。 |
| P2-01 events>participants 被错误拒绝 | **关闭** | 模型与保存路径仅对 `crude_rate + participants` 应用 `n<=N` 和自动粗率；`count/events`、`person_time`、`adjusted_rate`、`ls_mean` 反例均通过，后两者及无关同值事实不被重算。 |
| P2-02 浏览器证据只覆盖编辑页且无 manifest | **部分关闭** | 五张截图确为真实 A/B/C 门户且非白图；A 两张超长但内容真实，不能因长图/稀疏直接判 W04 功能失败。DOM/console/screenshot 已入 manifest；但 runtime/current/DB/event/journal 和 dirty digest 方法未绑定，见本次 P2-01。 |
| P3-01 `/api/import` 同义入口 | **关闭** | 服务只接受 `/api/save`；有效 JSON 请求 `/api/import` 返回 404，multipart `/api/save` 返回 415。 |

## W04 acceptance 逐项判定

| 验收项 | 判定 | 证据与边界 |
|---|---|---|
| 1. typed target identity / expected_revision / request_id / rationale；幂等、漂移、并发 | PASS | 完整身份、旧 revision、同 request 异 payload、两线程竞争均失败关闭；相同完整 request 正常幂等。 |
| 2. 追加事实版本；旧 accepted/source quote/evidence 保留；user_modified；undo 追加 | PASS | DB 与迁移/测试支持；v3 有 revision 1/2/3 complete request 和 committed journals，旧事实/fragment 未被覆盖。 |
| 3. n/N、时间、单位、语义、C threshold；统计对象范围 | PASS | participant crude rate 才重算；events/person-time/adjusted rate/LS mean 和无关事实边界通过。 |
| 4. impact DAG 来自真实 receipt/consumer identity | FAIL | DAG 不再是 facts×artifacts 全连接，但 receipt 由同一个新增 overlay helper按硬编码页面和固定五类 artifact 自报，不是既有 builder/原消费者身份。 |
| 5. staging、hash/reference closure、唯一 current、失败恢复/同 request | FAIL | transaction/file hash 闭包和发布前混版校验通过；但 raw pointer 伪原子及 event 部分写入重试失败。 |
| 6. compare_refresh typed three-way 与 RefreshService 持久化 | PASS | 完整字段并集、三值、presence、lineage、source version、resolution options、遗漏字段和撤回均已核验。 |
| 7. loopback 安全边界 | PASS（本范围） | `/api/import` 404、multipart 415；Host/Origin/session/CSRF/JSON/大小/路径/symlink 相关回归通过。未做 DNS rebinding 专项渗透。 |
| 8. v3 真实浏览器与截图证据 | FAIL（证据闭包） | 页面和截图本身真实、DOM 值合理、C 新鲜页 console 0/0；但 manifest 未绑定 runtime journey/current/DB/event/journal，且页面显示的是平行修订卡片。 |
| 9. 防自证/fixture 漂移/生产旁路/过度声明 | FAIL | latest/current Python 读取双轨已失败关闭，源哈希无漂移；但新增 overlay 自报 consumer/DAG，且 manifest 对 current/runtime 绑定过度声明。 |

## 实际命令与结果

### 相关回归与静态检查

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/integration/test_w04_user_fact_edit.py \
  tests/integration/test_correction_service.py \
  tests/integration/test_correction_flow.py \
  tests/integration/test_incremental_refresh.py \
  tests/integration/test_latest_delivery.py \
  tests/unit/test_render_transaction.py \
  tests/integration/test_sqlite_migrations.py -q --tb=short
```

结果：`91 passed in 23.04s`。

```text
.venv/bin/ruff check <8个W04生产文件> tests/integration/test_w04_user_fact_edit.py tests/integration/test_sqlite_migrations.py
.venv/bin/mypy --strict <8个W04生产文件>
git diff --check
```

结果：Ruff `All checks passed!`；mypy `Success: no issues found in 8 source files`；diff check exit 0。

### 独立反例

1. event 在 pointer 后失败：

```text
RETURNED_FAILURE OSError event-before-write
RAW_POINTER_CHANGED True RAW_REV 1
CANONICAL_REV 0 JOURNAL_PHASE prepared
```

2. event JSONL 部分写入：

```text
PARTIAL_FIRST EventStoreError 无法追加规范事件
AFTER_PARTIAL_CANONICAL_REV 0
PARTIAL_RETRY EventStoreError 规范事件流包含无效记录
```

3. 原 portal 消费链对照：

```text
A ORIGINAL_PAYLOAD_UNCHANGED_AFTER_REMOVING_OVERLAY True OVERLAY_CONSUMERS 5
B ORIGINAL_PAYLOAD_UNCHANGED_AFTER_REMOVING_OVERLAY True OVERLAY_CONSUMERS 5
C ORIGINAL_PAYLOAD_UNCHANGED_AFTER_REMOVING_OVERLAY True OVERLAY_CONSUMERS 5
```

`integrate_fact_revision()` 在生产源码仅由 `UserFactEditService._build_report()` 调用；既有 A/B/C builder 未消费 revision。

## hash / manifest / portal / DB 核验

- v3 evidence manifest SHA-256：`2610a9dc344ce45568b6b37d03277b10ccb738a8c7266f8c8add14e23b5a25d2`，与 STATUS/result 一致。
- 原独立审阅 SHA-256：`ae71fd6ae67e4d3e12045a978a2cf0729ad5578bdefdc2671e1740f0ffd6eecd`，未改变。
- W04-result SHA-256：`c30c5ae2522b2a4dd76faecd5a7b899dcdc3964a80fb52ad1dc2a92cdd7354a0`。
- manifest 列出的 13 个 source file SHA-256 全部与当前文件匹配。
- revision 2 A/B/C transaction manifest SHA-256 全部匹配；每站点全文件 hash 与 transaction manifest 相等；portal payload/search/custom JS/HTML receipt 哈希全部匹配；每报告 5 个 overlay consumer。
- 最终 `reports/current.json` 实际 SHA-256：`0a721caf6b83b0b0b33e4e7e14f316f51deba1f1d936915f023022e1436158fe`，revision 3；此值在 result 中出现，但不在 v3 manifest 中。
- 两个 runtime journey 实际 SHA-256：`7fc468f9ed61c8ff4d246dbcf2ec5dd408f3709e5dfd0f2af081e78d6266ff93`、`0ddebc143f15ade8021ab6baeed6bd0924117d19d2e8ac6cab98e43f491caa22`；均未被 v3 manifest 绑定。
- v3 DB 只读核验：三个 save request 均 `complete`（revision 1/2/3）；三个 journal 均 `committed`；refresh numerator 为 base=20、user=24、source=22、state=`conflict`，options=`keep_user/accept_source/manual`；事件流含三条 `user.fact.saved` 和一条 `refresh.user_fact.compared`。
- 五张截图 hash 全部匹配 manifest；目视确认均为真实 abc-v106 A/B/C 页面。A rate/threshold 是 8848/10229 px 的长页，内容并非空白；不把长度、原门户视觉稀疏或 W05 密度问题误判为 W04 功能失败。
- 代表性未受影响页面 `A/landscape.html`、`B/overview.html`、`C/overview.html` 与 abc-v106 原字节一致，证明 v3 确由真实门户复制而来；同时也支持 P1-01 对“只追加 overlay”的判断。
- `dirty_source_digest=a2c208...` 无复算方法。source map canonical JSON 等常见算法均不匹配；该值保持 **UNVERIFIED**。

## 最小修复序列

1. 取消 `user_fact_revision` 平行展示作为验收面；让现有 A/B/C builder 用 revision fact 重新生成真实领域 payload、原图表/表格/叙事/索引/来源绑定，并从 builder 产出消费者 receipt/DAG。
2. 重排事务，使 `reports/current.json` 的原始 pointer 只在 DB/event/恢复状态可持久完成后切换；失败必须保持旧 pointer 字节。补 raw pointer 与 directory-fsync 反例。
3. event store 改为可恢复的完整记录提交，处理 partial write/尾记录；同 request 必须在该故障后恢复。
4. 扩展 v3 manifest：定义 dirty digest 算法并绑定 runtime journeys、最终 current、DB/event/journals、revision 3 transactions/portal receipts；再做一次独立只读复审。

## 未验证范围

- runtime model/effort：**UNVERIFIED**。
- 全 gate。
- 8适应症×A/B/C 的 24 门户。
- W05 四视口视觉门：1440×900、1024×1366、390×844、320×568；宽屏利用率、纵向/窄屏密度、首屏信息密度均未验。本复审不要求 W04 做视觉重构。
- 三宿主真实安装/入口/失败恢复/语义一致。
- 全量真实生产资料 A/B/C 重建、W05/W06/W07 完整集成。
- 正式科学、医学、产品、用户与 RC 接受。

本 FAIL 给出的修复只针对 W04 工程风险，不要求进入 W05，也不改变其他工作包状态。
