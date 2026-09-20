# 竞品调研重基线 M0/M1 完成检查点（2026-09-04）

## 结论

M0 `Provenance recovered` 与 M1 `Canonical contracts` 已完成并由 Codex 接受。R0 首份 worker 报告因错误扩大“全绿”和 provenance 结论而被驳回；有用实现经当前字节复核、确定性门、独立会商 VETO→修复→同会话 PASS 及 Codex 外部恢复锚点复核后重新建立可信基线。R1 canonical v1.3 合同也已通过独立 VETO→修复→同会话 PASS。

本检查点仅放行 R2-R4 实施，不是产品、门户、安装包、三宿主、真实数据矩阵、RC 或 release 验收。

## 权威合同

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`
- `plans/competitive-intelligence-workflow-roadmap-v1.3.md`
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`
- `reviews/zcode_disposition_ci-rebaseline-rebuild_20260904.md`
- `reviews/codex_v13_implementation_gap_matrix_20260904.md`
- 本任务当前 `prd.md`、`design.md`、`implement.md`

历史 v1.2、v1.3 draft、ZCode 原件、暂停交接和既有竞品调研 Skill 均只作为待核验历史输入；不得覆盖上述合同。

## M0 决定性证据

- Codex 最终四步门：Ruff 通过；`mypy --no-incremental --strict src tools --show-error-codes` 对 191 个源文件通过；`tests/unit tests/contract` 860 项通过；`LEGACY_REF_OK` 通过。
- 门状态严格为 `GATE_OK status=quality-only steps=4`，没有把 dirty tree、历史 422-file source set 或局部门伪装成 release readiness。
- 无效的 `--require-clean` + 历史 source-set 组合在任何质量步骤前退出 2；symlink target 使用 `os.readlink` 加词法 `abspath`，不解析或跟随目标。
- ReportLab 边界如实记录 31 个逐行 `import-untyped` ignore 和 2 个既有 `misc` ignore；没有全局 `ignore-missing-imports`。
- R0 独立会商：Pi `cursor/default`，session `01a06b65-d857-7000-8f30-816c54f99ec5`；首轮 2 P1 + 3 P2 VETO，全部修复后同会话续审 PASS，无 fallback。
- 会商结构校验和 Codex `review-gate --require-verification` 均通过。

## 恢复点

### Previous

- 路径：`/Users/smkzw/Documents/AI Products/.ci-rebaseline-backups/ci-workflow-r0-20260904T074503Z`
- 19,498 节点；5,910,548,662 字节；当前逐节点复核仍匹配 manifest；可写节点 0。
- 回执：`context/ci-rebaseline-rebuild-20260904_recovery_snapshot_receipt.json`

### Current M1

- 路径：`/Users/smkzw/Documents/AI Products/.ci-rebaseline-backups/ci-workflow-m1-20260904T082040Z`
- 18,878 节点；5,888,661,178 字节；source/backup manifest 完全一致；备份逐节点重新哈希通过；可写节点 0。
- source canonical digest：`1e7e3aeeb031d0391a7fb333fb9825869047835cc54aff46b268fee7575b9d22`
- backup canonical digest：`ad496281d4785240e322400b0b0c86ebfb0d574058d4afe7d26c51e38754679c`
- source manifest 文件 SHA-256：`982fe56970a69a66f13fb68d3d533173ce10995056f3e9e8192d48cb2086a8c2`
- backup manifest 文件 SHA-256：`d10c56e5e586d6300ae538a1733057dff8c4a186f27adc84bab5d7f18d7b3739`
- 回执：`context/ci-rebaseline-rebuild-20260904_m1_recovery_snapshot_receipt.json`

两个恢复点都是当前脏树的恢复锚，不是“所有变更前”备份，也不是最终 HTML-only release source set。

## M1 决定性证据

- canonical v1.3、正式路线图、执行 v3、ZCode disposition 与 Task 10.6 三文档已互相同步。
- R1 独立会商在首轮 VETO 后修复 publication、宇宙闭包、证据不足、B 气泡、LangGraph 和历史格式继承等合同缺口；同一 Pi/Cursor session 最终 PASS。
- Task 10.6 Trellis context 已具备真实 implement/check 文件清单；G01-G20 矩阵已更新为 M0/M1 已关闭状态。
- 首版范围保持 HTML-only、A/B/C 三个独立门户、人工触发刷新、一次性 publication 补件门、独立上下文复核、24 真实门户与三宿主一致性。

## 里程碑磁盘卫生

- 精确盘点 54 个仓库内可再生缓存目录，首次直接占用 53,368 KiB。
- 在门和会商证据落盘后删除这些目录；首次清理后工作区总占用从 5,849,544 KiB 降至 5,795,152 KiB。
- Task/Trellis 验证重建了其中两个已授权目录，验证后再次精确删除并多回收 216 KiB；共 56 次目录删除事件、54 个唯一目录，最终同类目录剩余 0。
- 保守报告总回收 53,584 KiB；完整清单见 `metrics/ci-rebaseline-m1-disk-hygiene-20260904.md`。
- `.venv`、`.playwright-cli`、会商日志/报告、历史归档、fixture、科学证据、未验收报告、规范文档、回执以及 current/previous 恢复点全部保留。
- 未以任何命令盘点或清理禁止接触的旧工程。

## 安全边界

- 当前工作树仍为用户与既有实现共同形成的脏树；未 reset、checkout、clean、`git add .` 或推测性分组提交。
- Task 10.3-10.5 封存记录未修改。
- 当前没有最终 HTML-only source set；只能在 R2-R4 产品面和安装面完成后从 clean commit 构建。
- 未创建 RC、未发出 `RC_FROZEN`/`RELEASED`，未执行真实宿主分发，未触碰任何真实凭据。
- 旧工程继续零接触；退役需要未来单独条件和用户再次明确批准。

## 下一安全动作

1. 复核现有 governed execution packet 中 `worker_03` 的完整提示与写边界，确认其从磁盘完整读取 canonical v1.3，并以 G01-G20 和 R2-R4 为唯一实施路线。
2. 运行 prompt preflight 后按原定 `openai-codex/gpt-5.6-luna:max` 执行路线启动 worker；不把 R0 worker 或旧 Skill 的结论作为实现权威。
3. 先完成 G01-G09 的 RED→GREEN 研究/证据合同，再进入 G10-G13 门户，最后 G14-G18 HTML-only 包和宿主适配；每个边界由 Codex gate 与独立会商接受。
4. R5 的 24 个真实门户和 R6 RC 仍保持锁定，直到 R2-R4 全部门实际通过。
