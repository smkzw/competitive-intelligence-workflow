# 独立会商备忘录：Round-2 交叉项裁决与根因分析

- **日期**：2026-09-21
- **会商角色**：独立会商者（与生产会话无共享上下文）
- **工作目录**：`/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`
- **输入证据**：
  - `runs/test-igan/findings.json`（grok-4.6/high）
  - `runs/test-uc/findings.json`（cursor/composer）
  - 当前代码：`policies/endpoint-families/registry-v7.yaml`（version **7.4**）、`src/ci_workflow/reports/b/registry_observation.py`、`tools/build_a_payload.py`、`src/ci_workflow/renderers/portal/report_a.py`、`src/ci_workflow/renderers/portal/assets/report-a.js`、`packets/2026-09-20-test-round-1/builders/build_pnh_{b,c}_audit.py`
  - 载荷真值：`packets/2026-09-20-test-round-2/{igan,uc}-a-payload.json`
- **复验方法**：对当前仓库直接 `classify_registry_endpoint` / `_native_endpoint_zh` / `load_report_a_data` 探针；对载荷行计数；不臆测。

## 假设

1. Round-2 载荷文件仍是当前复验真值；生产侧若另有未入库的重建产物，不在本会商范围。
2. 「已修复」= 当前代码下原失败探针不再复现，且对应载荷/渲染契约已对齐；仅版本号变化或旁路规则增补不算修复。
3. A 构建器以 `tools/build_a_payload.py` 为通用骨架，`tools/build_{igan,uc}_payload.py` 视为同族；裁决以通用路径 + 现存载荷为准。
4. 矩阵空态以 `report-a.js` 的 `renderMatrix` 准入条件为准（默认轴：疗效数值 × `any_teae` × `treatment_sample_size`）。
5. B/C「可移植」指：换适应症项目目录后，不改 PNH 硬编码即可产出可提交包；AD 同构 fork 证明可复制，不证明通用化已完成。

---

## 裁决表

| # | 交叉项 | 状态 | 证据（文件:行号 / 复验） | 根因层 |
|---|---|---|---|---|
| 1 | 分类器跨适应症误匹配（complement / 裸 remission / `\biga\b`） | **未修复** | 政策已升到 `registry-v7.yaml:3` version `7.4`，但 `endpoint-pnh-complement-inhibition-v1`（`171:173`）仍含 `complement\|…\|plasma concentration`；`endpoint-ad-iga-v1`（`192:193`）仍为 `\biga\b`；`endpoint-uc-remission-v1`（`373:374`）仍为 `clinical remission\|remission`。YAML **无** `indication_scope`/门闩字段。分类器是**首条命中、全局单列表**（`registry_observation.py:63-73`）。当前探针复现：Factor B/sC5b-9 → `complement_inhibition`；`Plasma Concentration of Atrasentan` → 同；`Sustained Remissions…` → `clinical_remission`；`IgA nephropathy proteinuria reduction` → `iga`。IgAN 全表仍：`complement_inhibition=57`、`clinical_remission=3`。7.3→7.4 仅新增 `endpoint-pnh-ldh-normalization-v2`（git `01d29d2`），未收紧上述三条。 | **政策**（规则排序与门闩缺失）+ **合同**（分类器契约是 indication-agnostic first-match，却把 per-indication 规则堆在同一平面） |
| 2 | TEAE 行混入疗效表（IgAN 44 / UC 16） | **未修复** | `is_safety_domain_endpoint` 能正确拒判（`registry_observation.py:57-69`；探针 TEAE/AEs → `None`）。但 A 构建器把 **全部** `outcomeMeasures` 写入 `efficacy_rows`（`tools/build_a_payload.py:415-474`），**未调用** safety_domain 守卫；AE 模块只另写 SAE/死亡汇总进 `safety_rows`（`475-510`）。当前载荷：IgAN `safety_domain_in_efficacy=44`（唯一标题 `Number of Subjects With TEAE and TEAESI`）；UC `=16`（`Number of Participants With Adverse Events (AEs)`）。分类器拒判与构建器入表脱节。 | **构建器**（域分流缺失）+ **合同**（安全域守卫只挂在分类器，未成为 A 载荷写入前置条件） |
| 3 | 矩阵气泡图空态（疗效×安全×样本量三轴） | **未修复** | `report-a.js:924-997`：默认 `any_teae`；`eventRate == null` 或（未切总样本时）`treatment_sample_size == null` 即丢点；空态文案与测试者一致。当前 IgAN/UC 载荷：`treatment_sample_size` **全部为 null**（构建器写死 `None`，`build_a_payload.py` 试验行）；安全表只有 `严重不良事件（登记）`/`死亡病例（登记）`，`term=…组别汇总计数`，`unit=例`（计数非发生率%）。`safetyTermKey` 无法把该类 term 映射到 `any_teae`/`any_sae`（得 `raw:严重不良事件组别汇总计数`）；`safetyRecordFor` 还要求 `category === "严重不良事件"` 与默认臂 `"治疗组"`（`report-a.js:263-278`），与载荷 `严重不良事件（登记）` + 登记原臂名不一致。IgAN 疗效单位以 `participants`/`ng/ml`/`ratio` 为主，亦缺乏稳定应答率轴。测试者 `steps_failed.matrix_chart` 现象在当前契约下仍必然成立。 | **合同/渲染器**（矩阵三轴假设与 A 构建器安全/臂/样本量投影不兼容）+ **构建器**（不产 TEAE%、不产 treatment_sample_size、category/term 命名偏离矩阵受控词表） |
| 4 | B/C 构建器不可跨适应症移植（PNH 硬编码） | **未修复** | `build_pnh_b_audit.py` / `build_pnh_c_audit.py` 仍绑定 `pnh-a-payload.json`、`ctgov-pnh-page-*`、`indication=阵发性睡眠性血红蛋白尿症`、`severity_anchor_concepts`（LDH/hemoglobin/pnh_clone 等）。AD 仅有同构 fork（`runs/test-ad/builders/build_ad_{b,c}_audit.py`），仍残留 `pnh-a-payload` fallback。`runs/test-igan/builders`、`runs/test-uc/builders` **不存在**。测试者实跑 PNH B 构建器 → PNH CAS sha256 `FileNotFoundError` 的失败模式未消除。 | **架构/构建器**（适应症垂直脚本，非参数化流水线） |
| 5 | A 渲染器 `_native_endpoint_zh` 肾脏/消化科标签 | **部分修复** | `report_a.py:768-808` 已补肾脏（UPCR/UACR/eGFR/蛋白尿/血尿/血肌酐等）与消化科（内镜/组织学/Mayo/IBDQ/钙卫蛋白/临床缓解等）规则；git `d964b7c` 起可见。当前探针：UPCR→`尿蛋白/肌酐比值（UPCR）疗效评价`，eGFR/血尿/血肌酐/内镜改善/临床缓解/钙卫蛋白均有中文身份。但 IgAN 显示层仍有 **67+50** 行落入「其他临床疗效指标…」；TEAE 被标成「其他临床疗效指标疗效评价」；`药物浓度浓度` 存在形式叠词。原「只有 AD/EASI 规则、肾脏全军覆没」已不成立，但「显示层稳定、无占位淹没」未达成。 | **渲染器**（启发式词典扩展，非政策驱动的族→标签投影） |

---

## 根因分析

### 1. 分类器跨适应症误匹配

表面症状是「IgAN 补体/PK 被标成 PNH 补体抑制」「肾脏 remission 被标成 UC 缓解」「`IgA` 被皮炎 IGA 吃掉」。真正问题在政策架构：`registry-v7.yaml` 把 PNH/AD/IgAN/UC 规则线性拼进同一 `rules[]`，`classify_registry_endpoint` 只做 safety 拒判后的**全局首条正则命中**（`registry_observation.py:63-73`），没有任何 `indication_id` 门闩或优先级作用域。PNH 的 `complement|plasma concentration` 与 UC 的裸 `remission` 天生过宽，又排在后置的 IgAN 专用族之前（或作为后置宽规则误伤他适应症）。描述写「per-indication 配置块」，实现却是 flat list——合同语义与执行模型不一致。v7.4 只加了 PNH LDH 正常化规则，没有修复门闩，因此「升版本」不等于「修误匹配」。

### 2. TEAE 混入疗效表

分类器层的 `safety_domain_pattern` 工作正常，测试者看到的 `SAFETY_REJECT` 正是这一层。但 A 载荷构建把 CT.gov `outcomeMeasuresModule` 的**所有**可解析数值测量无差别写入 `efficacy`（`build_a_payload.py:415-474`），安全域只从 `adverseEventsModule` 抽 SAE/死亡汇总。结果是：同一 TEAE 标题在分类时被拒、在门户疗效表里仍占据数十行。根因是**域分流守卫挂错层**——合同把「AE 不入疗效域」写在分类器注释里（`registry_observation.py:1-5`），却未成为构建器写入前置条件，也未成为 A schema 校验。渲染器随后把这些行当疗效终点做中文收敛，进一步污染疗效页。

### 3. 矩阵气泡图空态

矩阵不是「偶发无数据」，而是**三套契约互相不认账**。（a）构建器：`treatment_sample_size=None`；安全行为计数 `例` + category `…（登记）` + term `…组别汇总计数`；臂名为登记原名。（b）JS 矩阵：默认找 `any_teae` 百分比发生率；`safetyTermKey`/`category` 精确匹配受控词表；默认臂 `"治疗组"`；且依赖 `treatment_sample_size`（`report-a.js:932-973`）。（c）疗效侧：IgAN 以连续变量/参与者计数为主，缺少稳定「应答率%」锚点。任一轴失败即 `points=[]` 并显示测试者记录的空态文案。修筛选 UI 或改默认终点都治不好；必须先统一「矩阵可渲染安全事实」的投影合同（发生率%、受控 term_key、臂角色、样本量字段）。

### 4. B/C 构建器不可移植

B/C 审计包是从 PNH 垂直样例长出来的脚本：输入文件名、CAS blob、source_id、CT.gov query、indication 文案、severity 锚点概念、role/rule set id 全部硬编码。AD 复制粘贴改锚点证明「骨架可复用」，也证明当前交付物仍是**适应症 fork**，不是「indication 配置 + 通用构建器」。IgAN/UC 测试目录甚至没有 builders。根因在架构选择：把适应症知识写进 Python 脚本常量，而不是写进可替换的 indication profile / 政策包。所以换第 N 个适应症的成本 ≈ 再 fork 一份千行脚本，而不是改 YAML。

### 5. `_native_endpoint_zh` 肾脏/消化科标签

生产侧已在渲染器内堆叠肾脏/消化科正则（`report_a.py:768-808`），核心探针可出中文身份，故不能再裁「完全未修」。但该函数仍是**与分类政策平行的第二套启发式**：不读取 `family_meta.label_zh`，对未覆盖短语回落「其他临床疗效指标」，并对安全域串台行继续当疗效翻译。根因是呈现层自己维护医学词典，而非「分类族 → 展示标签」的单一事实源；词典扩一条适应症就加一批正则，第 4 适应症还会再分叉。

---

## 泛化风险清单（第 4 适应症：特发性肺纤维化 IPF 推演）

若下一适应症为 IPF（典型终点：FVC/%pred、DLCO、6MWD、急性加重、PFS、SGRQ 等）：

1. **分类器**：当前探针 `Forced Vital Capacity (FVC)…` → `generic_unclassified`。若临时把 FVC/肺活量规则插入全局列表，可能与既有宽规则（`survival`、`plasma concentration`、裸 `remission`/`response`）互相误伤；`\biga\b` 对含 IgA 的合并症描述仍是潜伏坑。**风险：每加一适应症，误匹配组合爆炸。**
2. **安全域入疗效表**：IPF 登记同样常把 TEAE/AE 放在 outcomeMeasures。若构建器不前置过滤，疗效表会再次混入安全行；分类器「拒判」只造成统计上的 unmatched，不阻止门户展示。
3. **矩阵空态**：IPF 若仍只有 SAE 计数、`treatment_sample_size=None`、臂名为登记原名，矩阵在默认 TEAE% 轴下会继续永久空态——与适应症无关的结构性失败。
4. **B/C 构建器**：需要再 fork `build_ipf_{b,c}_audit.py`，重写 severity 锚点（FVC/6MWD 等）、CAS、source_id、indication 文案；PNH/AD 经验不能零代码复用。维护面随适应症线性（或超线性）增长。
5. **`_native_endpoint_zh`**：需再堆 FVC/DLCO/6MWD/急性加重等正则；在补全前，IPF 门户会大量「其他临床疗效指标」。若先补词典、后补分类族，会出现「显示中文好看、族身份仍 generic」的双轨漂移。
6. **政策版本幻觉**：仅 bump `7.4→7.5` 并追加 IPF 规则块，若无门闩，会被测试者误判为「已泛化」；复验仍会看到跨适应症误匹配。
7. **别名/宇宙污染**：IgAN 已暴露关键词假阳性；IPF 的 fibrosis/ILD 检索同样可能卷入非目标试验，加重空矩阵与错误产品宇宙。

---

## 修复排期建议

排序原则：**阻断复核收敛 > 事实正确性 > 泛化能力 > 呈现质量**。工作量：S≤1 日，M≈2–4 日，L≥1 周。

| 优先级 | 项 | 建议动作 | 规模 | 阻断价值 |
|---|---|---|---|---|
| P0 | **#2 TEAE 域分流** | 在 A 构建器写入 `efficacy_rows` 前调用 `is_safety_domain_endpoint`；命中则改入 `safety`（或丢弃并记 derivation）；schema/测试锁定「efficacy 不含 safety_domain」。同步修正显示层勿把 AE 当疗效翻译。 | **S–M** | 立刻清理疗效表污染，恢复复核可信的行集合 |
| P0 | **#1 分类器门闩** | 政策增加 `indication_scope`（或 per-indication rule files + 运行时只加载当前适应症 ∪ shared）；收紧 `complement`（去掉裸 `plasma concentration`）、裸 `remission`、`\biga\b`（改为 IGA/vIGA/investigator global…）；补 albuminuria/UACR/haematuria；UACR 优先于 creatinine 泛化肾功规则。回归探针集（IgAN/UC/AD/PNH/IPF 互测）。 | **M** | 阻断错误族身份进入 B 观察与比较 |
| P0 | **#3 矩阵契约对齐** | 先定合同：矩阵点所需字段（疗效锚点单位、安全 `term_key`∈{any_teae,any_sae,…}、发生率%或显式允许计数轴、`treatment_sample_size` 或总样本默认策略、臂角色映射）。构建器产齐；JS 按合同放宽精确字符串匹配。无完整三轴时显示「缺哪一轴」而非笼统空态。 | **M–L** | 解除「永远空图」对验收的硬阻断 |
| P1 | **#4 B/C 参数化** | 抽取 `IndicationProfile`（payload 路径、CAS、source_id 模板、query、severity 锚点、role/rule set）；PNH/AD 迁入配置；IgAN/UC 只加 profile。禁止新适应症再复制千行脚本。 | **L** | 泛化能力；不修则第 4 适应症无法进入 B/C 验收 |
| P2 | **#5 展示标签单源化** | `_native_endpoint_zh` 优先消费 `family_meta.label_zh` + form；词典仅作未分类回退；消灭「药物浓度浓度」叠词；降低「其他临床疗效指标」占比作为适应症验收门槛。 | **M** | 呈现质量；在 P0 事实层稳定后做，避免粉饰错误行 |
| P2 | **IPF 预留** | 在门闩落地后，用独立 `endpoint-ipf-*.yaml`（或 scoped block）加 FVC/6MWD 等；禁止先改全局宽规则。 | **M** | 第 4 适应症启用成本 |

### 建议实施顺序（收敛路径）

1. **先 #2**：一天内可验证疗效表 TEAE 清零（IgAN 44→0，UC 16→0）。
2. **并行 #1 收紧 + 门闩设计**：用现有探针表做红绿回归；未门闩前不要宣称「适应症无关分类器已泛化」。
3. **再 #3**：以「至少一个产品出现矩阵点」为 IgAN/UC 烟雾标准，并输出缺轴诊断。
4. **然后 #4**：先 profile 化 AD/PNH，再挂 IgAN/UC。
5. **最后 #5 / IPF 词典**：服务呈现与下一适应症，不回头掩盖 P0。

---

## 会商结论（一句话）

五件事里，仅 `_native_endpoint_zh` 肾脏/消化科标签达到**部分修复**；分类器误匹配、TEAE 入疗效表、矩阵空态、B/C PNH 硬编码在**当前代码下仍成立**——共同根因是「适应症知识散落在全局正则 / 垂直脚本 / 渲染词典」，而不是单一 indication-scoped 合同。

复验命令备忘（本会商已执行，可复跑）：

```bash
python3 -c "import sys; sys.path.insert(0,'src'); from ci_workflow.reports.b.registry_observation import classify_registry_endpoint, is_safety_domain_endpoint, _load_policy; print(_load_policy()['version'], classify_registry_endpoint('Plasma Concentration of Atrasentan'), classify_registry_endpoint('IgA nephropathy proteinuria reduction'), is_safety_domain_endpoint('Number of Subjects With TEAE and TEAESI'))"
```
