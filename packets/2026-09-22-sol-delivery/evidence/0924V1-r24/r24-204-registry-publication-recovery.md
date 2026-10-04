# R204｜登记—论文反向扩展与原始字节复核

2026-10-04 CST。W07 当前资料候选；不是采用、完整竞品闭包、正文齐备或 RC。
唯一工程、固定 HEAD 与脏树保护继续不变。owner 内联负责共用来源身份；R199/R202
模型各自冻结输入，不在途读取产物 QA。未新增框架、依赖、缓存数据库或角色。

## 实际结果与保留失败

- 现有生产登记连接器处理全部 1758 条研究：2256 个显式论文边，1812 个唯一 PMID；
  DERIVED 787、BACKGROUND 1265、RESULT 204。58 条没有 PMID 的引用完整保留待识别。
  平台 RESULT 不是医学“主要论文”裁决，背景引用不因数量大自动删除。
- 相比已核的 5993 条宽泛 PubMed 检索集合，1254 个显式关联编号没有进入检索结果。
  这是另一种恢复检索策略，不截取 Top-N，也不把无登记号的相关研究判为无关。
- 首次 200-ID 批实际 invalid_response/0 条；停止后续批。一次只读诊断确认同种
  4228 字节编码请求实际 HTTP 414，不是来源无数据或已解决的 429。旧失败回执
  `eadf82362cbec1564aee30ef8d5fef4a5419bdabae734ac2a6ad5c46c449736a` 原样保留。
  原私有脚本存入 CAS `5af89189ea4f3af118cbeb9a8626688db8f9b8e8948877f2cb1945e2421fb29d`。
- 最小调整为每批 50 个**精确编号**，保留全 1254 的请求集合：93394 exit0，26 批
  全部 complete、1254 请求/1254 返回/0 缺失。没有改生产解析器或自动重试规则。
- owner 离线重放每个新回执和 52 个原始页：原 SHA/size、ESearch 原编号、
  期刊/书籍原生节点身份、生产 typed metadata digest、逐批集合和全局并集全部核对。
  合并集合 7247，1812 个登记关联 PMID 均有元数据；58 个无编号引用仍未解决。
  核验 0 HTTP，不赋予新的核查日期，不覆盖原始回执，不切 current。

## 小型可恢复清单（路径相对唯一英文工程根）

| 实物 | SHA-256 | 用途 |
| --- | --- | --- |
| `.artifacts/r24-204-ad-registry-publication-edges-20261004/registry-publication-edges-v1.json` | `ad6bfe975f2f3c11dbe2f55b369fd8d5ceb877f245269957772f5a76faa1dd86` | 全部边、精确登记定位、源集合与未识别引用 |
| 同目录 `linked-pmid-recovery-v1.json` | 原失败文件保持原样 | 200-ID 首批失败和未执行集合，不记 PASS |
| 同目录 `linked-pmid-recovery-v2.json` | `baccb7c554069c5280b5e93ba4ddaa76a23a9e79f3a7364cc3561381fcca237e` | 26 个获取回执 CAS 指针、请求/未取集合 |
| 同目录 `verified-publication-union-v1.json` | `e358bb678d03d26a88bfc5379c2fa1da470693b12613971aa8ea0e2bdbea5753` | 原生节点定位、每记录 digest、7247 编号和未接受状态 |
| 同目录 `recover_linked_pmids.py` | `23fa3e9cbe88ffd4f78e149cf975541352e270c14a212fb4d1d60cf1a5005c14` | 当前精确请求脚本；已存在输出时在网络前拒绝覆盖 |
| 同目录 `verify_recovery.py` | `1810756cc3e49da0b14ff39521d435fff9bd7c5f07e54ed9be82d05899d37004` | 无网络可重放校验；另取新版本输出，不能覆写历史 |

源 CAS 在 `.artifacts/r24-200-ad-current-research-20261004/project/evidence/raw/sha256/`。
验证引用已核 203 清单 `4566cacdb7e07526c137af9a9e5fbaa4ab4bf217e28f931be1ba9f540d7130ef`；
生产解析器 `bb0e743be74b53674a935d0a62bffa0719882ca0a189f2fcba395c87877f94df`。
新恢复页集合 digest `aca0ae7ee59a55f42da44961a643f3aaee099d64d5cc6ef3a9ca83d359035705`。
实核命令：`uv run python .artifacts/r24-204-ad-registry-publication-edges-20261004/verify_recovery.py`
已 exit0；现有文件是保留结果，重复命令会在开头拒绝覆写，不是新的 FAIL。

## 下一步与明确未验

1. 按创新治疗宇宙、登记—论文关系与正文证据分类，不按 7247/2256 数量证明医学完整性。
   主论文/延长期/关键安全性逐论文复核；元数据不是全文、科学采用或来源授权。
2. R199 终态后核 DUBHE/CRSwNP 逐原文候选，再单一独立 source-first review。
3. R202 终态后核 C 正常生成入口：当前 base 模板未加载 `charts.js`，复制列表也缺该文件。
   共享 planner 的 VM PASS 不证明普通 C 页面可用。owner 接依赖/命名空间整族校验，
   不在途修改该 worker 冻结输入；必要时一次有界扩展 renderer/template 范围。
4. 原 R164 仅证明官方当前 Protocol/SAP 可得。是否同样允许当前官方/存储库论文
   原文的获取见证，已原生选择 Ask 待答；不擅自扩展、更不倒推历史截止日。
   Ego 空间、AD 药智、C 补充论文策略也待答，只阻断各自依赖项。
5. 新生产字节稳定后一次 milestone 门/新包。旧 81ad 包、1117 quality-only 门、
   宿主/分享切片不得继承给当前新字节。四档实屏、24 门户、三宿主全部模式及 RC 均开放。
