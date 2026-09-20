# Task 8.6 HTML-PPT 全页多视口原图与诊断台账

记录时间：2026-08-31T06:34:31.094814+00:00
收集器：`tools/collect_html_ppt_visual_baseline.py`
状态：**非终验**。本文件是首轮真实渲染证据和自动缺陷基线；
Codex 仍是视觉、医学与监管结论的最终权威。

## 绑定哈希

| 报告 | 路径 | 页数 | 锁定 SHA-256 | 实测 SHA-256 | 结果 |
|---|---|---:|---|---|---|
| A | `output/html-ppt/report-a.html` | 20 | `718705c6d1aa1347907b600e27a9753230f8ad93afb17a0cfa73f44eb164d7a6` | `718705c6d1aa1347907b600e27a9753230f8ad93afb17a0cfa73f44eb164d7a6` | 匹配 |
| B | `output/html-ppt/report-b.html` | 24 | `2bf6a334fd484f1df99bca363f1425503f83e9aa9727a73986a6fcd846c3a406` | `2bf6a334fd484f1df99bca363f1425503f83e9aa9727a73986a6fcd846c3a406` | 匹配 |
| C | `output/html-ppt/report-c.html` | 18 | `e284dec451cc8355a5ebdd376a903785b3a10e984a9a6bae9bc3c73a61a8f342` | `e284dec451cc8355a5ebdd376a903785b3a10e984a9a6bae9bc3c73a61a8f342` | 匹配 |

## 采集矩阵

- 浏览器：chromium
- 截图张数：248（62 页 × 4 视口 × 1 浏览器）
- 协议：`file://`；设备像素比 1；视口原图（非整页文档滚动、非元素裁切）
- 入场动效：截图时 `animations=disabled`，翻页后等待稳定再拍

| 视口 | CSS 像素 | 用途 |
|---|---|---|
| `1280x800` | 1280×800 | CFORCE CSS 最大化基线 |
| `1920x1080` | 1920×1080 | Mi Monitor CSS 最大化基线 |
| `2048x1024` | 2048×1024 | 非 16:9 压力视口 |
| `1280x720` | 1280×720 | 逻辑画布回归视口 |

## 自动缺陷汇总

去重视图（跨浏览器/视口合并同类）：阻断 0、高 0、中 0、低 0。完整逐次命中见 JSON。

本轮自动诊断未发现溢出、裁切、远程请求或缩放合同失败。

## 首轮重点页

| 页标识 | 移交问题 | 自动诊断 | 代表原图 |
|---|---|---|---|
| `a-matrix-2` | A 矩阵第二页标签留白/引线 | 自动诊断未报警（仍须人工看原图） | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1280x800/a-14-a-matrix-2.png` |
| `b-efficacy` | B 疗效页 92.2 与图例间距 | 自动诊断未报警（仍须人工看原图） | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1280x800/b-04-b-efficacy.png` |
| `c-endpoints` | C 终点页 EASI ≥ 75 % 中文排版 | 自动诊断未报警（仍须人工看原图） | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1280x800/c-09-c-endpoints.png` |

## 62 页索引（Chromium 1920×1080）

| 报告 | 序号 | 页标识 | 标题 | Chromium 1920×1080 原图 |
|---|---:|---|---|---|
| A | 1 | `a-cover` | 特应性皮炎竞品全景 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-01-a-cover.png` |
| A | 2 | `a-toc` | 汇报章节 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-02-a-toc.png` |
| A | 3 | `a-summary` | 首页摘要 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-03-a-summary.png` |
| A | 4 | `a-landscape` | 竞争格局 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-04-a-landscape.png` |
| A | 5 | `a-products` | 产品总览 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-05-a-products.png` |
| A | 6 | `a-clinical` | 临床开发组合 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-06-a-clinical.png` |
| A | 7 | `a-efficacy` | 疗效 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-07-a-efficacy.png` |
| A | 8 | `a-efficacy-2` | 疗效（续1） | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-08-a-efficacy-2.png` |
| A | 9 | `a-efficacy-3` | 疗效（续2） | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-09-a-efficacy-3.png` |
| A | 10 | `a-efficacy-4` | 疗效（续3） | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-10-a-efficacy-4.png` |
| A | 11 | `a-efficacy-5` | 疗效（IGA 应答） | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-11-a-efficacy-5.png` |
| A | 12 | `a-safety` | 安全性 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-12-a-safety.png` |
| A | 13 | `a-matrix` | 疗效与安全性矩阵 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-13-a-matrix.png` |
| A | 14 | `a-matrix-2` | 疗效与安全性矩阵（续1） | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-14-a-matrix-2.png` |
| A | 15 | `a-regulatory` | 中国与全球监管 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-15-a-regulatory.png` |
| A | 16 | `a-companies` | 企业与交易 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-16-a-companies.png` |
| A | 17 | `a-patents` | 专利与保护 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-17-a-patents.png` |
| A | 18 | `a-history` | 历史与边缘观察 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-18-a-history.png` |
| A | 19 | `a-limitations` | 研究依据与局限 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-19-a-limitations.png` |
| A | 20 | `a-ending` | 谢谢 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/a-20-a-ending.png` |
| B | 1 | `b-cover` | 阵发性睡眠性血红蛋白尿临床试验结果比较 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-01-b-cover.png` |
| B | 2 | `b-toc` | 汇报章节 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-02-b-toc.png` |
| B | 3 | `b-summary` | 首页摘要 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-03-b-summary.png` |
| B | 4 | `b-efficacy` | 疗效 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-04-b-efficacy.png` |
| B | 5 | `b-longitudinal` | 纵向结果 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-05-b-longitudinal.png` |
| B | 6 | `b-safety` | 安全性 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-06-b-safety.png` |
| B | 7 | `b-matrix` | 疗效与安全性矩阵 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-07-b-matrix.png` |
| B | 8 | `b-baseline-overview` | 基线与人群总览 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-08-b-baseline-overview.png` |
| B | 9 | `b-demographics` | 人口学 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-09-b-demographics.png` |
| B | 10 | `b-disease-context` | 疾病语境 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-10-b-disease-context.png` |
| B | 11 | `b-severity` | 基线疾病严重程度 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-11-b-severity.png` |
| B | 12 | `b-disposition-overview` | 试验完成情况总览 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-12-b-disposition-overview.png` |
| B | 13 | `b-flow` | 受试者流转 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-13-b-flow.png` |
| B | 14 | `b-adherence` | 依从性 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-14-b-adherence.png` |
| B | 15 | `b-loss-exit` | 失访与退出 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-15-b-loss-exit.png` |
| B | 16 | `b-screen-failure` | 筛败与原因 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-16-b-screen-failure.png` |
| B | 17 | `b-rescue` | 补救治疗 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-17-b-rescue.png` |
| B | 18 | `b-prohibited` | 禁用药使用 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-18-b-prohibited.png` |
| B | 19 | `b-deviation` | 方案偏离 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-19-b-deviation.png` |
| B | 20 | `b-exposure` | 试验与暴露语境 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-20-b-exposure.png` |
| B | 21 | `b-subgroups` | 亚组与支持证据 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-21-b-subgroups.png` |
| B | 22 | `b-profiles` | 产品与试验档案 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-22-b-profiles.png` |
| B | 23 | `b-limitations` | 研究依据与局限 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-23-b-limitations.png` |
| B | 24 | `b-ending` | 谢谢 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/b-24-b-ending.png` |
| C | 1 | `c-cover` | 中重度特应性皮炎临床试验设计比较 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-01-c-cover.png` |
| C | 2 | `c-toc` | 汇报章节 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-02-c-toc.png` |
| C | 3 | `c-summary` | 首页摘要 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-03-c-summary.png` |
| C | 4 | `c-design-map` | 设计图谱 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-04-c-design-map.png` |
| C | 5 | `c-population` | 人群与疾病定义 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-05-c-population.png` |
| C | 6 | `c-inclusion` | 入选标准 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-06-c-inclusion.png` |
| C | 7 | `c-exclusion` | 排除标准 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-07-c-exclusion.png` |
| C | 8 | `c-arms` | 分组、干预与对照 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-08-c-arms.png` |
| C | 9 | `c-endpoints` | 终点、定义与时间点 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-09-c-endpoints.png` |
| C | 10 | `c-visits` | 访视、疗程与随访 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-10-c-visits.png` |
| C | 11 | `c-stats` | 样本量与分析集 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-11-c-stats.png` |
| C | 12 | `c-dossiers` | 试验档案 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-12-c-dossiers.png` |
| C | 13 | `c-identity` | 试验定位核对 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-13-c-identity.png` |
| C | 14 | `c-patterns` | 设计模式与权衡 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-14-c-patterns.png` |
| C | 15 | `c-path-1` | 可选路径一 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-15-c-path-1.png` |
| C | 16 | `c-path-2` | 可选路径二 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-16-c-path-2.png` |
| C | 17 | `c-limitations` | 资料版本与局限 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-17-c-limitations.png` |
| C | 18 | `c-ending` | 谢谢 | `docs/acceptance/runs/8.6/visual-final-4-chromium/screenshots/chromium/1920x1080/c-18-c-ending.png` |

## 复跑

```text
uv run python tools/collect_html_ppt_visual_baseline.py
```

哈希不匹配时收集器以退出码 2 失败关闭，不生成误绑原图。
