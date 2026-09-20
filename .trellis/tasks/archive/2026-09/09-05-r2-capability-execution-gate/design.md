# 设计 — R2 核心能力矩阵持久化与选择性执行门

## 数据流

`RunContext` 接收显式 probe/host → `selection_from_project` →
`run_capability_preflight` → 原子保存 `capabilities/preflight.json` → 把矩阵留在本次
上下文 → 研究/交付边界按报告读取 readiness → 写运行清单与中文状态。

## 关键决定

1. 复用既有 `CapabilityMatrix`，不建立第二状态模型或数据库表。
2. preflight 是易变宿主事实，每次 `run_project` 都执行；即使 `--resume` 且输入摘要
   未变，也不复用历史完成事件。
3. 标准项目回执路径沿用 CLI 已有的 `capabilities/preflight.json`。应用层提供唯一
   安全写入函数，CLI 默认路径与项目运行共用它。
4. `RunContext` 持有显式 `capability_probe`、`capability_host` 和本次矩阵。未注入时
   才构造真实探针；测试使用 `StaticCapabilityProbe`，不篡改生产环境。
5. 新增明确的 `capability_blocked` 运行结局和非零退出码。它只描述执行环境不足，
   不写科学证据不足状态，也不生成报告草稿。
6. 研究 readiness 在进入报告研究前检查；delivery readiness 在首次渲染/验收边界
   检查。若当前组合尚不能拆开研究与渲染，则保留已完成研究事实并在交付前停止，
   不把交付标为完成。
7. 原子写入拒绝目标、父目录或中间路径软链接；任何失败不得覆盖既有字节。

## 兼容与恢复

- 既有调用不传 probe 时获得真实生产行为；fixture、宿主 smoke 与单元测试必须显式
  注入可重放探针。
- 当前矩阵是可变运行回执，不属于不可变科学证据。历史运行仍由事件流和运行清单
  保留；恢复计划继续由前后两个矩阵计算。
- 可选药智登录能力没有 `required_by`，因此不参与研究/交付阻断或整链重排。

## 不做

不实现药智网站登录状态探测，不增加通用调度器，不改变证据门、报告视觉或发布状态。
