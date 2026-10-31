# ciw v2｜远程审阅入口（第15次后）

第15次已正常结束，当前工作流已暂停。47源条款/11阅读队列及新候选科学、实屏仍待验收。

本目录是代码和记录的审阅资料，不是恢复执行授权。最新状态见[STATUS](../STATUS.md)，完整经过见[详细交接](PAUSE_20261031_AFTER_REBUILD15.md)。

## 请审这两个分支

- CI：`smkzw/competitive-intelligence-workflow` / `codex/ciw-clinical-endpoint-index`。真实15使用产品786bf8e、启动HEAD0e00486，产物fa2407，耗时9小时7分19秒。默认main是旧工程，v2-trunk也不是最新候选。
- 工作台：`smkzw/protocol-v3-workbench` / `codex/ciw-report-reading-focus`。运行产品389fdea，文档提交另见manifest。

两个分支均保留历史，无main合并或强推。主作者与隔离分支的重复cherry-pick不要算两次功能。

## 阅读顺序

1. [STATUS](../STATUS.md)：唯一当前状态，PAUSED及具体终态。
2. [详细交接与全阶段复盘](PAUSE_20261031_AFTER_REBUILD15.md)：执行包以来做/未做、需求变化、踩坑、恢复步骤。
3. [PRD](../PRD.md)、[DECISIONS](../DECISIONS.md)、[架构](../ARCHITECTURE.md)、[计划](../PLAN.md)：唯一现行产品合同；后来的D17–D22覆盖旧条款。
4. [脱敏版本/运行/测试清单](REBUILD15_REVIEW_MANIFEST_20261031.json)：源码、当前报告、保全和未执行项。
5. [截图索引](../screenshots/README.md)：每张都标明版本，不用旧截图假称15已经验收。
6. [原执行包](EXECUTION_PACK.md)、详细交接末尾所有历史链接：只作背景，不自动执行旧PID/旧模型/旧构建命令。

## 重点审什么

|优先级|问题|代码入口|
|---|---|---|
|高|来源条款/中文是否保持完整人群、AND/OR、比较符、单位及时间；真实越界是否仍拒|`verify/design_clauses.py`、`design_labels.py`、`normalize/design.py`|
|高|为什么同一资料两段模型流程/全上下文材料键仍耗时；部分待核批次会重复请求已接受兄弟，何处可在既有两角色内减少重复|`research.py`、`pipeline.py`、`crosscheck.py`及schema|
|高|临床相关集合与同轴资格是否分开；保留所有原值/独立组/来源统计|`endpoint_families.py`、`comparison_axes.py`、`analyze/results.py`和工作台adapter|
|高|第15实际报告与代码是否同版本；原件/缓存/历史快照是否保全|manifest、`release.py`、`store.py`|
|高|真正用户阅读与横比是否可用；密度与ECharts不靠小字/假点/隐藏事实|`render/static`、工作台EvidenceDesignWorkspace、实屏|
|中|事件引文、论文分组/方向、完整查询采用与来源空缺|`events.py`、`publications.py`、`sources/pubmed.py`|
|中|单写、恢复、版本URL/旧404、身份租户边界及默认关闭本地入口|工作台`ciw_research*`、`ciw_release_adapter.py`、`ciw_local_identity.py`|
|中|正式认证/最新Studio消费、A企业/MAH/中国/关键论文尚未闭合|当前PRD、handoff未完成清单|

不建议为本轮增加图数据库、向量库、通用DSL、模型路由器、逐事实审批或另一套恢复/签发平台。测试按根因成族，最终宽门，不以903测试或一个audit替代真实任务。

## 可独立做的离线代码检查

```sh
uv sync --frozen
uv run pytest
uv run ruff check src tests
git diff --check
```

已经在当前执行机的**新GitHub clone**剥离模型凭据后运行：903 passed（15.97秒）及其余命令成功。它是同机可重建验证，不假称远端机器或临床E2E。工作台的范围/命令见其`docs/ciw-release-adapter.md`；不要顺手调用真实Studio医学AI。

原件、数据库、完整模型响应、运行日志及内部Design不在公共Git。可审代码/夹具/记录/截图；要复现真实私有运行，需另经授权取得运行区及独立凭据。不要凭空引用本机路径、重做全部研究或把缺材料写成通过。

## 获取固定源码

```sh
git clone --branch codex/ciw-clinical-endpoint-index https://github.com/smkzw/competitive-intelligence-workflow.git
git clone --branch codex/ciw-report-reading-focus https://github.com/smkzw/protocol-v3-workbench.git
```

源代码固定到manifest所列产品提交；文档在当前分支包含本次暂停结果。不要从旧main或旧v2-trunk取代本次候选；审阅不自动恢复Goal、研究或浏览器操作。
