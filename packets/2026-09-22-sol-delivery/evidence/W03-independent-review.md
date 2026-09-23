# W03 冻结风险合同独立挑战审阅

日期：2026-09-22  
模式：`MODE=CONFERENCE`，独立只读挑战审阅；未修改产品、测试、状态或既有证据。  
请求模型/effort：`gpt-5.6-sol:medium`。当前会话没有可核验的运行时 model/effort 回执，实际模型状态：**UNVERIFIED**。  
冻结身份：HEAD `2df24bb441e555f20b233ad2011b4ffd3610655b`；已跟踪工作树 diff SHA-256 `b9e327cd2a298cba2011e13ddfbcdf6336604d184aca036fc18ad1bfeb55f2e0`。W03 关键文件哈希与 `W03-result.md` 所列一致。

## 结论

**总体：FAIL。P0=0；P1=6；P2=1。**

W03 的 helper 层对分母身份、安全概念、typed 数值和 C 实例分别增加了有价值的守卫，作者源与 mirror 也字节一致；但冻结生产链仍存在可构造的科学语义绕过。主要问题是：A 分母“显式关系”仍由标题与 ID 后缀推导；丰富安全语义没有进入生产行；A/B 的实际图表仍存在绕过 typed projection 的入口；C 兼容 fallback 可把多主要终点缺时点误判为完整；真实 PNH B/C 构建器仍输出粗 locator。现有测试和 W03 浏览器证据没有覆盖这些反例。

本结论仅是冻结风险合同的工程/科学语义挑战结果，不是全部药物结果的正式科学接受，也不替代医学、统计或项目批准。

## 六项审阅判定

| 审阅项 | 判定 | 摘要 |
|---|---|---|
| 1. 分母身份与跨模块/跨期/组别混配 | **FAIL** | 生产 A 构建器把标题相等加 EG/OG 数字后缀相等写成 `related_group_ids`；旧兼容查询仍能凭标题和唯一候选返回分母。 |
| 2. 安全语义保真 | **FAIL** | helper 能识别否定、grade 集合和复合项，但生产 A/B round-trip 折叠成 `generic_ae`，语义字段未进入门户数据模型。 |
| 3. typed 数值 A/B/C 全链 | **FAIL** | A 主疗效图仍直接读 raw `value`；A 气泡默认治疗组 N 而表格显示总 N；B 的任意 `matrix_views.point` 可覆盖投影并标“可比较”。 |
| 4. C outcome 全 universe/实例与 arm 关系 | **FAIL** | 新实例 helper 可用，但实际兼容 fallback 只比较角色集合；构造两个 primary、仅一个 timepoint 仍被 Fresh C 接受。无 arm 关系的 intervention 被静默丢弃。 |
| 5. W01 精确来源/locator | **FAIL** | B/C 合成 fixture 的精确 JSON locator 窄范围通过；真实 PNH B/C 构建器仍使用 `studies[]` 或 `studies[]/{nct}` 粗定位及生成式原文。fixture 修复没有修复生产路径。 |
| 6. 测试是否覆盖实际反例 | **FAIL** | 冻结测试 18/18 通过，但安全与 C 新测试主要测 helper；联合运行 C fixture 仍走无 `outcome_id` 的旧 fallback；W03 绑定浏览器证据只有 A 矩阵一条旅程。 |

## 确认缺陷

### F01 — P1：A 的“显式”分母关系仍由标题和数字后缀制造

- 精确位置：`packets/2026-09-11-pnh-vertical/build_pnh_a_payload.py:426-460`；`src/ci_workflow/reports/b/safety_denominator_crosswalk.py:126-168`。
- 可复现条件：同一研究存在 AE `EG001` 与 outcome `OG001`，标题相同，但来源没有声明两者关系。构建器以 ID 尾号相同且标题相同生成 `related_group_ids`，随后 rich lookup 将其当显式边接受。另用单条 `other` 记录调用旧兼容 `lookup(stat="other", period="TP1", title="Drug X")`，当前返回 `10`，完全没有 study/module/group/source 身份。
- 确认类型：**确认缺陷**；旧无元数据调用的可达性另属于迁移风险。
- 违反合同：DESIGN §4 要求分母关系由来源身份和显式关系证明，标题只能形成候选；同 N、唯一候选或跨模块命名不能创建关系。当前实现只是把标题启发式包装成“显式边”。
- 最小修复：生产构建器只接受来源真实关系、测量自身 denoms 或经审计的映射表；不要从 EG/OG 后缀与标题生成边。把无 rich identity 的兼容 lookup 隔离到只读历史迁移，并在新生产路径 fail closed。

### F02 — P1：否定、grade 集合、严重性、TEAE/相关性和复合父子语义未进入生产消费链

- 精确位置：丰富对象定义于 `src/ci_workflow/reports/b/safety_concepts.py:85-143`；A 生产构建器仅调用粗分类并只写 `term_key/category`，见 `packets/2026-09-11-pnh-vertical/build_pnh_a_payload.py:540-607`；A 门户 `SafetyRow` 没有 polarity/grade/seriousness/relatedness/parent/children/count_basis 字段，见 `src/ci_workflow/renderers/portal/report_a.py:167-186`；B 再映射会把未列入少量字典的概念降为 `common_ae/generic_ae`，见 `packets/2026-09-11-pnh-vertical/build_pnh_b_audit.py:394-408,1067-1093`。
- 可复现条件：将 `Non-serious TEAEs`、`Participants without SAEs`、`Grade 4 adverse events`、`Grade 1 or 3 adverse events`、`TEAEs, SAEs and events leading to discontinuation` 依次通过当前 helper→A/B 生产映射。helper 分别识别 `non_serious_teae`、`absence_sae`、`grade_specific`、`grade_specific`、`composite_ae`，但生产 round-trip 均变成 `generic_ae`；grade 集合、否定和 children 消失。
- 确认类型：**确认缺陷**。
- 违反合同：PRD §4.3 和 W03 步骤 2 要求这些语义贯穿实际 A/B 消费者，不得只有 helper 正确。语义丢失会使“无 SAE”与“有 SAE”、Grade 4 与任意 AE、复合父项与单项在展示/筛选/比较层不可区分。
- 最小修复：把 `SafetyConcept` 的全部 typed 字段加入事实/门户模型并序列化；生产构建器消费 `describe_safety_concept()` 而非只消费字符串 key；B 不得通过有限 family 字典再降级；复合项保留父子及 count basis，不自动求分母或拆分数值。

### F03 — P1：typed 数值没有成为 A/B 图表与表的唯一真源

- 精确位置：A Python 已生成 projection，见 `src/ci_workflow/renderers/portal/report_a.py:565-575,1748-1757`；但 A 疗效图直接按 raw `item.value/unit` 分组、定域和绘制，见 `src/ci_workflow/renderers/portal/assets/report-a.js:768-838`。A 矩阵虽读取 projection，却将非百分比轴仍至少扩到 100，并在 tooltip 固定加 `%`，见同文件 `:1037-1093`。默认气泡大小是治疗组 N，模板见 `src/ci_workflow/renderers/portal/templates/a/matrix.html.j2:7-17`，但表格更新固定写 `trial.sample_size`，见 `src/ci_workflow/renderers/portal/assets/report-a.js:908-925`。
- 精确位置（B）：`matrix_view(s)` 只是任意 Mapping，见 `src/ci_workflow/renderers/portal/report_b.py:1246-1271`；matrix 投影直接信任 `point.x_value/y_value/size`，再覆盖 `renderable` 并标记“可比较”，见同文件 `:2411-2425`。
- 可复现条件 A：输入 efficacy `value=12, unit="人"` 且无 numerator/denominator。Python projection 因无法形成参与者比例为 `renderable=false`，但 A JS 的 `renderEfficacy` 仍按 raw 12 画柱。当前 W03 截图也显示默认“治疗组样本量”语义下，完整表的“试验样本量”列为总 N（420/188/612/156），与气泡 size basis 不同。
- 可复现条件 B：直接向 `_project_record(domain="matrix")` 提供单臂绝对点 `{x_value:42,y_value:7,size:30}`；当前返回 `renderable=True,status="可比较"`，即使没有对照、没有可验证差值，且附带的 projection 被误推为 `participant_count|%`。
- 确认类型：**确认缺陷**。
- 违反合同：DESIGN §2/§4 和 V2-20–26 要求 Python→payload→JS→表消费同一 typed 投影；无对照不得形成差值，无 N 的人数不得形成比例，轴域和 size label 必须来自最终投影。
- 最小修复：所有数值图 JS 只消费 `numeric_projection.plot_value/plot_unit/renderable/facet_key`，raw 值仅留折叠表证据列；按 facet 分图并从最终点定域。A 表的样本量列随当前 size preset 切换并显示逐点 `size_basis`。B 将 matrix view 改为封闭 typed 模型，只接受 `reports/b/pages.py` 已校验的 comparison row/point，不允许任意 Mapping 提交绝对点。

### F04 — P1：C 兼容 fallback 可跨实例误配并漏掉多 primary 缺口

- 精确位置：新实例校验位于 `src/ci_workflow/reports/c/endpoint_instances.py:35-156`；Fresh C 仅在任一 endpoint 有 `outcome_id` 时使用它，否则回退到每试验 `endpoint_key` 集合相等，见 `src/ci_workflow/application/fresh_c_research_package.py:286-332`。
- 可复现条件：以当前 C fixture 为基础，在 `trial-alpha-1` 增加第二条 `endpoint_key="primary"` 的终点定义，不增加时间点、保持所有行无 `outcome_id`。当前 `validate_fresh_c_content()` 接受该包（实测 `legacy_multiple_primary_missing_timepoint=ACCEPTED 33`），因为集合仍是 `{primary}`。
- 确认类型：**确认缺陷**。
- 违反合同：PRD §4.3、DESIGN §4 和 V2-30/31 要求每个 outcome 实例独立绑定角色、组/队列/期/窗；角色集合不能替代实例身份。
- 最小修复：所有新 C 包强制每条 endpoint/timepoint 带稳定 `outcome_id`；旧 fallback 只能用于已标识的历史只读快照，且至少要求每角色恰好一个终点和一个时间点，否则 fail closed。把反例放进 Fresh C 完整内容验证和页面投影测试，而非只测 helper。

### F05 — P1：W01 精确 locator 只修了合成 fixture，真实 PNH B/C 仍不满足

- fixture 的窄范围正证据：B 为每个事实建立 `$.facts[index].quote` 并把对应文本写入 JSON bytes，见 `tests/unit/reports/b/test_fresh_b_research_package.py:415-479`；C 为每个 observation 建立 `$.observations[index].source_text`，见 `tests/integration/test_fresh_c_research_package.py:366-387`。联合运行已通过 W01 摄取，这部分为 **PASS（仅合成 fixture）**。
- 生产缺陷位置：PNH B 事实仍使用 `studies[]` 粗路径和生成式 `"CT.gov 登记结果度量"`，见 `packets/2026-09-11-pnh-vertical/build_pnh_b_audit.py:370-391`；PNH C 的所有观察共用 `studies[]/{nct}`，见 `packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py:42-52,96-98`。
- 可复现条件：把真实 PNH B/C 构建器产物送入要求“原始字节→无通配精确 locator→原文重提取”的 W01 流程。粗集合/研究级路径无法唯一重提取每条数值或条款，生成式 original text 也不是来源原文。
- 确认类型：**确认缺陷**；“fixture 已修”不能证明生产路径已修。
- 违反合同：FR08、DESIGN §3 和 V2-07–16 要求 source version 字节与逐事实精确片段闭合，不能以报告级/研究级 locator 或生成说明替代。
- 最小修复：PNH B/C 从已持久化原始 JSON 对象生成每条事实的无通配 JSONPath（含真实数组索引与字段），`original_text/source_text` 必须等于该路径重提取值；再以同一真实构建器跑 W01 ingest 和 manifest-only 恢复测试。

### F06 — P1：测试通过但漏掉实际生产反例

- 精确位置：安全/数值新测试集中于 helper 和模型，见 `tests/unit/test_w03_safety_numeric_contract.py:19-126`；C 新测试直接调用实例 helper，见 `tests/reports/c/test_w03_instance_contract.py:14-70`。C 联合 fixture 的 `_observation` 没有 `outcome_id` 输入/输出，见 `tests/integration/test_fresh_c_research_package.py:182-242`，因此联合运行实际走旧 fallback。
- 实测：`PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q tests/unit/test_w03_safety_numeric_contract.py tests/reports/c/test_w03_instance_contract.py tests/integration/test_multi_report_product_run.py::test_multi_report_submission_runs_each_report_independently_and_resumes_idempotently --tb=short` → **18 passed in 2.87s**。同一源码上的多-primary缺时点反例仍被接受。
- 浏览器证据：W03 绑定的新证据只有 `output/playwright/W03-matrix-journey.png` 和一个 A fixture payload；截图确认了 A 矩阵和表，但恰好暴露 size basis/总 N 不一致。没有与当前冻结源码和 W03 反例绑定的 B/C 浏览器旅程。历史 B/C 截图不能自动继承为本候选证据。
- 确认类型：**测试缺口/接受缺口**。
- 违反合同：W03 出口和 ACCEPTANCE V2-17–26/30/31 要求实际 A/B/C 消费者与浏览器，不是 helper-only 绿灯。
- 最小修复：加入四类端到端反例：安全 typed 语义从 builder 到 A/B payload/JS/表；A projection-unrenderable 不绘图且样本量列跟随 preset；B 任意/单臂 matrix point 被拒；Fresh C 多-primary/组期窗错配及生产 PNH 精确 locator 被拒。浏览器至少覆盖 A/B/C 各自受影响页面、tooltip、轴域和折叠表同源。

## 仅风险 / 次要缺陷

### R01 — P2：无 arm 显式关系的 intervention 被静默丢弃

- 精确位置：`src/ci_workflow/reports/c/arm_interventions.py:17-24` 对非列表或未知 label 直接 `continue`；生产 C 构建器只遍历成功关系，见 `packets/2026-09-11-pnh-vertical/build_pnh_c_audit.py:329-347`。
- 可复现条件：intervention 存在但缺 `armGroupLabels`，或 label 与 arm label 仅大小写/空白不同；该干预不会进入任何 arm，也没有“关系缺失”观察或覆盖状态。
- 类型：**确认的数据可见性缺陷**，尚未证实会把干预错配到另一 arm；因此不作为跨 arm 误配 P1。
- 最小修复：保持“不回退 arm1”，同时为未绑定 intervention 生成显式缺关系状态/阻断项，并测试它不会被页面误当“无干预”。

## PASS 项与未验证范围

- **PASS**：W03 两个新 helper 测试和联合运行在当前冻结字节上均通过；关键新增文件哈希与实现结果一致。
- **PASS**：`src/ci_workflow/renderers/portal/assets/report-a.js` 与 `assets/portal/report-a.js` 字节一致；`charts.js` 两副本字节一致。
- **PASS（局部）**：新 C `outcome_id` helper 对完整身份、多 primary 正例和缺实例反例有效；arm intervention 正例只按 `armGroupLabels` 投影。
- **UNVERIFIED**：请求模型/effort 的实际运行时身份；完整 B/C 当前浏览器旅程；真实 PNH v107 重建；全 gate；24 门户；三宿主；正式科学接受和 RC 接受。

## 最终判定

W03 不满足冻结接受条件，不能进入“风险合同已接受”状态。下一安全动作应先修复 F01–F06，随后用真实生产构建器重跑 W01 精确重提取、A/B/C typed payload 与浏览器同源反例；任何修订都会改变当前候选身份，受影响门需要重新验证。
