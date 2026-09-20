# Task 8.3 设计约束

- 使用项目已冻结的 `core + project_profile + stream + pdf` 设计合同；不再同步通用康哲规范。
- “PDF 阅读器”指标准桌面阅读器中的真实打开与检索验收，不新增网页阅读器。
- 验收器严格只读：只能报告、生成验收证据和否决，不得改写 PDF、fixture 或投影代码。
- 复用 Task 8.2 已有 pypdf、pdftotext、pdftoppm 与 coverage projection；不增加新依赖或第二套检查引擎。
- 原始页图保留逐页分辨率；contact sheet 只用于总览，不能替代原图逐页检查。
- 验收记录对用户使用中文临床阅读语言；程序字段仅留在结构化证据，不进入报告正文。
