# 独立端到端测试：IgA 肾病 (IgAN)

## 你的身份
你是独立测试者，从零开始使用竞品调研工作流完成端到端报告产出。你不是开发者——以用户视角测试。

## 环境
- 仓库: /Users/smkzw/Documents/AI Products/competitive-intelligence-workflow
- CLI: `.venv/bin/python -m ci_workflow`
- CT.gov 数据已在 packets/2026-09-20-test-round-2/igan-page-1.json
- 你有完整 shell 权限，可用所有 tools/skills

## 适应症
IgA 肾病 (IgA Nephropathy) — 肾脏/免疫学领域。核心终点包括：蛋白尿（UPCR/UPCR）、eGFR、血尿、肾功能 decline。药物包括布地奈德（Nefecon）、sparsentan、iptacopan 等。

## 任务
1. 创建项目 `runs/test-igan`
2. 从 igan-page-1.json 提取实体和结果
3. 参考 `tools/build_a_payload.py` 构建载荷（参数化：--cas-dir --alias-map --indication）
4. 需要创建 IgAN 别名映射表（参考 pnh-alias-map-v1.json 格式）
5. 参考 `build_pnh_b_audit.py` / `build_pnh_c_audit.py` 构建 B/C
6. 构建 audit envelope 并 submit
7. `project run --resume` 渲染 A/B/C
8. 视觉验证（playwright 打开 HTML，检查图表/表格/筛选）
9. 记录所有发现到 `runs/test-igan/findings.json`

## 专项验证项
- S1: A 矩阵是否有数据点（不再空态）
- S2: B 是否有剔除行披露（b-dropped-disclosure.json）
- 跨适应症泛化：肾脏终点（蛋白尿/eGFR）是否被分类器正确识别
