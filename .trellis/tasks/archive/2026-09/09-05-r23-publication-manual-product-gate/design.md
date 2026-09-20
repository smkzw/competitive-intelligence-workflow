# 设计 — R2.3 Publication 与人工补件产品门

## 当前判断

`publication_gate.py` 已有分类与快照级单次响应合同，`manual_inbox.py` 已有内容匹配、
隔离、原地重命名和重抽取状态机，但二者尚未被证明由 `research submit` 和
`run_project` 作为同一产品门消费。R2.3 的工作重点是收敛为一个权威状态机，而不是
重写成熟的文件操作能力。

## 最小架构

1. 扩展严格 ResearchPackage：登记—publication 关系、规则/模型/独立 verdict、自动
   获取尝试和缺失请求均有类型化字节绑定。
2. 提交期验证分类、来源角色、项目/截止日/来源政策与报告适用性；必需论文的未解决
   状态不得进入普通报告门。
3. 运行期在 universe 后、报告 gate 前执行共享 publication/manual 节点；无缺口直接
   通过，有关键缺口则原子发布唯一 Markdown gate 并返回 `awaiting_user`。
4. 用户补件只由 ManualInboxService 核验与原地重命名；接受回执驱动重抽取和受影响
   报告恢复。无法取得的单次终态依据官方证据充分性分流。
5. 同节点+同输入摘要幂等；任何文件、verdict、请求或来源摘要漂移拒绝恢复。

## P1 迁移裁决

- 正式 publication verdict 与自动获取尝试进入 domain/research-package 合同；PubMed
  `PublicationRole` 只作为模型/规则分类信号，不再构成第二产品权威。
- `ManualSupplyGate` 是每快照唯一用户中断真源；`DownloadRequest` 是 gate 下逐文件
  操作状态，不单独生成多份用户 gate。
- `run_service` 负责 gate 发布、受影响报告暂停、恢复与多报告聚合；文件核验和改名
  只调用 `ManualInboxService`，不在运行服务重写。
- 错误、不可读或歧义文件继续移入项目内 content-addressed quarantine，避免下一次
  扫描重复误收；已接受文件严格在原收件目录原地规范重命名且保持 inode/字节。
- publication 自审在 publication verdict/ResearchPackage 层直接失败关闭，不能借用
  universe review 或最终 scientific review 代替。

## 失败语义

技术失败保持 recoverable；用户尚未响应保持 awaiting_user；用户确认不可得且官方
证据足够为 limited；核心不足为 evidence_blocked。不得把四类状态合并成“无数据”。
