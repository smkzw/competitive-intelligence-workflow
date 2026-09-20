# Task 8.3 点名视觉复验 · 同会话收口

MODE=TEST。沿用当前会话与只读边界。只复验最后收口对象，不重启宽泛审查、不读其他测试者结论、不修改文件、不联网。

- 当前 C SHA-256：`9cfa1a6323fcddac0a3d83df32ab351ebab03c12e84f0984f59d746a87628a68`。
- `docs/acceptance/runs/8.3/verification/summary.json`、C 的 structure/evidence、20 张 C 页图现已重新生成并绑定该哈希；总页数仍 A10+B24+C20=54，summary `ok=true`、缺陷 0。
- 请真实打开当前 `C/renders/page-20.png` 与 `C/page-text/page-20.txt`，确认长比较句的第二个 `NCT02260986` 已作为完整编号换到下一行；确认支撑试验列、内部过程措辞、页脚和页面边界无回归。
- 复开当前 `A/renders/page-09.png`，按实际像素确认气泡 C 与底轴之间是否保留间隙；代码合同按气泡半径加 2 点钳制，不得仅凭缩略图猜测。

中文返回：当前哈希/证据绑定、C20、A9、是否仍有阻断、是否建议 Codex 接受。问题必须给当前页图的具体可见证据。
