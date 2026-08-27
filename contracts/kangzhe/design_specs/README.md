# 竞品调研工作流 · 康哲设计合同

本目录是项目运行时唯一设计权威。它从 2026-08-11 稳定读取的康哲通用 `design_specs/` 内化而来，并增加竞品调研专属的受众、中文表达、四格式路由和验收规则。

## 读取顺序

1. `ROUTER.md`：根据交付格式确定项目路线；
2. `core.md`：读取共享康哲品牌、排版、图表和质量合同到 EOF；
3. `project_profile.md`：读取竞品调研专属用户与内容表达合同到 EOF；
4. 读取路线指定的一个主轨到 EOF；PDF 的 `track_pdf.md` 是项目补充合同，不是第二个媒介主轨；
5. HTML-PPT 继续读取 `htmlppt_fx.md`，并注入 `assets/htmlppt/gx_fx.css` 与 `gx_fx.js`；
6. 使用 `assets/logo_bot.svg`。

## 项目路线

| 项目交付物 | 必须加载 |
|---|---|
| 站点式门户 | `track_site.md`；筛选、联动和下钻见 `project_profile.md` |
| 原生 PDF | `track_stream.md` + `track_pdf.md` |
| HTML-PPT | `track_htmlppt.md` + `htmlppt_fx.md` |
| 可编辑 PPTX | `track_pptx.md`，并走 PPT Master |

## 独立演进

- 通用版只作为来源记录，不是运行依赖。
- 后续改动只提交到本项目合同，不反向更新通用版，也不自动吸收通用版变化。
- `manifest.json` 保存来源稳定摘要与本项目当前逐文件摘要。
- `local_map.md` 只描述项目相对路径，不含个人机器绝对路径。

## 文件角色

| 文件 | 角色 |
|---|---|
| `ROUTER.md` | 四种项目交付物的读取路线 |
| `core.md` | 康哲共享品牌和设计硬合同 |
| `project_profile.md` | 竞品调研用户、中文、页面与验收专属合同 |
| `track_site.md` | 多页面站点壳层 |
| `track_interactive.md` | 未来独立单页驾驶舱；不参与多页面门户加载 |
| `track_stream.md` | 连续阅读与原生 PDF 内容基线 |
| `track_pdf.md` | 原生 PDF 专属排版与验收 |
| `track_htmlppt.md` | 浏览器幻灯片及讲者运行时 |
| `htmlppt_fx.md` | HTML-PPT 动效与冻结验收合同 |
| `assets/htmlppt/gx_fx.css`、`gx_fx.js` | HTML-PPT 随包注入的视觉运行层 |
| `track_pptx.md` | PPT Master 与可编辑 PPTX |
| `assets/logo_bot.svg` | 康哲 Logo |
