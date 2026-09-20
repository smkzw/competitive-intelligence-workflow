Delegated mode（执行模块角色：独立宇宙遗漏审查节点 Reviewer-G）

# 硬边界

只读评审（read-only 沙箱）；不修改文件；唯一工作区 /Users/smkzw/Documents/AI Products/competitive-intelligence-workflow；禁止访问旧中文工程。你的结论将作为 PNH 首验 A 报告的独立科学复核依据（reviewer 身份独立于生产者 zcode-main-thread）。

# 任务：PNH 竞品宇宙独立遗漏审查

生产者（zcode-main-thread）从 CT.gov"paroxysmal nocturnal hemoglobinuria"当前记录查询（189 条，2 页，2026-09-06 获取，原始 CAS 在 .artifacts/source-cas/ctgov-live-20260906）派生了竞品宇宙：
- 109 个产品实体（干预去重，清单+试验/申办方数据见 packets/2026-09-11-pnh-vertical/pnh-a-payload.json 的 products/trials/companies）
- 派生脚本 packets/2026-09-11-pnh-vertical/build_pnh_a_payload.py
- 中国路线（CDE）执行器未部署，首验如实记 access_blocked；PubMed 真实获取 878 条记录（complete_with_attrition）

请独立审查（基于你的医学领域知识 + 可读取上述文件）：

Q1 **已知重大遗漏**：以你对该领域的了解，PNH 治疗领域是否有重要在研/已上市竞品（如已上市或后期阶段的补体抑制剂/其他机制）大概率不在"CT.gov 当前 189 条记录"覆盖内（例如仅在中国登记、已退出登记、或以不同适应症名登记）？列出你认为最可能遗漏的方向（不需要穷尽，列你有把握的）。
Q2 **派生质量**：抽查 pnh-a-payload.json 的 products/trials（读文件），干预→产品映射与状态/阶段聚合是否有明显错误方向（如安慰剂/显像剂被当产品、阶段取错）？
Q3 **结论**：在"当前首验=全球 CT.gov 单一真实来源 + 中国路线如实阻断"的范围内，该宇宙是否可作为 A 报告首验候选（accepted）？还是存在必须先补的遗漏（rejected + 必补清单）？

# 输出格式（严格）

## 结论：accepted / rejected
## 遗漏方向清单（若有）
## 派生质量问题（若有）
## 观察意见（将原样进入复核 observations 字段，中文，≤5 条）
