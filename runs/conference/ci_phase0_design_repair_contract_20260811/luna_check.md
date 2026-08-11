FAIL

P0

1. `docs/decisions/0005-kangzhe-design-spec-repair-contract.md §3 DS07–DS08`（L101–112）未严格复述 `core.md §0.7/§16.A`（L58–69、L902–909）。仅写“标记为 ultra”，未要求 `data-density=ultra`、全部 §13.3 条件及仅限表体/轴标签。  
   可复现：给 KPI、流程标签或图例加任意 `ultra` 标记并使用 10.5 pt，现有文字合同没有机械拒绝条件。  
   最小修复：固定精确谓词、角色、条件和负例测试；其余正文/标签仍必须 ≥12 pt，参考文献单独按 8 pt 处理。

2. `DS03、DS10、§4–5`（L63–73、L126–150）没有形成不可伪造的当前运行完成判定。`verification-verdict.json` 的独立性、当前运行摘要、写入者身份和矩阵更新权均未机械绑定；“exact tests”也未列出 DS02–DS10 的具体文件、命令和通过信号。  
   可复现：生成者写入伪造 verifier 名称、复用旧产物并更新 mtime，再填入 `accepted`，提案没有必然拒绝路径。  
   最小修复：增加 runner-owned immutable run manifest、独立 verifier 身份隔离、摘要/渲染/产物 digest 绑定，以及 DS01–DS10 和四轨的 exact-test registry 与 self-sign/reused-artifact 负例。

P1

3. `DS02、DS04`（L53–82）对 `source-pack.json` 只规定“至少包含”字段，没有机器 schema、数字 token 分类、来源定位、单位/分母和互斥规则。  
   可复现：把兄弟 fixture 的业务数字加入宽泛允许表，或把业务数字归入页码/日期/章节号，现有文字断言无法证明其来源。  
   最小修复：分别定义 `audience_fact`、页码、日期、章节号和品牌常量的 typed allowlist；要求稳定 ID、source locator、语义角色、单位/分母，禁止重叠归类并加入负例。

4. `DS04、DS07`（L79–103）要求讲稿数字通过 DS04，但 HTML 提取范围仅是受众可见文本，没有定义对隐藏的 `aside.notes` 单独提取和跨页比对。  
   可复现：页面显示 `5/9`、讲稿写 `6/9`，验证器按已定义范围可漏检。  
   最小修复：将 notes 作为独立受控文本层提取，绑定 slide/claim ID，并与页面、图、表共同重算。

5. `DS01`（L42–51）声称检查 compat stubs，却只明确读取 README、ROUTER、ARCHITECTURE、local_map 四个文件；根目录两个 stub 不在读取集合中。  
   可复现：任一 stub 恢复第二份 MUST/NEVER 正文，该测试仍可能通过。  
   最小修复：测试同时读取两个 stub，验证其内容、相对链接、无第二正文，并加入 stub 含正文的失败 fixture。

6. `§4 DS2 矩阵`（L128–137）及 `§5`（L139–150）未明确保留 ADR 0004 的原生 PDF 和 PPT Master 必经边界。  
   可复现：任意直接生成的可编辑 PPTX 只要通过 DS08 的 OOXML、渲染和视觉检查即可被 S2 接受；原生 PDF 没有对应轨道验收。  
   最小修复：明确 S2 只修复/验收 design package；产品后续仍必须走门户、原生 PDF、HTML-PPT 固定运行时和 PPT Master source/receipt/finalize 流程，并把直接 PPTX、截图替代和非原生 PDF列为负例。