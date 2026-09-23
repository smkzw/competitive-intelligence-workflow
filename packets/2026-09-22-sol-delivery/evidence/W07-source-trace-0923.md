# W07 真实来源链只读追踪（2026-09-23，开发证据）

判定：**未闭合**。本记录不是科学复核、全量验收或已修复回执。只操作英文工程；旧中文工程零接触。只读原生子任务提供了八组 PNH 实例，主线程独立复核了下述计数、代码断点和两个 CAS 文件哈希；其余逐个 JSONPath 尚待生产链重放，不能把子任务结论直接当正式验收。

## 三个不同分母，不得混用

- W05A v6 实际 `data/report.js` SHA-256 `e4e8c181e56fc6e9c8fbdf511226561c877279813b5ad0532d766becd979a695`：疗效 3895 + 安全 517 = **4412**；逐事实 `source_field_path` 与 `source_text` 同时/任一具备均为 **0/4412**。这是当前受审展示载荷，不自动等同于数据库或另一份中间包。
- `runs/test-pnh/evidence/library/a-portal-payload.json` SHA-256 `da36a48bb49c8afdd683290dc76a3eb00f14c4de6d119a8c3a00420cfbaa8eed`：疗效 4141 + 安全 136 = **4277**（本轮 `jq` 重算）。
- 同目录 `a-research-package.json` SHA-256 `3d9c091f1a119594b65ca9aebe2b14c9456ac9dc7d930b62ee8d64dfbc30fdec`：**4458 facts**（本轮 `jq` 重算）；其中还含非疗效/安全事实。

## 存储与断点

本轮只读 SQL 重算 `runs/test-pnh/state/project.sqlite`：`content_blobs=10`、`source_versions=10`、`evidence_fragments=10`、`source_text_derivations=0`、`fact_versions=4759`、`fact_evidence=4759`。两个按研究切片的 CAS 文件已按字节重算，SHA-256 与文件名相同：`57/5745725fe69c03ee4a145888c2f9137df00be2ffef2c17f7638b1fb491695ecd.bin`、`8c/8c7cc7ac11529a753e40705ce711e574b774eb00e239316a84bbc6b1bfed7345.bin`（均位于 `runs/test-pnh/evidence/raw/sha256/`）。

历史包装器 `packets/2026-09-11-pnh-vertical/build_pnh_audit.py` 仍使用 `studies[]` 粗定位，并把“某行的登记结果事实”构造为 `original_text`；这是占位文本，不是原始来源引文。`tools/build_a_payload.py` 未把逐事实精确路径/原文携带到最终 A 行。当前 `source_research_service.py` 可抽取结局/AE的部分精确路径，但尚无死亡汇总字段；旧 A 构建器虽读取死亡汇总，却不满足新精确摄取合同。`storage/source_derivation.py` 已有拒绝通配符、从 CAS 重提取原值的能力；`application/fresh_research_ingestion.py` 已要求事实原文等于重提取结果。主要断点是旧 PNH 构建路线绕过这条新合同，而非 CAS 全部遗失。

只读样本显示：多组、多期、真实零值、复合安全类别、LDH 多时间点的数值在 CAS 中有可追踪候选；某些分母在对应终点对象中确实缺失或跨对象来源未证实；另有 `hasResults:false` 的研究本身无结果。**不能**因为数值可找到就自动补分母、编造来源或把真实零值当缺失。尚未验证八组全部 JSONPath、组别/时间窗语义和版本绑定，也没有发现可证实的这批真实记录解析失败；“未发现”不等于全量不存在。

## 下一最小实施批

1. 选上述多组/多期/零值/缺失/多终点/复合安全小批真实 CAS；重放 `SourceCapture`，将按研究切片的来源版本和 `source_text_derivations` 持久化，禁止再用页级 `studies[]` 当事实定位。
2. 每条采用事实绑定研究、终点/事件、组、类别、时间窗、稳定身份、精确无通配符路径、重提取原文；数值/分母分别证明，派生值必须携带输入事实与公式。
3. 用真实小批在快照和 A 页面核对逐事实入口，分类记录 `source_missing`、`parse_failure`、`source_unmapped`；然后才选择唯一新的 A 载荷哈希，重新计算全量闭合分母并扩展 B/C。W05B/C 的桌面结构可以并行，不因来源暂缺而虚报终验或暂停开发。

当前请求的子任务模型/effort只有请求参数，没有独立运行时回执，身份记 **UNVERIFIED**；该报告是只读诊断，不是用户所禁止的执行/会商机制。
