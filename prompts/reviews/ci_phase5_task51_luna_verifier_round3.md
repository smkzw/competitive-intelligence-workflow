第三轮最终复验，保持同一 session、只读、不要扩展到 Task 5.2。只核查你第二轮列出的剩余 P0/P1/P2 是否已关闭：

- Protocol/SAP 不能满足疗效或 TEAE/SAE 最低记录；
- bool 不能被归一化为 numeric_value 或 denominator；
- 安全性 `unit_id` 与规范测量单位分离，`unit="teae"` 不通过；
- 单项目 product_id 必须属于 snapshot；
- 终点级同试验证据可成为锚定事实，跨产品仍失败；
- `NOT_APPLICABLE` 必须使用 snapshot 已声明谓词、封闭停止开发事件单元，并与项目监管事件一致；
- 早期项目中的未知/跨产品 core/anchor 记录也立即失败；
- 空 aliases 必须有明确无别名依据；
- 用户阻断说明公共模型和生成路径都拒绝“门槛、竞品宇宙、基础层”等后端语言。

运行最新 91 项 A 专项测试与必要的最小反例。若无 P0/P1，输出 PASS；若仍有，输出 REVISE 和精确反例。P2 仅列会实际影响 Task 5.1 用户功能的事项，不要把后续页面、搜索、渲染职责算作本任务缺陷。
