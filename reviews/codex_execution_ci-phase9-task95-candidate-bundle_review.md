# Codex Execution Review: ci-phase9-task95-candidate-bundle

## Verdict

Accept。Task 9.5 已达到获批实施计划的 bundle、fresh-install、三真实宿主、初始无草稿阻断、补件恢复与站点式 HTML 退出条件。

## Worker Outputs

三个执行工作项均完成：worker_01 交付 allowlist 构建、逐文件清单、外部摘要和失败关闭校验；worker_02 交付内容寻址 fresh-install 与真实宿主 runner；worker_03 交付安装/宿主验收测试、中文说明和归档合同。后续整合补齐了完整阻断—恢复场景、公共 Skill 自发现、安装 CLI 与归档绑定。

## Boundary

范围仅限 Task 9.5 的完整候选包、隔离安装、真实宿主验收、中文说明与归档；未实现或验收 PDF/PPT，未修改科学真源、既有用户项目或旧工程，也未开展安全专项测试。

## Manager Assessment

本路由不设执行 manager，由 Codex 直接整合。整合时处理了两个真实缺陷：完成态只暴露 `html.manifest.json` 导致宿主回执无法绑定首页；Hermes 默认提供方把 OpenAI 兼容请求送至错误端点并返回 404。前者通过解析产物清单并绑定 `overview.html` 修复；后者保留失败证据，在同一 Hermes 会话切换至可用路由后完成，未把技术故障误写为没有资料。

## Codex Independent Verification

最终候选包 `dist/competitive-intelligence-workflow.tar.zst` SHA-256 为 `50a91aac3e0050887ae48e29e921a45cf540d986b418eaac8d4af068f6a3e8c3`，共 374 个文件，`BUNDLE_OK`。规范候选根安装于 `/Users/smkzw/.cc-switch/skills/clinical-research/competitive-intelligence-workflow`，`PACKAGE_OK`；共享根和 OMP 链接均解析到同一内容地址版本。

Codex、Hermes、OMP 三个 PATH 真实入口均完成独立外部进程验收；三份回执分别绑定初始 `evidence_blocked`、退出码 4、零报告文件，固定补件、显式重开/重新绑定，最终 `rendered`、退出码 0、`overview.html` 摘要和当前事件链。批次结论 `real_host_pass=true`。聚焦测试 `63 passed, 1 skipped`，Ruff 与六个目标源码的 mypy 均通过。

## Cleanup Decision

保留候选包、三宿主回执、批次/归档索引、会商输出和路由日志。治理审计通过后归档执行包；旧候选安装均已可恢复地移至废纸篓，不删除用户工程或其他任务数据。
