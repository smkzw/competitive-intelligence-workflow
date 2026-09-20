# 竞品调研多 Skill 工作流

面向资深临床试验医学人员的竞品研究系统：一个公共入口接受适应症或严格研究包，自动完成检索、证据获取、事实建模、复核，并生成 A 适应症竞品全景台、B 临床结果证据室、C 试验设计图谱三个相互独立的中文多页面 HTML 门户。

首版交付面只有站点式 HTML（`package-manifest.json` 的 `formats: ["html"]`）。PDF/HTML-PPT/PPTX 代码保留在开发仓做出范围回归，不进入安装包；不提供 CSV/XLSX 导出、雷达图、证据成熟度视图、定时监测或默认排名。

当前状态：开发候选构建中（详见 `context/ci-gpt6-takeover-20260905.md` 检查点与 `plans/zcode-execution-plan-v6-20260911.md` 计划）。旧工程仅作为迁移证据，零接触。

## 产品底线

- 关键证据不足时不生成草稿或占位报告；核心可回答时带明确限制，否则仅交付证据不足说明。
- 只纳入创新药；传统药仅可作为背景、救援或对照事实出现。
- A、B、C 是三个各自完整的多页面门户，不以首页或 Top-N 摘要代替正文。
- 用户可见语言采用中文原生临床试验表达，不展示检索日志、Prompt 或后端标签。
- 跨试验比较由版本化医学语义政策与独立复核裁决；渲染层只投影，不自行裁决。

## 项目管理

工程使用 Trellis 保存任务、设计、实施和恢复状态：

```bash
python3 ./.trellis/scripts/task.py current --source
python3 ./.trellis/scripts/task.py list
```

开发质量门：`bash tools/gate.sh`（quality-only，非发布验收）。
