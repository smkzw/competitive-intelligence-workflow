# 候选包宿主冒烟验收归档

本目录只保存候选 `.tar.zst` 包 fresh-install 后的验收证据。它不是源码 checkout 的回执暂存区，也不接受由适配器在同一进程拼出的 JSON。

## 归档文件

一次完整归档必须同时包含：

- `codex.json`
- `hermes.json`
- `omp.json`
- 一份归档索引 `archive.json`，符合本目录的 `archive-contract.schema.json`

三个回执正文必须分别符合仓库内 `schemas/host-receipt.schema.json`，并由 `tools/run_host_smoke.py` 从真实安装入口生成。缺少任一回执、只保存 capability preflight JSON、或只保存适配器语义 JSON，都不能写入“已接受”。不要手工复制旧 Task 9.4 回执；每次候选包变更都必须重新运行。

三个单宿主命令分别产生对应回执；完成跨宿主比较后汇总的 `batch.json` 只是本次运行的原始批次绑定，不能替代归档索引。完成包、case、回执、路径和独立性检查后，才可按本合同汇总出 `archive.json`。若检查未完成，保留 `pending` 或 `rejected`，不得写成 `accepted`。

## 运行顺序

在仓库根目录执行。命令只写入明确的候选包、隔离项目和本归档目录；不要覆盖既有宿主入口：

真实宿主命令必须显式携带 `--allow-real-host`；缺少该开关时只记录环境阻断，不启动宿主进程。


```bash
mkdir -p dist
uv run python tools/build_bundle.py \
  --output dist/competitive-intelligence-workflow.tar.zst
uv run python tools/verify_bundle.py \
  --bundle dist/competitive-intelligence-workflow.tar.zst

export CI_WORKFLOW_INSTALL_ROOT="$HOME/.cc-switch/skills/clinical-research/competitive-intelligence-workflow"
uv run python tools/run_host_smoke.py --allow-real-host --host codex \
  --case host-smoke-v1 --require-external-host-process \
  --project-root "$CI_WORKFLOW_INSTALL_ROOT/projects/codex" \
  --receipt "$PWD/docs/acceptance/host-smoke/codex.json"
uv run python tools/run_host_smoke.py --allow-real-host --host hermes \
  --case host-smoke-v1 --require-external-host-process \
  --project-root "$CI_WORKFLOW_INSTALL_ROOT/projects/hermes" \
  --receipt "$PWD/docs/acceptance/host-smoke/hermes.json"
uv run python tools/run_host_smoke.py --allow-real-host --host omp \
  --case host-smoke-v1 --require-external-host-process \
  --project-root "$CI_WORKFLOW_INSTALL_ROOT/projects/omp" \
  --receipt "$PWD/docs/acceptance/host-smoke/omp.json"

uv run pytest tests/hosts/test_fresh_install.py \
  tests/hosts/test_conformance.py \
  tests/hosts/test_real_host_smoke.py -q
```

`verify_bundle.py` 必须输出 `BUNDLE_OK`。`run_host_smoke.py` 必须从同一个 fresh-install 候选包依次启动三宿主公共 Skill；测试项目、会话和外部进程各自独立。任何命令失败时，只撤销隔离候选安装，不触碰旧入口和已接受科学快照。

## 归档索引最小字段

机器可读索引使用 `archive-contract.schema.json`，并绑定：

- 候选包路径、`.tar.zst` SHA-256、包内 `package-manifest.json` SHA-256；
- `host-smoke-v1` case digest；
- 三个固定回执文件名；
- bundle 校验、回执 Schema、当前性、`path_resolved`、包摘要与案例摘要一致性、语义状态一致性、`process/session/run` 互异、no-draft 断言和 HTML-only 范围共十项布尔检查；
- `pending`、`accepted` 或 `rejected` 状态及中文说明。

只有十项检查全部为真、三个宿主均为 `path_resolved`、均完整绑定初始 no-draft 阻断与补件恢复后 HTML，且 `real_host_pass=true` 时，索引才可写 `acceptance_status=accepted`。`explicit` 测试替身和 `unavailable` 环境状态可以保留为诊断证据，但绝不构成真实宿主通过。

## 首版范围和失败说明

首版实际交付只有 A/B/C 的站点式 HTML。PDF、HTML-PPT、PPTX 只保留选择性能力合同，不进入本次 bundle fresh-install 退出门；不要因为这些可选能力缺失而阻断 HTML。

用户提示必须区分两类问题：

- **技术或环境问题**：例如真实宿主不可执行、外部进程启动失败、浏览器/网络/运行时不可用。提示“本轮遇到技术问题，尚未完成；请恢复环境后重试”，不能写成“未检索到资料”。
- **关键证据不足**：例如输入资料缺少关键来源或字段。提示“关键证据不足，暂不生成草稿；已完成的检索和缺少的材料见证据不足说明”，并保持 `no_draft=true`。不能用技术故障掩盖证据缺口，也不能用猜测补齐事实。

归档记录应保留真实退出码、开始/结束时间、外部进程 argv、宿主版本、安装入口、事件链、manifest 与 HTML 产物（如有）的摘要。归档本身不替代 Codex 对科学、视觉、临床、监管和生产范围的最终验收。
