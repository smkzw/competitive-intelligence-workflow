# 独立测试第一轮派发

## 测试者与适应症分配

| 节点 | 适应症 | CT.gov 查询 |
|------|--------|-------------|
| grok build/grok-4.6(high) | 特应性皮炎 (AD) | query.cond=atopic+dermatitis |
| omp/cms-router/deepseek-flash(max) | 阵发性睡眠性血红蛋白尿症 (PNH) | query.cond=paroxysmal+nocturnal+hemoglobinuria |
| omp/google-antigravity/gemini-3.8-flash(high) | IgA 肾病 (IgAN) | query.cond=iga+nephropathy |
| omp/cursor/default(auto) | 溃疡性结肠炎 (UC) | query.cond=ulcerative+colitis |

## 测试者指令

你是独立测试者，从零开始使用竞品调研工作流完成端到端报告产出。

### 环境
- 仓库: /Users/smkzw/Documents/AI Products/competitive-intelligence-workflow
- CLI: `.venv/bin/python -m ci_workflow`
- Python: `.venv/bin/python`
- 你有完整的文件读写和 shell 执行权限

### 步骤
1. 创建测试项目（适应症见上表）：
   ```bash
   .venv/bin/python -m ci_workflow project create --root runs/test-{你的适应症缩写} --indication "{适应症中文名}" --reports A,B,C
   ```
2. 从 CT.gov API v2 抓取你适应症的试验数据（pageSize=20，翻页用 pageToken）：
   ```bash
   curl -s "https://clinicaltrials.gov/api/v2/studies?query.cond={英文疾病名}&pageSize=20" -o /tmp/{ind}-page-1.json
   ```
3. 入库 CAS（sha256 寻址）并构建 A 载荷：
   参考 `tools/build_a_payload.py` 的参数说明
4. 运行 `capability preflight` 和 `research submit`
5. 运行 `project run --resume` 生成 A/B/C HTML
6. 使用 ego lite 打开渲染的 HTML 文件，真实点击、筛选、查看
7. 记录所有发现（科学正确性、中文原生、视觉、交互、数据完整性）
8. 将发现写入 `runs/test-{ind}/findings.json`

### 注意
- 不使用旧的 runs/ 下的任何缓存或产物
- 每步如实报告成功/失败
- 发现问题不修复，只记录（修复由主控会话处理）
