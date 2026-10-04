# R24-247｜支持性证据不再误走疗效分组

2026-10-04；既定 W03/W05/W07 根因族，不是新产品权威。
原 HEAD/脏树/来源/74页完整候选保留，未 current/commit/push。

## 实际修复

普通 B supporting 页面原走 efficacy membership，丢失免疫原性/PK/biomarker
科学分类并把原始指标标题写成“临床概念未列示”。投影保留独立 source_domain /
source_metric、测量实例、class/category；展示域仍 supporting，原值、单位、引用
不变。不套疗效词表或 AE 分类，也不把产品关系未知变成不存在研究。

支持性默认面板按研究、原测量实例和语境分开；同研究同测量的登记组原值可
描述并列。措辞归并即使有正向独立回执，也不能跨不同科学域/metric。沿用已有
语义引擎，加硬边界而非另建本体；政策版本 v3 使旧裁决摘要失效，历史不回填。

## 成族检验

实际7 RED/1.08s：三个原生源页域丢失、疗效错误路由、跨域/metric正向误归并、
同研究不同测量实例误合并。RED XML SHA
`451e9e99a801d53b583ce06ca47a2f9abf76c3e28b96153ed9be7363d0896d9f`。
一组最小完整修复后82相关PASS/4.31s，包括现行语义/批准归并/源候选/B普通入口。
GREEN XML `39a5f8943b45eddc7fa7247b6ffe730b34b299695c5007dfabb9c95cfbebd35a`。
strict-mypy两源、Ruff三个文件通过；没有按每行重跑全仓。

## 真实原源普通入口切片

命令：`uv run python .artifacts/r24-247-b-supporting-domain-20261004/replay_supporting_v1.py`。
零新HTTP；固定54研究母池原SHA `043b4a9578923e0e080221f2cca1c13c90dd4926dede02f7cf558c8a477b5f41`。
全部48支持性原始观察进普通 B 入口，74物理页/6901745B/28面板。
site SHA `82593f0ec7f0accd2f5c9a7c2ba9a4b5a71ee22134408bb5d7d25d3e94b0145c`。
逐48科学域/metric、值、单位、原文、来源版本、测量实例精确核对，28面板均单
研究/单domain/单metric/单测量实例。不是整6346临床结果报告的替代或医学可比接受。
组件目录约6.6MiB，不再重建另一202MiB全站。原完整 B v1 原件和探针FAIL均保留。

私有checkpoint SHA `cb15264810d4ef8bbdac1bd440cf83c8241e7f33e2bc1c06762367c023180829`；
audit SHA `4100ea2c2e58afc7f12e6b3e549b89189650b821bffdec153d2d5bbc5bc0ed8d`。
源码 report_b.py SHA `7394aa5097cecb32903fcd4d5a76473a3674e5788ef1abb849abc9594c3347e8`；
semantic_grouping.py `d63b6a9d2e91e58507ad882280fa2508c980093390e3577b2cc82216cc2c6eb7`。

## 尚未接受

Node/普通渲染/源重放不是 Ego 像素审美或独立医学采用。C compound coverage /
设计锚点/发现宇宙问题、全球中国/文献、current编辑分享、24完整报告、三宿主
全部模式、安装恢复/RC仍开放。245执行仍只等kernel终态，不在途QA或重派。
