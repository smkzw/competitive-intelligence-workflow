# 独立科学复核任务（报告 A · 项目 abc-v102 · PNH · 第 46 轮）

你是独立上下文复核者，与生产者无共享会话。基于自己对仓库文件的真实检查给出结论。

## 材料
1. `runs/pnh-vertical/abc-v102/state/scientific_review/A/review_request.json`（绑定字段）
2. `runs/pnh-vertical/abc-v102/reports/A/v1/html/`（已渲染门户）
3. `runs/pnh-vertical/abc-v102/evidence/library/{a,b,c}-research-package.json`（科学载荷）

## 本轮重点（round-6 veto 项修复验证）
- A r45 五项：①安全页组别列现显示解码名+（登记名：原文）括注；②类目/类标题经 measure_context 字段进入事件标签（NCT00867932 的 9 条类目行应可区分）；③复合指标 measure_label；④分母脚注措辞已与实际三态（分子/分母人、分母无法归属、未公开）对齐；⑤矩阵横轴单位与气泡溢出——本轮未动，如仍存在请按"数据正确但呈现待改"归类
- B r59 两项：①基线域影子行渲染总出口过滤——产品页/证据视图应无 -declared 行；②含中文的半翻译分面（如"至30天 末次给药后 研究 drug"）——纯英文标注已修，含中文残片本轮未动，如实归类
- C：上一轮 accepted；本轮快照更新，做一致性确认即可
- 通用：事实可溯源、中文原生、诚实边界

## 产出
写 `runs/pnh-vertical/abc-v102/state/scientific_review/A/verdict.json`（UTF-8 JSON）：
- schema_version "1.0"；criteria_version/project_id/contract_version/report_kind/report_version/report_object_id/candidate_snapshot_id/candidate_content_digest/gate_result_key/coverage_set_id/coverage_digest/source_refs/locators/review_input_digest — **逐字复制** review_request.json scientific_context 对应值
- verdict_id: "verdict-omp-deepseek-abc102-a-r46"；verdict: "accepted"|"veto"
- veto 必带 issues 数组（issue_id/severity/category/description_zh/source_version_id/fragment_ids 逐字复制）；accepted 不得带 issues
- reviewer_id: "omp-cms-router-deepseekflash-max"；reviewed_at 当前 UTC；valid_until +30 天

## 绑定字段速查（以 review_request.json 为准）
- `criteria_version`: `A_MATURITY_V1`
- `project_id`: `project_4f03a7a2853a252c359be588`
- `contract_version`: `1`
- `report_kind`: `A`
- `report_version`: `v1`
- `report_object_id`: `report_A`
- `candidate_snapshot_id`: `report-snapshot_e459fe6b1ecf2b527810589f`
- `candidate_content_digest`: `c70493bb45f0c76d4ff0ccb80b93dd37798a8661723be1bbc81f1bc4eb9bff61`
- `gate_result_key`: `gate-evaluation_b97b4453d6ebee53d764c21c`
- `coverage_set_id`: `coverage-set_70df5decc7e4615a1bbcb51e`
- `coverage_digest`: `39ba2e2d68dc53bb33f3b85dc2938a762c44424c3d10546e259717efb26bdafc`
- `review_input_digest`: `None`

## 执行纪律
立即执行，不提问不等待；完成后退出码 0。
