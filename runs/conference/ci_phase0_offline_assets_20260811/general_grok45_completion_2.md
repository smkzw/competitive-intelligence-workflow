Running digests and contract tests first, then acceptance/browser and the fake-green mutation.Brand manifest source path is missing — next I'll run contract/acceptance tests and verify the path claim.Acceptance suite passed. Running an independent browser probe and a temp-dir fake-green mutation next.Mutation A caught the digest drift. Re-running the English-label and brand-source fake-green proofs with fixed paths.# Conference Participant Output: ci_phase0_offline_assets_20260811 - general_grok45

## Verdict

**FAIL** — P0: 0，P1: 1

Task 0.3 离线运行时本体（六文件摘要、ECharts 6.1.0/Apache-2.0、HTML-PPT 衍生运行层、Chromium/WebKit `file://` 行为）机械上可用；但品牌 manifest 的**内部来源路径不存在**，来源链未闭合，且静态合同对此假绿。按会议成功标准「发现 P0/P1 时 Task 0.3 不得接受」，本参与者结论为 **FAIL**。不声称 A/B/C 报告完成。

---

## Boundary Check

| 边界 | 状态 |
|---|---|
| 工作根仅项目目录 | 遵守 |
| 只读、未改项目文件 | 遵守 |
| 未联网 | 遵守（未做外部拉取；上游 `source_runtime_sha256` 仅核对 manifest 声明） |
| 未读其他参与者输出 | 遵守 |
| 未写 runner 报告路径 | 遵守（本正文由 runner 落盘） |
| 临时变异仅在 `mktemp` 且已删除 | 遵守 |
| 范围仅 Task 0.3 离线基础设施 | 遵守 |

---

## Independent Work Product

### 1) 六资产独立 SHA-256 与 manifest 绑定

| 资产 | 字节 | 独立 SHA-256 | manifest 绑定 |
|---|---:|---|---|
| `assets/brand/cms-logo.svg` | 9542 | `8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae` | `brand.sha256` **一致**；`file=cms-logo.svg` 存在；`view_box=0 0 121 25` |
| `assets/third-party/echarts/echarts.min.js` | 1121883 | `b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0` | `bundle_sha256` **一致**；`version=6.1.0`；`license=Apache-2.0`；`bundle` 路径存在 |
| `assets/third-party/echarts/LICENSE` | 11990 | `634293835b43a6dd2094fa39182a3d9a6b9ca43b7fdb9ac354e8037af2a3093a` | `license_sha256` **一致**；`license_file` 存在 |
| `assets/html-ppt/runtime.js` | 14246 | `ab31d115026ce6ef57292c95a022962b054d7ec1d9e85bdd09ba0515997cbcc4` | `derived_files.runtime.js` **一致** |
| `assets/html-ppt/runtime.css` | 2595 | `7613a3884d7f502a0313cfa8c716707d6fe3579345fbb4f898d3ea4b144bb15e` | `derived_files.runtime.css` **一致** |
| `assets/html-ppt/LICENSE` | 1084 | `a5ed4059e25a3ec35e439abd2623753d1f42d4aa4989ffb5c6b7a97b61f6a949` | `license_sha256` **一致**；`license=MIT` |

内部来源路径存在性：

| 字段 | 声明路径 | 存在？ |
|---|---|---|
| brand.`source` | `contracts/kangzhe/brand/logo/cms-logo.svg` | **否**（目录 `contracts/kangzhe/brand/` 不存在） |
| brand.`file` | `assets/brand/cms-logo.svg` | 是 |
| echarts.`bundle` / `license_file` | 相对 `assets/third-party/echarts/` | 是 |
| html-ppt.`license_file` + derived | 相对 `assets/html-ppt/` | 是 |

旁证（同源字节，非 brand 声明路径）：

- `contracts/kangzhe/design_specs/assets/logo_bot.svg` **存在**，9542 字节，SHA 与 `cms-logo.svg` **逐字节一致**。

### 2) 静态合同与验收测试（项目根命令）

```text
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider tests/contract/test_offline_assets.py -q
→ 6 passed in 0.01s

PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider tests/acceptance/test_html_ppt_runtime_smoke.py -q
→ 5 passed in 2.21s
```

Acceptance 覆盖：Chromium 1600×900、WebKit 2048×1024 导航/页码/深链/逐字稿/演讲者视图；`?preview=`；Chromium+WebKit 本地 ECharts SVG；请求监听 `http(s)` 为空。

### 3) 独立 Chromium `file://` 探针（非仅 pytest 断言）

对 `tests/fixtures/html-ppt-runtime/index.html` 与 `tests/fixtures/offline-echarts/index.html`：

| 检查项 | 结果 |
|---|---|
| 深链 `#/2` | 标题「主要疗效」；页码 `2 / 3`；`location.hash=#/2` |
| `N` 逐字稿抽屉 | 打开；含「主要终点」 |
| `S` 演讲者视图 | `title=演讲者视图`；当前/下一页/计时 `00:00`/页码「第2页，共3页」；脚本中文；「下一页」后主窗同步到「安全性概览」 |
| ECharts | `#chart svg`=1，`canvas`=0；文本含「竞品甲」「主要终点变化值」 |
| HTTP/HTTPS 请求 | 主窗与图表窗均为 `[]` |

（WebKit 以 acceptance 参数化通过为证据；本轮额外人工探针仅 Chromium。）

### 4) 假绿变异（`mktemp`，结束后已删除）

| 变异 | 操作 | 结果 | 含义 |
|---|---|---|---|
| A 摘要漂移 | 临时副本篡改 `echarts.min.js` 字节 | `test_echarts_…` **失败**（期望 `b66b25…`，得 `8d85ac…`） | 合同能抓住 bundle 摘要破坏 |
| B 英文标签 | 临时副本将「演讲者视图」「逐字稿」改为 `Presenter View` / `SPEAKER SCRIPT`，并同步改 manifest 衍生摘要 | 中文原生测试 **失败**；manifest 绑定测试仍过 | 中文/禁用词闸门有效；仅改 hash 不能绕过 |
| C 来源路径假绿 | **不改项目文件**：`brand.source` 缺失但 `file`+`sha256` 正确 | 项目合同 **仍 6 passed** | **测试器缺口**：未断言内部 `source` 路径存在/可解析 |

临时目录：`/tmp/ci_offline_fake_green_Gfcrzz`、`/tmp/ci_offline_fake_green_sO3RWz` 均已 `rm -rf`。

### 5) P1 缺陷（唯一阻断项）

- **级别**: P1（来源链/溯源闭合；非运行时崩溃）
- **文件**: `assets/brand/manifest.json`（字段 `source`）；间接相关 `tests/contract/test_offline_assets.py`（未校验内部 source）
- **可复现**:
  1. 读 `assets/brand/manifest.json` → `source = contracts/kangzhe/brand/logo/cms-logo.svg`
  2. `test -f contracts/kangzhe/brand/logo/cms-logo.svg` → 失败；`contracts/kangzhe/brand/` 不存在
  3. 同时 `assets/brand/cms-logo.svg` 与 `contracts/kangzhe/design_specs/assets/logo_bot.svg` SHA 均为 `8d16d3ae…`
  4. `pytest tests/contract/test_offline_assets.py` 仍全绿
- **最小修复**（建议由 Codex 授权编辑轮执行，本角色只读）:
  1. 将 `source` 改为真实存在且 SHA 匹配的路径，推荐 `contracts/kangzhe/design_specs/assets/logo_bot.svg`；或真正创建 `contracts/kangzhe/brand/logo/cms-logo.svg` 为同字节副本并在合同中引用；
  2. 按 ADR 0003 §2.2 补齐官方 URL / 获取时间 / 字节数字段（当前 manifest 缺这些）；
  3. 在 `test_offline_assets.py` 增加：凡 manifest 声明的**仓内相对路径**必须 `is_file()`，且内容 SHA 与 `sha256`/`bundle_sha256` 一致。

### 6) 产品 vs 测试器 vs 环境

| 类别 | 判定 |
|---|---|
| 产品/资产缺陷 | brand `source` 悬空；命名 `cms-logo.svg` vs 设计合同 `logo_bot.svg` 双轨 |
| 测试器缺陷 | 合同不检查内部 source 存在性 → 变异 C 假绿 |
| 环境缺件 | 无（uv/pytest/playwright Chromium+WebKit 可用） |

---

## Evidence And Assumptions

**Evidence（直接观察）**

- 六文件摘要与三个 manifest 字段绑定结果见上。
- 合同 6 passed；验收 5 passed。
- 独立 Chromium 探针：深链、页码、逐字稿、演讲者、ECharts SVG、零 `http(s)`。
- 变异 A/B 失败；变异 C 证明 source 缺失时合同仍绿。
- 同源替代路径 `design_specs/assets/logo_bot.svg` 存在且 SHA 相同。

**Assumptions（推断）**

- 打包意图是把设计合同中的 `logo_bot.svg` 封装为 `assets/brand/cms-logo.svg`，但 `source` 误写成不存在的 `contracts/kangzhe/brand/logo/…`。
- 验收套件的 WebKit 通过可 credibly 代表跨浏览器；未再开第二次 WebKit 人工脚本。
- 在禁止联网前提下，无法重新验证 npm tarball / GitHub commit 的**上游**完整性，只能验证仓内封装字节与 manifest 自洽。

**Uncertainty**

- html-ppt `source_runtime_sha256`（上游原版）与 echarts `npm_integrity` 无法在本轮离线重拉校验。
- 未做最终视觉/投影审美验收（Codex 权限）。

---

## Risks, Gaps, And Verification Needs

**最高影响异议（给 Codex）**

1. **来源链假绿**：生产者可只靠「文件+硬编码 SHA」过关，而 manifest 自述 source 可以是幽灵路径。若接受现状，后续报告生成器可能引用错误 logo 路径。
2. **ADR 与 manifest 不完全同构**：ADR 要求官方 URL/时间/字节；brand manifest 目前主要是内部字段且 source 错误。
3. **双名 logo**：`cms-logo.svg` vs `logo_bot.svg` 增加报告装配歧义，即使字节相同。

**对「全绿即可 PASS」的挑战**

- 静态+浏览器全绿**不能**推出「来源链闭合」；本轮变异 C 是机械反例。

**给 Codex 的有界问题**

1. brand.`source` 应绑定 `design_specs/assets/logo_bot.svg`，还是新建 `contracts/kangzhe/brand/logo/cms-logo.svg` 镜像？
2. 该 P1 是否必须在 Task 0.3 关闭前修复，还是降为「文档债、不阻断离线运行时」？（本参与者按字面成功标准倾向**必须修**。）

**安全临时路径**

- 在修复前：运行时继续使用 `assets/brand/cms-logo.svg`（SHA 正确）；勿引用 `contracts/kangzhe/brand/…`。

---

## Recommended Next Step

1. **Codex 授权小修复轮**（仅下列文件）：
   - 修正 `assets/brand/manifest.json` 的 `source`（及建议补 ADR 字段）；
   - 在 `tests/contract/test_offline_assets.py` 增加内部路径存在 + SHA 绑定断言。
2. 修复后重跑：
   - `PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider tests/contract/test_offline_assets.py -q`
   - `… tests/acceptance/test_html_ppt_runtime_smoke.py -q`
3. Codex 人工打开观众页 / 演讲者 / WebKit 图表截图后，再裁定 Task 0.3 是否可接受。
4. **不要**因本 FAIL 回退 ECharts/HTML-PPT 运行时；阻断项仅 brand 溯源字段与合同缺口。

---

### 本轮命令与恢复点（若后续续跑）

已完成：摘要绑定、合同、验收、Chromium 探针、假绿 A/B/C、临时目录清理。  
恢复点：若 Codex 修了 brand manifest/测试，从第 1 步重算 source 存在性 + 两套 pytest 即可；无需重扫目录。
