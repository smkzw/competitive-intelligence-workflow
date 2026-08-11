待办事项列表属于会议工作，由于报告由运行器管理，我将跳过待办事项的修饰，直接提供完整的会议参与者输出。

---

# 会议参与者输出：ci_phase0_offline_assets_20260811 - general_pi_qwen38

## 结论

**通过** — 有条件（离线运行时基础设施在功能和证据上均稳健；需标记一个 P1 级来源链接缺陷和两个 P2 级测试覆盖率缺口，不阻碍任务 0.3 离线基础设施的验收）。

- **P0: 0**
- **P1: 1**（品牌清单的 `source` 字段指向了不存在的路径；目前没有测试能捕获此错误）
- **P2: 2**（契约测试从未验证 `source` 的可达性；离线网络边界依赖于验收测试，而非独立的契约保护）

## 边界检查

- ✅ 工作目录限定在项目根目录。未读取 `runs/conference/ci_phase0_offline_assets_20260811/` 下的任何其他参与者输出。
- ✅ 未修改任何项目文件。对所有变异/临时测试工作均使用了 `mktemp` 目录；临时目录和 `/tmp/pi_probe*.py` 已删除；已验证 `git status` 未显示我编写的任何更改。
- ✅ 无网络/外部访问。所有哈希重计算均通过本地的 `shasum -a 256` 完成；浏览器测试通过 `file://` 运行，且远程请求数组断言为空。
- ✅ 未对 A/B/C 报告内容、PPTX/PDF 或 Kangzhe 报告页面提出任何结论——仅限于离线运行时基础设施。
- ✅ 未执行最终视觉/PPT/临床验收（保留给 Codex）。

## 独立工作产出

### 1. 源、哈希和许可证重计算（本人执行，而非断言）

| 资产 | 清单 SHA-256 | 独立 `shasum -a 256` | 字节大小 | 匹配 |
|---|---|---|---:|---|
| `assets/brand/cms-logo.svg` | `8d16d3ae…1cae` | `8d16d3ae…1cae` | 9,542 | ✅ |
| `assets/third-party/echarts/echarts.min.js` | `b66b25ae…0fd0` | `b66b25ae…0fd0` | 1,121,883 | ✅ |
| `assets/third-party/echarts/LICENSE` | `63429383…093a` | `63429383…093a` | 11,990 | ✅ |
| `assets/html-ppt/runtime.js` | `ab31d115…bcc4` | `ab31d115…bcc4` | 14,246 | ✅ |
| `assets/html-ppt/runtime.css` | `7613a388…b15e` | `7613a388…b15e` | 2,595 | ✅ |
| `assets/html-ppt/LICENSE` | `a5ed4059…a949` | `a5ed4059…a949` | 1,084 | ✅ |

- **Logo 字节链闭合**：`assets/brand/cms-logo.svg` 与 `contracts/kangzhe/design_specs/assets/logo_bot.svg` 字节完全一致（相同的 SHA-256，`cmp -l` 无输出），且与合同清单条目 `design_specs/assets/logo_bot.svg: 8d16d3ae…1cae` 一致。ADR 声明的官方 URL 哈希匹配。
- **viewBox** `"0 0 121 25"` 确认无误；Logo SVG 中没有 `<script`（grep 计数 = 0）。
- **ECharts**：`manifest.json` 绑定 npm 完整性 `sha512-q0yaFPgg…yHZA==`，源提交 `c5a48f5f…ffb4`，bundle/LICENSE 哈希均匹配。LICENSE 文本包含“Apache License” + 附录 → Apache-2.0 ✓。bundle 文本无 `sourceMappingURL`，无 `require(`，无 `import(`。
- **HTML-PPT**：`manifest.json` 绑定上游提交 `f3a8435d…3107`，上游运行时 SHA `d7b066a9…4f79`，MIT LICENSE 哈希匹配，派生文件哈希匹配。LICENSE 第一行 = “MIT License” ✓。
- **目录结构**：无孤立文件。每个资产目录恰好包含其清单声明的文件以及资产本身。

### 2. 假绿（Fake-Green）变异挑战（4 次变异，在临时目录中隔离）

我将 `assets/`, `tests/`, `contracts/` 复制到一个全新的 `mktemp` 目录中，进行了突变，并使用项目的 venv (`Python 3.13.13`, `pytest 9.1.1`) 运行相关的契约测试：

| 变异 | 测试 | 结果 | 结论 |
|---|---|---|---|
| 翻转 ECharts bundle 中的 1 个字节 | echarts 契约 | ❌ 失败 (哈希不匹配) | ✅ 已捕获 |
| 在 runtime.js 中注入 `Presenter View` (英文) | 中文原生契约 | ❌ 失败 | ✅ 已捕获 |
| 在 runtime.js 中注入 `fetch("https://x")//` | 离线边界契约 | ❌ 失败 | ✅ 已捕获 |
| 品牌清单 `source` → 已断开路径 | Logo 契约 | **✅ 通过** | ❌ **未捕获** |

契约测试在检测内容损坏（哈希、标签、网络 API）方面是稳健的，但对于来源可达性来说并非防弹的——见下文 P1。

### 3. 实际的 Chromium + WebKit 运行时（我已执行，非生产者声明）

验收测试套件 (`test_html_ppt_runtime_smoke.py`) — **5/5 通过**：
- 导航 + 演讲者视图在 Chromium (1600×900, scale `1.25`) 和 WebKit (2048×1024, scale `1.4222…`) 环境下
- 预览模式 `?preview=3` 隐藏进度/导航
- ECharts 在两种浏览器中渲染真实的离线 SVG（断言 `#chart svg` 为 1，`canvas` 为 0）

**我的独立深度探测**（超出验收范围，一次性 Playwright 脚本，`file://`，随后已删除）：

| 属性 | Chromium | WebKit |
|---|---|---|
| 深度链接 `#/3` → 标题 “安全性概览”, 页码 `3 / 3`, scale `1.5`, 进度 `100%` | ✅ | ✅ |
| `Home` 键 → 返回第 1 页 (`1 / 3`) | ✅ | ✅ |
| **远程请求数组** | `[]` | `[]` |
| `n` 打开笔记抽屉, `Escape` 关闭 | ✅ | — |
| 演讲者 `s`：跨窗口广播 — 演讲者点击“下一页”同步主窗口到 “主要疗效” + hash `#/2` | ✅ | — |
| 预览 `?preview=2`: scale 空 (已禁用), `data-preview=true`, 进度 `display:none` | ✅ | — |

ECharts SVG 结构 (Chromium)：1 个 `<svg>`, 0 个 `<canvas>`, 11 个 `<path>`, 11 个 `<text>`，轴标签 “主要终点变化值” 存在。

### 4. 完整套件（v3.13 下的仓库范围）

**49 个通过，0 个失败**（与生产者声明的 49 个相符）。合同专项：6/6。验收专项：5/5。

## 证据与假设

**直接观察到的证据：**
- 所有六个资产哈希、字节大小和许可证头均已通过本地工具重新计算并匹配。
- 静态契约测试 (6/6) 和实际浏览器验收测试 (5/5) 已通过项目 venv 重新运行。
- 三个损坏检测变异被正确捕获；一个来源可达性变异未通过。
- `remote_requests == []` 在 Chromium 和 WebKit 的所有浏览器运行中均独立确认。

**推论 [INFERENCE]（非直接观察到的）：**
- ADR 对上游 `runtime.js` SHA `d7b066a9…` 的声明以及 npm tarball SHA-1 `ae0f6859…` 依赖于外部获取；我无法在不联网的情况下重新验证这些声明（根据任务约束，已正确排除）。包内哈希链（上游 SHA 记录在清单中，派生 SHA 与磁盘文件匹配）在本地是完全闭合的。
- 运行时的 `BroadcastChannel` 跨窗口同步在我的 Chromium 探测中有效；WebKit 的精确弹窗+广播路径在验收测试中进行了测试（而非我的探测），并已通过。

**假设：**
- 任务约束不允许网络访问，因此我接受 ADR 记录的上游提交/npm 完整性值作为源绑定规范，并验证了项目重计算的所有内容均与这些清单一致。
- Playwright 捆绑的 Chromium/WebKit 是“真实浏览器”的代理；ADR 和 Codex 检查清单保留了最终的渲染视觉验收。

## 风险、缺口和验证需求

### P1-1: 品牌清单 `source` 字段损坏（未指向任何真实路径）
- **事实**：`assets/brand/manifest.json` → `"source": "contracts/kangzhe/brand/logo/cms-logo.svg"`。该路径**不存在**。实际字节相同的源文件位于 `contracts/kangzhe/design_specs/assets/logo_bot.svg`，且合同清单 (`contracts/kangzhe/manifest.json`) 在该路径下正确列出了哈希。
- **为什么重要**：清单应该是一个闭合的来源链。悬空的 `source` 意味着未来的审计者或打包步骤如果遵循清单指针，将会失败或静默地什么都不绑定。这与 ADR §2.2 的声明“manifest 同时记录官方 URL、获取时间、字节数、SHA-256 与 viewBox”相矛盾——但当前清单缺少官方 URL、获取时间，且具有错误的内部路径。
- **变异证明**：Logo 契约测试 (`test_cms_logo_is_the_verified_official_offline_asset`) 在临时副本上运行时仍然 **通过**，尽管源字段已断开。没有现有的测试检查 `source` 的可达性。
- **建议修复** (Codex 执行写入)：更正 `source` 为 `contracts/kangzhe/design_specs/assets/logo_bot.svg` 并添加 ADR §2.2 要求的字段 (`official_url`, `fetched_at`, `bytes`)，或者完全记录为什么项目内部路径是权威源。添加一个 `Path(...).is_file()` 断言，以保证契约测试中 `source` 字段的可达性。

### P2-1: 离线网络边界没有独立的契约守卫
- 离线属性（无 `fetch(`/`XMLHttpRequest`/`WebSocket`/`EventSource`，无 `url(http`，无 `@import`）在 **契约** 测试中检查为静态文本，实际的零请求断言仅存在于 **验收**（Playwright）测试中。如果验收套件被跳过（例如在 CI 或无头环境不可用），损坏的运行时可能会添加运行时获取，而仅契约测试无法捕捉它（它们只检查源文本中的字符串字面量——动态构建的 URL 将会绕过）。建议：保持两者并存；不要将验收测试视为可选。

### P2-2: 预览模式禁用了缩放，但没有契约断言预览不能导航
- 我确认 `?preview=2` 将 `--deck-scale` 设置为空且 `data-preview=true`。运行时在预览模式下正确忽略了箭头键（我的探测：预览中按 ArrowLeft 保持第 2 页活动状态）。这是行为测试，而非契约测试。风险较低，因为预览仅用于演讲者 iframe；标记给 Codex 以决定是否需要静态守卫。

### 质疑 Codex 的假设
- ADR §1.1 声称 “当前官网、本机缓存和候选 design_specs/assets/ 三者逐字节一致。” 我确认了两个本地副本是字节相同的，但官网相等性是一个联网声明，我无法（也不应该）验证。ADR 正确地将此作为生产者声明；会议不应将其提升为已验证。
- 验收测试使用固定视口 (1600×900, 2048×1024)。ADR §4.4 还声称在 “实际最大化窗口” 下进行了测试。Playwright 无法产生真正的操作系统最大化窗口；该声明只能由 Codex 的手动视觉检查满足。这不是缺陷——这是一个 Codex 必须亲自拥有的验收边界，根据上下文，它确实如此。

## 建议的下一步

1. **Codex 修复 P1-1**（品牌清单 `source` 路径 + 缺失的 ADR 字段）并添加一个 `source` 可达性契约断言。这是一个 2 行的清单更正 + 1 行测试添加。在完成此操作之前，不要关闭任务 0.3——不是因为离线运行时损坏（它没有损坏），而是因为来源链文件与 ADR 自相矛盾，且没有测试捕捉到它。
2. **Codex 重新运行** 契约 + 验收套件并手动打开实际的观众页面、演讲者视图和 ECharts SVG 截图（上下文中 Codex 的验证清单项）。
3. 在 P1-1 关闭后，任务 0.3 离线基础设施 **接受**。P2 项是跟踪改进，而非阻碍项。
4. **给 Codex 的有限问题**：品牌清单的 `source` 是应该指向内部合同路径 (`contracts/kangzhe/design_specs/assets/logo_bot.svg`) 还是应该同时携带 ADR §2.2 的官方 URL + 获取时间？这是一个设计决策，而不是我作为参与者应该单方面决定的事情。安全临时路径：指向现有的字节相同合同文件，并添加官方 URL + 获取时间作为附加字段，与 ADR §2.2 保持一致。

---

给运行器的说明：我没有写入 `runs/conference/ci_phase0_offline_assets_20260811/general_pi_qwen38.md`（该路径由运行器管理）。上面的完整报告是返回给运行器以进行持久化的内容。所有临时文件已被删除；未修改任何项目文件。
