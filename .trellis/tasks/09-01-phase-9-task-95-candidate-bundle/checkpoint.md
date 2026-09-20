# Task 9.5 完成检查点

## 已完成

- 候选包：`dist/competitive-intelligence-workflow.tar.zst`，374 个文件，SHA-256 `50a91aac3e0050887ae48e29e921a45cf540d986b418eaac8d4af068f6a3e8c3`；外部摘要、逐文件清单和 `BUNDLE_OK` 一致。
- 规范安装：`/Users/smkzw/.cc-switch/skills/clinical-research/competitive-intelligence-workflow`；共享根和 OMP 单一链接指向同一内容地址版本，`PACKAGE_OK`。
- 三真实宿主：Codex、Hermes、OMP 均为 PATH 解析的独立外部进程；每份回执证明初始关键证据不足、退出码 4、零草稿，固定补件、显式重开和重新绑定，最终生成站点式 HTML 并通过项目复核。
- 批次归档：`docs/acceptance/host-smoke/{archive.json,batch.json,codex.json,hermes.json,omp.json}`，`real_host_pass=true`，绑定当前 bundle、包清单和 case digest。
- 确定性复核：63 passed、1 skipped；Ruff 与六个目标源码 mypy 通过。
- 独立会商：Pi/Cursor 会话 `01a05a8c-f404-7000-aada-4c33619bd1a4` 首轮拒绝后，同会话复审确认技术缺口闭合；治理关联轮要求的 Trellis 同步已完成。

## 关键故障与处理

- 完成态只列出 `html.manifest.json`，宿主回执无法定位首页：改为解析产物清单并绑定真实 `overview.html` 与摘要。
- Hermes 默认提供方端点返回 404：与“没有资料”区分，保留请求转储和日志；同一 Hermes 会话切换至可用提供方/模型后完成验收。

## 边界

- 首版只交付站点式 HTML；PDF、HTML-PPT、PPTX 不在本任务退出门。
- 未删除旧工程，未进行安全专项测试，未改科学真源或用户项目。
- 两次被替换的候选安装已可恢复地移至废纸篓；规范候选根保留当前已接受版本。

## 下一安全动作

进入 Task 10.1：依据获批计划固定正负基准矩阵；不得把 Task 9.5 候选包冒充 Task 10.6 最终 RC。
