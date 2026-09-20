# 设计 — R2.2 竞品宇宙闭包运行态

## 当前判断

`ontology_universe.py` 已有创新治疗纳排、本体边界和粗粒度
`UniverseClosureReceipt`；`ResearchPackage.assert_gate_ready()` 也已有部分恢复/饱和
约束。但现有闭包主要以字符串 receipt ID 表示四类扩展，缺少逐尝试结果、实体集合、
来源/输入绑定和项目快照身份，且尚未证明产品运行真正以该闭包作为唯一上游门。

## 最小重构

1. 定义 `UniverseSearchAttempt`：route/dimension、strategy、query/input digest、状态、
   source IDs、discovered entity IDs、诊断和时间；使用封闭枚举区分失败与真实零发现。
2. 定义 `UniverseEntityDisposition`：规范实体 ID、原始名称/别名、纳排状态、本体规则、
   证据片段与可选独立边界审查绑定。
3. 将 closure receipt 绑定 project/contract/data cutoff/source-policy、attempt 集和实体集
   摘要；从实际尝试推导路线、维度、收敛和闭包状态，不接受调用方自由声明。
4. 独立 closure verdict 绑定生产上下文摘要、候选 receipt 字节和 reviewer identity；
   运行服务仅消费经校验结果，不让 worker 自证。
5. product run 在 universe 边界持久化当前工作状态；失败/等待/恢复与 evidence blocker
   分开，closed 后才开放 gate/snapshot/render。

## 兼容与迁移

保留现有 v1.3 research-package fixture 的读取路径直到新 schema/test vectors 完成迁移，
但产品入口不得通过兼容字段绕过新闭包。避免建设通用图数据库、排名引擎或第二状态库。
