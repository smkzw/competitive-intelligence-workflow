# W04 实际事实编辑、派生与跨报告原子同步结果

## 2026-09-23 第五次独立复审终态

- **W04 工程风险闭包：PASS。** 全新上下文第五次独立复审
  `W04-independent-rereview-4.md`（SHA-256
  `c81e71537d8288844079346716527cb75aef06aaadfb182aba06ef959767b4d1`）确认
  `P0=0 / P1=0 / P2=0 / P3=1`。前四份 FAIL 原文与失败现场继续保留，不以最终 PASS
  覆盖历史。
- 独立复审重跑 `118 passed`，复算 v6 的 23 个 source、36 个 artifact 和 3 份 builder
  input，并确认 artifact、目标行、非目标字段、任意字节以及额外路径逃逸/重复成员篡改均失败关闭。
  完整科学 binding、来源与用户修订分层、原 A/B/C 消费者重建、immutable generation +
  SQLite committed selector、three-way、统计对象和 loopback/API 边界均通过本包验收。
- 唯一 P3：A 基础行没有 `source_text/source_field_path` 时，“依据与说明”可显示字面量
  `None`；不影响 W04 来源归因或事实一致性，转入 W05 视觉/空值呈现修复清单。另将 verifier
  的最终 symlink 检查改为未 resolve 路径逐组件检查，作为后续小型硬化项。
- 此 PASS 只关闭 W04 工程风险，不代表全 gate、24 门户、W05 四视口视觉、三宿主、正式
  科学/医学/产品/用户或 RC 接受。请求模型/effort 仍无可核验回执，保持 **UNVERIFIED**。

## 2026-09-23 第四次独立 FAIL 后 P1-01/P2-01 修复（当前有效结论）

- W04 正式 verdict 仍为 **FAIL，待第五次独立只读复审**。第四份独立报告
  `W04-independent-rereview-3.md` SHA-256 为
  `fdc4e7f124452ce5246ba764528fd07c1be0f4cf0940a078ab3d442f0355bbc2`；四份独立报告原文均
  未修改。v5 及更早清单仅保留为历史失败现场，不能作为当前验收证据。
- P1-01 将用户修订值与原来源证据严格分层。A/B/C active projection 只改变当前显示值、
  `review_state=user_modified` 和用户编辑 provenance；原 `source_text/original_text`、结构化
  locator、source version、fragment id 保持 base 原值。原消费者图表/表格明确显示“用户修订，
  未独立复核”，来源抽屉并列当前用户值与原来源值、原文、定位和版本。B 科学分组投影现将
  `_user_edit` 注记带回原消费者行，修复了浏览器旅程发现的表格状态标签丢失。
- P2-01 升级为 v6 证据闭包：A/B/C 三份冻结 builder input 都是 manifest artifact；verifier 逐
  report 校验 delivery 路径/边界/哈希/实际字节/唯一清单成员，并从冻结输入重算 receipt binding
  与 original-row digest。artifact、目标行、非目标 indication、任意字节四类内存篡改均失败关闭。
- 集中 RED：`2 failed, 44 deselected in 2.02s`，分别命中缺少分层 `user_edits` 和缺少 v6
  verifier。最终完整 W04 相关批为 **`118 passed in 43.51s`**。Ruff（新/typed 文件全规则，
  A/B/C legacy builder 使用 F401/F821/I001 受影响规则集）、8 文件 strict mypy、
  `git diff --check` 均通过。
- 当前有效清单为
  `W04-remediation-real-portal-v6-final-3/evidence-manifest.json`，SHA-256
  `f2657c431875098860544bc8c4bbed0b2063c8dc80515f10b67e89c9c2c7e814`；formal verdict 为
  `FAIL_PENDING_FIFTH_INDEPENDENT_REVIEW`。它按 UTF-8、Unicode 路径排序和
  `path + NUL + sha256(raw bytes) + LF` 绑定 23 个 source inputs、36 个 artifacts，dirty source
  digest 为 `96cbcf9b67800c684f7631af1ab0c9daea2d9be7cf3923d17397677df1536ded`。正常复算：
  `checked_artifacts=36 / checked_builder_inputs=3 / checked_sources=23 / error_count=0`；四类篡改
  probe 的 `error_count` 分别为 `1/3/2/2`，均 `tamper_rejected=true`。

### v6 真实浏览器旅程

- Headed Chromium 通过实际 loopback 编辑器把同源 C 行从 `EASI >=16.0 分` 保存为
  `EASI <=18.0 分`，得到 revision 3，仅重建 C；selected generation SHA-256 为
  `8c84b88e89c94f422c87b46ec4a1a292a322843c04a97a6bc3e71357b28b592c`。
- A 原安全性热图显示当前 `67%` 和修订状态，抽屉并列原值 `66.2%`；B 原图表/展开表格显示
  `30 / 24 / 80` 和修订状态，抽屉并列原值 `54.8% (34/62)`、Table 3 定位与原 source version；
  C 原入选标准表显示 `EASI <=18.0分` 和修订状态，抽屉保留原值 `≥16 分`、原英文原文和原
  入选标准 locator。三页本次页面 console 合计 `0 errors / 0 warnings`。
- 三张非空截图 SHA-256：A
  `43e7eb78c7c7a2c51e70c975c2e253f2d4e7e1abd0ed65c13bedc7a547ba6653`；B
  `2a2ed64fe2cec5dbad2221b4262e7208a1567c80d70e6c396abf47cd0f623127`；C
  `e31dfaa6ed4a558f7668def7644b44394ccb356ff0f958466ff9172377b1cdb2`。三者 RGB extrema 均含
  非 255 像素，非白图。

精确核心验证命令：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/integration/test_w04_user_fact_edit.py \
  tests/integration/test_correction_service.py \
  tests/integration/test_correction_flow.py \
  tests/integration/test_incremental_refresh.py \
  tests/integration/test_latest_delivery.py \
  tests/unit/test_render_transaction.py \
  tests/integration/test_sqlite_migrations.py -q --tb=short
# 118 passed in 43.51s

PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/verify_w04_v6_evidence.py \
  --repo '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow' \
  --manifest '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/packets/2026-09-22-sol-delivery/evidence/W04-remediation-real-portal-v6-final-3/evidence-manifest.json'
# checked_artifacts=36; checked_builder_inputs=3; checked_sources=23; error_count=0

# 在同一命令末尾分别添加：
# --tamper-check artifact | builder-target | builder-nontarget | builder-byte
# error_count=1 / 3 / 2 / 2；四项 tamper_rejected=true
```

仍未验证：第五次独立复审、全 gate、24 门户、全页/多视口视觉、三宿主和正式科学/医学/产品/
RC 接受。未进入 W05 或视觉重构。请求 `gpt-5.6-sol:medium` 无可核验运行时 model/effort 回执，
保持 **UNVERIFIED**。

## 2026-09-23 第三次独立 FAIL 后 P1-01/P1-02 重构（当前有效结论）

- W04 正式 verdict 仍为 **FAIL，待第四次独立只读复审**。第三份独立报告
  `W04-independent-rereview-2.md` SHA-256 为
  `eb846e42233001b3924b130b8ce691e1274484ecebc0aa7a8173929396dbeb98`；连同前两份独立
  FAIL 原文均未修改。v4 现仅为历史失败现场，不再作为有效验收证据。
- P1-01 改为不可漂移的完整科学身份：report/collection/row、product/drug、trial/registry、
  group/arm/cohort/period、endpoint 或 event、statistical form、measure object、unit/normalized
  unit、source version/pointer、original-row canonical SHA-256。A/B/C 原 builder 在创建任何
  staging 前统一逐项复算并校验；stale row、同 row 异科学身份、原行摘要漂移、A→B/C 错绑均
  fail closed。receipt 及 impact binding 均记录完整已验证身份；不同事实分别只重建实际消费的
  报告。实际旅程中 A/B/C 报告 revision 分别为 `1/2/3`，各自 request_id 绑定各自 transaction，
  不再强迫一条事实覆盖三个无关原行。
- v5 setup 暴露并修复了一个真实 bug：旧校验把全局最新 request_id 错用于所有历史报告事务，
  使 A revision 1 后仅重建 B revision 2 无法发布。`CurrentReportDelivery` 现保存报告级 request_id，
  全局 request_id 只表示 selector 的最新提交。
- P1-02 改为不可变 `reports/generations/<sha256>.json` 加 SQLite
  `current_delivery_state` committed selector。`reports/current.json` 是稳定、无 revision 的公开协议
  描述符；任何 reader 只读取 durable selector 指向的 generation。generation 文件完全写入并
  file/directory fsync 后才进入单个 SQLite FULL 同步事务；不再覆盖 raw pointer 后尝试二次 replace
  回滚。generation replace/fsync、DB、event、journal 故障均保持已提交 selector；提交结果无法分类
  时显式抛出 indeterminate。进程重启后同 request 从 journal/event/request 状态精确恢复。
- 集中 RED 保存于 `W04-rereview2-red/pytest-red.txt`（SHA-256
  `5967956f33059481e27ea76770a3db8d6a22b788edaf3f4844ccbdd47f70075c`）：
  `9 failed, 23 deselected in 9.16s`。扩展后的最终 W04 相关批为
  **`116 passed in 40.57s`**；聚焦 W04 文件为 `44 passed in 39.41s`。Ruff 通过，7 个 W04 typed
  source/tool 文件 strict mypy 通过，`git diff --check` 通过。
- 当前有效证据为
  `W04-remediation-real-portal-v5-final/evidence-manifest.json`，SHA-256
  `c9e350ca23b88261c60694a8fb328694522672567d8d7b57e7816f8576c0c86d`。清单按 UTF-8、Unicode
  路径排序、`path + NUL + sha256(raw bytes) + LF` 对 13 个明确输入复算 dirty digest
  `02a11de46e1896a66bd290c307b475718870a27f67b492216260504f94c29c32`，绑定 39 个 runtime、
  raw contract、selector、immutable generations、只读 DB 摘要、event、全部 journal、三份
  transaction/identity receipt、DOM/console/screenshot 工件。独立 verifier 为
  `checked_artifacts=39 / checked_sources=13 / error_count=0`；将首个 artifact SHA 改为 64 个零的
  内存篡改探针返回 `error_count=1 / tamper_rejected=true`。

### v5 真实浏览器旅程

- Headed Chromium 从实际 `127.0.0.1:8765` 编辑接口把同源 C 原行
  `c-nct04178967-inclusion` 从 `EASI >=16.0 分` 保存为 `EASI <=18.0 分`，revision 3 仅重建 C。
  随后从 `127.0.0.1:8766` 打开原 A/B/C 门户：A 原安全性热图显示任何 TEAE `67%`；B 原图表、
  展开表格和来源抽屉显示粗率 `30`、分子 `24`、分母 `80` 与 ClinicalTrials.gov；C 原入选标准表
  和来源抽屉显示 `NCT04178967 / EASI <=18.0分` 及同一来源。页面不显示内部 fact id 或平行同步
  组件。A/B/C 三个新鲜页面分别为 `0 errors / 0 warnings`。
- 四张非白门户截图 SHA-256：A
  `9ed1718b45a40981f7cb02b5d6914b555fd8fbebd49aa001dc37bea98f5c2e1e`；B 原表
  `f942d7a927112cbb2768cb07117540e2d3550e6153c106cb4fdffaa65680c26e`；B 来源抽屉
  `24e5899c5aafbc97ce86363e313eca952239f10e952d0068dfed946bede4c174`；C
  `5b426a2f83178eaf6866cfc9ca06908ad8ba6c253cf84890da930386a22c673d`。

精确验证命令：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/integration/test_w04_user_fact_edit.py \
  tests/integration/test_correction_service.py \
  tests/integration/test_correction_flow.py \
  tests/integration/test_incremental_refresh.py \
  tests/integration/test_latest_delivery.py \
  tests/unit/test_render_transaction.py \
  tests/integration/test_sqlite_migrations.py -q --tb=short
# 116 passed in 40.57s

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/verify_w04_v5_evidence.py \
  --repo '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow' \
  --manifest '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/packets/2026-09-22-sol-delivery/evidence/W04-remediation-real-portal-v5-final/evidence-manifest.json'
# checked_artifacts=39; checked_sources=13; error_count=0

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python tools/verify_w04_v5_evidence.py \
  --repo '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow' \
  --manifest '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/packets/2026-09-22-sol-delivery/evidence/W04-remediation-real-portal-v5-final/evidence-manifest.json' \
  --tamper-check
# error_count=1; tamper_rejected=true
```

仍未验证：第四次独立复审、全 gate、24 门户、全页/四视口视觉、三宿主、正式科学/医学/产品/RC
接受。W05 宽屏利用率及纵向信息密度未在本轮扩张。请求 `gpt-5.6-sol:medium` 无可核验运行时
回执，继续 **UNVERIFIED**。

## 2026-09-23 第二次独立 FAIL 后定向修复（历史记录，已被第三次 FAIL 取代）

- W04 正式 verdict 仍为 **FAIL，待第三次独立只读复审**。首轮报告
  `W04-independent-review.md`（SHA-256
  `ae71fd6ae67e4d3e12045a978a2cf0729ad5578bdefdc2671e1740f0ffd6eecd`）和第二次报告
  `W04-independent-rereview.md`（SHA-256
  `37c7cc732d3b8b67196972e798eca7037b4496a89dba8f7dd9beb0bbcc6b2e90`）均保持原文不变。
  本节仅记录 P1-01/P1-02/P2-01 的实现侧关闭，不冒充独立接受。
- P1-01：A/B/C 原 builder 现在直接接受 active revision facts，并重建原安全性
  series/rows、原表格行、原叙事、原 search index 和原 source binding。运行路径不再调用
  `fact_revision.py`；该旧 helper 已隔离为 forensic compatibility，不再输出
  `user_fact_revision` 或“当前事实同步”组件。consumer receipt 由各原 builder 在实际渲染时记录
  chart/table/narrative/index/source 的具体页面与行身份，impact DAG 只使用这些实际 receipt。
- P1-02：`reports/current.json` 的原始 pointer 被改为最后一步切换；DB request、event 和 ready
  journal 均先持久化。pointer replace 后目录 fsync 失败会按保存的旧字节回滚并再次 fsync，错误不再
  吞掉；所有失败返回均保持 raw pointer 旧字节。EventStore 在锁内识别有效 JSONL 前缀，以完整临时
  流 fsync + replace + 目录 fsync 提交；模拟半条写入后，同 request 重试会截断损坏尾、保留历史有效
  记录并完成。
- P2-01：有效证据升级为
  `W04-remediation-real-portal-v4/evidence-manifest.json`（SHA-256
  `bce5c414ca4ea00d6f375f5994b969a34b8cc65532ffedfe508fa9f0241359ff`）。v4 明确定义 dirty
  digest 为：13 个列明输入，按 Unicode codepoint 路径排序；每条为 UTF-8
  `path + NUL + sha256(raw bytes) + LF`，再做 SHA-256；复算值
  `9c5d95e88c75aef771c116e87b54a45d96b5369d8efa06c465991f4ff44918ce`。清单还绑定
  browser/fault/final 三份 journey、最终 raw current、只读 DB 摘要、event stream、全部 3 个
  journal、revision 3 A/B/C transaction 与 builder consumer receipt，以及四张非空截图。

### 第二次复审反例 RED / 成批 GREEN

集中 RED 日志 `W04-rereview-red/pytest-red.txt`（SHA-256
`4911257b21ae8d002d62518c1e183c55958e0b1fc48422cda8d035b7b56ed4a6`）为
`4 failed`：去除 revision metadata 后原领域 payload 不变、event 失败后 raw current 改变、半条
event 导致同 request 无法恢复、v4 digest/manifest 不存在。修复后一次相关完整批：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/integration/test_w04_user_fact_edit.py \
  tests/integration/test_correction_service.py \
  tests/integration/test_correction_flow.py \
  tests/integration/test_incremental_refresh.py \
  tests/integration/test_latest_delivery.py \
  tests/unit/test_render_transaction.py \
  tests/integration/test_sqlite_migrations.py -q --tb=short

95 passed in 38.58s
Ruff（W04 typed files/tests + A/B/C 既有 debt exclusions）: All checks passed!
strict mypy（10 个 W04 typed source/tool files）: Success: no issues found
git diff --check: pass
```

独立清单复算命令：

```text
uv run python tools/verify_w04_evidence.py \
  --repo '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow' \
  --manifest '/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/packets/2026-09-22-sol-delivery/evidence/W04-remediation-real-portal-v4/evidence-manifest.json'

checked_artifacts=19; checked_sources=13; error_count=0
```

### 新真实门户旅程

- Chromium 通过实际 loopback 编辑页保存 revision 2 阈值 `<=9.5 g/dL`；随后直接打开真实
  A/B/C 门户，而非编辑测试页。A 原安全性热图与原明细行显示 `30%`、`24/80人`、更新叙事和
  `registry.results.safety[0]`；B 原 event-rate 图、展开表格和证据抽屉显示 `30`、分子 24、分母
  80 及来源版本；C 原入选标准表、search index 和证据抽屉显示 `≤9.5g/dL` 与原文
  `筛选期血红蛋白浓度：<=9.5 g/dL。`。三页均不显示同步卡片、内部 fact id 墙或
  `user_fact_revision` overlay。
- 本次 A/B/C 页面各自 console 均为 `0 errors / 0 warnings`。四张截图像素 extrema 均跨越非白
  区间；SHA-256 依次为 editor
  `3e6ff0d64faeda6e274200c262d99ca6a252155a0d6ecc781e47a8fc77504d2b`、A
  `c92d7eb90bc405a9601712bb62eeb06ac3c6f800d039762a5a585f67898f170a`、B
  `a6e4815e7a480d4e7a7d6177c467ac95064e62678c6be3fa86c67de6771bf723`、C
  `1dcf31d1c005d3e1255606ae29b54512391bfe9b04d1c0011a18b6ce63b4458a`。
- revision 3 undo 后 raw current SHA-256 为
  `c762eeea2cdc7b2d9c5858139e6436c057974e395f0f5e82c9619719f383b5c1`；A/B/C transaction
  SHA-256 分别为 `575907b939538761c98be57957334e2ffa34f1b98e9de7a9c781408d2baba6f9`、
  `e58a6e24e0808853ad109cf70631efd6c5e232f03a5318d77cab87a804759498`、
  `3179bf1dfadb532d904b07cdbd7d3899aab21752f4de8e21fee58e9eed216923`。refresh 冲突保留
  base/user/source 三方字段与显式 resolution 要求。

仍未验证：第三次独立复审、全 gate、24 门户、全页/四视口视觉、三宿主、正式科学/医学/产品/
RC 接受。A/B/C 大型 legacy builder 的全文件 strict mypy 仍有既存债务；本次通过的是 10 个 W04
typed source/tool 文件及相关运行时/集成检查。W05 宽屏利用率与纵向信息密度未在本轮扩张。
请求 `gpt-5.6-sol:medium` 无可核验运行时回执，继续 **UNVERIFIED**。

## 2026-09-23 首轮独立 FAIL 后修复（历史记录，已被第二次 FAIL 取代）

- 权威状态仍为 **FAIL，待新的独立只读复审**。原审阅
  `W04-independent-review.md` 保持不变，SHA-256
  `ae71fd6ae67e4d3e12045a978a2cf0729ad5578bdefdc2671e1740f0ffd6eecd`。
  下方旧 PASS 是审阅前历史自验，已被本节取代。
- 实现侧已关闭全部 P1/P2 与 P3-01：fact revision 直接写入既有
  `window.REPORT_A/B/C.user_fact_revision`，实际消费者页加载同一
  `data/report.js`，渲染图、表、文字、来源指针并更新既有 search index；不再生成
  `w04-*.json`。存在 user current 时 `read_latest_delivery` 拒绝旁路。
- publish/read 复用 duplicate/report revision/fact digest/逐文件哈希/transaction
  manifest/portal receipt/消费者闭包校验。durable journal 采用
  `prepared -> pointer -> request DB -> event -> committed` 可见性屏障；replace、fsync、
  DB、event、journal commit 故障中，任何返回失败均不暴露新 current，同 request 可精确恢复。
- impact DAG 来自 portal receipt 的真实 report/page/fact/文件消费者身份，不再做
  facts×artifacts 全连接。RefreshService 持久化 base/user/source 字段并集、三方值、
  presence、来源版本、谱系、状态和 resolution options，并验证 user 沿 base 的 typed
  save 谱系。`n<=N` 与自动粗率只用于 participant crude rate；events、person-time、
  adjusted rate、LS mean 和无关同数字事实均有反例。
- `/api/import` 已移除，只保留 `/api/save`。实际浏览器负例：import=404、multipart
  save=415。

### RED / GREEN

独立审阅反例集中 RED：

```text
6 failed, 30 passed in 10.90s
```

最终完整 W04 相关批：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/integration/test_w04_user_fact_edit.py \
  tests/integration/test_correction_service.py \
  tests/integration/test_correction_flow.py \
  tests/integration/test_incremental_refresh.py \
  tests/integration/test_latest_delivery.py \
  tests/unit/test_render_transaction.py \
  tests/integration/test_sqlite_migrations.py -q --tb=short

91 passed in 18.32s
Ruff: All checks passed!
strict mypy: Success: no issues found in 8 source files
git diff --check: pass
```

浏览器旅程还实际暴露并修复了两个此前测试未覆盖的 bug：跨 revision 重复追加消费者、
B/C 实际页面未加载 `data/report.js`。两项均加入回归；另补 pre-replace current 文件
fsync 故障反例，末次完整批为 91 passed。

### 真门户完整旅程与证据

有效目录为 `evidence/W04-remediation-real-portal-v3/`，输入是既有
`runs/pnh-vertical/abc-v106/reports/{A,B,C}/v1/html`。较早 v1/v2 修复目录保留失败现场，
明确不作为有效证据。

1. Chromium 在真实 loopback 保存 24/80，revision 1 粗率为 30%。
2. revision 2 阈值保存注入 event 故障；返回失败后 reader 仍看到 revision 1；同 request
   重试恢复到 revision 2、`<=9.5 g/dL`。
3. A `clinical-portfolio`、B `baseline-disease-context`、C `inclusion-criteria` 三个真实页面
   均断言单一消费者、revision 2、图=1、表=1、文字=1、来源指针=1、搜索结果=1，digest
   同为 `97c4445320f4810c488e3bf81bda6f19441a9391c4fad9b4500bf0036946a7bd`。
4. A safety 真页面显示 `30% (24/80)`，adjusted rate 仍为 `23.7%`；最终事实同时断言
   LS mean=`20.0`、无关事实仍是 `fact-unrelated-20-v1`。
5. undo 追加 revision 3，C 真页面恢复 `<10 g/dL`；RefreshService 随后持久化
   numerator base=20/user=24/source=22 的显式 conflict。
6. 新鲜 `w04-final-clean` 会话为 `0 errors / 0 warnings`。五张有效截图均通过像素非空检查。

机器清单 `W04-remediation-real-portal-v3/evidence-manifest.json` SHA-256 为
`2610a9dc344ce45568b6b37d03277b10ccb738a8c7266f8c8add14e23b5a25d2`，绑定：

- dirty source digest
  `a2c208c689dde2883e51447c1f9c4ceaddcafe6b324e8cf549c442984d34e732`；
- revision 2 A/B/C transaction manifest SHA-256
  `57c976992543e73a9e76d1096b5834bdbf2bf74e92926940b4b700a2e907b04b`、
  `c1a1d0b44ddabf581e5030286c06c0046f241d168b4f025e49f6a96286394303`、
  `173699e3fad31931e6616c2ec44732fc179ff34a8d608c35e179407f40a3cc94`；
- 最终 revision 3 current SHA-256
  `0a721caf6b83b0b0b33e4e7e14f316f51deba1f1d936915f023022e1436158fe`；
- DOM/console、截图像素与哈希、runtime journey、DB/current/transaction receipts。

截图 SHA-256：A rate
`1d2dca0a4ba06b5bf9b983b7340ac2d9e502bdd16fb023e65130ccec92355d35`；A/B/C
threshold 分别为 `7afc9015bbe9c79f257f476a2a148a185e0ff5c70449542224bc094bf9501271`、
`0ea99f20b1bead25617e060760522f2f54874df5cb5aaf45c40234e7228e15de`、
`d71db6a1c88515c4f3c3439591ab1380b729e6a5acafe321069ecead8c832edb`；C undo
`9a3374554774a58f55656552135a0ac5b2aa62422896ba8d5c455d660f451ee9`。

仍未验证：新的独立复审、全 gate、24 门户、全页/全 viewport、三宿主及正式科学/医学/
产品/RC 接受。未进入 W05。模型/effort 无回执，仍为 **UNVERIFIED**。

## 结论与边界

- 历史工程自验结论曾记为 PASS；该结论已被独立 FAIL 和上方当前修复状态取代，**不得作为当前 W04 PASS**。
- 此结论是工程验证，不是独立科学接受、正式医学/产品/RC 接受。新版本均为 `review_state=user_modified`，不会继承旧版本 `accepted`。
- 请求运行时为 `gpt-5.6-sol:medium`；当前会话没有可核验 model/effort 回执，因此身份 **UNVERIFIED**。
- 唯一工程根为英文工程。保留 W00–W03 与其他既有脏树；未 commit/push/add/reset/checkout/clean，未删除未跟踪资料，未进入 W05，也未派子代理。

## 实施面

1. `UserFactSaveCommand` 封闭定义 target 身份、可编辑字段、`expected_revision`、`request_id`、用户依据、保存者与时区时间；同 request 同 payload 返回原结果，同 request 异 payload 拒绝，旧 revision/两标签并发显式冲突。
2. n/N、时间、时间窗、单位、完整医学/统计语义及 C 阈值均追加新事实版本；旧事实、原 source quote 与 evidence edge 不变。撤销同样追加 `user_modified` 新版本。
3. 影响图覆盖事实→派生数值/医学语义/分面→图表/表/叙事/索引/来源指针→页面/格式，拒绝环、悬空及跨 revision 边。仅 `statistical_form=crude_rate` 且有明确 n/N 时重算；reported adjusted rate 与 LS mean 不被覆盖，同数字无关事实不联动。
4. 所有已存在且受影响的 A/B/C 站点分别在 staging 复制并重建实际 JSON/HTML 文件；每份交易 manifest 绑定 report、revision、事实闭包和逐文件哈希。全部完成后只原子替换一次 `reports/current.json`；中断/失败保留旧完整 current，精确重试可复用已完成候选。缺失报告不会凭空生成。
5. 事件追加增加文件锁；保存写入真实 event store。`compare_refresh` 产生字段级 unchanged/user-only/refresh-only/converged/conflict，并将双方同字段异值持久化为需显式解决的冲突，不静默覆盖。
6. loopback 首版只绑定 `127.0.0.1`，严格 Host/Origin、HttpOnly SameSite session、CSRF、固定资源路径、JSON 类型和 64 KiB 上限；无 wildcard CORS、`file:`/`null`、shell、任意路径或 multipart 导入面，current/站点拒绝 symlink。

## RED / GREEN

初始集中 RED（实现前）：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/integration/test_w04_user_fact_edit.py \
  tests/integration/test_sqlite_migrations.py -q --tb=short

collection error: No module named ci_workflow.application.user_fact_edit
1 error in 0.14s
```

实现后首轮为 `11 passed / 2 failed`；两项均为新测试夹具问题（嵌套临时目录未创建、阈值负例没有实际改变字段），修正夹具后进入 GREEN。最终规定的一次完整相关集成批：

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider \
  tests/integration/test_w04_user_fact_edit.py \
  tests/integration/test_correction_service.py \
  tests/integration/test_correction_flow.py \
  tests/integration/test_incremental_refresh.py \
  tests/integration/test_latest_delivery.py \
  tests/unit/test_render_transaction.py \
  tests/integration/test_sqlite_migrations.py -q --tb=short

80 passed in 2.39s
```

补强/格式修订后的聚焦回归分别为 `13 passed in 1.34s` 和 loopback 末次 `8 passed in 1.24s`。Ruff、strict mypy（6 个生产文件）、Python compile、两份 JSON schema 解析、`git diff --check` 均通过。

测试覆盖：typed 字段、原版本/quote 不变、粗率选择性重算、C 阈值、时间/单位/语义、撤销、幂等 payload 漂移、两标签与线程并发、刷新三方冲突、DAG 环/悬空/跨 revision、中断后旧 current、恢复重试、A/B/C revision/hash/引用闭包、Host/Origin/session/CSRF/类型/大小/路径及 symlink 攻击。

## 完整浏览器编辑旅程

实际服务：`python -m ci_workflow.application.user_fact_edit_server --project <W04-browser/w04-project> --port 8765`；实际 Chromium headed 旅程使用 Playwright CLI。

1. 初始 UI 显示 `revision 0`、n=`20`、N=`80`、C 阈值 `<10.0 g/dL`。
2. 将 n 改为 `24`、N 保持 `80`，点击“保存人数粗率”。返回 `revision 1`、`derived_crude_rate=30`、`review_state=user_modified`、`rebuilt_reports=[A,B,C]`。
3. 将 C 阈值改为 `<=9.5 g/dL`，点击“保存 C 阈值”。返回 `revision 2`、`review_state=user_modified`、`rebuilt_reports=[A,B,C]`。
4. UI 明示“用户修订，未独立复核”。
5. 截图：`W04-browser/01-rate-24-of-80.png` SHA-256 `3118793330a1ef207c4e46629964d357d3141be1cc8656f93112888088f2255b`；有效替换后的 `W04-browser/02-threshold-revision-2.png` SHA-256 `062f0b407a46ea70a2fbdbcf9bcef108828c7148339b1a0657a1b021933ca999`。

### revision 2 截图证据修复

主线程复核发现原 `02-threshold-revision-2.png`（旧 SHA-256 `3878570f4a62a0d65f57cf1754e0269e56ec797f4e36e26b44c172eb6e800401`）为 `1280×720` 全白图，不能作为浏览器证据。该截图已在不改变 DB、current、产品逻辑或 revision 的前提下，被同路径的新截图覆盖替换；旧白图不再作为有效证据。

修复使用独立 Playwright 会话 `w04-evidence`，先从真实服务读取现有 revision 2 页面，再断言实际 DOM：status 精确为 `当前 revision 2；用户保存后不继承独立科学接受。`，阈值控件精确为 `<=`、`9.5`、`g/dL`，人数控件为 `24`、`80`，页面正文同时包含“C 阈值”和“人数粗率”。返回结果：

```text
{"url":"http://127.0.0.1:8765/","title":"事实修订",
 "status":"当前 revision 2；用户保存后不继承独立科学接受。",
 "threshold":"<=9.5 g/dL","rate":"24/80","bodyTextLength":102}
```

本次命名会话的 console 查询为：

```text
Total messages: 0 (Errors: 0, Warnings: 0)
```

新截图采用实际页面 `body` 元素捕获，像素检查命令使用 Pillow 的 `ImageStat`、与纯白图的 `ImageChops.difference` 及非白掩码；断言非白 bbox 存在、非白像素大于 1000、至少一个通道低值小于 250。实际结果：

```text
size=[860,566], mode=RGB
mean=[245.987478,244.469108,245.139214]
extrema=[[0,255],[0,255],[0,255]]
nonwhite_pixels=72119 / 486760
nonwhite_ratio=0.148161
nonwhite_bbox=[0,7,860,566]
SHA-256=062f0b407a46ea70a2fbdbcf9bcef108828c7148339b1a0657a1b021933ca999
```

精确执行入口：

```text
.venv/bin/python -m ci_workflow.application.user_fact_edit_server \
  --project packets/2026-09-22-sol-delivery/evidence/W04-browser/w04-project \
  --port 8765
/Users/smkzw/.codex/skills/playwright/scripts/playwright_cli.sh \
  -s=w04-evidence open http://127.0.0.1:8765 --headed
/Users/smkzw/.codex/skills/playwright/scripts/playwright_cli.sh \
  -s=w04-evidence run-code "async page => { const status=(await page.locator('#status').innerText()).trim(); const op=await page.locator('#threshold-operator').inputValue(); const value=await page.locator('#threshold-value').inputValue(); const unit=await page.locator('#threshold-unit').inputValue(); const numerator=await page.locator('#numerator').inputValue(); const denominator=await page.locator('#denominator').inputValue(); const bodyText=(await page.locator('body').innerText()).trim(); if(status!=='当前 revision 2；用户保存后不继承独立科学接受。') throw new Error('revision text mismatch'); if(op!=='<='||value!=='9.5'||unit!=='g/dL') throw new Error('threshold DOM mismatch'); if(numerator!=='24'||denominator!=='80') throw new Error('rate DOM mismatch'); if(!bodyText.includes('C 阈值')||!bodyText.includes('人数粗率')) throw new Error('body text missing'); return {url:page.url(),title:await page.title(),status,threshold:op+value+' '+unit,rate:numerator+'/'+denominator,bodyTextLength:bodyText.length}; }"
/Users/smkzw/.codex/skills/playwright/scripts/playwright_cli.sh \
  -s=w04-evidence console
/Users/smkzw/.codex/skills/playwright/scripts/playwright_cli.sh \
  -s=w04-evidence screenshot body \
  --filename packets/2026-09-22-sol-delivery/evidence/W04-browser/02-threshold-revision-2.png \
  --type png
.venv/bin/python - <<'PY'
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
path = Path('packets/2026-09-22-sol-delivery/evidence/W04-browser/02-threshold-revision-2.png')
with Image.open(path).convert('RGB') as image:
    stat = ImageStat.Stat(image)
    difference = ImageChops.difference(image, Image.new('RGB', image.size, 'white'))
    mask = ImageChops.lighter(
        difference.getchannel('R'),
        ImageChops.lighter(difference.getchannel('G'), difference.getchannel('B')),
    )
    histogram = mask.histogram()
    total = image.width * image.height
    nonwhite = total - histogram[0]
    assert difference.getbbox() is not None
    assert nonwhite > 1000
    assert any(low < 250 for low, _high in image.getextrema())
    print(image.size, stat.mean, image.getextrema(), nonwhite, total, difference.getbbox())
PY
```

本证据修复未执行保存请求，数据库仍为 revision 2；未发现实际旅程产品 bug，未修改产品逻辑。

## 实际 DB / 文件闭包

- `reports/current.json`：revision `2`，SHA-256 `b8182173a4117049e2083aee8b0522317b6d468f4a0ad02c161276520da16067`。
- A/B/C 的 `fact_revision_digest` 均为 `7ecac20fad55ed1448a0f937313eee79bd38640370d779e531c92979df51ea23`；每份当前站点均绑定 8 个实际文件（legacy、chart、table、narrative、index、source pointer、projection、HTML）。
- A/B/C revision 2 事务 manifest SHA-256 分别为 `59c21bc65d470812e1f03f512320082d93f7ad52b82540759bea85bfa01a173c`、`8a88b115dc9b92b7b6d066063e9abcff7709168a79837c7913e3e2b94b030f6d`、`13ac950caeebe8be71d46286a8605992e01ceee7deb2f218465d3d8292e95bf2`。
- DB 新版本：粗率 `30% (24/80)`、阈值 `<=9.5 g/dL`，均 `user_modified`；旧 `25% (20/80)` 和 `<10 g/dL` 仍为原 accepted 行。adjusted rate `23.7%` 与无关事实 `20` 保持原版本；LS mean 由测试闭包确认不变。
- 两个浏览器 request 均为 `complete`，revision 分别为 1、2；粗率 derivation 明确记录公式 `numerator / denominator * 100` 及“不覆盖调整率或 LS mean”的适用范围。

## 源文件哈希

```text
133f35909128e7f97c07fab3826c7cb9334bc5a6df1ad4dfaf1dacd280f2d9c3  migrations/0012_user_fact_edits.sql
265331aa9dc697d88e0880b95d4b9699953b147bad1f2eb768618647d1faa264  schemas/fact.schema.json
adbafa51e371fc689bcfc9872d046921b2fe705bad2bc3aef0e4e5ea930cb00d  schemas/user-fact-save.schema.json
2f61185592116699fefd4553d6b958c455edb3a3e68dc4010fb1efc1ce1a57b3  src/ci_workflow/application/latest_delivery.py
d22d6e8a3fb678c2985a6769a5a5f51b647a1d03372d90c95d6339f86ea6e21d  src/ci_workflow/application/user_fact_edit.py
f280991fda439694f412f65435ef750f3f04d9563923faf9899fd73e80641696  src/ci_workflow/application/user_fact_edit_server.py
2afbbab796c8912b02f2e28710eeb90c126dbaf007e732d8efc556767c89405d  src/ci_workflow/domain/enums.py
a39b44e7e716d39873267269cabc24be8224c886f67f33da8d143e9b9ef6b5ab  src/ci_workflow/graph/impact.py
a215acd4634f907bef135bb04e47bdbc4c0061d35d0ff403275e3f894f0ad0e7  src/ci_workflow/storage/event_store.py
979c3be4c505ba3c7484024e85bfb4797d39edf27771181136288aec5fab6163  tests/integration/test_sqlite_migrations.py
faebf8b7892da9e5ce4f2f7a6e7161b80981e235a319eefe080db48c513fbfae  tests/integration/test_w04_user_fact_edit.py
```

基线保持 `main` / `HEAD=2df24bb441e555f20b233ad2011b4ffd3610655b`。

## 未验证与下一安全动作

- 未跑全 gate、24 门户、全页/全 viewport 视觉、三宿主、真实生产资料的全量 A/B/C 重建或正式医学/产品/RC 接受；这些不在 W04 本轮允许范围。
- 未做独立模型复核：用户指定本线程为唯一实现写入者并禁止派子代理；工程结论依赖确定性测试、真实文件/DB 闭包和实际浏览器旅程。
- W07 可接 `compare_refresh` 的显式三方冲突结果；W05 可消费本包编辑入口，但本线程不进入 W05。
