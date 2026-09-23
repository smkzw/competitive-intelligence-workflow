# 2026-09-23 W05A v6 独立复审终态与无损暂停准备

## 当前有效状态（本节取代下方“v6 待独立复审”）

- **W05A 前端响应式返修范围已独立通过；W05A 正式整体门仍为 FAIL。** 独立报告为
  `evidence/W05A-independent-rereview-v6.md`，SHA-256
  `c92e6926bd8ade9e4601401805cd45667f424e5daca7357012a6f4b01a07289b`。
- 305/320/390/1024/1440/1920 六档响应式硬门通过。独立 Chrome 在请求 305px、实际内容宽
  290px 的更苛刻条件下，核心单元底边为 562.6px，仍在 568px 首屏内；正文不低于 16px、阶段
  标签不低于 14px、触控不低于 40px，无页面或局部横向滚动。1920/1440 使用真实横向矩阵，
  1024/390/320/305 使用紧凑但完整的阶段摘要和靶点折叠，不再以缩小字号换密度。
- 独立决定性批为 **`12 passed in 160.98s`**；它验证六档高负载、三档移动完整表、同一查询驱动
  图表与表格、1024 安全详情以及稳定产品链接/抽屉回焦。实现侧同批为 `12 passed in 162.02s`。
- **正式 W05A 仍不得记 PASS：**真实 A 载荷共有 4412 条疗效/安全事实，逐事实来源字段闭合为
  `0/4412`，依赖 W07；报告级公共来源清单不能替代逐事实 locator 与原文。另有 6 个共享
  pointer/drawer/focus/chart-table-sync 节点和 2 个历史 A 合同节点在当前树上精确复跑为
  **`8 failed in 290.33s`**。
- 两个历史 A 合同差异需要后续明确产品合同：疗效 endpoint/timepoint 是要求当前 DOM 全量，还是
  允许分页但必须可验证全量可达；安全性继续保留旧连续色热图合同，还是正式迁移到 observation/card
  合同。禁止通过删除或放宽测试制造绿色。
- 本轮到此停止，不进入 W05B、W05C 或 W06–W10。全 gate、B/C、24 个真实门户、三宿主、安装、
  恢复及 RC 均未验收。请求运行时 `gpt-5.6-sol:medium` 仍无可核验身份回执，记
  **UNVERIFIED**。
- 早先 `evidence/PAUSE_HANDOFF_20260923_065547.md` 是 v5 时点的历史现场，不改写；最终接管请读
  新的最终 handoff。原 Goal 保持 `paused`，不以本次局部通过伪造完成。

# 2026-09-23 W05A v6 305px 稳定性小修状态

## 当前状态（v6 待独立复审）

- **v5 独立复审仍为 FAIL；v6 仅完成305/320跨浏览器首屏稳定性小修，待新的独立只读视觉/产品复审，不宣布 W05A PASS。** 结果见 `evidence/W05A-remediation-result.md`；当前真实浏览器 receipt 为 `evidence/W05A-remediation-browser-v6/browser-receipt.json`，SHA-256 `c15c8a4a9dfafe34b3de33b4578044780ac1299ecebfba5dda8256af307700b6`。
- 真实45产品下，305×568 核心单元底边550.5px，320×568底边539.2px；两者均完整显示 universe 摘要和全部6阶段。305/320/390/1024/1440/1920 均为45产品/6阶段、正文≥16px、阶段文字≥14px、触控≥40px、页面横向 overflow=0、console error=0。
- 唯一决定性批覆盖六档高负载、305/320/390移动完整表、同 query、1024 safety 和稳定产品链接/抽屉回焦，结果 **`12 passed in 162.02s`**。v6 RED 与 GREEN 原始日志均保留。
- 本轮未改 B/C、共享 pointer/drawer、来源数据、独立复审或历史证据。真实逐事实来源闭合等既有未闭合项状态不变；不得据此进入 RC 或写成 W05A 总 PASS。
- 请求 `gpt-5.6-sol:medium` 无可核验运行时身份回执，记 **UNVERIFIED**。下一安全动作仅为 v6 独立只读复审。

# 2026-09-23 W05A 独立 FAIL 连续返修状态（v5 历史）

## 当前状态（前端返修完成，待重新独立复审）

- **W05A 尚未最终 PASS。** 独立复审 FAIL 的响应式硬门与当前可归因回归已完成实现侧连续返修；结果见 `evidence/W05A-remediation-result.md`，当前真实浏览器 receipt 为 `evidence/W05A-remediation-browser-v5/browser-receipt.json`。
- 真实 45 产品下：1920/1440 保留完整横向矩阵与双列核心筛选；1024/390/320 使用完整阶段分布摘要 + 靶点折叠分组。320 核心单元 y=406.2、h=136.2、底边=542.4，首屏完整；五档 overflow=0、最小触控=40、console error=0。
- 移动完整表为无横向滚动 6 字段卡片/定义列表；宽屏保留表格。1024 安全详情表实际维度列 104.27px、首行 99.38px、容器 948/948。产品详情稳定链接、返回状态与三层下钻保持通过。
- 测试证据：集中 RED `14 failed / 10 passed`；唯一规定相关批 `355 passed / 10 failed`；其中 2 项可归因失败在同批后修复，最终精确闭合 `3 passed`。规定批剩余 8 项为 6 项共享 pointer/drawer 基线和 2 项既有首页疗效/旧 heatmap 合同差异，原始日志与根因均保留，未通过改无关测试掩盖。
- **来源 P1-02 未闭合。** 英文工程 152 份 A payload 搜索结果为全量逐事实来源闭合候选 0；不得伪造 locator，依赖 W07。来源完备 fixture 仅证明前端来源层，不能写成真实 A 来源 PASS。
- 模型/effort 请求 `gpt-5.6-sol:medium` 无可核验回执，记 **UNVERIFIED**。全 gate、24 门户、B/C、三宿主、全站无障碍与 RC 未验；下一安全动作是新的独立只读视觉/产品复审。

# 2026-09-22 Review 与 fork 执行准备状态（历史）

## 当前状态（W05A 实现侧完成）

- **W05A：实现侧完成，待独立视觉/产品复审；未宣布最终 PASS。** 结果见
  `evidence/W05A-result.md`，真实浏览器 receipt 见
  `evidence/W05A-browser/browser-receipt.json`。运行时请求 `gpt-5.6-sol:medium` 无可核验回执，
  model/effort 记 **UNVERIFIED**。
- A 已实现完整阶段集合守恒、无 Top-N/默认排名的竞争宇宙、同查询图+折叠表、三层下钻/返回、
  产品机制/模态/企业/试验/全球中国状态/结果/来源可达、本机视图配置和 W04 编辑/来源分层；A 空
  来源字段不再显示字面量 `None`。
- 响应式共享空间令牌已进入作者源但仅由 A 专属布局消费：1920 主内容 1760 px（91.7%），
  1440/1024/390/320 主内容占宽均 100%；五档无横向溢出、最小可见触控高 40 px、console error 0，
  320×568 首屏完整宇宙摘要底边 567.5 px。真实旅程“宇宙→机制→产品→地域→试验→结果→证据
  →返回”通过。
- 新增合同集中 GREEN `9 passed`；W05A/W04/A 关键闭包 **237 passed**。更宽混合批为
  **486 passed / 49 failed**；失败涉及脏树冻结摘要/W03 hash/真实运行前置/共享抽屉及旧浏览器预期，
  未在 W05A 越界改写。因此全 gate 仍未验，不可写成全绿。
- 未进入 W05B/W05C/W06；B/C、全 gate、24 门户、三宿主、RC 均未验。下一安全动作仅为 W05A
  独立只读视觉/产品复审；用户本轮禁止派子代理，故本实现者没有自行补做或宣称独立复审。

## 当前终态（W04 第五次独立复审之后）

- **W04 工程风险闭包：PASS。** 第五次独立报告
  `evidence/W04-independent-rereview-4.md` SHA-256 为
  `c81e71537d8288844079346716527cb75aef06aaadfb182aba06ef959767b4d1`，结论
  `P0=0 / P1=0 / P2=0 / P3=1`。独立复跑 `118 passed`，v6 23 source/36 artifact/3 builder
  input 与多类篡改检查通过。前四轮 FAIL、错绑/伪原子/来源污染等失败现场均原样保留。
- 当前 W04 已关闭 typed 修订、完整科学 binding、原消费者重建、来源与用户值分层、immutable
  generation + SQLite selector、故障恢复、three-way 和 loopback/API 边界。唯一 P3 为 A 空来源字段
  显示字面量 `None`，转入 W05 空值/视觉修复；verifier symlink 逐组件硬化列为后续小修。
- 下一安全动作：进入 W05A/B/C 三门户重构，重点执行用户新增的宽屏横向画布利用、纵向/窄屏
  卡片 gap/padding/固定图高收紧和首屏信息密度门。W04 PASS 不代表全 gate、24 门户、视觉、三宿主
  或 RC。模型/effort 无可核验回执，保持 **UNVERIFIED**。

## 当前纠偏（第四次 W04 独立复审之后，晚于下方历史记录）

- W04 正式 verdict 仍为 **FAIL，待第五次独立只读复审**。第四份报告
  `evidence/W04-independent-rereview-3.md` SHA-256
  `fdc4e7f124452ce5246ba764528fd07c1be0f4cf0940a078ab3d442f0355bbc2`；四份独立报告原文均
  未修改。
- P1-01 已把 user current 层与 immutable source 层分开：A/B/C 原消费者显示当前修订值和
  “用户修订，未独立复核”；来源抽屉并列原来源值、原文、结构化 locator、source version，
  fragment 不变。B 原科学分组投影丢失状态注记的真实浏览器 bug 已最小修复。
- P2-01 v6 manifest 绑定 A/B/C 三份实际 builder input 字节；verifier 逐 report 验证 delivery
  路径/哈希/边界/清单成员，并从冻结输入重算 binding/original-row digest。artifact、目标行、
  非目标 indication、任意字节四类篡改均失败关闭。
- 集中 RED 为 `2 failed, 44 deselected in 2.02s`；最终完整 W04 相关批为
  **`118 passed in 43.51s`**。Ruff、8 文件 strict mypy、`git diff --check` 均通过。
- 当前有效证据为
  `evidence/W04-remediation-real-portal-v6-final-3/evidence-manifest.json`，SHA-256
  `f2657c431875098860544bc8c4bbed0b2063c8dc80515f10b67e89c9c2c7e814`；dirty source digest
  `96cbcf9b67800c684f7631af1ab0c9daea2d9be7cf3923d17397677df1536ded`。正常 verifier 为
  `36 artifacts / 3 builder inputs / 23 sources / 0 errors`；四类篡改 error count 为 `1/3/2/2`，
  全部拒绝。
- Headed Chromium 实际完成 revision 3 C `>=16 → <=18` 保存，并核验 A `67% vs 66.2%`、
  B `30% (24/80) vs 54.8% (34/62)`、C `<=18 vs ≥16` 的当前值/原来源并列；三页 console
  `0 errors / 0 warnings`，三张截图像素均非空。
- v5 作废为历史失败现场。未进入 W05 或视觉重构；下一安全动作仅为第五次独立只读复审。
  模型/effort 无可核验运行时回执，保持 **UNVERIFIED**。

## 当前纠偏（第三次 W04 独立复审之后，晚于下方历史记录）

- W04 正式 verdict 仍为 **FAIL，待第四次独立只读复审**。第三份报告
  `evidence/W04-independent-rereview-2.md` SHA-256
  `eb846e42233001b3924b130b8ce691e1274484ecebc0aa7a8173929396dbeb98`；三份独立报告均未修改。
- P1-01 已重构为完整科学 binding identity 和 builder 前置全量校验。A/B/C 使用三条各自同源的事实，
  当前报告 revisions 为 `A=1 / B=2 / C=3`；stale row、科学字段漂移、原行 digest 漂移和 A→B/C
  错绑均在任何 staging/receipt/current 前失败关闭。报告级 request_id 修复了后续仅重建另一个报告
  时误校验历史事务的真实 bug。
- P1-02 已改为 immutable generation + SQLite committed selector；稳定
  `reports/current.json` 仅声明 reader contract，不含 revision。generation replace/fsync 故障后 selector
  保持旧 revision，进程重启同 request 精确恢复；无 pointer rollback 路径，也不存在普通失败同时
  公开 raw 新 revision 的状态。
- 集中 RED 为 `9 failed, 23 deselected in 9.16s`；最终完整相关批
  **`116 passed in 40.57s`**，Ruff、7 文件 strict mypy、`git diff --check` 均通过。
- 当前有效证据为
  `evidence/W04-remediation-real-portal-v5-final/evidence-manifest.json`，SHA-256
  `c9e350ca23b88261c60694a8fb328694522672567d8d7b57e7816f8576c0c86d`；dirty source digest
  `02a11de46e1896a66bd290c307b475718870a27f67b492216260504f94c29c32`。清单绑定 13 个输入、39 个
  runtime/current/selector/generation/DB/event/journal/transaction/identity receipt/DOM/console/screenshot
  工件；verifier 为 `error_count=0`，SHA 篡改探针为 `error_count=1 / tamper_rejected=true`。
- Headed Chromium 实际保存同源 C 行并核验原 A/B/C 门户：A `67%`；B `30`、`24/80` 与来源；
  C `NCT04178967 / EASI <=18.0分` 与来源。三页各 `0 errors / 0 warnings`，四张截图均非白。
- v4 作废为历史失败现场。未进入 W05 或视觉重构；下一安全动作仅为第四次独立只读复审。模型/
  effort 无可核验运行时回执，保持 **UNVERIFIED**。

## 历史纠偏（第二次 W04 独立复审之后，已被第三次 FAIL 取代）

- W04 正式 verdict 仍为 **FAIL，待第三次独立只读复审**。首轮报告 SHA-256
  `ae71fd6ae67e4d3e12045a978a2cf0729ad5578bdefdc2671e1740f0ffd6eecd`，第二次报告
  `W04-independent-rereview.md` SHA-256
  `37c7cc732d3b8b67196972e798eca7037b4496a89dba8f7dd9beb0bbcc6b2e90`；两份原文均未修改。
- 本轮仅定向修复第二次复审 P1-01/P1-02/P2-01：active facts 直接进入既有 A/B/C builder
  与原领域 payload；原图表、表格、叙事、search index、source binding 被重投影。运行时不再消费
  `user_fact_revision` overlay/同步卡片，receipt 与 impact DAG 来自 builder 实际消费节点。
- raw `reports/current.json` 只在 DB request、原子 EventStore 和 ready journal 全部持久后切换；
  replace/前后 fsync/DB/event/journal 故障均覆盖。EventStore 可识别并截断半条 JSONL 尾记录，保留
  有效历史后精确重试。失败返回保持原始 current 字节，而非 reader journal 遮蔽。
- 第二次复审反例集中 RED 为 `4 failed`；最终完整 W04 相关批 **`95 passed in 38.58s`**。
  Ruff 通过；10 个 W04 typed source/tool 文件 strict mypy 通过；`git diff --check` 通过。A/B/C 大型
  legacy builder 全文件 strict mypy 的既存债务仍未在 W04 扩张处理。
- 当前有效证据为 `evidence/W04-remediation-real-portal-v4/evidence-manifest.json`，SHA-256
  `bce5c414ca4ea00d6f375f5994b969a34b8cc65532ffedfe508fa9f0241359ff`，dirty source digest
  `9c5d95e88c75aef771c116e87b54a45d96b5369d8efa06c465991f4ff44918ce`。v4 定义 13 个输入、
  Unicode 路径排序、UTF-8 `path + NUL + sha256(raw bytes) + LF` 后再 SHA-256，并绑定 19 个
  runtime/current/DB/event/journal/transaction/receipt/DOM/console/screenshot 工件；独立校验为
  `checked_artifacts=19 / checked_sources=13 / error_count=0`。
- 新 Chromium 旅程在 revision 2 的真实 A/B/C 门户分别核验原安全性热图/表/叙事/索引/来源与
  原入选标准图表/表/证据抽屉；A/B 为 `30%`、`24/80`，C 为 `<=9.5 g/dL`。每个新鲜页面
  console 为 `0 errors / 0 warnings`，四张截图非白且已入 v4。revision 3 undo、refresh conflict、
  raw current 和三份 transaction/consumer receipt 均被清单绑定。
- 用户锁定的宽屏利用率、纵向/窄屏密度要求仍归 W05；本轮未做视觉重构。当前下一安全动作仅为
  第三次独立只读复审；复审接受前不得把 W04 改为 PASS 或进入 W05。模型/effort 无可核验运行时
  回执，保持 **UNVERIFIED**。

## W04 实施更新（晚于 W03）

- 下列旧“PASS”与仅 loopback 编辑页截图描述均是独立 FAIL 前的历史自验，已被上方纠偏取代，不构成当前验收。当前只能表述为“实现侧修复完成，待新的独立只读复审”。
- 集中 RED 为缺少用户编辑模块的 collection error；实现后规定的一次完整相关集成批为 **`80 passed in 2.39s`**。末次聚焦回归 `13 passed`/loopback `8 passed`，Ruff、strict mypy、compile、schema 解析、`git diff --check` 通过。
- 实际 headed Chromium 旅程完成 n20/N80→24/80、粗率25%→30%，随后 C 阈值 `<10.0 g/dL`→`<=9.5 g/dL`。最终 current revision 2；A/B/C 同一事实闭包摘要、各 8 个真实文件和各自事务 manifest 哈希全部核对，无混版。浏览器与服务已关闭。
- 安全/原子性测试覆盖两标签与线程并发、同 request payload 漂移、中断保留旧 current、精确重试、DAG 环/悬空/跨 revision、恶意 Host/Origin/session/CSRF/类型/大小/路径/import 及 symlink；reported adjusted rate、LS mean 和无关同值事实不联动。
- 请求 `gpt-5.6-sol:medium` 无可核验运行时 model/effort 回执，仍为 **UNVERIFIED**。本结论不是独立科学、正式医学、产品或 RC 接受；未跑全 gate、24 门户、全页视觉、三宿主或真实生产全量重建。保留 W00–W03 与其他脏树，无 commit/push/add/reset/checkout/clean/删除，未进入 W05。
- 当前实现侧报告：`evidence/W04-result.md`（SHA-256 `c30c5ae2522b2a4dd76faecd5a7b899dcdc3964a80fb52ad1dc2a92cdd7354a0`）及 `evidence/W04-remediation-real-portal-v3/`。下一安全动作仅为新的独立只读复审；未获接受前不进入 W05。

## W03 实施更新（晚于 W02）

- **W03 最终工程风险终态：PASS。** 第三次复审已将科学/生产缺陷降至 `P0=0 / P1=0 /
  P2=1`；随后只修复其唯一 P2（冻结站点与旧合成截图错绑）。新的独立只读核验
  `evidence/W03-independent-freeze-review.md` 确认 `P0=P1=P2=P3=0`：固定 CAS 与当前源码可
  重建一致的 `report.js`/sitemap/两页 HTML，两条 Chromium 旅程的 payload 与 DOM 均显示
  同一组 6 项真实 PNH NCT，console 为 0 error/0 warning，manifest/route/page/journey/
  screenshot 哈希全部闭合，旧合成截图不再被当前 manifest 引用。该 PASS 只关闭 W03 工程
  风险合同，不是正式医学、产品或 RC 接受；请求模型/effort 仍因无运行时回执而
  **UNVERIFIED**。下一安全动作：W04 实际事实编辑、派生失效与 A/B/C 原子同步。
- **最新终态（第三次独立复审后的证据绑定返修）：实现侧 PASS，可交新的独立只读复核。**
  第三次独立审阅原结论保持 **FAIL (`P0=0 / P1=0 / P2=1`)**，原文未修改；唯一 P2 为旧
  manifest 把真实 6 项 PNH `report.js` 与 4 项合成试验截图错误绑定。
- Freeze 已升级为 `w03-browser-freeze-v2`：从固定 CAS 重建真实站点，在
  `endpoint-timepoint-matrix` 与 `treatment-arms` 两页执行 Playwright 结构化旅程；payload 与
  DOM 均精确断言 6 项真实 PNH NCT 集合，两页 console 均 `0 errors / 0 warnings`，新截图可见
  6 项身份。旧合成截图保留历史字节但已从当前 manifest 解绑定。
- 当前 manifest 绑定 CAS、生成/模板/资产/工具源码、`report.js`、保留 sitemap、两页 HTML
  哈希、两份结构化旅程与两张新截图；不保留完整临时站点。manifest SHA-256 为
  `44b994b9fee2a237132be62a437c343e6368e0eeecd8729c86d7b46becf3262a`，`report.js` SHA-256
  仍为 `fff71397b08d24b8ed3ef21f9736298ca16b9814ee88df143e4f12af21b1882d`。
- 定向 freeze 测试 RED 为 `1 failed in 0.34s`，修复后 `1 passed in 0.30s`；作者源/mirror/
  manifest 节点 `1 passed in 0.02s`；Python `py_compile` 与 `git diff --check` 通过。本轮仅改
  证据/工具/机械测试，未重跑无关 93 项生产闭包，未改变第三次复审已通过的 F01–F06/R01。
- 三份独立审阅原文均保留；当前只是实现侧关闭 P2，不冒充独立接受。未进入 W04，未提交、
  推送、暂存、回滚、清理或删除资料。请求模型 `gpt-5.6-sol:medium` 无运行时身份回执，仍为
  **UNVERIFIED**；全 gate、24 门户、全页/全 viewport、PNH v107 和正式科学/产品/RC 接受亦
  未验证。完整证据见 `evidence/W03-result.md` 最后一节，SHA-256
  `306c47fb55e0bd26e191164ed017711736202271d8de4429f40fc315bee9484f`。
- **以下“可交第三次独立只读复审”是第三次审阅前的历史状态，已由上述最新状态取代。**
- **最新实现终态（晚于下方 86/93 项记录）：PASS / 可交第三次独立只读复审。** 第二次独立
  复审原结论仍为 **FAIL (`P1=4 / P2=2`)** 且原文未修改；本轮集中 RED
  `7 failed / 49 passed`，修复后原 86 项命令扩展为 **`93 passed in 35.33s`**。
- P1-01：B 受控 safety 语义优先验证/消费 row `term_key`；PNH B builder 不再从 family
  逆推 generic。builder→payload→筛选/表的 `absence_sae` 负例通过。
- P1-02：B JSON 矩阵入口携带 raw 数值身份并重算 canonical plot/facet；治疗/对照口径、
  safety `%`、size 正整数“人”与批准 size_basis 均强校验。复审中的 `g/L` 对 `%` 和 `%`
  size 伪造均被拒。
- P1-03：新 Fresh C schema 只允许 `instance_v1`；普通内容与 run_service 包自报
  `legacy_readonly_v0` 均失败关闭，不提供可由调用者开启的伪历史入口。
- P1-04：真实固定两页 CAS 已执行 A main→B/C main；A 输出 3895 疗效与 519 安全行均有
  source path/text，全部 B facts 与 C 258 observations-derived facts 通过 W01 ingest 和
  manifest-only restore。单独回执 **`1 passed in 28.15s`**。
- P2-01：HTML-PPT 基础合同改为单条完整 C 先例可用；第二路径 slide 仅结构兼容位，不是
  真实渲染门，未删除页面或缩小 coverage。
- P2-02：受控 `evidence/W03-browser-freeze/` 只保留 528 KB `data/report.js` 与 4 KB
  site manifest，绑定固定 CAS、当前源码、sitemap 及 C 截图；未保留巨大临时站点。
- 三类复审直接反例独立回执 **`5 passed in 0.48s`**；F01/R01 未修改且 93 项继续通过。
- Python `py_compile`、8 个作者源/镜像 `node --check`、作者源/mirror/manifest 独立节点与
  `git diff --check` 均通过。
- 两份独立审阅原文均保留：首轮 FAIL `P0=0/P1=6/P2=1`，二次 FAIL `P1=4/P2=2`。
  当前 PASS 仅为实现侧证据，不冒充新的独立接受。
- **最新实现终态（晚于下方 83/86 记录）：PASS / 可交主线程安排新的独立只读复审。**
  同一完整扩大闭包已复跑为 **`86 passed in 5.43s`（exit 0）**；上一轮两个 C
  recovery/double-exhaustion locator 失败与一个 C HTML-PPT coverage 失败均已关闭。
- C 两条恢复旅程现在从各自持久化来源 JSON 字节建立逐 observation 精确路径
  `$.observations[index].source_text`，生产 W01 ingest 可重提取相同 `original_text/source_text`；
  未放宽 RunContext 项目根边界或 W01 source derivation 合同。
- C HTML-PPT 的 `c-limitations` 保留原页并对齐权威 catalog 的 `evidence-limitations`；A/B
  非门户基础兼容保持不变，没有删除实际页面或缩小 coverage 检查。
- 第一轮独立只读审阅仍是 **FAIL (`P0=0 / P1=6 / P2=1`)** 且原文件未修改；当前 PASS
  仅为实现侧受影响闭包，不冒充新的独立接受。F01–F06/R01 当前实现侧均 PASS。
- 首轮独立只读审阅：`evidence/W03-independent-review.md` 判定 **FAIL**
  (`P0=0 / P1=6 / P2=1`)；原审阅文件未修改。本轮把 F01–F06/R01 全部纳入整族返修，
  当前实现侧逐项终态为 **F01 PASS、F02 PASS、F03 PASS、F04 PASS、F05 PASS、F06 PASS、
  R01 PASS**；仍待新的独立上下文复审，不把实现者自验写成独立接受。
- F01/F02：生产分母查找要求完整 rich identity 与显式来源边/审计映射，标题/同 N 不建边；
  旧 lookup 仅显式历史只读 adapter 可达。安全事实、portal payload、筛选与表保留 polarity、
  grade set、seriousness、TEAE、relatedness、parent/children/count basis；复合项不借 other N。
- F03：A/B 数值图只消费 typed projection；B 生产 builder 发出封闭 treatment/control/safety/
  size projections，任意 Mapping 与单臂伪差值被拒；JS 使用显式单位与逐点 size basis，非百分比
  生产测试为 `g/L`，人数比例才执行 `n<=N`。
- F04/R01：Fresh C 新包强制 outcome_id，并按 role/group/cohort/period/window 逐实例配对；旧
  fallback 仅 `legacy_readonly_v0`，多同角色失败关闭。干预按显式 arm-intervention 边归属，
  未绑定关系保留 blocking 状态，不丢弃、不回退 arm1。
- F05/F06：PNH A/B/C facts/observations 使用无通配精确 JSONPath 与可从持久化 JSON 标量重提取
  的 original/source text；生产 B/C builder 行已通过 W01 ingest 与 manifest-only 空目录恢复。
  A/B/C 多报告生产运行、真实 PNH B fixture 和 portal 消费者均纳入定向闭包。
- 返修 RED：`8 failed / 18 passed`，逐项命中审阅缺口；中间一次 fixture/catalog 摘要未同步为
  `4 failed / 46 passed`，同步输入 SHA 与 case digest 后关闭。最终受影响闭包：
  **`47 passed in 4.09s`**；Python 编译、4 个 JS 语法检查、作者源/mirror/manifest 合同与
  `git diff --check` 均通过。
- 浏览器：A 投影矩阵、B PNH typed 矩阵、C endpoint-timepoint 与 treatment-arms 受影响旅程
  均完成；tooltip/刻度/折叠表使用同一投影载荷，C 冻结 payload 可见 outcome_id/group_id/
  period 与非阻断显式关系；控制台 `0 errors / 0 warnings`。服务和浏览器均已关闭。截图与
  SHA-256 见 `evidence/W03-result.md`。
- 写入门：仍为 `main` / `HEAD=2df24bb441e555f20b233ad2011b4ffd3610655b`；保留 W00–W02
  与其他用户脏树；无 commit/push/add/reset/checkout/clean/删除，未进入 W04。
- **UNVERIFIED**：请求模型 `gpt-5.6-sol:medium` 的运行时 model/effort 回执、新的独立上下文
  复审、全 gate、24 门户、全 viewport/全页视觉、真实 PNH v107 与正式科学/产品/RC 接受。
- 证据：`evidence/W03-result.md`，SHA-256
  `e196fb6fcb66b4c257d67bc5dbb60dac4260451598aee70b4c07c7a1a5ea5ad3`。下一安全动作由主线程
  安排新的独立只读复审；本线程在 W03 终态停止，不自行进入 W04。

## W02 实施更新（晚于 W01）

- 当前包：W02 已完成通用入口、真实能力门、合并 SourcePlan、公共查询与 ViewState 的最小可执行切片；请求模型为 `gpt-5.6-sol/medium`，本会话无可核验 model/effort receipt，身份 **UNVERIFIED**。
- 写入门：仍为 `main` / `HEAD=2df24bb441e555f20b233ad2011b4ffd3610655b`；完整保留 W00/W01 与既有未跟踪资料；无 commit/push/add/reset/checkout/clean/删除，未触碰旧中文工程。
- 入口：`project create --request` 与高级 `--indication` 复用 `ProjectContract`；缺报告类型返回机器可读 `ASK_REQUIRED`；指定一种只形成对应报告分支；高级 `research submit` 继续受同一项目/研究语义和 W01 信任合同约束。
- 运行与计划：RunContext 显式校验项目根、适应症、报告、截止日及来源输入；全球/中国/四类反向扩展为一次共享计划，A/B/C 专属分析分支独立；每项目药智仍只问一次；C 单研究先例可用，不强制多个设计路径。
- 能力：生产 Runtime probe 只接受实际执行回执，静态 yes/env 声明不再通过；当前 Codex 宿主未配置真实独立上下文探针，预检及 run 均正确 `capability_blocked`，未生成生产研究待办，并提示子Agent/独立会话/兼容执行器恢复路径。`StaticCapabilityProbe` 仅用于测试。
- 查询/ViewState：WorkspaceMembership、FacetPlan、NumericFrameEligibility 分层；`Q=P∪U` 且不相交；零命中保持零；图例/缩放不改科学 query；图/表/选中/下钻以同一 fact 身份联动；A/B/C 现有筛选消费者已接公共 typed query。
- 批次：集中 RED 为缺少公共查询类型的收集失败；实现后首轮 `74 passed`；扩展闭环中一次新增测试夹具错误为 `10 failed / 140 passed`，修正后 `150 passed`；最终合并批次 `176 passed`（7.45s）。Ruff、8 文件 strict mypy、`git diff --check` 通过。
- 旅程：测试能力注入下，同一真实 CLI 形成 PNH-A、AD-B、AD-C 三个单报告可追溯开发待办；生产 PNH-A 预检失败关闭。前者不是生产能力证据，后者证明没有静默降级；均不代表真实研究、门户或 24 门户验收。
- 证据：`evidence/W02-result.md`（SHA-256 `e73f56e8b8d5fe38cb0c0e5517e804bdb5f87fd9edac13357c539addd19f5235`）与 `evidence/W02-journeys/`。未跑全 gate、全浏览器、三宿主、真实来源或 24 门户；未形成 RC 或产品接受。
- 下一安全动作：W03/W04/W05A/B/C 消费已冻结公共接口，W07 继续真实来源；在授权宿主提供真实独立上下文探针后恢复生产旅程。B/C 来源必须替换旧不可重放合成夹具，禁止放宽 W01。

## W01 实施更新（晚于 W00）

- 当前包：W01 已完成连贯工程实现与本包决定性验证；请求模型为 `gpt-5.6-sol/medium`，本会话无可核验 model/effort receipt，身份 **UNVERIFIED**。
- 写入门：仍为 `main` / `HEAD=2df24bb441e555f20b233ad2011b4ffd3610655b`；W00 的 13 个 tracked 修改和既有未跟踪证据完整保留；无 commit/push/add/reset/checkout/clean/删除。
- 信任合同：生产者只写 candidate；研究/渲染可消费候选，但接受转换必须校验生产 issuer 对请求、来源、规则和产物的真实签发记录，包内旧 reviewer 或伪 digest 不授权。
- 来源与版本：按 locator 从持久化真实字节重提取并严格比对逐事实原文；科学 context 纳入版本身份；同 ID 异内容显式冲突；source version、acquisition attempt、idempotency request 分离。
- 快照：v2 manifest/lineage 为 source/fragment/fact/claim/derivation/attempt/receipt 传递闭包，可在空目录只用 manifest 恢复；v1 历史身份不补签。
- 批次：集中 RED `13 failed / 138 passed`（4.64s）；实现后 W01 合并批次 `152 passed`（4.82s），迁移/历史快照 `16 passed`（0.26s），A 产品兼容入口 `2 passed`（0.69s）；Ruff、核心 mypy strict、`git diff --check` 通过。
- 限制：未跑全 gate、24 门户、完整浏览器、三宿主或恢复矩阵。额外多报告探测有 3 个旧 B/C 合成夹具因非 JSON 来源字节、粗 locator 和生成原文被新合同正确拒绝；未放宽生产约束，须在后续对应工作包替换为可重放来源。
- 证据：`evidence/W01-result.md`（SHA-256 `8bc462ac85ac0b824bf312496e5de9689fbbcb0935e152f652412265373c6acc`）。这不是 RC、科学、视觉或产品最终接受。
- 下一安全动作：进入 W02/W03；W07 可开始真实来源链。进入 B/C 生产旅程前先修复其不可重放合成来源与逐事实 locator。

## W00 实施更新（晚于下方 Review 基线）

- 当前包：W00 已完成受限工程实现与定向验证；执行模型请求为 `gpt-5.6-sol/medium`，运行时无可核验 model/effort receipt，身份 UNVERIFIED。
- 写入门：`HEAD=2df24bb441e555f20b233ad2011b4ffd3610655b`、`main`；写入前 tracked/index 无修改，完成收口前 HEAD 未变化；既有未跟踪材料保留。
- source-set：`evidence/W00-source-set.json`（SHA-256 `f2b0c37c382da199bb17fee3233c7a7535136ea588b8f79291fc43b737c2031e`）绑定 commit/tree、锁文件、交接包、必要 PNH 输入、两份 CAS、abc-v106 输入/页面 manifest 与 A/B/C verdict。
- 候选实况：abc-v106 A56/B70/C18，共144页；A/B/C 实际 verdict 均 `veto`，未改变候选或 verdict。
- 修复：C `evidence-limitations` 保留为真实页面并同步页面合同；模块 portal assets 定为唯一作者源，根 assets 定为发包镜像，manifest 覆盖镜像，bundle 构建前失败关闭地校验三者一致；README/ARCHITECTURE 仅增加新 PRD/Plan 入口。
- 批次：修复前 `38 passed / 1 failed / 1 error`（12.67s）；整族修复后同批次加 1 个资产单源合同，`41 passed`（13.19s）。未跑全 gate、24门户、完整浏览器、三宿主或恢复矩阵。
- 证据：`evidence/W00-result.md`。没有 commit/push/add/reset/checkout/clean；未形成 RC 或产品通过结论。
- 下一安全动作：W01 信任、精确片段与 manifest 传递闭包；继续保持 abc-v106 三份科学 veto 和未验门状态。

## Review 基线（历史记录）

- 当前授权：Review 本地工程、GitHub 和 GPT Pro 0922V2 专家材料，形成 PRD、计划、执行规范、资料索引与执行/验收包；不修改产品代码，不提交/推送，不启动下一实现任务。
- 方法：主线程只读审查与文档编制，配合一个原生独立只读审阅节点核验安全语义/分母/C实例三个相对独立边界；避免重复全仓模型审查。主线程持有版本比对、信任链、前端、总体计划与最终判断。
- 本地/远端 main 初始 HEAD：5ebbc8785143758981c0260e1600d6ff32b70b80；专家基线：700bd4c1fb90c49e27b6ff46fba07a5f7f296b6c。
- 初始已跟踪工作树无修改；存在大量未跟踪运行目录和部分 payload/derivation，保持原样。
- CAO 共享记忆检索服务不可用；只采用实际工程和只读历史记录，不建立替代记忆库。
- 已完成：专家逐项处置、核心生产消费者与 GitHub 对齐、一个原生独立只读审阅、40项定向测试、现成矩阵浏览器抽查、PRD/设计/Plan/执行规范/资料索引/40项验收映射/13个实施包/fork提示词。
- 用户本轮明确确认五项新增需求全部为正式范围：B全相关研究分面、实际事实修订并同步ABC、C设计先例检索横比、个人配置及离线分享、ABC同优先级。
- 结束观测本地/远端 HEAD：2df24bb441e555f20b233ad2011b4ffd3610655b；中途仅另一Agent提交runbook追记70，相关生产源未变。
- 实证：38 passed / 1 failed / 1 error，12.24s；页面catalog责任不一致和隔离安装portal.css摘要错误仍在。不是全gate。
- 浏览器：现成abc-v106 A矩阵桌面/手机无页面横溢、console无错误，但单位/差值语义问题真实可见；不是完整视觉通过。临时浏览器和本线程HTTP服务已关闭。
- 当前候选：abc-v106，A56/B70/C18共144页；追记70记录三份独立科学结论均veto，未RC。
- Goal工具实读仍paused，原文已保存evidence/goal-before-review.json。新Goal prompt只在FORK_START中，尚未激活。
- 下一安全动作：用户在gpt-5.6-sol:medium执行fork发出FORK_START任务，先确认英文根/最新HEAD/资料完整与写入所有权，再W00；不恢复旧v107逐补丁循环。
- 文档校验已完成：54个本地链接0缺失，13个工作包齐全，验收编号映射完整，选择的源/产物hash无漂移，tracked diff为空；详见evidence/PACKAGE_VALIDATION.md。
- 未执行：产品修复、全量模型/视觉轮次、发布/删除、Goal 更改、fork 启动。
