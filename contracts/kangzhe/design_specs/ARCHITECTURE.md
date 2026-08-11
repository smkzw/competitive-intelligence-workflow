# 架构：项目自有的分轨设计合同

## 决定（2026-08-11）

1. **唯一运行权威**：`contracts/kangzhe/design_specs/`。
2. **根文件仅为兼容入口**：`contracts/kangzhe/design.md` 不承载第二份正文。
3. **项目专属层**：`project_profile.md` 固定竞品调研用户、中文表达、页面结构和完成判定。
4. **组合路线**：门户加载站点与交互轨；原生 PDF 加载流式与 PDF 轨；HTML-PPT、PPTX 分别加载自己的轨。
5. **独立演进**：来源通用版不再是运行依赖；本项目不读取、不自动同步、不反向修改通用版。
6. **格式原生**：门户、PDF、HTML-PPT、PPTX 分别生成和验收，不以截图或其他格式冒充。

共享品牌与排版规则保留在 `core.md`，竞品调研专属规则只在 `project_profile.md` 和 `track_pdf.md` 增补，避免复制五轨正文。
