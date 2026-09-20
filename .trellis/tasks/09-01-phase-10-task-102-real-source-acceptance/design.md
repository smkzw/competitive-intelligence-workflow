# Task 10.2 设计

## 项目隔离

本次创建唯一 run 根：

`/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-<run_id>/`

其下为 `a-real`、`b-real`、`c-real` 三个开始时不存在的项目。测试先记录 run start、源码摘要、包摘要和空根证明，再调用唯一 CLI 创建项目。

## 科学输入

- A：特应性皮炎；完整创新药宇宙与全球/中国开发状态。
- B：阵发性睡眠性血红蛋白尿；疗效、安全性、基线、完成/退出/补救治疗/禁用药/方案偏离等披露状态。
- C：特应性皮炎；登记字段足够路径及关键临床设计字段缺失后的 Protocol/SAP 补件恢复路径。

每条事实保留来源 URL、来源身份、首次披露/获取时间、定位、原值、规范化值和证据状态。结果数值不得因自动抽取空 `drug_name` 而丢失；必须从 trial/arm 身份回填映射后再核验。

## 当前运行闭合

每类 exact test 沿：

`run_id → evidence/report snapshot → artifact manifest → artifact record → overview.html/详情页 → 双浏览器 verdict`

检查 producer run、source/package digest、cutoff、coverage、文件 SHA-256/bytes/mtime、全部路由 anchor。旧 mtime、预存项目、旧 manifest、断链、伪浏览器 verdict 或只验证首页均失败关闭。

## 故障处理

零竞品、零方案、零结果、大面积数值缺失或页面空白均视为异常信号，先检查检索词、API/页面结构、登录/限流、解析器、身份映射、截止日和门槛，再判断是否确实未公开。两次相同失败无新证据时改变方法或来源，不机械重试。
