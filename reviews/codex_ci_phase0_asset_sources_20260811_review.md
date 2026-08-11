# Codex Review: ci_phase0_asset_sources_20260811

Date: 2026-08-11
Direct Codex task; no Hermes or external Agent was dispatched. The guard-reserved `runs/codex_ci_phase0_asset_sources_20260811.md` remains runner-owned and was not edited.

## Verdict

`PASS WITH DEFERRED ACTIVATION`：官方来源、许可、摘要、裁剪边界和用户可见中文化要求已经核实并写入决策记录；康哲上游合同仍在进行 post-split 实产物验收，因此本轮不得复制资产、冻结合同或进入 Task 0.4。

## Boundary Check

- 只读检查康哲官网、Apache ECharts 官方 GitHub/npm、html-ppt 官方 GitHub，以及用户已放入范围的本机候选文件。
- 写入仅发生在新仓的 `context/`、`docs/decisions/`、`migration/legacy_manifest.jsonl`、Trellis 检查点、`reviews/` 和 `metrics/`。
- 未修改 `/Users/smkzw/Documents/康哲项目资料/模版/`、全局 Skill、旧工程或任何报告产物。
- 未复制 Logo、ECharts、runtime 或 design_specs 到活动包；未开展安全专项测试；未进入 Task 0.4。

## Codex Verification

直接验证包括：

- CMS 官网 Logo 两次流式获取；HTTP 类型、字节数、viewBox 与 SHA-256 一致；官网字节和两份本机缓存 `cmp` 一致。
- ECharts 6.1.0 官方 tag/commit、npm tarball SHA-512 完整性、Apache-2.0 LICENSE、classic min bundle SHA-256；扫描确认该浏览器 bundle 不依赖 require/import/CDN。
- html-ppt 官方仓库 commit、MIT LICENSE、runtime/base/presenter 文件摘要；本机对应文件与官方 blob 一致。
- `runtime.js` 960 行分四段完整读取，逐项定位主题切换、演示动画、总览 clone、首个页码选择器和英文讲者标签等与康哲合同冲突的位置。
- 当前 `design_specs` 12 文件集合摘要重算；6 项结构测试通过；另行确认 `local_map.md` 的旧双全文同步规则与当前单一包架构冲突，且 S1 实产物验收仍在运行。
- 仓库基础回归首次发现迁移 item-id 改名导致测试失败；修正为保留稳定 item-id 后重新执行完整检查。

## Direct Task Review

决策记录把观察、采用判断和待实施内容分开，没有把“官方地址可访问”写成视觉验收，也没有把结构测试写成合同冻结。ECharts 选择以报告所需图形覆盖和 `file://` 直接加载为依据；HTML-PPT 只复用运行职责，不复用通用主题。所有讲者界面词汇都给出中文原生替换，符合项目对非技术用户的语言要求。

## Residual Risk

- 康哲上游 portable package 的 S1 真实产物还未完成并接受；当前摘要只能作为候选快照。
- `local_map.md` 仍含已经失效的双全文同步规则，应由上游设计任务修正，本项目不越权修改。
- 衍生 runtime、结构 CSS、ECharts 和 Logo 尚未真正复制、构建或浏览器验收；这些属于用户确认后的 Task 0.3 实施，不在本轮完成声明内。
