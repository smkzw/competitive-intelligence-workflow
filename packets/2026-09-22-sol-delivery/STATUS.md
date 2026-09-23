# 2026-09-23 0923V1 新裁决与续建状态

## 2026-09-23 暂停前 W07 安全来源批量接缝（最新；开发候选）

- 本轮新增直接安全结局的批量候选核对：每份 CT.gov 研究切片只重提取一次；按完整身份唯一绑定，歧义、来源原子复用和无匹配各留显式缺口。原始人数没有同终点分母时仅保留直接人数并标风险率未知；原文明示 0/0 时不产生零风险率。复合 TEAE/SAE 标题在 class 未单独分面时保留原复合终点，不强拆成两种事件。
- 相邻科学审计发现原安全域正则把 `treatment-emergent ADA`（抗药抗体）误判为 AE；规则版本由 7.5 升至 7.6，去掉无条件的 `treatment[- ]emergent` 匹配，真实 TEAE/SAE 仍匹配。旧 AD 夹具仍明确保留 **7 条 0/0 + 1 条 `numAffected` 缺失**，未补零或改原始资料。
- 以原始两页 PNH CAS（SHA-256 `1e0a9bbe…`、`c3bdbe61…`）重建通用候选：**3898 疗效 + 514 安全**，载荷 SHA-256 `93a629cfbcc84569b22af635df95e8a44f616e94dd633c649c43f752387c32c9`。与上一候选 3895/517 的差额是 3 条 ADA 改回非 AE 域，不是事实被删除。安全 514 中直接报告结局 **243/243** 具有唯一精确候选（459 条原子事实、243 条直接来源声明）；另 **271 条 AE eventGroups** 未由本分支绑定。直接来源覆盖范围内仍有 **50 条解析问题**，不得把 243 候选称为来源闭包或科学通过。
- 正式 W05A v6 门户未替换，原 4412 条展示事实逐条完整来源闭包仍记 **0/4412**。本轮新候选均在自动清理的临时项目生成，未写正式 PNH SQLite/快照或重新发布 A/B/C；24 门户、三宿主、四档桌面视觉与 RC 均未通过。下一步先给 AE 事件组的实际人数（含死亡）建立独立精确绑定，再对新候选按来源/统计对象复核与正式快照投影；详见本轮 handoff。
- 最终源码的 W07/CT.gov/通用构建器相邻批 **34 passed in 94.75s**；Ruff 受影响 `src/tools/tests`、strict-mypy `243 source files` 与 `git diff --check` 通过。这不是全开发 gate、浏览器门、真实医学独立复核或发布验收。
- 暂停前另运行一次 `bash tools/gate.sh`（非 clean 模式）：**GATE_FAIL，6 步中 1 步失败**。Ruff、全 243 源 strict-mypy、保留轨 smoke 20/20、层级审计 7/7、旧路径检查均通过；活跃 unit/contract 为 **1062 passed、2 failed、20 deselected**。失败①旧枚举测试 `test_state_enums.py:96` 不含已存在的 `user_cleared`；② W03 冻结合同把冻结时 6 个 `current_sources` SHA 当当前源码哈希，后续合法源码变化造成漂移。两项在本轮起始提交 `887667b` 已存在；未改旧冻结材料、未把开发门记为 PASS。恢复后须先明确历史冻结证据与当前源码的适用语义，建立新版本/替代断言后再处理，不为绿灯回退真实功能。

## 2026-09-23 W07 直接报告安全结局的精确来源接缝（开发候选；未闭包）

- A 安全行新增仅供来源核验的原始 class/category 标题，通用构建器保留其未翻译字节，继续以现有中文 `measure_context` 展示。新绑定分支重新打开当前 CT.gov 切片，要求组号/组名、完整终点、class/category、访视、单位、统计对象、数值和既有引文全部一致；同值的另一类目不能被误绑。
- 人数、事件次数、原文百分比分别按各自直接报告数值入事实；人数附带同组分母原文时另存分母事实，但不把人数变成推算风险率。直接安全事实/声明进入现有 A 研究包提交前复验。AE eventGroups 的 `n/N` 派生继续走单独计算分支；来源缺字段、`0/0` 不会被改造成零风险率。
- 合成双类目同值、事件次数、直接百分比及人数+分母已覆盖正反例；人数小批经现有摄取器形成来源版本、两条事实及精确片段。此项尚未在 517 条真实 PNH 安全候选上做批量唯一匹配或正式项目摄取，也未做页面/浏览器与独立医学复核；当前门户逐事实来源闭包仍 **0/4412**。下一步对真实 CAS 批量统计唯一/歧义/解析缺口，再逐批投影；不因本接缝存在就改变 W07 FAIL。
- 最终源码的 W07 桥接与构建器定向批 **17 passed**；受改文件 Ruff、strict-mypy 3 个源文件和 diff 检查通过。更宽的 CT.gov 覆盖批在本轮早期字节 **30 passed**，不能与最终 17 项合并冒称同一终验。

## 2026-09-23 W07 通用 A 安全域观察保全（当前增量；未闭包）

- 通用 A 构建器原把登记 `outcomeMeasures` 内 TEAE/AE/SAE 等安全域数值只记旁路诊断、未写入安全行。现按现有概念分类保留原终点、class/category、原始组号/组名及观察窗；人数、事件次数、百分比分别为 `participant_count`、`event_count`、`participant_proportion`，复合/mixed 不借分母或拆数。AE eventGroups 的 SAE 人数与死亡人数分别处理：前者缺失不会遮蔽后者，字段缺失不变成零；明示零仍保留。合成多类型/缺失/真零测试通过。
- 同一两页真实 PNH CAS 重建为 3895 疗效 + **517 安全**，模型校验通过，A 站点实际渲染 `data/report.js` 仍含 3895/517 且两集合原始组号均完整；载荷 SHA-256 `4041ddec3751cf99e15344b0b79bdb740b39eeec1c08c96c9f971c8f505ccce1`。历史 v106 研究包的 519 安全行多出的 2 条是 `-declared` 声明臂归因影子行，非独立观察；v106 可见门户是 517 行。新候选 517 只是数量与统计对象接通，**没有逐事实 source version/精确切片绑定、医学独立复核或视觉验收**，不可宣称替换正式门户。
- 相关构建/来源定向 `4 passed`；A 相邻验收/安全投影批 `26 passed, 1 failed`，唯一失败为既有 AD 原文 7 条 `0/0` 比例未定义和 1 条缺失 `numAffected` 的科学门，未改原文/放宽门；Ruff 与 strict-mypy `src tools` 243 文件通过。当前 W07 正式来源闭包仍 **0/4412**，后续需给直接报告安全结果与 AE 组计数建立逐事实精确原子绑定，处理未映射行，再做独立科学与真实浏览器验收。

## 2026-09-23 W07 通用 A 构建器的组别/分母身份与旧链差异（当前增量；未闭包）

- 从与 v106 页来源逐字节相同的两份 CT.gov CAS、当前别名表重新运行通用 `tools/build_a_payload.py`，发现其直接输出虽同为 3895 条疗效行，但只有 **271** 条安全行（v106 研究包 519），原先 3895 条疗效行均未携带登记公布的组分母，666 行臂名也不同。故不能把通用脚本输出直接替换正式 v106。其原始候选重算为 2916/3895，979 无完整匹配；安全域观察丢失是单独的产品阻断，后续要把安全概念与原文计数接入共同证据链，而不是用总数补齐。
- 通用构建器现优先使用测量级组名，提取同一测量公布的正整数分母；相同重复值允许，组内冲突值明确不绑定并写入派生诊断。合成双测量反例确认多期组名覆盖与冲突拒绝。再用同一两页真实 CAS 重建：3895 疗效、271 安全、3895 行有同组分母，本样本 `denominator_conflicts=0`；新载荷 SHA-256 `98159d680da05abc3ea7d5343cbdee7856ee0ff295994a99f33cebea805d4d1f`，批量候选 **3425/3895**（原始事实 4034、470 条无完整匹配），`eff-10` 已可唯一绑定。来源仍有 3 个缺失和 51 个解析问题。合成/邻接定向 **3 passed**，Ruff、strict-mypy 243 文件、diff 检查通过。该生成物仅在可再生临时目录，清理后仅留此摘要与输入/输出 hash；**正式 4412 条门户来源闭包仍 0/4412**，也未解决 24 门户/三宿主/视觉门。

## 2026-09-23 W07 批量唯一结局候选接缝（当前增量；未闭包）

- 新增按来源只重提取一次的 A 疗效批量候选绑定：完整身份唯一且来源原子未被其他报告行复用才输出已绑定行、原始事实和直接证据声明；无匹配、跨来源多匹配、同原子跨行复用分别留下显式缺口，解析/缺失问题单独保留。两个不同访视的人数与分母在临时项目经现有摄取器形成 4 个事实版本、2 个声明版本及精确原文片段；真实 AD NCT02277743 的直接 `10.3` 行也与单行绑定结果一致。首次集成测试先后因原始 CAS 放在项目外、诊断 SQL 使用错误列名失败，修正测试设置后相关整族 **28 passed in 95.50s**，Ruff、单模块 strict-mypy、diff 检查通过。此 API 只产出**未独立复核的开发候选**，没有写正式 PNH 项目、没有生成最终门户；当前 4412 条来源闭包仍 **0/4412**，前端视觉门亦未通过。
- 提交后另以当前 v106 研究包原始字节 SHA-256 `867ca66458df8a7343889bd9a601b567c12e2dfb5e069835a865b416bdbb9607` 与两份本地分页 CAS 逐字节核对一致，在自动清理的隔离临时目录重开 48 个实际采用 NCT 切片。批量接口对 3895 条疗效行得到 **2966 个唯一候选、3557 条原始事实、2966 条直接证据声明、929 条无完整匹配**；来源另有 3 个缺失、51 个解析问题。此结果复现旧输入的候选盘点，且不含跨行原子复用，但**不是新载荷重建，更不是正式摄取/科学复核或 4412 条展示事实闭包**。必须先逐项解释 929 缺口与安全行，再决定可晋级范围。

## 2026-09-23 W07 类别时间窗误标修复（当前增量；未闭包）

- A 历史载荷构建器原把包含 `baseline` 的任何 class 当成 Baseline 访视；现与 CT.gov 原子解析共用明确单一访视判定。`from baseline` 是比较基准，不改写测量级时间窗；多访视类别也不擅自取一个时间点。定向来源/登记审计整族 **24 passed in 94.73s**，Ruff、两个源文件 strict-mypy、diff 检查通过。首次直接导入历史脚本测试因脚本顶层解析命令行而失败，测试改为验证共享判定后通过；历史冻结产物未修改。该修正尚未重建正式 PNH 研究包或门户，2966 唯一候选需在新输入版本重算，**0/4412** 当前逐事实来源闭包与 W05 前端视觉 FAIL 均不变。

## 2026-09-23 W07 测量/class/category/访视层级保真（当前增量；未闭包）

- CT.gov 原子及事实科学上下文现保留原始测量级时间窗、class/category 标题，并仅在 class 明确为单一访视时记录观察访视；`from baseline` 只表示相对基线，不能自动变成基线访视。A 疗效绑定同时核对人群标签/精确来源路径，公开绑定入口要求当前行**唯一**匹配，重复候选失败关闭。旧事实未携带新增字段时保持原序列化。W07/CT.gov/A 包邻接批 **25 passed in 96.20s**，Ruff、单模块 strict-mypy 和 diff 检查通过。
- 在当前 v106 A 研究包 SHA-256 `867ca66458df8a7343889bd9a601b567c12e2dfb5e069835a865b416bdbb9607` 的 3895 条原始疗效行上，只读重提取后严格单候选 **2966**（直接数值 2375、直接人数 591），未发现同原子跨行占用；929 条无完整匹配，不自动补造。真实例 NCT02534909 `eff-19` 的 `Overall (Up to Week 4)`/`Responder` 唯一匹配，NCT03500549 `eff-1191` 同值多 class 因 `Functional Scales - Cognitive functioning` 唯一匹配；NCT04820530 `eff-10` 旧构建器把“from baseline”错写为 `Baseline`，严格绑定明确拒绝。**2966 仍只是候选，不是已摄取/已复核/已发布**；站点 4412 行来源闭包仍 0/4412。下一步修正构建器错误时间标注，建立唯一候选批量来源→事实→快照→页面的受控接缝，并分别处理 929 条未匹配与安全行。

## 2026-09-23 W07 当前 v106 候选原始单位与时间身份复核（当前增量；未闭包）

- 改用实际 `runs/pnh-vertical/abc-v106` A 研究包（SHA-256 `867ca66458df8a7343889bd9a601b567c12e2dfb5e069835a865b416bdbb9607`）而非较早 `runs/test-pnh` 包重算：48 个报告采用试验、3895 条原始疗效行、519 条原始安全行，两个 CT.gov 分页来源。保留原始单位后，严格逐行唯一候选为直接数值 **1107**、直接人数 **62**，对应 1169 个不同来源原子；另有 238 条多候选、2479 条终点/时间窗失配、9 条单位失配。2479 中 2469 为同终点但时间窗不同、10 为无同终点或解析缺口。候选不是入库事实，当前 W05A v6 仍 **0/4412** 逐事实完整来源，不能混用 3895+519 与 3895+517 分母。
- NCT04820530 `eff-1` 真正从当前分页 CAS 切片重提取 `92.2`，原文单位 `Percentage of responders`、规范显示单位 `%`、同组同终点/时间窗唯一；报告保留原始单位和精确来源路径，不靠模糊同义词。该更改的 W07/CT.gov/W03 相邻批 **35 passed in 95.83s**，修改源码 Ruff 与 2 文件 strict-mypy 通过。仍未持久化正式项目，也未让 1169 条候选自动晋级。
- 另从当前 v106 源载荷用新代码重渲染 A 疗效页，在 1600 CSS px 的真实 Chromium 中无 console error、百分比可见，但首屏单观察行留白大、文字挤左，**桌面视觉门仍 FAIL**。截图本机 `output/playwright/w07-a-efficacy-unit-1600.png`（SHA-256 `3caed29ee656f9c5a6652477661ee4300047ce3ba8097d405c2c8eb35de608d8`）；不是四档/四状态验收。浏览器与本地预览服务已关闭，13 MB 临时渲染目录移入废纸篓。后续 W05 须按 PresentationPlan 收紧稀疏卡片几何；W07 须处理 class/category 与实际访视身份，不以 `from baseline` 字样推断“仅基线”。

## 2026-09-23 W07 登记直接报告人数的精确绑定（当前增量；未闭包）

- A 疗效绑定现区分来源直接报告的人数与由 n/N 推得的百分比：人数行须核对同一 NCT、原始终点、时间窗、来源组别全名、原始人数和同组分母，保留人数单位与数值，不能把 `30/35` 偷换为 `85.7%`；缺少或冲突的分母原子在研究包复验时拒绝。`Participants` 等明确人数单位进入人数图形分面，不被当成连续量。
- 用旧 PNH 研究包原始分页字节经临时 CAS 重提取 NCT04085601，旧包 `eff-1` 的 30 名应答者得到**唯一**精确身份匹配，绑定到 `$.resultsSection.outcomeMeasuresModule.outcomeMeasures[0].classes[0].categories[0].measurements[0].value`，原文人数 `30`、分母 `35`，该研究解析出 135 个原子、0 个问题。合成报告渲染后该行仍为 30 人的人数分面，非 85.7% 比例。真实探针未写入正式项目、未修改 W05A v6 门户，不计作 4412 行来源闭包。相邻来源与图形回归批 `24 passed in 40.20s`；修改文件 Ruff、2 文件 strict-mypy、diff 检查通过。下一步从旧包原始行系统性识别精确人数/直接数值、派生率及无法映射项，并将可证实项接入真实快照与页面；安全性计数、B/C 仍待处理。
- 对旧研究包的 **4141 条原始疗效行**另作只读严格候选盘点：366 条直接数值、26 条直接人数各有一个候选，且这 392 条没有复用同一来源原子；251 条多候选。其余 3498 条按首次失配点拆为终点/时间窗 3036、组别 325、单位 135、数值 2。诊断只给出候选资格，不代表已入正式快照或证明医学可比；旧包 4141 与站点 3895+517 的分母不可混用。当前正式站点仍 **0/4412** 完整逐事实来源；下一批优先追查 3036 条终点/时间身份和 251 条重复候选的类别/测量上下文。

## 2026-09-23 W07 PNH 50 研究批量来源试读与 0/0 门（当前增量；未闭包）

- 当前 W05A v6 门户的 3895 条疗效 + 517 条安全行仍为 **0/4412** 逐事实完整来源。旧研究包的 10 页 CT.gov 原文含 190 个 NCT，其中 132 个明确 `hasResults=false`、58 个有结果；门户所用 50 个 NCT 均在有结果集。新摄取接缝在这 50 个研究上重开原始登记字节，得到 15,556 个数值原子、81 个解析问题和 3 个缺失问题，没有整研究读取失败。仅按试验+数值初筛时，疗效 442 行无候选、1531 行单候选、1922 行多候选；安全性按试验+n/N 初筛为 269/19/229。以上都是**弱线索**，不能当临床身份闭合或把 4412 分子加一。
- 全 190 试读首轮发现无结果研究被误当解析失败，且 NCT00397813 的真实 0/0 使结果解析抛零除。解析器现对登记明确 `hasResults=false` 返回无数值，对 0/0 记录“比例未定义”的待核问题而不生成 0% 或令整研究崩溃；登记声称有结果但缺模块仍报错。实际报告所用 50 研究改后全数可读，但其 81/3 项问题未修复。下一批须按身份、分面和来源上下文拆分弱候选，并逐项解释 442/269 无候选与多候选；W07 继续 FAIL。详情见 [W07 来源追踪](evidence/W07-source-trace-0923.md)。
- 相邻 AD 来源审计旧断言原只允许 1 个缺失；新规则真实识别另 7 条 0/0（NCT03334396 与 NCT05131477），故首次邻接批 **1 failed / 27 passed**。未改原文或补零；更新断言分别核对原 `numAffected` 缺失与 7 条“比例未定义”，同时将受影响试验纳入未闭合列表。最终 W07/CT.gov 覆盖/A 研究包/发包镜像整族 **28 passed**；Ruff、243 文件 strict-mypy、候选包校验通过。这只证明相邻开发门，不是科学闭包或发布门。

## 2026-09-23 W07 真实 AE 计算依据进入 A 页（当前增量；小批）

- 从已锁定快照按事实版本、片段、计算声明和实际安全性行逐项核对，才投影公开计算依据；不从行内 `n/N` 猜测已有派生。真实 AD NCT02277743 的“任何SAE”7/229→3.1% 现可在 A 安全页证据侧栏展开查看两项登记原文、收集时间窗、计算式、精确字段及外部来源链接；错值被拒。未有结构化派生的旧行不自动冒称已核证。
- 1600px 真实 Chromium 首检发现长英文/字段路径把侧栏撑出视口（client 395px、scroll 610px）；调整单列栅格后为 395/395px，截图位于本机 `output/playwright/w07-calc-evidence-1600-final.png`，SHA-256 `e725a7af89616be0a9584da3f76cb2b4b7267bfb405f319ac7e447f533ac6a6e`。实际浏览器确认折叠、来源链接、Esc 关闭与焦点回到触发按钮；页面不是正式完整 AD 来源闭包。A 渲染/来源/事务/镜像相邻批 **44 passed**、Ruff、243 源文件 strict-mypy、JS 语法和候选包校验通过；见 [W07 来源追踪](evidence/W07-source-trace-0923.md)。

## 2026-09-23 W07 AE 计算派生与安装迁移清单（当前增量；未闭包）

- AD NCT02277743 的“任何SAE”真实 7/229→3.1% 小批计算声明现有结构化、版本绑定的 `calculation` 派生：输入事实版本和原文片段、规则/版本、公式、输出及适用行进入 append-only SQLite 与不可变快照，并验证空项目恢复。错算成 3.2% 在来源持久化前拒绝；重复摄取不重复新增派生。0015 迁移保留旧记录和防改/防删保护。
- 安装清单现声明全部 15 个迁移，包校验逐一比对实际 SQL。W07/迁移/包合同批 **13 passed**，`package verify` 为开发候选 `PACKAGE_OK`；此前相邻范围 32 项、全仓 Ruff 与 243 源文件 strict-mypy 通过。不同测试时点不合并为终验。fresh-install、三宿主、页面完整解释和 4412 条来源闭包仍未通过。详见 [W07 来源追踪](evidence/W07-source-trace-0923.md)。

## 2026-09-23 W07 登记结果原子路径与分母重提取（最新增量；未闭包）

- AE `timeFrame` 现进入原子/事实语境；AD NCT02277743 登记原文至 Week 28，旧 A 行“来源未单列时间窗”被新绑定拒绝，历史夹具未改。单条 `任何SAE` 的 7/229→3.1% 已拆成两项原始事实及共同计算声明，行内只把 `7` 当作来源原文；缺分母、错时间/组别/数值、缺声明拒绝。邻接批 `20 passed in 86.80s`，Ruff/单模块 strict-mypy 通过。尚缺输入 fact version 的结构化派生记录和页面完整说明，不能算来源门通过；见 [W07 来源追踪](evidence/W07-source-trace-0923.md)。
- A 研究包提交前现会重提取显式绑定的疗效原子并核对整行/原文/来源版本；同一行重复主事实、错行和编造引文被拒绝。真实 AD `10.3` 的正向绑定与研究包反例已测，相关批 `20 passed in 84.21s`，Ruff 与单模块 strict-mypy 通过。该门不替旧事实自动补原子，也不覆盖派生率、安全性或 B/C；W07 仍 FAIL。详见 [W07 来源追踪](evidence/W07-source-trace-0923.md)。
- 单条 A 疗效行的来源绑定已贯通：NCT02277743 的 16 周 Placebo IGA `10.3%` 重新抽取原文 `10.3` 后，核对试验/终点/组别/时间窗/单位/数值，带精确 JSON 路径及计算所得 source version 进入真实站点 `data/report.js`。错身份、错值、错组别与冲突引文均拒绝；人数/分母派生值不会走这条直接报告绑定。邻接批 `22 passed in 83.23s`、Ruff 与单模块 strict-mypy 通过。仅为单条内存小批，正式 PNH 4412 条及 B/C 来源门仍 FAIL；参见 [W07 来源追踪](evidence/W07-source-trace-0923.md)。
- 后续按用户明确裁决加固 `numAffected` 缺失的跨层回归：NCT05131477 的真实缺口只产生 `missing/未知待核`，不会生成零原子或零事实；NCT02277743 的原文明示零继续进入 `reported_zero`，事件术语进入事实科学上下文。首次测试因选错研究失败，修正后定向文件 `4 passed in 24.34s`，Ruff、单模块 strict-mypy 与 diff 检查通过；缺失未被修复，W07 来源科学门仍 FAIL。详情见 [W07 来源追踪](evidence/W07-source-trace-0923.md)。

- 后续已增加原子 `ResearchFact` 转换，并用现有摄取器在独立临时项目实际保存真实来源小批。AD 登记 NCT02277743 的报告值、真零事件与独立分母形成 3 个事实版本；本机 PNH CAS NCT04558918 的 `68.8` 形成 1 个来源版本、1 个事实版本及可重提取精确片段。科学组别/终点/时间/类别/角色进入事实版本上下文，旧事实省略新字段时序列化保持原样。相邻摄取/精度/回归 `11 passed`，首次诊断 SQL 连接用法错误已修正后探针成功；不把这解释为正式 PNH 入库或页面已绑定。
- 沿用已有 `SourceCapture`/CAS 和登记结果解析器，新增逐条数值、分母的精确 JSON 字段路径与重提取结果；派生百分比仍保留原始计数/分母独立路径。缺少 `numAffected` 不补零；同组某一汇总字段缺失不再遮蔽另一项有效统计。真实本机 PNH CAS NCT04558918 探针得 216 个原子结果、0 个该研究解析问题，`68.8` 可沿原始字段路径重提取。详情与 CAS 摘要见 [W07 来源追踪](evidence/W07-source-trace-0923.md)。
- 原子提取的受影响来源整族先得 `30 passed in 55.29s`；摄取接缝相关 `11 passed`；当前合并来源审计/摄取批 `24 passed in 53.59s`，改动源 Ruff/strict-mypy 与 `git diff --check` 通过。这只证明小批来源→事实/快照片段；尚未在正式 PNH 数据库摄取全部原子、建立报告行绑定与派生 DAG，也没有重算 4412 条展示事实的闭包分子。W07 科学来源门仍 FAIL；24 门户与 RC 仍未验收。下一步按 W07 工作包将真实小批接到 A/B/C 页面，再扩全量，不继续旧 PNH v107 补丁循环。

## 2026-09-23 W04 B 疗效完整事务与桌面折叠表（最新增量；开发候选）

- 在原始 PNH 夹具的内存增强样本上，一次 B 疗效保存将模型估计 82.3% 修订为 80.1%，图、完整表、来源 view 和证据抽屉显示同一当前值；51/60 原始计数仍保留，不被偷算成 85%。第二次 B 保存保留第一次修订自身的 request/revision。估计值计数改变而未同时提交重新核实的估计值、只提交一种估计表示，均拒绝。旧领域 ID 与页面来源 view ID 已分层，页面可见行 ID 用于抽屉和消费者定位。未知来源不再硬标 ClinicalTrials.gov。
- B 疗效完整表增加数值依据、原始应答人数、分析人数和口径提示。1440/1600 CSS px 卡片内横滚，1920/2560 自动展开；四档实测全页横溢均为 0，1440 键盘箭头可横向访问。此前浏览器曾缓存旧 CSS，强制版本重载后才观察到新规则；因此旧缓存截图不可作为新源码失败或通过证据。该视觉检查基于合成样本，只覆盖 B 疗效展开表，不代表 A/B/C 四档四状态全站门。
- 邻接批初次为 `113 passed / 1 failed`，失败系测试沿用旧领域行 ID；修正后 W04 集成 `63 passed`，最终字节的两个疗效节点及资源镜像合同 `3 passed`，邻接其余 51 项未以同一最终字节重跑。strict-mypy `243 source files`、全仓 Ruff、JS 语法与 `git diff --check` 通过。局部截图保留于本机 `output/playwright/20260923-b-efficacy-revision-1920.png`（SHA-256 `027f00f8...`）和 `20260923-b-efficacy-table-1440.png`（`8ed0f111...`），并非已入包终验回执。真实研究包尚不能自动产生核证 crosswalk、统计依据与逐事实原文，W07 4412 条来源门仍 FAIL；不得宣布 W04/E04 总验收、24 门户或 RC。

## 2026-09-23 W04 B 疗效来源 view 绑定与估计值边界（开发候选，最新增量）

- 历史 PNH 数据中 B 疗效领域行与来源 view 的 row ID 不同，且 82.3% 为模型估计比例而 51/60 是原始计数。新增可选显式 `source_view_row_id` 和类型化 `value_basis`；不对历史夹具做模糊自动链接。绑定时核对产品、试验、终点、组别、人群、单位、原值及分母；错指针、无指针与无类型化依据但数值不符合粗率均失败关闭。类型化模型估计保留 82.3%，不会误算为 85%。
- 基于历史夹具的内存增强样本验证了显式链接、错误链接拒绝、估计值边界和 B 门户生成：80.1% 的用户修订同步进入领域行、来源 view、门户 `report.js` 和用户修订披露，而原始 51/60 不被重算。W04+B 验收+语义分组相邻批 `87 passed`；Ruff `src/tests/tools`、strict-mypy `src/tools`（243 文件）通过，相邻 B 验收夹具原文件摘要未变。W03 旧冻结证据与当前源码不一致仍是已记录的历史失败，未通过改旧摘要伪造通过。此处尚未实现真实研究包自动产生已核证链接与类型化数值依据，也未完成 B 疗效全事务保存或 4412 条来源闭包，不得记 W04/W07 总验收。

## 2026-09-23 W04 用户清除数值的当前层切片（最新增量）

- 按用户裁决，显式 `null` 与省略已分开：仅数值白名单可清，混合“清除+设置”及非白名单清除失败关闭。清除一个数值核心字段时，当前原始值、规范值、人数分子/分母、阈值及依赖粗率一并失效；A+B 合法同源消费者与 C 阈值分别重建，原来源片段仍保持原字节。有效当前状态为“用户清除，待重新核实”，不冒称来源未公开；数据库来源披露状态保留，用户层由 append-only 修订上下文叠加。曾试探新增数据库枚举迁移，但在已有外键数据上失败，已撤销该未提交迁移，不修改历史迁移或既有工程数据。
- 首次清除、补齐数值恢复、撤销恢复、中途故障旧 current 不变并以同请求恢复，均有定向集成用例；W04、数据库迁移与证据视图相关批 `86 passed`。Ruff `src/tests/tools` 通过，strict-mypy `src/tools` 为 `243 source files` 零错误，修改过的 JS 语法与发包作者源/镜像合同通过。B 安全页真实 Chromium 的清除数值、原值可追溯、短图格标签和完整表格已目视；展开表格在 1440/1600/1920/2560 CSS px 均无页面横溢，截图为 [b-safety-clear-expanded-1920.png](../../evidence/W04-clear-0923-desktop/b-safety-clear-expanded-1920.png)（SHA-256 `5242a3166e68a382f909175645d54366c2c41bb72c693ca52e0b79e4c07fb7c5`）。这仍是单报告局部验证，非四档×四状态全站验收。CT.gov 夹具确实缺失 `seriousEvents[16].stats[7].numAffected`：科学审计保持未通过，旧全绿测试现改为精确断言这个真实缺口及其 `reported_not_projected` 状态，绝不补 0 或冒充来源闭包；登记覆盖与镜像合同相邻批 `10 passed`。
- 本切片尚未证明 B 疗效 view 的真实同源编辑可绑定：现有 PNH 夹具的疗效 view 与 legacy 行 ID 不一致，而且首条 82.3% 明确为模型估计比例，51/60 为原始应答计数，不能误按粗率重算成 85%。接续应建立唯一且可核验的行 crosswalk，并以来源统计形式决定派生规则；不得靠模糊名称匹配或强改行 ID。也未证明 4412 条逐事实来源、四档×四状态全站桌面视觉、离线分享、24 门户、三宿主及 RC。以下历史段落保留原时点证据；最新状态以本节为准。

## 2026-09-23 W05B 安全性稀疏图与证据侧栏桌面重排（当前增量）

- B 的安全图曾在 1–2 条观察时仍占完整宽度、强制 260px 高；原因是安全页 CSS 的 `!important` 覆盖共享 PresentationPlan。现移除旧覆盖，并让 ≤4 条安全热图/状态矩阵按观察数决定 160/184px、半宽并列；密集矩阵仍可占完整行。用户修订的计算值在图格中以三位有效数字并带“约”显示，完整人数和当前修订值留在表/证据层。
- 证据抽屉打开时，桌面主画布缩至侧栏左边界，图表由现有 ResizeObserver 重排，不再让右列卡片被侧栏盖住。1920px 真实 Chromium 中主内容右缘/侧栏左缘均为 `1360px`，12 个稀疏图卡为 6 格跨度，首图 184px，修改值标签“约38.7%”，全页横溢为 0。before/after 截图分别为 `evidence/W05B-0923-desktop/b-safety-before-1920.png`（SHA-256 `8241a5eeff13b6017aca7b5e290c076495525b6ccf3a781942e7c6ed0ff5e2e7`）和 `b-safety-after-1920.png`（`d45fdf5b4d53198acf2189eed715c43211d02bbc4430c4f0dec213045c49d7a5`）；两者为同一测试研究的修订版页面，不是正式 24 门户接受证据。
- Chromium/WebKit 的 1920/2560 稀疏图 + 1920 侧栏浏览器批 **6 passed**；共享图形 pointer/回焦相关批 **10 passed**，A/C 相邻证据交互批 **4 passed**。发包镜像摘要同步。仍未完成四档×四状态×所有物理页视觉矩阵、全部来源闭包和真实三宿主验收。浏览器检查另发现当前 W04 演示样本 A 页未绑定完整公共来源谱系、B 原来源原文显示“原文未提供”且来源名称与片段版本仍需 W07 复核；不能把这次图/表更新写成逐事实来源终验。

## 2026-09-23 W04 合法同源 A+B 扇出切片（当前增量）

- A 的疗效/安全行现在可选携带真实 `source_version_id`、`group_id` 和 `cohort_id`；缺省旧行的原有序列化与兼容路径不变。用户修订的 A binding 在这些字段存在时使用它们，不再只能把 A 报告行摘要当作来源版本。这是实际逐事实来源接入 A 的必要接口，不把旧合成摘要宣称为真实来源。
- 新集成样本把同一 PNH 原始研究的 A/B 行绑定到相同来源版本、精确定位及完整医学身份。一次保存 34/62→24/62 后，A+B 两套真实门户的数值、检索索引、披露、消费者回执和 current generation 同步改变，C 未被无理由重建；原始 34/62 来源片段仍在。另一故障注入在 A 构建后中断，旧 current 指针/内容不变，同一请求重试后 A+B 均完成。原有两条错误跨报告绑定仍拒绝。
- 验证范围：`tests/integration/test_w04_user_fact_edit.py` **50 passed**；相邻 A 安全投影和包内镜像合同 **9 passed**；改动文件 Ruff、A renderer strict-mypy 与 `git diff --check` 通过。该结果只证明合法同源样本和事务合同，不证明 4412 条当前真实事实已经获得同源 A/B binding。W04 显式清数值、衍生失效与全量真实来源仍未完成；现行拒绝清除的防错门保持生效。未运行本轮全开发 gate 或 RC 门。

## 2026-09-23 A 疗效页桌面宽屏利用率修复（当前增量）

- A 疗效观察在 1440/1600 CSS px 使用更紧凑的单列；在 1920/2560 CSS px 使用两列独立观察组，按观察数均衡列高。分页仍依原始稳定顺序，对全部 6753 条可绘制观察保留可达性，不用默认 Top-N 或仅呈现首项。作者源为模块内 `report-a.js/css`，`assets/portal` 仅作逐字节发包镜像，manifest 同步更新；未引入第二作者源。
- 实际 Chromium 定向批 `6 passed, 15 deselected`，覆盖四档宽度、列数、无横向溢出、第一页与第二页各 60 条且不重复；发包镜像合同 `1 passed`，JS 语法及 `git diff --check` 通过。真实浏览器截图：`evidence/W05A-0923-desktop/a-efficacy-1440.png`（SHA-256 `45b6c56289c4b3758689050299fccdc6237a987fc16b491619eebaf1322e449b`）与 `a-efficacy-2560.png`（`ff0f5a597f9302abda0a70f6a03eccb871aa84c8a08e17ec38c328247caea460`）。截图基于现有 AD 夹具，仅证明该局部呈现，不证明真实来源已闭合。
- 四档宽屏 × 稀疏/密集/筛选后稀疏/证据侧栏 × A/B/C 全物理页面的视觉门尚未完成；W07 的 4412 条逐事实来源、W04 用户清除实际投影与合法 A+B 扇出、W06 离线分享、24 门户、三宿主及 RC 均保持未验收。历史 FAIL 不得改写为 PASS。CT.gov AE `numAffected` 缺失按用户裁决仍为“未知、待核”，绝不自动补 0。
- 宽屏真实截图另暴露按人数比计算的百分比直接输出长串浮点数。A 疗效观察现只对有明确分子/分母的计算比例使用至多三位有效数字，发生舍入时加“约”；图形悬停保留精确分子/分母，原始事实/完整表不改。定向浏览器批 `7 passed, 15 deselected`，含 11/52→“约21.2%”及图形悬停原始 11/52；这仍是局部可读性修复，不代表科学或全页视觉终验。

## 2026-09-23 里程碑 gate 与旧合同成族修复

- 提交 `e770401` 后的 `bash tools/gate.sh` 实际范围：Ruff `src/tests/tools`、strict-mypy `src/tools`、活跃 unit+contract、保留轨兼容子集、测试分层、旧路径检查。结果 **GATE_FAIL**：静态两门全绿；活跃批 `10 failed, 1054 passed, 20 deselected`；保留轨 `20 passed`、分层 `7 passed`、旧路径检查通过。
- 十项失败中九项属三族旧测试输入/表示假设，现已按当前合同修订：B 的七项运行测试将研究包确实放入项目根内，不放宽生产路径限制；A 快照测试校验重新解析后的等价科学清单，保留锁摘要检查；状态枚举加入既有 `user_modified`，不删除状态。相关成组回归 `30 passed`，尚待完整 gate 复跑证明全局收口。
- 剩余 W03 冻结清单绑定的源码摘要与当前源码不同，且该清单创建时的部分摘要在其入库提交上也不一致；不得改历史摘要/回退当前产品字节来追求 PASS。历史产物与当前源码须分开验收，该节点继续 FAIL/待证据处理。另有 A 固定研究包 digest 与 CT.gov AE 缺失值审计的集成/验收失败，均不在上述 gate 活跃 unit+contract 范围，仍明确未闭合。

## 2026-09-23 续建增量：A 门户投影性能、桌面合同与 AE 缺失裁决

- A 报告原每个静态页和每个产品页均重新翻译/投影全部疗效与安全行，当前 38 产品夹具会触发大量重复正则处理。现对同一不可变报告修订只建立一次展示投影，页面共享该投影且每页仅修改导航/路径；`report.js` 和页面同源。新增“每集合仅投影一次”回归，A 投影单元批 `4 passed in 10.61s`。这解决本轮测试耗时根因之一，不证明全部 4412 真实记录渲染性能达标。
- A 浏览器验收中旧的默认 EASI-75/第16周预选、1280px 双热图、气泡必须显示完整产品名、旧矩阵产品计数措辞与现行 0923V1 合同不符；替代断言验证默认不预先缩窄全部公开观察、1440px 安全性密集观察、图点编号与实名图例映射及当前口径/全部口径计数。最新 A 批 `19 passed, 1 failed in 18.41s`；剩余失败是历史固定夹具摘要与当前字节不一致，**仍为 FAIL**，不直接更新冻结 digest。新断言不代替四档×四状态全站视觉验收。
- 用户新裁决：CT.gov AE `numAffected` 缺失即“未知，待核”，不能由同组分母推断零；原文明示 0 才可记零。解析器移除默认 0，记录精确 `stats[i].numAffected` 缺失路径；PRD/DESIGN/ACCEPTANCE 同步。缺失/真零定向负例 `2 passed`；整个登记覆盖旧夹具批 `8 passed, 1 failed`，唯一失败是旧“所有来源均通过”断言不再满足。该科学缺口在 W07 真实重提取前保持 FAIL，不回填零使旧夹具变绿。
- Python 静态门仍须在本增量提交后复核。当前 24 门户、4412 来源闭包、合法 A+B 修订扇出、离线分享、三宿主与 RC 均未验收；旧中文工程仍零接触。

## 2026-09-23 续建增量：全仓 Python 静态门与历史回归边界

- 历史 A 载荷构建器的类型、闭包绑定和格式问题与 W04 证据校验器的 Literal 类型问题已修复；保留 UC/IgAN 包装器仅作基础静态整理。`ruff check src tools tests` 全绿，`mypy --strict src tools --no-incremental` 检查 243 个源文件全绿。此处是**静态门**，不代表科学、页面或发布验收。构建器存在既有历史入口与产物路径，不把它当作新 W07 来源闭包实现。
- 相邻合同/集成批 `70 passed, 1 failed`；唯一失败是 W03 冻结清单把历史源码 SHA-256 当作当前工作树字节。失配的当前文件为 C 渲染器、portal/report-c CSS/JS 和 W03 构建器共 5 个；固定 CAS、保留报告及截图未在该失败点报错。历史清单不可重写，当前源码也不能按旧版本回退；该节点保留 FAIL，需拆分历史证据完整性与当前版本重新验收。
- A 关联批在 67% 后因末段大型数据投影耗时数分钟而主动中断，**未运行完毕**，不计 PASS。中途已确认的失败包括历史研究摘要 digest、旧默认 EASI-75 预选、已退出发布范围的 1280px 固定热图断言、旧矩阵覆盖措辞，以及真实运行清单未绑定当前提交；部分合成 C 运行返回 `capability_blocked`。须按历史身份、过时合同、当前功能或环境分别处置，不能直接放宽断言。中断栈停于 A 行级中文转写的 `re.sub`；性能根因尚未确认，需独立定界。
- 本增量没有修改 0923V1 仅桌面产品范围、4412 条逐事实来源缺口、用户清除数值失败关闭、合法 A+B 扇出、离线分享或 24 门户/三宿主状态。全 gate 尚未在这些修改之后重跑，RC 仍不可宣布。

## 2026-09-23 续建增量：B 分组旧断言与重复键

- 清除了 B 标签字典与 A payload 构造器中 12 个重复键；保留原先实际生效的后项值，未改变产品语义。`ruff check --select F601 src tests tools` 通过。
- B 的两条旧测试仍强制要求对已知治疗组显示“登记分组信息不全”，与此前 r39 的事实判定相冲突；测试现分别约束已知臂不误报、真实缺失臂要提示，跨试验仍分开。B 语义分组和 B 接受相邻批 `27 passed`。这只关闭该测试族，不代表 B 报告正式验收。
- 完整 gate 仍维持下文所记 `GATE_FAIL`；其余 112 项 Ruff、97 项 mypy 与活跃测试失败须按根因处理，本增量不重写历史失败记录。

## 2026-09-23 续建增量：包内用户事实 schema

- 将已经存在的 `schemas/user-fact-save.schema.json` 加入产品包清单与最终必备文件集合；包清单、bundle、fresh-install 相邻批 `72 passed, 1 skipped`。这是打包遗漏的闭合，不代表用户清除数值已实现；当前 schema 仍不接受清除请求，运行时继续安全拒绝。
- 检查时误并行启动了同一测试批次两份，只采信上述一份完整终态；两份进程均已退出。后续避免重复运行耗时批。完整 gate 仍保持上述 FAIL，待其余根因修复后再复跑。

## 2026-09-23 续建增量：B/C 科学类型与分母旧测试

- C 终点实例、B 安全概念和安全分母 crosswalk 的 strict-mypy 小文件族已清零；旧 SCI03/SCI04 测试迁移为完整身份查询，保留跨期、统计对象、冲突保护，不放宽生产门。相邻 B/C 科学批 `49 passed`，修改文件 Ruff 和 strict-mypy 通过。
- 安全概念末尾分支不再复用循环中的临时 `key`；改为使用最终确定的 `chosen_key` 生成相关性和风险人数口径。仍须通过全仓宽门及真实来源投影验收；此前 gate 的 97 项计数是旧时点，不伪称当前全仓已清零。

## 2026-09-23 续建增量：登记分类与保留轨静态检查

- B 登记终点分类政策缓存加入映射形状守卫并标出受控返回类型；登记分类相邻批 `21 passed`。历史 W03 动态构建器与保留的 PDF A 投影只做类型/导入整理，三文件局部 strict-mypy/Ruff 通过；PDF 仍退出首版产品，不据此宣称 PDF 运行验收。

## 2026-09-23 续建增量：A/C 门户投影与原生中文单位

- C 门户消除无类型时间窗转换与局部变量碰撞，保留页面/消费者的原映射；局部 strict-mypy/Ruff 通过，设计专题相邻批 `58 passed`。A 当前事实投影按安全/疗效行明确分支更新、可选扩展字段先收为映射，局部 strict-mypy 通过；A 文件仍有 25 条历史 Ruff（主要长行），未记静态全绿。
- A 关联批先得 `5 failed, 62 passed`：冻结研究内容摘要已与当前文件不符（历史身份不可改写）；默认 EASI-75 预选、1280px 固定热图、矩阵覆盖文案三项需按 0923V1 新合同重判；图形数值旁的英文 `Score on a scale` 是真实呈现缺陷。后者已在展示投影翻译 `plot_unit` 为“分”，保留来源单位与分面身份；新增数据合同和原失败浏览器节点精确复测 `2 passed`。其余四项仍 FAIL/待裁决，不能记 A 整体通过。

## 2026-09-23 续建增量：B 影子行实际过滤与投影类型

- B 安全视图原有 `-declared` 过滤结果未被后续遍历使用，影子行可漏进展示。现安全视图、页级视图和总出口均使用过滤后的集合；新增真实 fixture 反例，保留未公开安全行的合法展示。B 相邻批 `41 passed`，修改文件局部 Ruff/strict-mypy 通过。清除不可达旧代码和局部事实扩展字段类型不会代替 B 实际来源及全页验收。

本节优先于下方历史状态。用户已授权修订并实施 D1–D6；原 Goal 仍暂停，实施授权不等于恢复 Goal。唯一工程为本英文仓库，旧中文工程零接触。起点 HEAD 与 origin/main 均为 `8daa7ce51880e8b31f0ef153e33286b6ce5efa52`。专家 ZIP SHA-256 为 `4ab7f84686fa9f0c74180e93168868e8859dd0f1e94ead85a78691fd9e71a917`，其中探针和 40 条验收案例是审阅输入，不能记作本工程通过。

首个阶段实施提交 `2863a27bbea19d7c8157acc7457f6e541d1c4eb4` 已推送 `origin/main`；下方“未提交、未推送”是该提交之前的测试时点记录。后续改动须依当时 HEAD 再核对，不能把这个阶段提交误记为 RC。

| 0923V1 范围 | 当前状态 | 接续要求 |
| --- | --- | --- |
| A/B/C 独立、同优先，共同证据底座与事实修订 | 基础已有；跨真实 A+B 合法扇出待行为验收 | D5 与 D6 |
| 仅桌面宽屏 1440/1600/1920/2560 CSS px | 规范已迁移；A/B/C 在部分页面完成浏览器探针和截图，四档×四状态×全部物理页尚未验 | D1–D3 后完整矩阵验证 |
| 旧 305/320/390/1024 竖屏发布门 | **退出 0923V1 发布范围**；历史结果原样保留 | 不再作为新 RC 阻断或伪造 PASS |
| A/B/C 图形、完整 facet、共享交互 | 共享图形几何与 A 多 facet 已局部修复；六个旧 pointer nodeid 在 Chromium/WebKit 精确复跑通过；完整 D1–D3 尚未关闭 | 继续普通入口和完整页面行为验收 |
| 用户清除数值 | 用户已裁决为“用户清除，待重新核实”；当前已区分省略与显式 `null`，但清除完整投影未接通时明确拒绝保存，旧 current 不变 | D5 尚未实现/验收，不得写成来源未公开 |
| 4412 条真实采用事实逐事实来源 | 已在 W05A v6 实际载荷重算：疗效与安全共 4412 条，`source_field_path` 与 `source_text` 均具备 0 条，两者任一具备也是 0 条；这只是该载荷的当前实测，并非全工程来源审计 | D4 先做小批真实链路，再扩全量；报告级来源不算逐事实闭包 |
| 离线分享、三宿主、24 门户 | 尚未终验 | D6 与后续 W 工作包 |

0923V1 已改动作者源的共享图形/布局、A 多 facet 和单观察呈现、测试与镜像，并保存 `evidence/0923V1-desktop/` 局部真实截图；不能据此宣称全部前端达标。旧六个 pointer 节点先复现失败，修复 SVG 实际 glyph 命中后 Chromium 3/3 与 WebKit 3/3 通过；A 单观察/多 facet 新例 2/2，其他定向批 WebKit 5/5。A/B/C 相邻批 `45 passed / 1 failed`，唯一失败是已退出 0923V1 发布范围的 320×568 旧首屏门，仍保留为历史 FAIL，不篡改为 PASS。当前截图中 A 1600 核心图起点约 y=478，B 2560 约 y=549，尚需降低无效纵向留白；C 2560 从三列含空白卡改为双列，但设计图本身仍偏空。专家 ZIP 的 40 案例未逐条执行，不得记通过。大体积未跟踪证据、缓存与历史失败记录均保留，未清理。候选仍是开发候选，不是 RC。

F01–F09 当前处置：F01 单观察满宽装饰条已局部修复；F02 facet 首项截断已改为可选择且计数，选择写入 URL/本机视图并通过浏览器重载/重开反例，普通入口全量验收待做；F03 图高与坐标范围已有内容自适应第一版，且修复非百分比疗效被误当人数比例而漏绘的缺陷，科学数值域仍需专项验；F04 同 category/series 不同观察以 occurrence 分列，冲突映射待强化；F05 共用 pointer/ResizeObserver 和实际 glyph 命中已局部修复，完整排序/过滤/生命周期矩阵待验；F06 显式清除从“悄悄忽略”改为“尚无完整投影时拒绝保存”，完整清除及派生失效未实现；F07 真实 4412 逐事实来源闭包未完成；F08 A/B/C 页面全量桌面密度未验；F09 离线分享默认当前事实和配置未验。以上均不是正式全项 PASS。

C 设计模式页全部要素披露状态相同时，已将无区分度热图改为逐研究具体设计事实对照；随后修复带 ID 的旧 CSS 规则压过新宽屏规则的问题。最新 `evidence/0923V1-desktop/c-2560-design-summary-fullwidth.png` 直接显示四项研究同排、可选路径下置，首屏利用率明显改善；相关 C 相邻浏览器批（1440/2560 × Chromium/WebKit 及设计路径/终点/概览）`10 passed`，又将该设计页扩为四档宽屏 × 双浏览器 `8 passed`，保留逐观察来源入口和筛选同步。它只覆盖设计模式一页，不能据此称 W05C 全站桌面密度合格。W05A v6 来源重算所用 `data/report.js` SHA-256 为 `e4e8c181e56fc6e9c8fbdf511226561c877279813b5ad0532d766becd979a695`；逐事实 locator/原文皆为 0/4412，不能借报告级来源清单记 PASS。

C 其余十一物理页的浏览器合同现改按正式四档桌面宽度运行；“十一页无横向拖动/默认图与完整表”和首屏核心图相邻批为 `48 passed`（Chromium/WebKit，47.80 秒）。这仅验证该合同的行为，不等于各页的稀疏、密集、筛选后稀疏、证据侧栏四状态截图和人工视觉审阅均已完成。

W07 只读来源追踪见 [W07-source-trace-0923.md](evidence/W07-source-trace-0923.md)：当前 A 展示 4412、历史同运行中间门户 4277、研究包 4458 是三个不同分母，不能混合闭包。SQLite 本轮重算仅有 10 个来源版本/fragment、0 个文本派生，旧包装器仍以 `studies[]` 和自造“登记结果事实”作粗引用；两个真实 CAS 研究切片字节哈希已复核。小批实例支持“多数有原始数值但未映射”这一修复方向，尚不能断言全量可恢复；具体路径需逐条重放。真实来源门继续 FAIL，子任务模型身份 UNVERIFIED。

W07 首个接缝现可把 `derive_ctgov_records` 的单研究 CAS 切片转换为现有 `SourceCapture`，重开原始资产校验 NCT/日期；本机真实 NCT04558918 切片按精确路径重提取 `68.8`。相关邻接集成批 `16 passed`；`source_research_service.py` 的返回后不可达旧摄取段已移除，修改模块 Ruff 与 strict mypy 通过。此步**尚未**把 4412 条事实写入 SQLite 或接到报告页，来源门仍 FAIL。用户明确的清除数值功能、A+B 合法修订扇出与离线分享也仍待做。

同一真实切片在自动清理的临时试验项目中已经走过共享摄取边界：1 个来源版本、1 个原文派生回执、1 个精确定位的事实版本，SQLite fragment 原文 `68.8`。这只证明接缝技术可行；正式 PNH 数据库、稳定事实身份、组/期/类别、派生分母、门户逐事实入口和 4412 闭包尚未完成。

本次里程碑运行 `bash tools/gate.sh` 的声明范围为 Ruff `src/tests/tools`、strict mypy `src/tools`、活跃 unit+contract、保留轨兼容子集、测试分层和旧路径检查。结果 **GATE_FAIL**：Ruff 112 项，mypy 97 项/10 文件，活跃批 `15 failed, 1047 passed, 20 deselected, 1 error`；保留轨兼容 `20 passed`、分层 `7 passed`、旧路径检查通过。抽查失败分别涉及旧快照 JSON 形状、B 运行输入根约束、已新增 `user_modified` 状态与旧枚举预期不符、安装包 schema 清单漏列，以及 W03 冻结证据哈希与当前作者资源变动不符。后者必须保留历史 FAIL，不得改旧证据哈希迎合当前版本。全仓静态与合同门尚未通过；本轮修改的来源模块单独 strict mypy/Ruff 与 W07 相邻集成 `16 passed` 不能替代全门。按根因成族修订，不逐行全仓重跑。

旧 A “初始 DOM 必须显示所有疗效行”测试已按用户 0923V1 裁决迁移为“数据全量+可验证筛选到达”：四档桌面×两浏览器验证非百分比 -4/0/7 分观察可达并与折叠表一致；同批含多 facet 保留/视图恢复共 `10 passed`。这不是删掉负面案例：旧测试原先 8 个失败已在本轮复现；根因同时包含初始 DOM 旧合同和非百分比数值的真实科学投影缺陷。数值投影单元整组 `13 passed`；相邻 B 图表兼容与门户集成 `101 passed`；修改模块 strict mypy/Ruff 通过。

本次 W04 受影响集成批为 `48 passed`：显式 null 不得静默忽略，事件流也必须只记录实际提交字段，不能把默认 null 伪装成用户清除。共享图形/证据点击/空图语义在补齐折叠表后的 Chromium/WebKit 定向批为 `12 passed`；图和表都不得把“已公开但未绘制”称为“未公开”，并保留完整记录入口。先前在单线程本地 fixture HTTP 服务下出现 `ERR_SOCKET_NOT_CONNECTED`/`ERR_CONNECTION_RESET` 与点击不稳定，已将该测试服务改为并发服务并直接让系统分配端口，未放宽点击/来源/回焦断言；完整整族稳定性仍需复跑。最新字节的镜像校验、所改 Python Ruff、JS 语法、`user_fact_edit.py` strict mypy 及 `git diff --check` 通过。当前作者源 SHA-256：`charts.js 976f9eff...`、`portal.css 673aa9e6...`、`report-a.js 52a6ca7d...`、`report-c.css a36ddb8d...`；构建前仍需重新校验镜像。未提交、未推送；所有未跟踪历史资料保留。

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
