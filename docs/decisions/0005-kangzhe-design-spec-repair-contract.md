# ADR 0005：内化康哲最新版设计合同

- 状态：已实施并通过独立合同验收；报告实产物验收按后续渲染阶段执行
- 日期：2026-08-11
- 项目运行权威：`contracts/kangzhe/design.md → design_specs/`
- 不改变：竞品调研 v1.2、四格式独立生成、PPT Master 必经路径和关键证据不足不生成草稿

## 1. 用户决定

用户明确要求：

> 康哲design.md请选取最新版，并内化为项目自己的design spec，后续不用同步改通用版design.md。

这项决定取代暂停前的二选一问题。本项目获权读取当时最新版，形成项目自有合同；没有获权修改通用模板目录，也不需要等待通用版继续修复。

## 2. 最新版判定

2026-08-11 本机模板目录中：

- `design.md`、`design_v2.md`、`design_share_v2.md`、`design_shareable.md` 均为相同的 829 字节入口 stub，SHA-256 均为 `e513b4c5...ed18`；
- 四个入口都明确指向同目录 `design_specs/`；
- 真正完整合同是 `design_specs/{ROUTER,core,track_*...}`，不是任一 stub；
- 对四个入口和整个 `design_specs/` 连续执行两次 path/hash/metadata 读取，两次快照相同，稳定快照摘要为 `82a81132...25b`。

因此“最新版 design.md”被解释为该稳定入口所指向的完整 `design_specs/` 集合，而不是复制 829 字节入口后声称设计合同已完成。

## 3. 内化架构

项目内新增：

```text
contracts/kangzhe/
├── design.md
├── manifest.json
└── design_specs/
    ├── ROUTER.md
    ├── core.md
    ├── project_profile.md
    ├── track_site.md
    ├── track_interactive.md
    ├── track_stream.md
    ├── track_pdf.md
    ├── track_htmlppt.md
    ├── track_pptx.md
    ├── README.md
    ├── ARCHITECTURE.md
    ├── local_map.md
    ├── assets/logo_bot.svg
    ├── schemas/
    │   ├── design-source-pack.schema.json
    │   ├── design-run-manifest.schema.json
    │   └── design-verdict.schema.json
    └── tests/test_package_load.py
```

运行时只读取项目内文件。`manifest.json` 同时保存来源稳定摘要和项目当前逐文件摘要；后续改动只更新项目副本与项目摘要，不读取、不自动吸收、不反向同步通用版。

## 4. 项目专属路线

| 交付物 | 读取路线 | 格式边界 |
|---|---|---|
| 门户 | `core + project_profile + site` | 多物理页面；筛选/联动/下钻属于站点页面责任，不继承单页驾驶舱或幻灯片画布 |
| 原生 PDF | `core + project_profile + stream + pdf` | 原生文字、矢量图、书签、续表；不拼网页截图 |
| HTML-PPT | `core + project_profile + htmlppt` | 固定 1280×720 与讲者运行时；不是门户/PPTX |
| PPTX | `core + project_profile + pptx` | 必经 PPT Master 串行来源包与原生导出 |

四条路线共享锁定报告快照与内容覆盖集合，但不共享最终页面代码，也不能相互冒充。

## 5. S1 反例转成项目合同

暂停前的 S1 候选暴露：零产物流式任务退出 0、HTML-PPT 缺讲者窗口和讲稿、5/9 与 6/9 跨页矛盾、PPTX 9 pt 和 KPI 重叠、来源外硬编码数字、生成者自签完成。项目内 `project_profile.md` 因此固定：

- 用户可见中文必须为临床试验语境的中文原生表达；程序状态、日志、提示词和后端字段不进入报告；
- 图在前、完整表格在后；疗效含试验组和安慰剂/对照组；安全性用分维度热图；综合矩阵用气泡图；
- B 类基线与试验完成情况、C 类具体试验设计要素下钻均为页面责任；
- 所有可见数字及讲者稿从同一事实集重算；
- 当前产物必须绑定不可变 run manifest、摘要、真实渲染和独立验证，生成者不能写 `accepted`。

## 6. 独立审查缺口的闭合

暂停前只读审查及内化后的同会话复核先后给出 2 个 P0、4 个 P1 和 2 个 P0、5 个 P1；后者不是重复计数，而是对初版“只写规则文本”的机械可验收性复核。本次逐项处理：

1. **超高密度字号例外**：只有 `data-density=ultra`、角色为表体/轴标签、≤18 行、行高≥18 px、对比度≥4.5:1、原分辨率可读且有 `data-detail-ref`/真实详情链接时成立；KPI、流程标签、图例明确禁用，参考文献单列。
2. **不可自签的当前产物**：项目合同要求 runner-owned immutable run manifest，绑定当前 run、快照、设计/source pack/产物/渲染摘要和验证者身份；改 mtime、复用旧收据/截图或伪造验证者均失败。
3. **typed source pack**：数字 token 分为互斥的事实、页码、日期、章节号和品牌常量；事实必须有稳定 ID、locator、语义角色、单位和分母。
4. **notes 受控层**：隐藏 `aside.notes` 单独抽取，绑定 slide/claim ID，并与页面、图、表和四格式共同重算。
5. **compat stub**：测试同时固定四个来源 stub 摘要，项目只保留一个非正文入口，禁止恢复第二份规则正文。
6. **PDF/PPT Master**：新增 `track_pdf.md`；项目路线和负例明确禁止非原生 PDF、截图替代和绕过 PPT Master 的 PPTX。
7. **可执行合同**：新增来源包、当前运行清单和独立验收结论三份 JSON Schema，以及 `tools/design_contract_validation.py`；负例覆盖缺分母、事实伪装页码、讲者稿游离声明、跨载体数值不一致、旧收据、旧渲染、只改时间、错摘要和生成者自签。
8. **来源与入口不可漂移**：测试固定通用版稳定快照逐文件摘要表和项目入口精确摘要；给入口追加第二套规则正文、删减来源文件映射或放宽 v1.2 优先级都会失败。

## 7. Task 0.3 与实产物验收分界

Task 0.3 只接受“项目设计合同来源可审计、自包含、一致、摘要正确”。它不生成或接受任何 A/B/C 报告实产物，也不再为通用版跑 S2 四轨样例。

门户、原生 PDF、HTML-PPT、PPTX 的 current-run 实产物验收仍在后续对应实现阶段完成，并必须使用真实浏览器、PDF、PowerPoint/LibreOffice 和 PPT Master 锚点。这样既不把合同导入误报为视觉成片通过，也不会为了修复通用模板扩大本项目范围。

## 8. 精确测试

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/contract/test_design_contract_hashes.py \
  tests/contract/test_design_acceptance_contracts.py -q
PYTHONDONTWRITEBYTECODE=1 uv run python \
  contracts/kangzhe/design_specs/tests/test_package_load.py -q
```

最终复核信号分别为 `32 passed` 和 `Ran 8 tests ... OK`；连同仓内既有合同与迁移测试为 `38 passed`。同一隔离 Luna 会话在第三次复核中亲自重跑五类变异：旧 verdict 绑定被改写清单、未知运行前状态配合 mtime 改写、`999` 脱链声明、业务事实伪装页码、讲者稿追加未绑定数字，五类均被拒绝，结论为 `PASS`。这只接受设计合同，不接受任何报告实产物。

## 9. 回滚

删除新仓 `contracts/kangzhe/` 及对应新测试即可回滚本次内化；通用模板和旧竞品调研工程没有被修改。进入 Task 0.4 后，回滚必须连同依赖该设计合同摘要的包清单一起处理。
