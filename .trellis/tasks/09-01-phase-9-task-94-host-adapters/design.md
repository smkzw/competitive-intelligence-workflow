# Task 9.4 设计

## 单一语义合同

`HostAdapter` 接收规范化最小输入和既有项目路径，只返回宿主调用计划、中文状态消息、中断/恢复映射和产物定位。共享 `HostSemanticReceipt` 是三宿主一致性的比较面；宿主名称、可执行文件、真实路径、进程和会话属于运行身份，不参与科学语义摘要。

宿主适配器不得导入门槛评估器、来源策略写入、事实/声明存储、快照锁定、修订批准或报告渲染内部实现。它只能调用公共 CLI/应用入口并验证回执。

## 回执层次

- `HostSemanticReceipt`：最小输入、能力选择、规范状态、阻断/恢复、部分交付和产物摘要。
- `HostRunIdentity`：宿主、安装入口 realpath、可执行文件/版本、外部 PID、会话 ID、工作流 run ID。
- `HostReceipt`：绑定 package digest、case digest、语义回执运行点摘要、事件链摘要、no-draft 断言、最终 manifest 与退出码。语义回执摘要用于定位运行时差异，并由整份回执自摘要防篡改；由于能力探针具有时点性，它不单独充当事后真实性判据。

三宿主一致性比较排除工具定位与运行身份，但要求项目合同、状态/失败/恢复、事件链阶段、no-draft 与最终 manifest 语义一致。

## 首版格式裁决

Task 9.4 的真实 smoke 仅请求 `html`。能力矩阵仍保留其他格式的选择性阻断合同，以证明缺失 PPT Master/Office 不会阻断 HTML；PDF、HTML-PPT、PPTX 不作为首版退出门，也不在三个宿主重复生成。

## 中断与恢复

关键证据不足时公共执行器写规范事件与检查点，适配器只把状态翻译成中文宿主消息。恢复信号必须绑定同一项目、同一中断和用户新提供材料；宿主私有会话丢失后仍可从项目文件恢复。

## 真实入口边界

源码级适配器测试不等于真实宿主 smoke。HA09 要求外部进程和各自安装入口；Task 9.4 先冻结回执/runner 合同并在当前可用入口验证，Task 9.5 对最终候选包 fresh-install 后重新运行并绑定最终包摘要。任何模拟回执都不能标记真实宿主通过。

Task 9.5 的候选交付物是完整 `.tar.zst` Skill bundle，而不是仅承载 Python CLI 的 wheel。完整包必须保留仓库式相对布局，至少包含 `package-manifest.json`、唯一 `fixtures/catalog.yaml`、`fixtures/synthetic/host-smoke-v1/`、包内 Schema 与控制台入口；fresh-install 验收从解包后的独立目录安装并运行同一合同。wheel 仍只承担 CLI 模块分发，不被误当作完整工作流候选包。
