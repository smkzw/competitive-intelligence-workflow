# W00 结果：当前基线、资源单源与可重复接手

日期：2026-09-22。范围：仅 W00。状态：**W00 工程合同与定向回归完成；产品仍为开发候选，未形成 RC。**

## 执行身份与边界

- 请求模型：`gpt-5.6-sol/medium`；本运行时没有提供可核验的模型/effort receipt，故身份 **UNVERIFIED**。
- 执行方式：由 W00 单节点直接修改共享可变源码；资产真源、打包镜像、清单和隔离安装属于同一事务，不拆分写入者。
- 唯一工程根：英文工程。未读取、盘点或修改旧中文工程。
- 未执行 `commit/push/reset/checkout/clean/git add .`；既有未跟踪材料未删除、未搬移。
- 写入前 `HEAD=2df24bb441e555f20b233ad2011b4ffd3610655b`、branch=`main`，tracked/index 均无修改。完成写入前再次核对 HEAD 未变化。

## 固定基线与 source-set

- Git tree：`eb1901963d514bf64fe9c1af0cbfc075578b3925`。
- W00 输入：`work_packages/W00.md` SHA-256 `1da6795464f7f1db10abf50800e2e145523e4164a459d4a3ab595d423a746f65`。
- 原交接清单：`delivery-manifest.json` SHA-256 `b8d573298d0b084b3c62663b670a0cc96006b9a84fca6532b93a1913fe3eae2a`；实施前重算 45 项，0 mismatch。
- GPT Pro 专家包：按 `checksums.json` 重算 10 项，0 mismatch；其内容仅作证据，没有作为新权限。
- 最小可重复记录：[W00-source-set.json](W00-source-set.json)，SHA-256 `f2b0c37c382da199bb17fee3233c7a7535136ea588b8f79291fc43b737c2031e`。它白名单绑定固定 commit/tree、锁文件、必要 PNH 派生输入、两份未跟踪 CT.gov CAS 字节、候选输入/页面 manifest 和 A/B/C verdict；明确排除整批 `runs/`、旧候选、缓存和凭据。
- 必要 CAS：
  - `1e0a9bbe…ab98.bin`，2,811,140 bytes，内容 SHA-256 与文件名一致。
  - `c3bdbe61…fbdf3.bin`，2,871,697 bytes，内容 SHA-256 与文件名一致。

## 当前候选事实

候选 `runs/pnh-vertical/abc-v106`，run `run_b6d6d289715d3b558b641f47`：A/B/C 分别 56/70/18 个物理 HTML，共 144 页。页面 manifest SHA-256 分别为 `139f3085…13d7d`、`c2f9e20c…a080`、`76927bd1…3aea`。

实际 verdict 均为 `veto`，不是 accepted：

| 门户 | verdict 文件 SHA-256 | candidate snapshot | candidate content digest |
|---|---|---|---|
| A | `d912d39b…bbae5` | `report-snapshot_ac46182f135b95f031d966ae` | `9dce8bf5…0639` |
| B | `6350cf9b…f3b0` | `report-snapshot_bd4b82d9194b6db8bb6e792f` | `767710e7…d2ef` |
| C | `46e12a1c…f28f` | `report-snapshot_5b299d9874b99125329158f7` | `ff65145b…fa83` |

## 两项失败的同环境归因与修复

### C 页面责任

生产 `docs/architecture/page-catalogs/C.yaml`、包内 catalog、C 渲染器和 C 集成测试都已将 `evidence-limitations` 作为真实物理页；失败来自 `test_page_catalogs.py` 仍冻结旧 11 页集合并把“完整数值表”要求错误施加给证据局限叙事页。修复为：保留页面和生产渲染，合同纳入该页；仅该非数值页允许 `complete_table=false`，其余页面仍强制完整表。

### portal assets 与隔离安装

实际运行消费者 `builder.py`、A/B/C renderer 均优先读取 `src/ci_workflow/renderers/portal/assets/`；bundle 同时携带根 `assets/portal/`，安装验证按根 manifest 校验根副本。手工双写导致 `portal.css` 及多个相邻 JS/CSS 漂移，旧 manifest 的摘要/字节数也不对应真实运行集合。

修复合同：

1. 模块 assets 是唯一作者源，运行时不再回退根副本，缺包内资源失败关闭。
2. 根 `assets/portal` 是发包镜像；本次把 6 个漂移文件同步到模块字节。
3. manifest 覆盖 11 个镜像文件，并记录真实 SHA-256/bytes、作者源与镜像策略。
4. `default_allowlist()` 在 bundle 构建前逐文件校验作者源＝镜像＝manifest；漂移在打包前失败，不再等安装阶段才发现。

关键修复后 hash：

| 对象 | SHA-256 |
|---|---|
| `assets/portal/manifest.json` | `2d7cffcbe41c277daaeacc40a737ced0b60a4f01becc2456afb95616cad18028` |
| `src/ci_workflow/renderers/portal/builder.py` | `de1488fab54d1ef51553e8ac81a5ee85e7ebdb7e8d4bff9e64f7a93c5158bf33` |
| `tools/bundle_contract.py` | `82f29e7b7909565411ba956f5fd158ab76c52800b40db80899264c7899c4e665` |
| `tests/contract/test_page_catalogs.py` | `cfbcba630e8f3cad8dafa36d593a7e620de49a57f2021b411874452e809b9ef8` |
| `tests/contract/test_bundle_scientific_closure.py` | `a9d5428adafb5010609cfe69df13d586bf89ddabcf9883882e0c9ea54e5b0fec` |

`package-manifest.json` 未改，SHA-256 `facdc54cb92fba350b4e519ff7db6e7e7a3a5499d4dd74a53bd43bcfd677434d`。

## 批次命令与结果

RED（修复前，仅一次）：

```bash
/usr/bin/time -p env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/test_v96_review_invariants.py tests/integration/test_review_r07_ingestion_invariants.py tests/contract/test_page_catalogs.py tests/contract/test_bundle_scientific_closure.py -q --tb=short
```

结果：`38 passed, 1 failed, 1 error in 12.67s`；real 12.85s。失败分别为 C 多 `evidence-limitations`、隔离安装 `assets/portal/portal.css` 摘要不一致。

GREEN（完整缺陷族修复后，仅一次同批次）：同一命令。结果：`41 passed in 13.19s`；real 13.34s。新增 1 个合同测试显式校验模块作者源、根发包镜像和 manifest 三者一致；隔离安装链真实构建并安装 bundle 后通过资源校验和科学复核入口导入。

另执行只读 `git diff --check`、JSON 解析、11 个镜像文件 `cmp`，均通过。一次交接 hash 循环误用了 zsh 特殊变量名 `path`，导致命令搜索路径失效；该输出废弃，随后用 `rel` 在新进程完整重跑并得到上述 0 mismatch。

## 未验项与下一动作

- 未运行 `bash tools/gate.sh`，未重建/复核 24 门户，未跑完整浏览器矩阵、真实研究刷新、三宿主或恢复矩阵。
- 现有 abc-v106 A/B/C 科学 verdict 仍全部 veto；W00 没有改变候选字节或其 verdict。
- 没有保留新的 release bundle；本次隔离 bundle 是 pytest 临时产物，测试结束后由临时目录回收。
- 旧交接 `delivery-manifest.json` 是 W00 输入基线，不改写；W00 新输出由 `W00-source-set.json` 和本文绑定。
- 下一安全动作：**W01**，按新 source-set 做信任、精确片段与 manifest 传递闭包修复；不得把 W00 GREEN 扩张为 RC/产品通过。
