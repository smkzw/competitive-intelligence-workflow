# 独立端到端测试：PNH（阵发性睡眠性血红蛋白尿症）

## 你的身份
你是独立测试者，从零开始使用竞品调研工作流完成端到端报告产出。你不是开发者——你以用户视角测试系统。

## 环境
- 仓库: /Users/smkzw/Documents/AI Products/competitive-intelligence-workflow
- CLI: `.venv/bin/python -m ci_workflow`
- 你有完整的 shell 执行权限
- CT.gov API: https://clinicaltrials.gov/api/v2/studies

## 任务
对适应症"阵发性睡眠性血红蛋白尿症"(PNH) 完成从数据获取到 A/B/C HTML 门户渲染的全流程。

### 步骤
1. **创建项目**：`project create --root runs/test-pnh --indication "阵发性睡眠性血红蛋白尿症" --reports A,B,C`
2. **能力预检**：`capability preflight --host local --project runs/test-pnh --independent-context yes`
3. **获取数据**：从 CT.gov API v2 抓取 PNH 试验数据（COMPLETED 过滤，pageSize=20，pageToken 翻页）
4. **入库 CAS**：sha256 寻址存储原始 JSON
5. **构建载荷**：使用 `tools/build_a_payload.py` 参数化构建 A 载荷
6. **构建 B/C 载荷**：参考 `packets/2026-09-11-pnh-vertical/build_pnh_b_audit.py` 和 `build_pnh_c_audit.py`
7. **构建审计信封**：参考 `build_pnh_audit.py`
8. **提交**：`research submit`
9. **渲染**：`project run --resume`
10. **视觉验证**：用 playwright 打开 HTML，检查图表、表格、筛选、下钻
11. **记录发现**：所有问题写入 `runs/test-pnh/findings.json`

### 记录格式
```json
{
  "tester": "你的节点标识",
  "indication": "PNH",
  "steps_completed": ["step1", "step2", ...],
  "steps_failed": [{"step": "...", "error": "..."}],
  "findings": [
    {"category": "科学正确性|中文原生|视觉|交互|数据完整性",
     "severity": "blocking|major|minor",
     "description": "...",
     "evidence": "页面/截图/数据引用"}
  ],
  "overall": "pass|fail|partial"
}
```

### 注意
- 不使用 runs/ 下任何已有项目（清洁环境）
- 每步如实报告，不修饰
- 发现问题只记录不修复
- 如果你无法完成某步，记录失败原因并继续下一步
