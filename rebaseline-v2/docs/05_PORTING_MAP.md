# 05 · v1 → v2 移植地图

> v1 路径以 main 为准；定位用 `git ls-files | rg <关键词>`。**只移植知识，不移植结构**。

| v1 | v2 | 方式 | 里程碑 |
|---|---|---|---|
| `policies/endpoint-families/registry-v7.yaml` | `src/ciw2/domain/endpoints.yaml` + `endpoints.py` | 精简为 终点族键 → 同义表达/时间点要求 | M4 |
| `policies/endpoints/*`、`policies/timepoints/*` | `domain/semantics.py` 规则 + 测试 | 只保留可测试的硬规则 | M1/M4 |
| `policies/studies/study-role-v1*` | `skills/coverage-review` 正文 + 试验角色字段 | 规则写进 Skill 与 `entities.attrs.role` | M1 |
| `policies/ontology/innovation-therapy-v1*` | `DrugCandidate.innovative` 判定说明 | 写进 universe-* Skill | M2 |
| `policies/sources/source-policy-v1*` | `docs/02_ARCHITECTURE.md` 信任模型 + 来源可信度表 | 文档 + `sources.meta.trust` | M5 |
| `policies/recovery/source-strategies-v1*` | `skills/universe-*` 路线表 + `china.py` 退回策略 | 路线即代码/Skill | M2 |
| `connectors/clinicaltrials_gov.py`、`ctgov_fetch.py` | `sources/ctgov.py` | 已重写（v2 JSON API） | M0 ✓ |
| `connectors/pubmed*.py` | `sources/pubmed.py` | 已重写 | M0 ✓ |
| `connectors/china_registries.py`（CDE/NMPA/chinadrugtrials 模型） | `sources/china.py` | 只核验字段知识；中国登记列表接现有Ego公开UI，详情/CDE/NMPA待验，不新增浏览器框架 | M2 |
| `connectors/regulators.py` | `sources/openfda.py` + M5 EMA/PMDA | FDA 已重写 | M0 ✓ / M5 |
| `connectors/authoritative_wechat.py` | `sources/wechat.py` + 权威账号白名单 | 白名单作为 `sources.meta.trust` | M2 |
| `contracts/kangzhe/v6-site/tokens/tokens.json`、portal.css | `render/static/kangzhe.css` | 已移植 tokens | M0 ✓ |
| `renderers/portal/assets/echarts.min.js` | `scripts/fetch_assets.sh` 复制/下载 | 不入库 | M0 ✓ |
| `REVIEW.md` F01–F11 | `tests/regressions/` | 每条一个最小用例 | M4 |
| `renderers/report_a.py` `report_b.py` | — | 不移植（含项目硬编码）；只参考版式 | — |
| `renderers/pdf_native` `pptx_master` `html_ppt` | — | 不移植；v1历史只读保留 | — |
| `application/run_service.py` | `pipeline/*` | 不移植 | — |
| `runs/ output/ packets/ prompts/ reviews/` | — | 不移植；本表不授权清理旧工程或历史证据 | — |
