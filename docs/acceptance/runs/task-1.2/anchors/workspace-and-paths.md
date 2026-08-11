# Task 1.2 真实锚点

- 新项目生成 v1.2 完整目录与 12 个初始文件，`PRAGMA integrity_check` 返回 `ok`。
- 项目改名并移到另一父目录后，合同恢复相等，核验根目录为新位置。
- A/B/C x HTML/PDF/HTML-PPT/PPTX 的 12 组产物路径及各自 manifest/coverage projection 均为 `reports/<A|B|C>/<version>/...` 相对路径。
- 缺目录、绝对路径污染、损坏 SQLite、小写报告、省略版本、路径跳转均失败关闭。
