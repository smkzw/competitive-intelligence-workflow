继续同一会话的有限跟进。先读取更新后的三个文件。

服务端 F1/F3 修复已核对。现在读取更新后的测试文件。

F1/F3 修复与 F1/F4 测试均已核对。现在确认 C 模板的共享脚本引用（第 4 点更正）。

# Conference Output: ci-1007-current-navigation-security-v1 - evidence_single_object followup

## Output

### 0. 裁决（仅限 F1/F3/F4）

**`ACCEPT_BOUNDED`** — F1（失败关闭 A）、F3、F4 三项均按声明落地且经逐行+测试核对；初始 REVISE 仍为不可变历史，本报告仅绑定本次新字节（server SHA `d4fe5de0…`、test SHA `2cc8675c…`，均**未由我复算**，见 §6）。F2 的静态担忧按 owner 证据**缩窄**但绝不能表述为浏览器 PASS（§5）。发现一处需要更正的事实（C，§4）与一处应留档的收紧后果（§2）。

### 1. F1 复核 — 失败关闭 A 已正确落地（含测试矩阵）

**实现**（`src/ci_workflow/application/user_fact_edit_server.py`）：
- L73-75：`declarations = fact.get("consumer_bindings", ())`；`not isinstance(declarations, (list, tuple))` → `raise ValueError("事实消费者绑定无法核验")`。这同时封掉了旧代码中「容器为 str 时逐字符迭代 / 为 None 时 `TypeError`」两个变体。
- L76-77：逐条 `ActiveFactBinding.model_validate(declaration)`（`extra="forbid"`，非 dict、缺键、Literal 不符、多余键全部抛 `ValidationError`；`ValidationError ⊂ ValueError`）。
- L78-85：仅在模型校验通过后才读取 `report/collection/row_id`，B 仍走 `_b_source_view_row` 映射与一致性核对。
- 出口：L719-720 既有 `except (UserFactSaveError, OSError, ValueError)` → 409 `"当前交付未能完整核验"`。**旧代码中能逃逸的 `TypeError/KeyError` 类别在该面上已不存在**；`_b_source_view_row` 的 `ReportBPortalError(ValueError)` 与 B 缺少 builder 输入的 `ValueError`（L66-67）同样落 409。

**测试**（`tests/integration/test_1007_current_report_edit_navigation.py:185-202`，4 例参数化 `None / "legacy" / ["legacy"] / [{"report": "A"}]`）：把 `fact-unrelated-20`（无注册绑定 → 走 `_public_fact` 原样透传的裸 context 路径，正是我的反例族）注入后 GET 报告 A，断言**精确为 409** 且 body 的 `error` 等于 `"当前交付未能完整核验"` —— 同时钉死"不得静默跳过、不得断连接"两项语义。✔ 与我上一轮 F1 的两个方案中 owner 选择的 A 完全一致。

**留档（有意收紧，非缺陷）**：对「三键齐全但含额外键」这类模型不合法、旧代码尚能出链的绑定，现在会 409 整页。这是 fail-closed A 的必然语义，与同一子系统其它消费者（保存/重建路径的 `ActiveFact.model_validate`）一致——**不会基于未经核验的绑定发出任何编辑链接**，我接受该取舍。测试用 monkeypatch 注入状态（未走 init-adoption 构造），但 F1 的契约点（服务端面对脏绑定必须 409）已被精确覆盖，判定充分。

### 2. F3 复核 — ASCII 前置守卫、时序与空代际全部落实

- **ASCII 守卫**：L604-608 `session is None or not csrf.isascii() or not secrets.compare_digest(session[1], csrf)` —— 守卫在 `compare_digest` 之前短路，非 ASCII 头值与 `None` 会话同归 403 `"会话或CSRF校验失败"`。已彻底移除上一轮的未捕获 `TypeError` 出口。
- **会话注册时序**：L627-652 —— 代际校验（L630-640）与 `_editor_page` 构造（L641-646）都在 try 内，`session_id/csrf` 在成功后（L650-652）才生成注册；409 与任何异常路径不再向 `_sessions` 泄漏条目（我上一轮的备注已闭合）。
- **空代际**：L630-633 `parse_qs(..., keep_blank_values=True)` → `?generation=` 保留为 `[""]`，与 `[sha]` 不等 → 409 于 L634-640。`?fact=x`（无 generation）与正确 generation 路径不受影响。
- **测试**（L205-225）：`GET /?generation=`（带会话）→ 409；随后 POST 使用 `_open` 得到的**有效会话** cookie（并非 session=None 混淆）且 `X-CSRF-Token: "\xe9"`（latin-1 线码 → 服务端解码为非 ASCII）→ 403；块外断言 `read_current_delivery() == before`，证明未发生任何状态变更。✔

### 3. F4 复核 — 保存后 A/B/C 全部新链接均已验证

测试 L156-182：`assert all(href 变化)` 保持；旧 A 链接 409、旧 generation 编辑导航 409 保持（L157-167）；**新增循环** L168-182 对 `reply["report_links"]` 的每一条（A、B、C）执行 GET → 200，解析注入的 `ci-current-edit` 上下文，断言：全体 `context["revision"] == 1`；B 页保留显式 view 身份 `eff-row-nct04558918-apply-treatment` + `fact-b-estimated-efficacy`（即保存重建后 B 的域→view 映射仍可解析，闭合我上一轮的覆盖缺口与最高风险组合）；C 页存在 `collection == "observations"` 绑定。✔ 我上一轮 F4 建议的最小增量已按"保存后全链接 + B 显式身份"落地。

### 4. 更正：C 页共享所有者 — 我上一轮的推断错误

**更正成立。** `templates/c/base.html.j2`：L115 `{{ evidence_embed | safe }}`（`__EVIDENCE_VIEWS__`/标签权威），L116 `<script src="{{ asset_prefix }}/portal.js">`，L119 `<script src="{{ asset_prefix }}/evidence-drawer.js">`。即 C 页加载的正是我审阅过的两个共享所有者：`portal.js:12-35` 定义唯一 helper，`evidence-drawer.js:473-475` 是共享调用点。**不存在 C 专用 helper，也不需要**；我上一轮"仓库 grep 仅见 report-a.js / evidence-drawer.js 两处调用点 ⇒ C 页无页内编辑链接"的推断把"共享调用点"误读成了"A/B 专属"。正确表述：**C 的页内编辑能力经同一 evidence-drawer 路径与同一 helper 提供**；剩余待验项仅是浏览器层"某条 C 绘制行确实渲染出链接"（Codex 浏览器面），以及 C 行级 id 与注入绑定的对齐仍仅由保存时 `validate_active_fact_revision_c` 保障、新测试为元数据级断言——不再有"缺实现"的说法。

### 5. ECharts / F2 状态（按 owner 证据缩窄，不得读作 PASS）

- 接受 owner 的事实认定：捆绑包内 `new Function` 唯一出现在 GeoJSON 遗留解析回退 `JSON.parse ? JSON.parse(i) : new Function(...)()`；在正常环境（含浏览器）走 `JSON.parse` 主路径，回退不可达。据此，**我上一轮"无 `'unsafe-eval'` CSP 可能打断图表"的静态担忧已缩窄**为"仅当环境缺失 `JSON.parse` 才触发回退"。
- owner 的 SSR 探针（VM `codeGeneration strings:false`、正常 JSON.parse、含负值柱渲染 → 3021 SVG bytes；首次探测缺 `setTimeout` 的失败是 `ReferenceError` 而非 CSP）我采信为**打包产物可渲染的证据**，但它**不是**真实浏览器的 CSP 或视觉接受。
- 结论表述边界：**F2 实际浏览器（Ego/Chromium/WebKit + 编辑路由 CSP）仍为 NOT_RUN**，不得标记通过；未做也未被授权任何 `unsafe-eval` 放宽（与我的建议一致：即使将来证实违规，也只应在报告体响应上做窄化处理，编辑页保持严格 CSP）。
- 未按要求读取整份压缩 vendor，未展开任何无关工作流。

### 6. 实际检查与未运行（本轮）

- **实际做**（全部只读）：完整读取新 server（820 行）与新测试（292 行）；定向读取 `c/base.html.j2:92-125`；把 F1/F3/F4 每条声明映射到精确行号并核对测试矩阵与断言；核对了 `ValidationError ⊂ ValueError`、短路顺序、会话注册时序、`keep_blank_values` 语义与测试是否被 `session=None` 混淆（F3 非 ASCII 用例使用有效会话，未被混淆）。
- **未运行**：新 server/test SHA256 复算与记录值比对（本会话无 shell，权限拒绝，未尝试绕过）；`pytest`（含本轮相关用例）；任何浏览器/CSP/视觉检查；`git diff`。工具/权限失败如实保留，无隐藏。
- 本报告在给定 16 turn 预算与只读边界内完成，未写 runner 输出路径，未做任何修复或递归派发。

### 7. 残余限制（不改范围、不重开）

既有且未主张修复的项维持原状：陈旧标签页 409 仍为原始 JSON 表面；`_sessions`（现仅成功路径增长）仍无上限；报告读取面每请求整站重哈希；C 行级身份对齐为"保存时校验 + 测试元数据级"，其浏览器级确认归 Codex。初始 REVISE 不可变；本报告证明 F1/F3/F4 已按 owner 选择闭合，并绑定本次新字节；科学、浏览器、安装与发布接受仍全部归 Codex。
