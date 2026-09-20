# 独立测试：IgAN 泛化验证

## 任务
你是独立测试者。测试竞品调研工作流对 IgA肾病（肾脏/免疫学领域）的泛化能力。

## 环境
- 仓库: /Users/smkzw/Documents/AI Products/competitive-intelligence-workflow
- 已有: A 载荷 packets/2026-09-20-test-round-2/igan-a-payload.json（260 疗效行/26 安全行）
- 项目: runs/test-igan（已创建，reports=A,B,C）
- 分类器: policies/endpoint-families/registry-v7.yaml（25 条规则）

## 你要做的
1. 检查 A 载荷质量：
   - 产品数、试验数、疗效/安全行数是否合理
   - 药物名是否正确（无 placebo/vehicle 混入产品列表）
   - 疗效终点文本是否包含肾脏学核心指标（蛋白尿/eGFR/血尿/肾功能）
2. 检查分类器泛化：
   - 从 A 载荷中取 10 条疗效行，检查其 endpoint 文本
   - 对照 registry-v7.yaml 中的规则，判断哪些会被正确分类、哪些会掉入 unclassified
   - 特别关注：蛋白尿(proteinuria/UPCR)、eGFR、血尿(hematuria) 是否有对应族
3. 尝试渲染 A 门户：
   - 使用 `src/ci_workflow/renderers/portal/report_a.py` 中的 `build_report_a_artifact` 函数
   - 或直接调用 CLI（如可行）
   - 用 playwright 打开 HTML 并截图
4. 尝试构建 B 载荷：
   - 参考 build_pnh_b_audit.py 的逻辑，判断哪些部分可直接复用
   - 记录哪些部分需要适应症特定修改
5. 将所有发现写入 findings.json

## 输出格式
```json
{
  "tester": "grok-4.6/high",
  "indication": "IgAN",
  "overall": "pass|fail|partial",
  "findings": [
    {"category": "...", "severity": "...", "description": "...", "evidence": "..."}
  ],
  "generalization_gaps": ["需要适应症特定代码的具体位置"],
  "classifier_coverage": {"matched": N, "unmatched": N, "sample_unmatched": ["..."]}
}
```
