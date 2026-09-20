# 独立端到端测试：UC（溃疡性结肠炎）

同 IgAN 结构，适应症为"溃疡性结肠炎"。
- CT.gov 数据: packets/2026-09-20-test-round-2/uc-page-1.json
- 项目根: runs/test-uc
- 核心终点: Mayo score, clinical remission, endoscopic improvement, bleeding
- 药物: infliximab, vedolizumab, ustekinumab, upadacitinib, etrasimod 等

### 专项验证项
- S1: A 矩阵数据点
- S2: B 剔除披露
- 泛化: 消化/自身免疫终点是否被正确识别
