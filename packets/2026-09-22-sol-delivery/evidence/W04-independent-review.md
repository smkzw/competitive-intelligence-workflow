verdict: FAIL

# W04 独立只读审阅

## model/effort verification

- 请求运行时：`gpt-5.6-sol:medium`。
- 核验结果：**UNVERIFIED**。本会话没有可核验的 model/effort 运行时回执；未猜测身份，未静默替换模型。
- 审阅方式：全新上下文、单审阅者、只读产品代码/测试/既有证据；仅本报告为持久写入。未派子代理、未联网、未进入 W05，未执行 commit/push/add/reset/checkout/clean/delete。

## 缺陷表

### P0

0。

### P1

| ID | 文件:行 | 可复现证据 | 影响 | 建议 |
|---|---|---|---|---|
| P1-01 | `src/ci_workflow/application/user_fact_edit.py:715-747`; `tests/integration/test_w04_user_fact_edit.py:221-233,276-319`; `src/ci_workflow/application/visual_acceptance.py:44-56` | 生产重建仅复制旧站点、另写 `data/w04-*.json`，并在 `index.html` 注入 revision marker；测试直接读取新增 `w04-projection.json`。`rg` 显示生产 A/B/C renderer、门户 JS、视觉接受及公开 CLI 均不消费 `w04-*.json`/`reports/current.json`，实际接受入口仍使用逐报告 `latest.json`。冻结证据中的 A/B/C 页面只是 `<h1>A/B/C报告</h1><div>revision …</div>` 的测试页。 | 这是影子数据链，不是“真实事实和所有消费者更新”。图、表、叙事、索引、来源指针虽然各生成了 JSON，却没有进入现有 A/B/C 门户的实际读路径；旧接口可继续展示旧事实。V2-06、V2-36/37 和 W04 出口未关闭。 | 将 W04 revision 接入现有 portal builder/render transaction/交付读取入口；由真实 A/B/C payload、HTML、JS 消费同一 fact revision，并用真实门户旅程证明图/表/文字/索引/来源指针同步。移除仅供测试读取的影子投影作为验收替代。 |
| P1-02 | `src/ci_workflow/application/user_fact_edit.py:640-679`; `src/ci_workflow/application/latest_delivery.py:140-169`; `packets/2026-09-22-sol-delivery/evidence/W04-result.md:15,49` | 故障注入令 `EventStore.append` 在 pointer 发布后抛错：`save()` 返回 `OSError`，但独立读取显示 `CURRENT_BEFORE_AFTER 0 1 request-save-rate-1`。另一反例构造 bundle revision 1、report revision 0；`publish_current_delivery` 返回成功并写盘，之后 `read_current_delivery` 才以“跨revision混版”拒绝。既有中断测试只在 B 构建后、pointer 切换前抛错（`tests/integration/test_w04_user_fact_edit.py:481-497`）。 | “失败/中断保留旧 current”和“单一原子 current”均不成立。调用方可能收到失败但读者已看到新 current；公共发布路径还能持久化自身无法读取的混版 pointer。 | 在任何外部可见 current 切换前完成可恢复 journal/event/request 状态，或实现明确两阶段提交及崩溃恢复；发布前对完整 bundle 执行与读取相同的 duplicate/report revision/fact digest 不变量校验。增加 pointer 后故障、event/DB/fsync/os.replace 故障反例。 |
| P1-03 | `src/ci_workflow/application/user_fact_edit.py:246-254,957-1027` | `compare_refresh` 只遍历调用者提供的 `source_fields`，返回对象只有状态标签，没有 base/user/source 字段值。临时项目中用户同时修改 `threshold_value` 和 `timepoint`、source 只传 `threshold_value` 时，结果为 `{'threshold_value':'conflict'}`，`USER_CHANGED_TIMEPOINT_PRESENT False`。仓内 `refresh_service.py` 没有该接口调用。 | W07 无法从返回值获得完整、可复核的字段级三方状态；被 source payload 遗漏的 user-only 修改静默消失，也没有实际刷新链消费者证据。 | 以 base/user/new-source 完整 typed fact 为输入，对字段并集分类并返回每字段三值、状态、来源版本和解决要求；校验 user 确实沿 base 继承；在真实 `RefreshService` 路径消费并持久化该结构，补遗漏字段和同字段异值反例。 |

### P2

| ID | 文件:行 | 可复现证据 | 影响 | 建议 |
|---|---|---|---|---|
| P2-01 | `src/ci_workflow/application/user_fact_edit.py:169-177,480-490` | `FactEdit(numerator=120, denominator=80, statistical_form='count', measure_object='events')` 在模型层被无条件拒绝。约束没有先判断 `crude_rate + participants`。 | 合法“事件次数可大于人数/风险集”的事实无法编辑，科学边界把事件次数错误套成人数比例约束；与 PRD 的统计对象区分不一致。 | 仅对明确 `statistical_form=crude_rate` 且 `measure_object=participants` 的 n/N 施加 `n<=N` 并重算；事件次数、人时率、调整估计和 LS mean 分别验证，不联动。 |
| P2-02 | `packets/2026-09-22-sol-delivery/evidence/W04-result.md:53-59,65-77,91-128`; `tests/integration/test_w04_user_fact_edit.py:221-233` | 两张截图已独立目视；revision 2 图不是白图，清楚显示 revision 2、24/80、`<=9.5 g/dL`。但它们只展示独立编辑页，不展示 A/B/C 门户。证据目录没有独立 DOM assertion/console receipt/浏览器 manifest；DOM 和 console 结果仅写在报告文本中，截图 hash 也未被 `current.json` 或事务 manifest 引用。 | 截图足以证明编辑页状态和非白图，不足以证明关联门户真实更新、console 结果、源码版本或 current 产物绑定。报告把它扩张为“完整浏览器编辑旅程”及跨报告闭包，证据强度不足。 | 保存机器可读 browser receipt（URL、DOM 断言、console、source/current/manifest/screenshot hashes），由一个不可变 evidence manifest 绑定；在当前 A/B/C 实际页面逐一断言可见值及图/表/来源一致。 |

### P3

| ID | 文件:行 | 可复现证据 | 影响 | 建议 |
|---|---|---|---|---|
| P3-01 | `src/ci_workflow/application/user_fact_edit_server.py:199-222` | `/api/save` 与 `/api/import` 进入完全相同的 `UserFactSaveCommand` 处理；现有安全测试只证明 multipart import 被拒，未定义合法 JSON import 的独立语义。 | 增加一个无必要的同义写入口，模糊审计/API 面；当前没有绕过 Host/Origin/session/CSRF/JSON/大小限制的证据。 | 在真实 typed import 合同出现前删除 `/api/import` 别名，只保留 `/api/save`。`ponytail net: -1 route branch possible.` |

## W04 acceptance 判定

| 验收项 | 判定 | 独立结论 |
|---|---|---|
| 1. typed target identity / expected_revision / request_id / rationale；幂等、载荷漂移、两标签/线程 | PASS | 完整目标身份在保存前与当前记录逐字段核对；同 request 同 payload 返回原结果，同 request 异 payload、旧 revision 和并发第二写均失败关闭。80 项批次及源码检查支持此结论。 |
| 2. 追加事实版本；旧 accepted/source quote/evidence 不变；新版本 user_modified；undo 追加 | PASS | 冻结 DB 中旧 accepted 行与 fragment 保留，新两版为 user_modified 且 supersedes 旧版；migration 有 append-only trigger；undo 测试产生新版本。此 PASS 只针对 W04 测试项目的事实存储。 |
| 3. n/N、时间、单位、完整语义、C threshold；仅 crude rate 重算 | FAIL | 粗率选择性重算、adjusted rate/LS mean/同值事实不联动在固定样本中成立；但事件次数 n>N 被错误禁止，完整统计对象边界未关闭。 |
| 4. impact DAG 覆盖真实 fact→消费者；拒绝 cycle/dangling/cross-revision | FAIL | 图结构本身能拒绝环、悬空和跨 revision；但 `_impact_graph` 是按全部 facts×全部 artifacts 临时合成的影子图，不来自真实 A/B/C 依赖，产物也未被真实门户消费。 |
| 5. staging 只重建已存在受影响 A/B/C；hash/reference closure；单一原子 current；失败恢复/重试 | FAIL | 固定测试项目的 3×8 文件 hash 与 manifest closure 可复算；但真实消费者未接入，post-publish 失败会留下新 current，公共 publish 可写入无效混版。 |
| 6. compare_refresh 可供 W07 消费，字段级 three-way、不静默覆盖 | FAIL | 同字段异值在被提供字段内标为 conflict；但字段全集不完整、返回缺三值，且未接入 RefreshService。 |
| 7. loopback 安全边界 | PASS | 静态检查和测试支持仅绑定 127.0.0.1，严格 Host/Origin、HttpOnly SameSite session、CSRF、固定路径、JSON/64 KiB 与 symlink 拒绝；未发现可实际绕过上述控制的请求。P3-01 是 API 面收缩建议，不提升为安全失败。 |
| 8. 真实浏览器证据与 revision 2 非白图 | FAIL | “revision 2 不是白图”本身 PASS；但截图/DOM/console 只覆盖编辑页，未覆盖真实 A/B/C，且缺独立机器回执和 hash manifest，因此 W04 浏览器验收整体 FAIL。 |
| 9. 测试自证、fixture-only、生产入口、过度声明、hash 漂移、旧接口旁路 | FAIL | 找到 fixture-only 影子门户、生产 latest/current 双轨及报告过度声明。未发现所列 W04 源文件、截图、result/current/事务 manifest 的现时 hash 漂移。 |

## 实际执行命令与结果

1. 冻结批次复跑：

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

结果：`80 passed in 2.24s`。这证明既有断言通过，不抵消上表独立反例。

2. 生产消费者追踪：

```text
rg -n "w04-(projection|chart|table|narrative|index|source_pointer)|w04-revision|UserFactEditService|user_fact_edit_server" src assets skills README.md ARCHITECTURE.md tests
rg -n "read_current_delivery\(|publish_current_delivery\(|reports/current\.json|read_latest_delivery\(|publish_latest_delivery\(" src skills tests
```

结果：`w04-*` 仅由 W04 producer/test 使用；现有 portal/visual acceptance 继续使用 `read_latest_delivery`/`publish_latest_delivery`。未找到真实 A/B/C 消费链。

3. post-publish 故障与无效 pointer 反例（临时目录，未改现有证据）：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
# 复用 test_w04_user_fact_edit._project 建临时项目；
# 注入 EventStore.append 失败，并直接调用 publish_current_delivery 写不一致 bundle。
PY
```

结果：

```text
POST_PUBLISH_FAILURE OSError injected event append failure
CURRENT_BEFORE_AFTER 0 1 request-save-rate-1
MIXED_WRITE_RETURNED 1 [0, 0, 0]
MIXED_READ_REJECTED_AFTER_WRITE CurrentDeliveryConflictError 当前交付存在跨revision混版
EVENT_COUNT_REJECTED ValidationError 1 validation error for FactEdit
```

4. three-way 字段完整性反例（临时目录）：

```text
RETURN_FIELDS ['base_fact_version_id', 'conflict_id', 'fact_id', 'field_states',
               'requires_explicit_resolution', 'user_fact_version_id']
FIELD_STATES {'threshold_value': 'conflict'}
USER_CHANGED_TIMEPOINT_PRESENT False
```

5. hash/闭包/DB 只读复算：`shasum -a 256 ...` 与只读 SQLite/Python closure 检查。

结果：报告列出的 W04 源文件 hash 全部匹配；`W04-result.md` 为 `5d229b3c…f234d`；current 为 `b8182173…16067`；A/B/C 均 revision 2、各 8 文件，文件 hash 与 transaction manifest 均 `True`。旧 accepted、新 user_modified、adjusted rate、LS mean 和无关同值事实与报告一致。

6. 截图独立目视与 hash：

```text
01-rate-24-of-80.png              31187933…2255b
02-threshold-revision-2.png       062f0b40…a999
```

结果：两图可读；第二张不是白图，并显示 revision 2、24/80、`<=9.5 g/dL`。

## 当前截图与 source/artifact hash 绑定

- Git：`main`，`HEAD=2df24bb441e555f20b233ad2011b4ffd3610655b`；工作树含 W00–W04 及其他既有修改/未跟踪资料，本审阅未把 HEAD 当作完整 dirty source identity。
- W04 源文件 hash：与 `W04-result.md:141-151` 全部一致，无现时漂移。
- 冻结测试项目 current：SHA-256 `b8182173a4117049e2083aee8b0522317b6d468f4a0ad02c161276520da16067`；A/B/C transaction manifest 分别为 `59c21bc…a173c`、`8a88b115…0f6d`、`13ac950c…bf2`，均复算通过。
- 截图 hash 与报告一致；revision 2 截图已确认非白图。
- 绑定缺口：截图、DOM assertion、console 结果没有独立 evidence manifest 绑定到上述 HEAD/dirty source hash/current/三份事务 manifest；current/事务 manifest 也不引用截图。故只能确认“这些字节当前匹配”，不能确认其形成了可重放的 source→browser acceptance chain。

## 未验证范围

- 运行时 model/effort 身份：UNVERIFIED。
- 未运行全 gate、24 门户、全页/全 viewport、三宿主、真实生产资料全量 A/B/C 重建、W05/W06/W07 完整集成、正式科学/医学/产品/RC 接受。
- 未把 W04 缺陷扩大为其他工作包失败；W01–W03 仅作为接口依赖阅读，未重新接受其全部结论。
- loopback 未做网络命名空间/浏览器 DNS rebinding 专项渗透；当前严格 Host/Origin 与 127.0.0.1 绑定未见直接绕过。

## 最小修复序列

1. 先把 W04 revision 接入真实 A/B/C builder、portal payload/JS 和统一交付读取入口；消除 `latest.json` 与 `current.json` 的旁路双轨，并让真实图/表/叙事/索引/来源指针消费同一事实版本。
2. 修复 current 事务边界：发布前验证完整 bundle 不变量；用 journal/两阶段恢复覆盖 pointer、event、request DB 的所有故障点，确保任何返回失败都不会暴露半提交 current。
3. 将 impact DAG 建自真实依赖与实际页面/产物身份，不用“全部事实连接全部影子 artifact”的合成图代替。
4. 重做 `compare_refresh` 为完整 typed 三方字段并接入 RefreshService；补遗漏字段、异值冲突、撤回和 lineage 反例。
5. 按统计对象收紧数值规则：仅明确受试者粗率限制 n<=N/自动重算，事件次数、人时率、adjusted rate、LS mean 分别处理。
6. 用真实 A/B/C 当前页面重跑保存→故障→恢复→撤销→刷新浏览器旅程，生成独立机器可读 evidence manifest，绑定 source/current/artifact/DOM/console/screenshot hashes；再交新的独立只读复审。

本次 FAIL 仅否定 W04 工程风险闭包；不作科学、医学、产品、全 gate、24 门户、三宿主或 RC 结论。
