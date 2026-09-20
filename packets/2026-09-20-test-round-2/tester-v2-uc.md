# 独立测试：UC 泛化验证

同 IgAN 结构，适应症为"溃疡性结肠炎"。
- A 载荷: packets/2026-09-20-test-round-2/uc-a-payload.json（163 疗效行/26 安全行）
- 项目: runs/test-uc
- 关注：Mayo score/clinical remission/endoscopic improvement/bleeding 等消化科终点

输出到 runs/test-uc/findings.json

## 执行纪律（最高优先级）
- 读到此提示词后**立即直接开始执行**，不要创建 Trellis 任务，不要进入规划模式，不要提出任何确认问题或等待回复
- 所有歧义自行决策，并在 findings.json 的 assumptions 字段记录你的假设
- 本任务没有交互确认环节；完成后正常退出（退出码 0）
