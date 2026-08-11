Re-verifying the Logo manifest fix: recompute digests, run the logo contract node, and prove fail-closed with a temp broken-source mutation.# Conference Participant Follow-up: general_grok45

## 1. Verdict

**PASS** — P0: 0，P1: 0

（仅回验原 Logo 溯源 P1；不声称 Task 0.3 之外或 A/B/C 报告完成。）

## 2. 亲自执行的命令与关键结果

**正向绑定（项目根）**

```bash
# 独立摘要 + source 存在/同字节
python3  # hashlib 对 cms-logo.svg 与 design_specs/assets/logo_bot.svg

# Logo exact node
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider \
  tests/contract/test_offline_assets.py::test_cms_logo_is_the_verified_official_offline_asset -q
# → 1 passed

# 全量静态合同（附证）
PYTHONDONTWRITEBYTECODE=1 uv run pytest -p no:cacheprovider tests/contract/test_offline_assets.py -q
# → 6 passed
```

| 检查 | 结果 |
|---|---|
| `source` | `contracts/kangzhe/design_specs/assets/logo_bot.svg` **存在** |
| `file` | `assets/brand/cms-logo.svg` **存在** |
| 字节 | 两边均为 **9542**，`manifest.bytes=9542` |
| SHA-256 | 两边与 manifest 均为 `8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae` |
| 字段 | `official_url`、`official_retrieval_date=2026-08-11`、`view_box=0 0 121 25` 均在 |

**负向 fail-closed（`mktemp` 副本，未改项目；已删除 `/tmp/ci_logo_failclosed_51sJ3V`）**

| 变异 | 结果 |
|---|---|
| A：`source` → 不存在路径 `contracts/kangzhe/brand/logo/cms-logo.svg` | **失败**于 `assert source.is_file()`（exit 1） |
| B：source 路径存在但字节被篡改 | **失败**于 `assert _sha256(source) == LOGO_SHA256`（exit 1） |

合同现对「幽灵 source」与「source/封装不一致」均 fail closed。

## 3. 原 P1 是否关闭

**是，已关闭。**

原缺口（悬空内部 source、缺官网/日期/字节、合同未校验 source）均已在仓内修复并由本轮独立重算 + exact node + 负向证明确认。

## 4. 残留 P0/P1

**无。** 无需进一步最小修复以关闭该 P1。
