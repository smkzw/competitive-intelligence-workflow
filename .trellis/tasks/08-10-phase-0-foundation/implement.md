# Phase 0 实施清单

## Task 0.1 独立仓和批准基线

- [x] 创建独立 Git 根并初始化 Trellis 0.6.14。
- [x] 复制 v1.2 规格并写批准记录、README、忽略规则和迁移清单。
- [x] 先建立旧依赖测试 RED，再实现扫描器并取得 GREEN。
- [x] 提交 `chore: bootstrap independent competitive intelligence repository`。

## Task 0.2 技术栈与依赖

- [x] 先写依赖清单合同测试并确认 RED。
- [x] 固定 Python 与运行/测试依赖，生成 `uv.lock` 和 ADR。
- [x] 冻结同步及合同测试 GREEN。
- [x] 提交 `build: lock workflow runtime and test dependencies`。

## Task 0.3 康哲合同

- [x] 两份候选文件执行稳定双读并生成差异决策材料。
- [x] 追踪 2026-08-10 23:49 的预期外漂移，确认其来自用户另行授权的分轨设计演进，而非文件损坏或无来源覆盖。
- [x] 识别 2026-08-11 08:19 的第二次上游变化：双全文已变为相同入口 stub，`design_specs/` 已升级为 12 文件单一完整合同。
- [x] 运行当前包 6 项结构测试并核对集合摘要；识别 `local_map.md` 仍含旧“双全文同步”规则及 post-split 实产物验收尚未完成，未把结构 GREEN 误作冻结。
- [x] 核验 Logo、ECharts 6.1.0 和 HTML-PPT 上游运行时来源、许可证、摘要及最小离线边界；记录通用 runtime 的主题、动画、总览、逐页页码和英文讲者标签缺口。
- [x] 将已批准计划 Task 0.3 的双全文文件树、摘要合同、Skill 入口和 PM03 收据逐项映射为单一 `design_specs` 包的等价实现；确认前只记录，不创建目标文件。
- [x] 对 S1 三条已结束路线复核进程、日志与文件，并对 HTML-PPT 做真实浏览器/源码复核；区分流式工具故障下的零产物假成功、HTML-PPT 功能/字号/逐字稿不合规、跨页 5/9 与 6/9 定量矛盾，以及规范内部旧同步规则。
- [x] 固化“Agent 产出类型化医学内容、应用确定性渲染、独立验证者拥有完成判定”的 ADR 和 Phase 0 机器合同；未进入 Task 0.4 代码实现。
- [x] 对 S1 PPTX 执行 PowerPoint 结构读取、逐页渲染图检查和字号/备注扫描；确认第 11 页 KPI 重叠、第 4/6/8/11 页低于 12 pt，并追溯到指定来源外的硬编码数据，记录为候选不接受而非“已完成”。
- [x] 用户确认选取最新版并内化；稳定双读四个入口与完整 `design_specs/`，两次快照摘要均为 `82a81132...25b`。
- [x] 复制并内化项目自有合同，增加 `project_profile.md`、原生 PDF 轨、四格式组合路由和独立演进清单；未修改通用版。
- [x] 先运行 6 项合同测试取得 RED，再实现后取得 `6 passed`；包内结构与项目边界测试取得 `Ran 8 tests ... OK`。
- [x] 复用暂停前同一 Luna 会话做第一次 targeted follow-up；审查否决了仅靠规则文字的“当前运行”假绿，并新增 2 个 P0、5 个 P1。
- [x] 增加类型化设计来源包、runner 当前运行清单、独立验收结论三份 Schema 和确定性校验器；32 个专项合同测试覆盖清单重算、运行前状态、旧收据、旧渲染、自签、来源事实/讲者稿数值漂移和兼容入口第二正文等负例；仓内全量为 38 passed。
- [x] 同一 Luna 会话第二次 follow-up 继续否决 2 个 P0、2 个 P1：摘要未亲自重算、运行前状态含糊、声明与事实脱链、讲者稿文本可游离；修复后 38 个仓内测试通过。
- [x] 同一 Luna 会话第三次 follow-up 亲自重跑五类变异并全部拒绝，独立结论 `PASS`；明确未生成或接受任何报告实产物。
- [x] 按固定摘要封装正式 Logo、ECharts 6.1.0 classic bundle 与许可证、裁剪后的中文 HTML-PPT 固定运行时及来源清单。
- [x] 静态资产合同 6 项通过；新增 Chromium/WebKit `file://` 真实交互和 ECharts SVG 离线渲染验收，专项共 11 项通过。
- [x] 人工打开观众页、演讲者视图和 WebKit 图表截图，确认固定画布、中文界面、逐字稿和图表基础可读；未把运行时样稿冒充报告视觉验收。
- [x] 两名独立验证者分别重算摘要、运行真实浏览器并做假绿变异，共同发现 Logo 来源路径悬空 P1；修复后在各自原 session 负向复验均为 P0=0、P1=0、PASS。
- [x] Codex 最终复跑 43 项专项、49 项全量、Ruff、mypy、Node、uv lock/sync 和旧依赖扫描并人工查看三张真实截图；Task 0.3 接受，未接受报告实产物。
- [x] 阶段清理完成：临时下载/截图、项目测试缓存、4.4 MB 原始 runner stdout、两份空壳输出、旧暂停检查点和未使用/已被结果取代的提示模板移入独立废纸篓目录；保留最终会商报告、指标和修复证据。

## 独立验收加固

- [x] 会议复核并修复迁移清单、批准规格摘要、真实仓扫描、相对旧路径和锁文件检查的假绿缺口。
- [x] Codex 复跑 Ruff、mypy、pytest、真实仓扫描、锁文件与冻结同步；review gate 通过。
- [x] Task 0.3 仅接受对账材料，未越过用户确认边界。

## Task 0.4–0.5 包与报告机器合同

- [x] 用 Skill Creator 初始化一个公开入口与 15 个内部 Skill；正文只保留输入、输出、禁止与恢复合同，内部入口全部关闭隐式调用。
- [x] 建立严格 `package-manifest.json`/Schema 与唯一六命令 CLI；包校验绑定当前 Schema、Skill 提示词、康哲合同及离线资产摘要。
- [x] `project create/verify` 建立 Phase 0 最小骨架；后续 capability/project run/fixture 明确退出 3，不以 argparse 错误冒充功能阻断。
- [x] 将 argparse 固定帮助和参数错误改为中文原生；禁止别名和第七条 CLI，临时变异均失败关闭。
- [x] 53 项全量、Ruff、mypy、包校验和 Python 构建通过；Pi 原 session 与 Minimax 独立复核 P0=0、P1=0，会商 gate 通过。
- [x] 明确 Python wheel 只承载 CLI 模块；Task 9.5 仍负责完整 `.tar.zst` Skill bundle、fresh install 和三真实宿主验收，当前未越阶段。
- [ ] A/B/C 页面、筛选和 HTML/PDF/HTML-PPT/PPTX 格式合同。
- [ ] Phase 0 全套确定性检查和独立验收。

## 停止与回滚

康哲合同未确认、摘要漂移、依赖无法冻结、CLI 名称不唯一或存在旧运行依赖时立即停止；回滚只处理新仓，不触碰旧工程。
