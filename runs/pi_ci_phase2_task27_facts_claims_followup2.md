# Task 2.7 最终同 session 修复复核

**结论：PASS** — 三项修复全部机械验证通过；P0=0, P1=0, P2=0；六项真实运行全绿。未修改任何文件。

## 运行证据（真实执行）

| 检查 | 结果 |
|---|---|
| `uv run pytest tests/integration/test_source_to_claim_chain.py tests/integration/test_conflicts_preserved.py -q` | **4 passed in 0.06s** |
| `uv run pytest -q` | **182 passed in 5.53s** |
| `uv run ruff check src tests` | **All checks passed!** |
| `uv run mypy --strict src` | **Success: no issues found in 44 source files** |
| `uv run ci-workflow package verify --root .` | **PACKAGE_OK version=0.1.0a0 stage=phase-0-task-0.4** |
| `git diff --check` | **exit=0** |

## 三项逐条结果

**1. `reported_zero` 规范值 — 通过**
- Pydantic（`facts.py` model validator）：`isinstance(normalized_value, bool) or normalized_value not in (0, 0.0, None)` → 抛「已报告零值的规范值必须为零」。布尔短路显式拦截（`False` 与 `0` 相等，故必须先行 isinstance 检查，代码已做）。
- Schema（`fact.schema.json` allOf）：`"normalized_value": {"enum": [0, 0.0, null]}` → 字符串 `"0"` 与布尔均不匹配 enum，拒绝；`"numerator": {"enum": [0, null]}`、raw_value 零证据 pattern `(^|[^0-9.])0(?:\.0+)?\s*(?:%|/|$|\))` 与 Pydantic `_ZERO_EVIDENCE` 语义一致。
- 机械探针：norm=`"0"`/`True`/`False` → REJECT（规范值必须为零）；norm=`0`/`0.0` 通过零值规则（探针中因未附规范化记录被正交的「规范值必须链接规范化记录」规则拦截，属正确行为；集成测试带记录路径通过）。集成测试 `match="规范值必须为零"` 断言通过。

**2. `not_reported`/`not_publicly_disclosed` 全角数值 — 通过**
- Pydantic：`_NUMERIC_DISCLOSURE` 中 `\d` 匹配 Unicode 十进制数字（全角 `５０`），`[%％]` 含全角百分号 → `５０％` fullmatch 命中 → 抛「未报告或未公开状态不得携带数值型原始表达」；`结果未报告` 以「结」开头不匹配 → 接受。
- Schema：`not`-pattern 显式覆盖 `[0-9０-９]`、`[.．]`、`[%％]` → `５０％` 拒绝（测试断言 `ValidationError`）；`结果未报告` 通过。
- 机械探针：`not_reported`/`not_publicly_disclosed` × `５０％` 均 REJECT，× `结果未报告` 均 ACCEPT。

**3. 确定性计算 — 通过**
- 逻辑（`resolution.py`）：`result = round(treatment - control, 12)`；`magnitude_mode` 仅当三个复算值同号且出现匹配方向词（全≤0 + 下降/减少/降低，或全≥0 + 上升/增加/升高）时启用绝对值可见化；非 magnitude 模式要求 `result_text` 字面出现在声明中；**所有**声明中的数值必须 ∈ {treatment, control, result}（magnitude 模式含绝对值变体）。
- 机械探针（真实构造 -2.1 / -0.8 事实）：

| 声明 | 结果 |
|---|---|
| 正常有符号句「组间差为 -1.3 分」 | PASS, result=-1.3 |
| 「试验组下降 2.1 分，安慰剂组下降 0.8 分，组间差为 1.3 分」 | PASS, **底层 result 仍为 -1.3**（测试亦断言 `calculation.result == -1.3`） |
| 含正确值与 -9.9 矛盾值「组间差为 -1.3 分，但手算为 -9.9 分」 | REJECT |
| 纯错误值「组间差为 -9.9 分」 | REJECT |
| 方向词 + 错误幅度「试验组下降 9.9 分…」 | REJECT（9.9 ∉ allowed） |
| 方向词 + 错误方向「试验组上升 2.1 分…」 | REJECT（magnitude_mode 不成立，有符号 -1.3 不在声明中） |
| 无关幅度混入「…另次访视下降 9.9 分」 | REJECT |

方向词无法绕过：错误幅度、错误方向、无关幅度三种注入均被 `stated_values ⊆ allowed_visible_values` 拦截。测试中 `match="声明文字与复算结果不一致"` 两例断言通过。

## 新缺陷
无（P0/P1/P2 = 0）。

## 后续边界（非缺陷，超出本次验收契约）
1. **Unicode 数字脚本不对称**：Pydantic `\d` 匹配所有 Unicode Nd（如阿拉伯-印度数字 `٥٠٪`），而 schema 仅覆盖 `[0-9０-９]`。`٥٠٪` 会被 Pydantic 拒绝但被 schema 接受 —— 与全角契约一致，但如需跨脚本一致性需扩展 schema 字符类。
2. **方向词绕过路径无专门回归测试**：套件只覆盖了 magnitude 通过例与两例 -9.9 拒绝；错误幅度/方向/无关幅度绕过（本轮探针验证均被拒）未固化进测试。建议补一条参数化用例防止回归。
3. **magnitude 模式允许省略对照组数值**（如「试验组下降 2.1 分，组间差为 1.3 分」可通过，因 2.1、1.3 ∈ allowed）——输入事实已固定且受支持事实校验约束，属可接受的宽松，但文档未明示该语义。
