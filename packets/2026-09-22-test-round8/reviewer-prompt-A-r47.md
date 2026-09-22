# 独立科学复核任务（报告 A · 项目 abc-v104 · PNH · 第 47 轮）

你是独立上下文复核者，与生产者无共享会话。基于自己对仓库文件的真实检查给出结论。

## 材料
1. `runs/pnh-vertical/abc-v104/state/scientific_review/A/review_request.json`（绑定字段）
2. `runs/pnh-vertical/abc-v104/reports/A/v1/html/`（已渲染门户）
3. `runs/pnh-vertical/abc-v104/evidence/library/{a,b,c}-research-package.json`（科学载荷）

## 本轮重点（round-7 veto 项修复验证）
- A r46 五项：①类目上下文现经 measure_label 组合（"测量标题…｜类目标题"）；②分母措辞三态（分子/分母人、分母无法归属、分母未列示）+脚注对齐；③矩阵疗效轴上限数据驱动；④残留英文组名带"（登记原文，未译）"标注；⑤载荷内嵌复核声明悖论——生产者未动，等待裁决，不作为本轮 veto 依据
- B r60 两项：①影子行清洗改在门户数据入口（row_id/fact_id/source_row_id 三字段判定）——各页展开完整数据表应无重复事实；②含中文机器拼接分面带"（登记原文，未译）"标注
- C r44 三项：①统计兜底抑制扩展（试验有任一统计披露即抑制全部四个"未公开"兜底——NCT02605993 应不再矛盾）；②矩阵 SVG 文本压叠为"呈现待改"类（本轮未动）；③血清浓度终点"血清药物浓度评价"
- 通用：事实可溯源、中文原生、诚实边界

## 产出
写 `runs/pnh-vertical/abc-v104/state/scientific_review/A/verdict.json`（UTF-8 JSON）：
- schema_version "1.0"；criteria_version/project_id/contract_version/report_kind/report_version/report_object_id/candidate_snapshot_id/candidate_content_digest/gate_result_key/coverage_set_id/coverage_digest/source_refs/locators/review_input_digest — **逐字复制** review_request.json scientific_context 对应值
- verdict_id: "verdict-omp-deepseek-abc104-a-r47"；verdict: "accepted"|"veto"
- veto 必带 issues 数组（issue_id/severity/category/description_zh/source_version_id/fragment_ids 逐字复制）；accepted 不得带 issues
- reviewer_id: "omp-cms-router-deepseekflash-max"；reviewed_at 当前 UTC；valid_until +30 天

## 绑定字段速查（以 review_request.json 为准）
- `criteria_version`: `A_MATURITY_V1`
- `project_id`: `project_77aae8930816fd522571c67d`
- `contract_version`: `1`
- `report_kind`: `A`
- `report_version`: `v1`
- `report_object_id`: `report_A`
- `candidate_snapshot_id`: `report-snapshot_cd09b7fcc0a855de216bcf54`
- `candidate_content_digest`: `c70493bb45f0c76d4ff0ccb80b93dd37798a8661723be1bbc81f1bc4eb9bff61`
- `gate_result_key`: `gate-evaluation_ab9381457fdcc4bc9679b028`
- `coverage_set_id`: `coverage-set_13944ac36b5db55c41799f4e`
- `coverage_digest`: `949d85baebd23c9e0eb684cbe5aec16994292ec31f4c8e9d2eae6c897bed0675`
- `review_input_digest`: `None`

## 执行纪律
立即执行，不提问不等待；完成后退出码 0。
