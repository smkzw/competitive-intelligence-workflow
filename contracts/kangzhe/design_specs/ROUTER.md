# 竞品调研工作流设计路由

Package root：当前 `design_specs/`。这是项目运行时唯一设计权威。

## 固定读取顺序

1. 读取本文件并确定一个项目 `route_id`；
2. 读取 `core.md` 到 EOF；
3. 读取 `project_profile.md` 到 EOF；
4. 按下表读取该路线的全部 track 到 EOF；
5. 使用 `assets/logo_bot.svg`。

## 项目路线表

| 交付物 | route_id | 必须读取 |
|---|---|---|
| 多页面交互式 HTML 门户 | `portal` | `track_site.md + track_interactive.md` |
| 原生 PDF | `pdf` | `track_stream.md + track_pdf.md` |
| HTML-PPT | `htmlppt` | `track_htmlppt.md` |
| 可编辑 PPTX | `pptx` | `track_pptx.md` |

四种格式同时生成时，每条路线独立完成读取、渲染和验收。共享同一份锁定报告快照和内容覆盖集合，不共享最终页面代码。

## 硬边界

- 门户必须是真实多页面站点，详情页不能被首页或抽屉替代。
- 门户允许使用交互轨的筛选、联动、下钻和状态保持，但不能继承 1280×720 幻灯片画布。
- PDF 必须是原生文本、矢量图形和可分页表格，不得由网页截图拼接。
- HTML-PPT 使用固定 1280×720 逻辑画布和讲者运行时，不得冒充门户或可编辑 PPTX。
- PPTX 必须经 PPT Master 串行流程生成可编辑对象，不得把 HTML 截图塞入幻灯片。
- 受众可见内容不得出现程序状态、日志标签、提示词、验收节点名或无必要英文模块名。

## 资产

- Logo：`assets/logo_bot.svg`
- 来源与本项目摘要：上一级 `manifest.json`

`local_map.md` 仅提供项目相对路径；运行合规不依赖它。
