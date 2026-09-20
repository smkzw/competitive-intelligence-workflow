# Conference Review: ci-r2-stage-review-astra-20260905

## Boundary And Evidence Check

- 本轮只读审阅，未修改源文件、测试、计划、运行状态或报告文件；未联网、未启动其他代理，未访问禁止目录。
- 已读取指定设计、路线图、执行计划、执行上下文及检查点。指定的 `runs/execution/.../worker_01.md`、`worker_02.md`、`worker_03.md` 均不存在，不能核验这些交接报告。
- 已核对相关 Git 差异、当前实现及测试源码。脏树包含大量既有修改，不能全部归因于本轮执行。
- **本轮实测**：关闭 bytecode、pytest 缓存和插件自动加载后，33 项无需临时文件的合同/上下文/分层测试通过。首次选择中另有 3 个 `tmp_path` 参数用例被只读沙箱阻断，测试主体未执行；后续明确排除后为 `33 passed, 7 deselected`。
- **额外纯函数检查**：默认 bundle allowlist 不包含 `src/ci_workflow/qc/review_receipt.py`；仅改变 `created_at` 即改变报告快照 ID。
- 未执行全量 gate、真实宿主签发、完整 B/C 恢复链或浏览器验收。以下区分代码观察、影响推断和修复建议，不构成最终接受。

## Stage Verdict

**应暂停修复**

两阶段接线方向正确，跨项目/报告/快照/内容绑定、形式化 verdict 校验和 preview 状态拒绝已有实质实现；但尚不能声称关闭伪造签发、生产时间改写、晋级前门户字节漂移及恢复重试风险。应暂停将本切片视为已闭合的阶段依赖，继续进行下面的局部修复。

## Findings

未发现足以判定为 P0 的证据。

### P1-1：可自洽构造的回执仍被当作真实独立签发

**位置**：

- [review_receipt.py:254](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/qc/review_receipt.py:254)、[review_receipt.py:350](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/qc/review_receipt.py:350)
- [test_fresh_b_research_package.py:1029](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/tests/unit/reports/b/test_fresh_b_research_package.py:1029)，`test_b_candidate_requires_valid_verdict_artifact_before_promotion`

**观察**：验证器检查声明的 PID、argv、身份、时间、摘要和 verdict 文件，却没有核验这些进程/会话记录来自实际宿主执行。B 正向测试在当前测试进程内填写固定 PID、会话和可执行文件路径，生成 accepted verdict 与回执，然后调用真实 `run_project` 晋级。

**影响推断**：当前证明的是回执内部一致性，不是签发真实性。换一个 reviewer 字符串和 session 字符串，不能证明 clean context 或排除生产者自证。

**修复**：由宿主执行适配器取得真实会话、进程结果和输出字节，绑定运行时发布的唯一请求；晋级端核验独立于生产者自报材料的执行记录。保留模型合同测试，但增加“只有自洽 JSON、没有实际签发记录”的拒绝用例。不需要引入中心签名服务或 PKI。

### P1-2：生产身份、时间线和有效期尚未绑定可信执行历史

**位置**：

- [run_service.py:1677](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/run_service.py:1677)
- [scientific_review_transition.py:281](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/scientific_review_transition.py:281)、[scientific_review_transition.py:330](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/scientific_review_transition.py:330)、[scientific_review_transition.py:496](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/scientific_review_transition.py:496)

**观察**：

- 请求在 HTML 渲染前发布，`produced_at` 尚不能代表门户生产完成。
- `producer_session_id` 填入应用 `run_id`，不是实际宿主会话身份。
- 请求加载只检查文件自带摘要；未见将其生产时间/session 与首次生产事件交叉核验。删除请求后可以重新发布；同时修改请求及重算摘要的情形未被覆盖。
- verdict 有效期只与 `receipt.issued_at` 比较，没有与实际晋级时间比较。

**影响推断**：同宿主会话自审、请求时间改写，以及签发时有效但晋级时已过期的 verdict，仍存在放行空间。

**修复**：完成候选物化后固定生产事件、请求摘要、真实 producer session 和完成时间；重试读取该事件，缺失或漂移即阻断。以可注入时钟检查实际晋级时的有效期及未来时间。

### P1-3：科学晋级没有重新验证原候选门户字节

**位置**：

- [run_service.py:1193](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/run_service.py:1193)
- [run_service.py:1686](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/run_service.py:1686)、[run_service.py:1767](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/run_service.py:1767)
- [run_service.py:2737](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/run_service.py:2737)

**观察**：节点复用依据输入摘要；科学晋级检查研究内容/verdict，不检查 HTML 目录。最终输出收集仅重新记录 manifest，且基线来自此次运行开始时的文件。

**影响推断**：两次运行之间改变 HTML、JS 或 CSS，仍可能产生 `scientifically_reviewed_rendered_candidate`。后续视觉/真实来源验收有字节核验，能阻止部分下游接受，但不能证明本阶段所谓“不可变门户晋级”。

**修复**：在状态迁移前，重新计算门户目录摘要、字节数和 manifest/snapshot 绑定，并与首次生成事件固定的值比较。对页面修改、删除、增添及 manifest 漂移分别做 B/C 运行级负向测试。

### P1-4：真实来源验收把合法恢复限制成恰好两次运行

**位置**：[real_source_acceptance.py:236](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/real_source_acceptance.py:236)、[real_source_acceptance.py:283](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/real_source_acceptance.py:283)

**观察**：只允许当前运行与原门户生产运行两个 run ID；要求科学 QC 本次必须为 `completed`，不允许已完成节点幂等复用。

**影响推断**：生成后，在回执尚未到达时多续接一次，再取得有效回执，第三次运行会因中间事件被判为无关历史而无法验收。成功晋级后重复执行也可能使当前运行失去验收资格。

**修复**：用同一候选的受控恢复谱系判断关联性，保留中间失败/等待记录；拒绝跨候选、跨项目和无关历史。为成功晋级提供幂等结果，不能靠删除事件或新建根解决重试问题。

### P1-5：当前 bundle 漏收科学复核必需模块

**位置**：[bundle_contract.py:360](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/tools/bundle_contract.py:360)、[scientific_review_transition.py:53](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/scientific_review_transition.py:53)

**观察**：allowlist 对 `qc` 逐文件列举，未列入 `qc/review_receipt.py`；被收录的 `application/scientific_review_transition.py` 直接导入它。AST 检查确认遗漏。

**影响推断**：源码环境可用，干净安装包中的 B/C 路径会缺少依赖。注册 receipt schema 不能弥补 Python 模块缺失。

**修复**：补齐精确 allowlist 与 required-content 合同，增加脱离源码路径的安装包导入/最小调用测试。该依赖闭合应现在修；三宿主完整安装矩阵仍留 R5。

### P2-1：preview 隔离成立，但“确定性自锁”和失败恢复表述过强

**位置**：

- [report_b.py:3905](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/renderers/portal/report_b.py:3905)、[report_b.py:3965](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/renderers/portal/report_b.py:3965)
- [snapshot_store.py:154](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/storage/snapshot_store.py:154)
- [test_preview_report_snapshot_contract.py:131](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/tests/acceptance/test_preview_report_snapshot_contract.py:131)

**观察**：不存在的声明快照会被替换，现有坏快照会拒绝，preview 保持未复核；这些方向正确。但 B 先写门户，再验证/锁快照；失败会留下目录，下次被“版本已存在”阻断。快照含当前生成时间，相同内容重建不能得到相同 ID；现有测试不验证这种确定性或失败后恢复。

**修复**：明确“同候选重试”与“新生成版本”的身份语义，保存首次创建时间；先验证快照，再物化门户，或使用可恢复的临时生成目录。不得为了重试覆盖既有正式版本。

另，[run_service.py:2925](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/application/run_service.py:2925) 对未复核运行也输出“项目运行完成”，建议改为明确的“报告已生成，等待独立复核”。

### P2-2：测试分层没有直接隐藏失败，但尚不足以支撑本切片闭合

**位置**：

- [gate.sh:98](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/tools/gate.sh:98)
- [test_v1_test_layering.py:98](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/tests/contract/test_v1_test_layering.py:98)
- [test_scientific_review_transition.py:413](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/tests/integration/test_scientific_review_transition.py:413)
- [test_fresh_c_research_package.py:1087](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/tests/integration/test_fresh_c_research_package.py:1087)

**观察**：

- gate 同时执行活跃与保留轨的 unit/contract，二者失败均影响退出码；未见当前通过分层缩小原有 unit/contract 联集。
- 分层守卫允许“未登记但带 marker”的文件直接跳过，不能防止以后任意把活跃测试移出门禁。
- B 有真实 `run_project` 晋级测试，但回执由测试构造；C 有运行及阻断测试，未见对应完整晋级测试。时间请求改写、第三次运行、已接受后重试及门户字节漂移缺乏运行级覆盖。
- worker 债清单是其副本历史结果，不是当前集成树全量结果。

**修复**：检查 marker 文件集合与声明集合精确相等；补齐 B/C 对称的运行级负向和恢复用例。完整报告应分别列工程 gate、HTML 活跃全量、非 HTML 保留轨和未运行项。

## Adoption Decisions Proposed

| 性质 | 决策 | 内容 |
|---|---|---|
| 必须 | **修改后采纳** | 两阶段生成与独立科学复核；先关闭 P1-1～P1-4，再作为 R2 依赖。 |
| 必须 | **采纳** | 回执绑定真实 verdict 字节、项目/报告/快照/来源上下文，以及 preview 接受拒绝。 |
| 必须 | **采纳** | 精确补齐 bundle 依赖，不等到三宿主矩阵才发现导入失败。 |
| 必须 | **修改后采纳** | preview 自锁方案；补身份确定性与失败恢复，保留不可接受属性。 |
| 必须 | **修改后采纳** | HTML-only 测试分层；保留全量可见性，并补精确 marker 审计。 |
| 必须 | **采纳** | B 抽屉使用“分子来源未列示”，禁止由百分比反推分子；本轮仅确认断言方向，未重做原始临床来源核验。 |
| 可后置 | **延后** | R3 完整临床构念分组/数据投影；R4 页面族及全视口视觉；R5 三宿主、移动与完整恢复。当前改动涉及的局部合同测试不能一并延后。 |
| 不增加 | **拒绝** | 新建平行穷尽模型、第二套 receipt 体系、中心签名平台、通用工作流重构；现有事件/宿主合同足以承载必要修复，新增体系收益不足且增加迁移风险。 |
| 不增加 | **拒绝** | 为本轮重开 sealed Task 10.3–10.5，或恢复 PDF/PPT、导出、排名、监测等产品面。 |

## Design Roadmap Plan Amendments

**不建议改变产品方向或科学门槛。** v1.3 对证据完整性、临床比较、HTML-only 和独立接受的要求仍适用。

建议仅补以下合同：

1. **设计 §4/§6**：明确内部未复核候选与用户交付的区别；生产请求必须绑定首次真实生产事件、宿主身份和不可变候选。摘要一致性不能被描述为签发真实性。
2. **路线图 R2**：加入最小宿主签发与 B/C 恢复验收；R3/R4/R5 继续承担原定数据、视觉和完整宿主矩阵，不提前执行 24 门户。
3. **执行 v3 的 R2.4 续接状态**：将“全部闭合”“确定性自锁”等完成式措辞改为实际已实现项与开放缺口，特别注明本报告 P1。
4. **质量门口径**：同步执行 v3 §1.1 的 `mypy src/ci_workflow` 与当前 gate/路线图的 `mypy src tools`；明确工程质量门、HTML release 检查和非 HTML 保留回归的不同用途。
5. **当前执行计划**：补可读取的 worker 证据位置及逐项验收结果，替换 acceptance TODO；保留旧检查点，不倒改历史记录。

这些是既有合同的落实，不是新功能提案。唯一用户体验调整是“等待复核”的准确中文状态：收益是避免完成误解，依赖现有报告状态，风险低，应随 R2 修复完成。

## Next 3-7 Minimal Verifiable Work Items

1. **修复签发真实性与请求身份**  
   完成证据：至少一条真实宿主独立签发链；没有宿主记录的自洽回执、同宿主会话自审、请求时间/session 改写均拒绝。

2. **把门户完整性与有效期放在晋级之前**  
   完成证据：B/C 页面、资产、manifest、snapshot 漂移及过期 verdict 均不能产生科学晋级状态；成功路径 HTML 字节与首次生成完全一致。

3. **修复恢复与幂等合同**  
   完成证据：生成→等待重试→有效签发→晋级→重复调用可恢复且不重复接受；跨项目/快照/无关运行重放仍拒绝，历史事件完整保留。

4. **补 bundle 模块闭合**  
   完成证据：安装包包含 receipt 模块及 schema；隔离安装环境不借助源码路径完成 B/C 入口导入和最小运行。

5. **收敛 preview 生成与状态文案**  
   完成证据：单 B/C 与三报告预览自锁；损坏输入失败后可恢复；同候选重试身份稳定；实际视觉/真实来源接受入口均拒绝 preview。

6. **补对称运行测试并刷新阶段证据**  
   完成证据：B/C 正向、负向、恢复均覆盖；marker 集合精确；当前树工程 gate、HTML 全量和保留轨分别提供原始输出/摘要及剩余失败处置。不得把本轮 33 项当作全量通过。

## Unverified Items

- 真实 Codex/Hermes/OMP 会话签发、独立上下文及宿主不可用恢复。
- 写文件测试、完整晋级/恢复链、全量 ruff/mypy/pytest。
- 当前安装包实际构建与 fresh-install；本轮 bundle 结论来自明确 allowlist/import 缺口。
- 浏览器物理页面、Chromium/WebKit 四类视口、科学与视觉最终接受。
- R2.1–R2.3 全部来源路由、宇宙闭合、关键 publication 和 manual gate 的实际覆盖。
- B 分子/分母修改对应的原始临床文献；不能以旧债清单替代来源核验。
- 当前集成树剩余失败的准确数量。指定 worker 报告缺失，历史计数不作为当前结论。

## Additional Files Read

以下为指定初始集合之外读取或定向检索的文件；路径均相对于 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`。未展开阅读无关目录。

- `src/ci_workflow/application/{scientific_review_transition,run_service,acceptance_boundary,real_source_acceptance,visual_acceptance,fixture_runner}.py`
- `src/ci_workflow/qc/review_receipt.py`
- `src/ci_workflow/storage/snapshot_store.py`
- `src/ci_workflow/renderers/portal/{report_a,report_b}.py`
- `tests/integration/test_scientific_review_transition.py`
- `tests/integration/test_fresh_c_research_package.py`
- `tests/integration/test_fixture_run_cli.py`
- `tests/integration/reports/{test_b_report_portal,test_c_report_portal}.py`
- `tests/integration/test_incremental_refresh.py`：仅 `promot` 定向检索匹配。
- `tests/application/test_terminal_recovery.py`
- `tests/unit/reports/b/test_fresh_b_research_package.py`
- `tests/contract/{test_scientific_review_receipt_contract,test_v1_test_layering,test_bundle_packaging}.py`
- `tests/acceptance/{test_preview_report_snapshot_contract,test_release_acceptance_boundary}.py`
- `tests/browser/test_b_portal.py`
- `pyproject.toml`
- `package-manifest.json`
- `tools/{gate.sh,bundle_contract.py,build_bundle.py}`
- `reviews/worker03_v1_html_active_layer_debt_20260905.md`

另尝试读取 `conftest.py` 与 `tests/conftest.py`，两者均不存在。