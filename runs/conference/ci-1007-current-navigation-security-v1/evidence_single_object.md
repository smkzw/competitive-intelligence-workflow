Trellis SessionStart 上下文已加载。先读取初始读取集。

读取集已确认。现在验证冻结对象 SHA 并盘点文件规模。

Bash 在非交互模式不可用，SHA256 校验与 pytest 需改用只读工具近似执行或列入未运行项。继续读取冻结源文件。

服务器文件已读完。现在并行读取四个冻结 JS/测试文件。

report-a.js 超过单次读取上限，先用 Grep 定位关键调用点，再分块读取。

现在读取关键依赖定义。

`_b_source_view_row` 会抛 `ReportBPortalError` — 必须确认它是否继承 `ValueError`，否则 `_report` 的 except 元组接不住。

`ReportBPortalError(ValueError)` 已被 except 元组覆盖，无未捕获崩溃。继续读服务层与测试脚手架。

现在读取测试脚手架 `_project` / `_command` / `_request_http` 与 W04 既有编辑器测试的关键部分。

# Conference Output: ci-1007-current-navigation-security-v1 - evidence_single_object

## Output

### 0. 结论（先行）

**Verdict: `REVISE`（有界修复，非安全边界失败）。**

- 在本对象（冻结的五文件）内**未发现可被远程/跨站利用的绕过**：Host/会话/CSRF/Origin/CSP/路径/代际/哈希/符号链接/身份/版本控制经逐行核对与测试对照后成立（证据与精确行号见 §2）。
- 但新 GET 面（report→editor 注入）存在一处**可达的未捕获异常缺陷**：`_edit_context` 对 `consumer_bindings` 的形状不设防，非 dict/缺键条目会把整个报告读取面打成无 HTTP 响应的 traceback（§3-F1）。同一子系统在 `user_fact_edit.py` 中有三处 `isinstance(binding, dict)` 先例，唯独新面的这个消费者没有——这是有界、可两行修复的一致性缺陷。
- 另有一项**必须在封冻前由 Codex 用浏览器验证**的风险（我无法在此角色内运行）：新服务面对整站报告页施加了 `script-src 'self' 'unsafe-inline'`（无 `'unsafe-eval'`），而捆绑的 `echarts.min.js` 中存在 `new Function` 记号；若为活代码，图表**只会在编辑路由下**失败（§3-F2）。
- 我不代签科学/浏览器/发布接受；下述裁决仅覆盖本对象的安全与身份边界及随附的可达性缺陷。

---

### 1. 审阅对象与证据轨迹

**冻结对象（逐字节读取，未改写）**：`src/ci_workflow/application/user_fact_edit_server.py`、`renderers/portal/assets/{portal.js, report-a.js, evidence-drawer.js}`、`tests/integration/test_1007_current_report_edit_navigation.py`。

**依赖读取（按 context 授权清单）**：`application/user_fact_edit.py`（lock/current_facts/`_public_fact`/save/`_stage_fact`/`_finish_save`/preflight/builder 绑定）、`application/latest_delivery.py`（bundle 校验、committed generation、`current_bundle_sha256`）、`application/delivered_artifacts.py`（`_ordinary`）、`renderers/portal/report_b.py`（`_b_source_view_row`、`validate_active_fact_revision_b`、`active_fact_binding_for_b`）、`renderers/portal/report_a.py`（`active_fact_binding_for_a`、A 模板触发器）、`renderers/portal/active_fact_projection.py`（`ActiveFactBinding`）、`renderers/portal/evidence_drawer.py`、`tests/integration/test_w04_user_fact_edit.py`（`_project`/`_command`/`_request_http`/攻击矩阵）、`test_1007_real_fact_editor.py`、`test_1007_historical_save_retry.py`。

**追踪链（端到端）**：`GET /`（会话+CSRF）→ `GET /reports/<gen>/<R>/<page>`（manifest+哈希+注入）→ `portal.js:12-35` 生成 `/?fact=…&generation=…` → `GET /`（`?generation` 拒绝旧版）→ `POST /api/save`（Host+Origin+CSRF+revision+身份）→ 保存后新 links。每一环节的实际行均核对。

**方法限制（如实声明）**：本次会话无 shell（Bash 被非交互权限拒绝），因此**未能**：(a) 重算五个文件的 SHA256 与 context 记录值比对；(b) 运行可选回归 `pytest -q tests/integration/test_1007_current_report_edit_navigation.py --tb=short`；(c) `git diff e1a0126` 以逐行区分“新增 vs 既有”。我对“新增面”的归属依赖 conference context 的表述，而非 diff。所有结论均为**静态阅读+精确行号**证据，未标注处不作为“已验证运行”。

---

### 2. 边界核对结果（逐项，全部在冻结面上复核）

| 边界 | 结论 | 控制点 |
|---|---|---|
| Host | 成立 | `_host()` 精确匹配 `127.0.0.1:{port}`，GET/POST 均先检；无 Host/异 Host → 403（server:540-542, 605-607, 590-593） |
| 会话 | 成立 | `/reports/*` 必须先有会话（server:658-660）；cookie `HttpOnly; SameSite=Strict; Path=/`（652） |
| CSRF/Origin（写） | 成立 | `Origin` 精确等于 `http://host` + 会话令牌 `compare_digest`（594-601）；跨站无法读 `X-CSRF-Token`/meta（无 CORS；`CORP: same-origin`） |
| 路径 | 成立 | 单次 `unquote` 后 fullmatch + `""/./..` 段拒绝 + `%`、`\`、NUL 拒绝 + 扩展名白名单 + `_ordinary`（词法+resolve 双重包含检查、逐级拒符号链接）+ manifest 键精确匹配 + 落盘字节复哈希（server:661-695；delivered_artifacts.py:18-29） |
| 代际/旧版拒绝 | 成立 | 报告路由 `current_bundle_sha256 != generation → 409`（679-684）；编辑页 `?generation` 不匹配 → 409（624-631）；旧链接/旧 generation 均有测试钉死（测试 113-117, 156-167） |
| 字节完整性 | 成立 | `read_current_delivery → _validate_current_bundle → _verify_current_report` 每次整站重算哈希（latest_delivery.py:340-356）＋builder 输入哈希（187-196）；serve 时再比对（694-695）；symlink 换入 sqlite → 409 且不泄漏字节（测试 174-187） |
| 注入安全 | 成立 | `_safe_json` 转义 `<>&`（89-96）；context 仅含 revision/generation/report/bindings（无 csrf/project_root，测试 52-58）；`_report` 仅注入 manifest 列出的 `.html` 且要求 `<head>` |
| 身份（B 域→view） | 成立（失败关闭） | `_b_source_view_row` 要求域行/视图行唯一，并对 efficacy 做 8 字段一致性核对（report_b.py:5878-5924）；A 侧 `data-evidence-row-id`＝A 域行 id，与 `active_fact_binding_for_a` 同源（模板 efficacy.html.j2:20；report_a.py:2241+）；C 绑定被 `validate_active_fact_revision_c` 限为 observations |
| revision | 成立 | 保存强制 `project_id`、`expected_revision`、目标版本 ∈ active、四字段身份全等（user_fact_edit.py:1138-1151）；重复 request_id 幂等回放含历史代际校验（test_1007_historical_save_retry 全文件） |
| 多消费者 | 成立 | 同报告多行/A+B 跨报告均逐 binding 出链；保存 `_finish_save` 按 `consumer_bindings` 计算受影响报告集合并先 preflight 后落盘（1546-1572）；编辑页 `kindOf` 的 C 样本量判定与 `_REPORT_COLLECTIONS`（recovery:60-64）一致 |

**未发现可利用缺陷**：跨站/重绑定场景下无法同时满足精确 Host＋精确 Origin＋会话令牌＋RSA…（CSRF）四者；报告读取面无写副作用；`_sessions` 仅本地内存。

---

### 3. 发现（按影响排序；区分新面缺陷与既有局限）

#### F1（新面、有界缺陷，须修）— `_edit_context` 未防护的绑定形状 → 未捕获异常，整站报告页无响应
- **位置**：`src/ci_workflow/application/user_fact_edit_server.py:71-80`（`binding["report"]` @73、`binding["row_id"]` @75、`binding["collection"]` @77/79），异常出口在 `707-708`（`except (UserFactSaveError, OSError, ValueError)` 不覆盖 `TypeError/KeyError`）。
- **反例（可达状态）**：项目经 `initialize_current_delivery` 采纳既有报告（该路径对 `consumer_bindings` 只做 `isinstance(binding, dict)` 过滤，user_fact_edit.py:898-902），且某事实 `scientific_context_json` 携带 `"consumer_bindings": ["legacy"]`（或含 `report/row_id` 但缺 `collection` 的 dict），且该事实没有 `source_portal_consumer_bindings` 行 → `_public_fact`（1019-1027）原样返回该 context → `GET /reports/<gen>/{A,B,C}/overview.html` 在 @73 先求值 `binding["report"]`：字符串 → `TypeError`，缺键 dict → `KeyError`。异常逃出 `do_GET`；`BaseHTTPRequestHandler` 不回 500，只打印 traceback 并断开连接（浏览器显示连接重置）。**A/B/C 所有 HTML 页同时不可读**；且该状态无法通过 UI 保存修复（保存会在 `ActiveFact.model_validate` 处失败，user_fact_edit.py:639-640 → 409）。
- **同子系统先例（证明这不是“不可发生的输入”）**：`user_fact_edit.py:1336-1343`、`1546-1552`、`1562-1568` 对同一数据全部使用 `isinstance(binding, dict) and binding.get(...)`；`initialize_current_delivery` 亦用同类防护。唯独新注入面没有。
- **可利用性判定**：**不可利用**（无数据泄漏/无越权写；写路径仍失败关闭）。属**可用性+错误契约缺陷**：同一模块“一切失败都应是带类型的 4xx JSON”被破坏。
- **建议修复（有界，二选一）**：
  - A（最小、保留最严姿态）：在循环内对 `isinstance(binding, dict)` 与 `report/collection/row_id` 键做显式校验，不合法即 `raise ValueError("事实消费者绑定无法核验")`，落入既有 409 路径；异常类型随即被覆盖。
  - B（更优 UX，需 Codex 认可）：该 binding 静默跳过（或该报告整体不注入 `ci-current-edit`），页面照常以哈希校验后的字节提供、**不输出任何未核验链接**——省略注入不产生错误链接，安全上不弱于 409。
  - 二选一都必须做；推荐先做 A 封住异常类，B 作为是否“整页拒绝”的设计决定交 Codex。

#### F2（新面风险，未验证；须 Codex 浏览器门）— 新 CSP 可能使编辑路由下的图表静默失效
- **证据**：`user_fact_edit_server.py:557-562` 对**所有**响应（含整站报告 HTML/JS）施加 `script-src 'self' 'unsafe-inline'`，**无 `'unsafe-eval'`**；而在本工作区 grep：`renderers/portal/assets/echarts.min.js` 至少含 1 处 `new Function` 记号（`eval(` 为 0 处）。静态分享（file://）无 CSP，因此该失败**只会在带编辑链接的新路由上出现**——恰好是本对象的唯一新增面。冻结测试只做 HTTP 字节断言（无浏览器），不可能发现此问题。
- **不确定性**：无法从只读工具确定该 `new Function` 是否在加载/图表初始化路径执行（可能位于死分支或被 try/catch）。若执行 → A/B 页图表 EvalError、控制台 CSP 违规；不影响安全边界，属 Codex 的视觉/浏览器接受面。
- **须运行（Codex 侧，本角色不代签）**：在 Chromium 与 WebKit 打开 `/reports/<gen>/{A,B,C}/overview.html`（经编辑页建立会话），检查控制台 CSP/EvalError 与图表 canvas。**若确认违规**，推荐修复：仅对报告体响应放宽（报告体字节已被 manifest 哈希钉死、不含秘密），编辑页保持严格 CSP；不要为整站同时放宽。

#### F3（既有局限，建议顺手加固）— 非 ASCII CSRF → 未捕获 `TypeError`
- `user_fact_edit_server.py:599` `secrets.compare_digest(str, str)` 对非 ASCII `X-CSRF-Token` 抛 `TypeError`（CPython 文档行为；未在此运行复验），逃出 `_authorize_write` → 同样是无响应断开。**失败关闭**（不会授权），但应改判 403。触发需有效会话 cookie，实际仅本地误用可达 → 既有、低危。修复：先 `try/except TypeError: return 403` 或对 token 做 ASCII 约束。

#### F4（测试覆盖缺口，非缺陷；建议在本对象内补齐）
- `test_1007_current_report_edit_navigation.py:156-171` 的“保存后新链接有效”只断言了 `reply["report_links"][0]`（`_REPORTS=("A","B","C")` ⇒ 恒为 A，user_fact_edit.py:74）。**保存后 B 页的再注入（`_edit_context` 的 B 映射只在读取时执行、且 builder 输入已在保存中更换）没有被任何断言覆盖**——这是最可能与 F1 家族协同出错的组合。建议在同一测试内加 2 行：保存后 `GET` 新 B 链接断言 200 且 bindings 仍含 `eff-row-nct04558918-apply-treatment`；另加 A 页断言（A 侧 row_id 一致性目前只有文本级 call-site 断言，测试 229-236）。
- 另缺口：空 `?generation=`（parse_qs 丢空值 ⇒ 跳过检查，无害但无测试钉死）；>64KiB body 413；非 ASCII CSRF（F3）。

#### F5（设计/UX 备注，不阻断）
- 旧标签页点击编辑链 → 编辑页返回**原始 JSON 409**（`{"error":"报告版本已变化…"}`），用户看到 JSON 文档而非中文页面；建议 409 分支对 `Accept: text/html` 返回极简中文提示页（不改变状态码语义）。
- `?generation=` 空值被当作“未提供”（parse_qs 默认 `keep_blank_values=False`）。
- 每次资源请求都在写锁内做**整站重哈希**（server:675-679；作者 ponytail 注释已承认）；大站点下编辑路由加载慢且与保存互斥。可接受，但建议在报告读取面加“已验证代际”缓存前先压测。
- `_sessions` 只增不减；GET `/` 在 409 前已注册会话（无 Set-Cookie）。纯本地内存项。
- C 页**没有任何页内编辑链接**（全仓仅 report-a.js:1724、evidence-drawer.js:474 消费 helper）。若这是有意的（context 只写 “exact B …identity”），请确认；若 C 导航属于本对象范围，则是功能缺口。

---

### 4. 实际运行与未运行

- **实际做**：五冻结文件+八个依赖文件完整/目标段阅读；针对身份接线（`data-evidence-*`、`a_row_id`、`view.row.row_id`）、防护先例（`isinstance(binding, dict)`）、CSP 敏感构造（`new Function|eval(|Blob|Worker`）、集合门（`_REPORT_COLLECTIONS`、`validate_active_fact_revision_*`）、context 写入者（registry/recovery）的定向 grep；调用链逐行核对。未做任何写操作、未派生子代理、未接触旧中文工作区或历史会话。
- **未运行**：(1) 五文件 SHA256 复算与 context 记录比对（无 shell）；(2) 可选 pytest 回归（同上；不据此推断浏览器/独立接受）；(3) 任何 Chromium/WebKit/视觉检查（Codex 职责）；(4) git diff 以形式化区分新增/既有行。

### 5. 给 Codex 的有界问题与安全暂定路径

1. **F1 修复语义**：不合法的消费者绑定应整页 409（方案 A），还是降级为“该报告不出链接、页面照常可读”（方案 B）？——决定我给出的两行修复取哪支；两者都必须先封住未捕获异常。
2. **F2 验收证据**：编辑路由下的 Chromium+WebKit CSP 例外检查由谁执行、是否作为本对象封冻门？未出结果前，本对象应视为“安全边界通过、浏览器面 UNVERIFIED”。
3. **C 导航**：C 页无页内编辑链是否为冻结设计？
4. **F4**：是否把“保存后 B 页 200+bindings 断言”并入本对象（改动仅测试、无生产行为变化）。

**安全暂定路径**：在 F1 的两行修复落地且 F2 浏览器结果为空之前，不得以“本对象已通过”对外表述；F1 修复本身不改变任何已验证的边界行为（对合法数据零差异），可独立回归（既有 45 项批 + 本对象 6 项测试即可覆盖）。

**我不代签**：科学、浏览器/视觉、打包、发布四项接受保留给 Codex。本输出为单次会议的完整报告，未写入 runner 报表路径。
