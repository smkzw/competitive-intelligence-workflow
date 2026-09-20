# 独立端到端测试：AD（特应性皮炎）

同 PNH 测试结构，但适应症为"特应性皮炎"。
- CT.gov 查询: query.cond=atopic+dermatitis&filter.overallStatus=COMPLETED
- 原始数据已在 packets/2026-09-18-omp-visual/ad-raw/（两页各20研究）
- 别名表种子: packets/2026-09-18-ad-vertical/ad-alias-map-v1.json
- 项目根: runs/test-ad

### 额外注意
- AD 的终点族（EASI/IGA/PP-NRS/BSA/DLQI/POEM/WPAI）已在分类器政策中定义
- 你需要验证这些终点是否被正确识别和分组
- 特别检查：非药物干预（润肤剂/vehicle）是否被正确排除或标注
