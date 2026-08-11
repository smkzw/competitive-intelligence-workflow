# Phase 2 录制来源锚点

- Fixture：`fixtures/recorded/phase-2-lineage/nct02912468-minimal.json`
- 类型：官方公开 API 的最小录制科学片段，不是全量试验记录，也不是完整竞品调研结果。
- 官方来源：`https://clinicaltrials.gov/api/v2/studies/NCT02912468`
- 录制时间：2026-08-12 01:20（Asia/Shanghai）
- 文件 SHA-256：`f497d57cb1d4dacf9f52ce015d12ff33d7c9dc43b0b788d3792d03e4ca38b1b1`
- 冻结字段：NCT、标题、结果首次发布日期、试验设计、组别/干预、两项主要终点、首项主要终点的组别分母和结果、主要结果论文 PMID。
- 使用边界：测试从该原文重建创新药宇宙、试验/组别实体、精确 locator、证据片段、事实和声明；糠酸莫米松作为传统背景治疗保留审计但不获得竞品档案。
- 当前 live 核对与后续刷新不能原地改写该文件；科学字段变化必须建立新录制版本并保留旧摘要。
