# ADR 0003：离线演示资产来源与裁剪边界

- 状态：来源核验完成；等待康哲合同候选冻结后实施
- 日期：2026-08-11
- 范围：正式 Logo、Apache ECharts、HTML-PPT 运行层
- 明确不包含：视觉主题重设计、安全专项测试、复制活动资产、进入 Task 0.4

## 1. 决定摘要

1. Logo 只使用康哲官网当前 `logo_bot.svg` 的核验字节；当前官网、本机缓存和候选 `design_specs/assets/` 三者逐字节一致。
2. 图表层固定 Apache ECharts `6.1.0` 的官方 npm 发行物，只封装浏览器可直接加载的 `dist/echarts.min.js`、Apache-2.0 `LICENSE` 与来源清单。不得依赖 CDN、npm 镜像或宿主全局安装。
3. HTML-PPT 不原样复制通用主题。以 `lewislulu/html-ppt-skill` 的 MIT 运行时为来源，制作项目内衍生运行层，只保留康哲合同明确需要的翻页、`#/N` 深链、逐页页码、进度条、全屏、讲者窗口、逐字稿、计时与双窗同步。
4. 通用 `base.css` 不整份进入包；只建立项目自有的结构 CSS，视觉全部由冻结后的康哲 `core + htmlppt track` 提供。
5. 在用户确认康哲合同前，本 ADR 只记录决定，不复制上述资产到活动包。

## 2. 康哲 Logo

### 2.1 直接观察

官方地址：

`https://web.cms.net.cn/wp-content/themes/qnz/assets/img/logo_bot.svg`

2026-08-11 两次独立流式获取均得到：

- HTTP 200；`Content-Type: image/svg+xml`
- 9,542 字节
- `viewBox="0 0 121 25"`
- SHA-256 `8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae`
- 官网响应记录的 `Last-Modified: Sun, 21 Apr 2024 07:55:46 GMT`
- 当前 SVG 未检出脚本节点

本机全局 Skill 缓存与当前 `design_specs/assets/logo_bot.svg` 均为相同字节和摘要。

### 2.2 封装规则

- 模块化 HTML：包内相对路径 `assets/logo_bot.svg`。
- 单文件 HTML / HTML-PPT：转为内嵌 SVG Data URL，最终运行不得请求官网。
- PPTX：嵌入同一 SVG，不使用截图或文字占位替代。
- manifest 同时记录官方 URL、获取时间、字节数、SHA-256 与 `viewBox`。
- 官网不可达属于网络/技术故障；只有成功获取但内容摘要变化才属于资产变化，两者不得混写。

## 3. Apache ECharts 6.1.0

### 3.1 官方来源与完整性

- GitHub release/tag：`6.1.0`，解析到提交 `c5a48f5f97d23e5379720870b8444cd05b50ffb4f`。
- 官方 npm tarball：`https://registry.npmjs.org/echarts/-/echarts-6.1.0.tgz`
- npm 声明许可证：Apache-2.0。
- npm tarball SHA-1：`ae0f68590f5ebbd728d900907c27acde7c5456d1`。
- 官方完整性字段：`sha512-q0yaFPggC9FUdsWH4blavRWFmxdrIodbkoKNAjJudAI6CA9gNPxHtV2RcZNEepZVlk4yvBYkOkbk6HIVpIyHZA==`；本次重新计算一致。

### 3.2 选择

采用：

| 文件 | 字节 | SHA-256 | 用途 |
|---|---:|---|---|
| `dist/echarts.min.js` | 1,121,883 | `b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0` | 浏览器 classic bundle |
| `LICENSE` | 11,990 | `634293835b43a6dd2094fa39182a3d9a6b9ca43b7fdb9ac354e8037af2a3093a` | Apache-2.0 许可文本 |

选择理由：竞品报告需要柱状、折线、散点/气泡、雷达、热图和自定义森林图等完整组合；`simple` 发行物无法证明覆盖完整组件，`common` 发行物面向 CommonJS，不适合 `file://` 下直接以普通 `<script>` 加载。完整 min bundle 没有 `require(`、动态 `import(`、`sourceMappingURL` 或 CDN 请求；文件内出现的 Apache、zrender 和 XML URL 是许可证/命名空间文本，不是运行时网络依赖。

拒绝：

- 不把本机 npm 镜像返回的 tarball 当成来源权威。
- 不使用 CDN 或在线模块加载。
- 不把 60 MB 的完整 npm 解包内容写入 Skill。
- 不在未验证组件覆盖前用体积更小的 `echarts.simple.min.js` 替代。

## 4. HTML-PPT 运行层

### 4.1 上游

- 官方仓库：`https://github.com/lewislulu/html-ppt-skill`
- 核验提交：`f3a8435d3901697d5ac5e64d356c933637e43107`
- 许可证：MIT；`LICENSE` SHA-256 `a5ed4059e25a3ec35e439abd2623753d1f42d4aa4989ffb5c6b7a97b61f6a949`
- 上游 `assets/runtime.js`：37,082 字节，SHA-256 `d7b066a96b99fcf5c9e15b593283a57a3d43ac2bcf795d172adc7f3ba0844f79`
- 本机 `runtime.js`、`base.css`、`presenter-mode.md` 与该提交对应文件逐字节一致；本机 `SKILL.md` 含康哲扩展，不能作为上游源码摘要。

### 4.2 原运行时不能原样采用的原因

完整逐行检查确认，上游运行时虽为零依赖并具备所需能力，但与康哲合同存在下列直接冲突：

1. `T` 键、主题列表、预览主题消息会创建或切换通用主题样式。
2. `A` 键会轮换演示动画，可能改变正式页表现。
3. `O` 总览把缩略画布硬编码为 1920×1080，并把 clone 类名改为通用 `slide is-active`，会丢失康哲母版类并复制质检标识。
4. 页码更新只命中 `document.querySelector('.slide-number')` 的首个元素，不满足逐内容页绑定 `N / TOTAL` 的合同。
5. 讲者窗口仍含 `Presenter View`、`CURRENT`、`NEXT`、`TIMER`、`Slide`、`Prev`、`Reset`、`END OF DECK` 等非中文原生可见词。
6. 通用 `base.css` 携带通用蓝紫色、卡片、药丸、网格和主题工具类；这不是康哲视觉层。

### 4.3 项目衍生运行层

保留：

- 左右键、空格、PageUp/PageDown、Home/End 翻页；
- `#/N` 直接打开与 hashchange；
- 每页 `data-current/data-total`、内容页 `N / TOTAL` 与视口底部进度条；
- `F` 全屏；
- `S` 讲者窗口：当前页、下一页、150–300 字逐字稿、计时器、双向翻页同步；
- `N` 逐字稿抽屉；
- `R` 重置讲者计时；
- `?preview=N` 只用于讲者预览和排版调试；
- `file://` 与单文件内嵌运行。

删除：

- 主题列表、`T` 键、主题 indicator、theme BroadcastChannel/postMessage；
- 演示动画轮换、`A` 键和 animation indicator；
- 原始 `O` 总览实现。只有完成 1280×720、母版类保留、质检属性剥离及真实浏览器测试后才可重新启用；否则正式版不创建 overview DOM。

中文化：

- `Presenter View` → `演讲者视图`
- `CURRENT` / `NEXT` → `当前页` / `下一页`
- `SPEAKER SCRIPT` → `逐字稿`
- `TIMER` / `Slide` → `计时` / `页码`
- `Prev` / `Next` / `Reset` → `上一页` / `下一页` / `重新计时`
- `END OF DECK` / `END` → `演示结束`

结构 CSS 只负责 deck/slide 显隐、进度条、备注抽屉、讲者预览和打印冻结；不得包含通用品牌色、卡片、药丸、内容网格或主题 token。康哲样式仍最后加载并由冻结的设计合同验收。

### 4.4 以后实现时的精确检查

1. 来源清单固定上游 commit、原始 SHA、衍生文件 SHA、MIT 许可证和改动说明。
2. 静态检查不存在 theme/`T`/animation-demo/`A` 和纯英文讲者标签。
3. 逐页激活时，仅当前内容页显示正确 `N / TOTAL`；非内容页无可见页码。
4. 直接打开 `#/5`、键盘下一页和点击下一页都维持 `#/N` 格式。
5. `S` 打开中文讲者视图，当前/下一页/逐字稿/计时同步；`R`、`N` 可用。
6. `file://`、单文件、Chromium/WebKit 与 1280×720、1920×1080、2048×1024、实际最大化窗口均复测。
7. 正式运行请求只允许当前 HTML 自身、`data:` 与运行时创建的 `blob:`；无 CDN 或官网请求。

## 5. 当前边界

2026-08-11 08:19，上游康哲合同再次改为“`design_specs/` 单一权威 + 根文件入口 stub”，并启动了新的分轨实产物验证。这个变化使 ADR 0002 中“复制两份完整主合同”的建议失效。当前资产来源已经足够明确，但活动包必须等待该设计任务完成、候选摘要稳定且用户确认后才能写入。
