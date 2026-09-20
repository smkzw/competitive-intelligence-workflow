# Task 9.5 设计

## 包形态

完整候选物是内容寻址的 `.tar.zst` Skill bundle；Python wheel 继续只承载 CLI 模块。bundle 保留自包含相对布局，使根 `package-manifest.json`、唯一 fixture catalog、`host-smoke-v1`、包内 Schema、康哲 `site` 设计合同和入口可从解包根解析。

## 构建与校验

构建器从允许清单生成临时 staging，计算逐文件 SHA-256，再生成 package manifest、bundle 与外部摘要。校验器在独立解包目录重算全部摘要并拒绝缺失、额外、重复、绝对路径、`..`、软链接逃逸和缓存文件。这里的路径约束只服务可移植性与内容闭合，不扩展为安全专项测试。

## 安装边界

候选包安装到隔离根，不覆盖现有入口。共享规范根只保留一个内容寻址版本；OMP 只建立一个指向同一版本的明确链接。安装完成前旧入口保持不变；任何失败只撤销候选安装。

## 宿主验收

`run_host_smoke.py` 只负责启动各宿主真实外部会话并收集回执，不能 import adapter 后在同一 Python 进程伪造三份结果。宿主会话读取已安装公共 Skill，运行最小输入、能力预检和 `host-smoke-v1`，将回执写入 `docs/acceptance/host-smoke/`。批次验证以 Task 9.4 的唯一 `HostReceipt` 为准。

## 首版格式

实际请求和真实交付只包含 `html`。PDF、HTML-PPT、PPTX 仅在 capability matrix 中保留选择性阻断合同，不进入 bundle fresh-install 退出门。
