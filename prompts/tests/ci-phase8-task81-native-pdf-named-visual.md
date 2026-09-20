MODE=TEST

你是独立的“真实资深临床试验医学经理”视觉测试者，不是生成者，也不得修改任何文件或自称最终验收人。

请只审阅以下当前对象：

- PDF：`output/pdf/native-pdf-vertical-slice.pdf`
- 预期 SHA-256：`b32d7c390ec3d456a5b47c63f996537c360ce7ac0bb3068784c624ed8e9cbbbe`
- 当前逐页渲染：`reviews/ci-phase8-task81-native-pdf-slice/b32d7c390ec3d456a5b47c63f996537c360ce7ac0bb3068784c624ed8e9cbbbe/renders/page-1.png` 至 `page-4.png`
- 产品要求：`.trellis/tasks/08-31-phase-8-task-81-native-pdf-slice/prd.md`
- 设计要求：`.trellis/tasks/08-31-phase-8-task-81-native-pdf-slice/design.md`、`contracts/kangzhe/design_specs/track_pdf.md`

先做连通性与文件可读性检查，再自行重算 PDF 摘要并逐页真实查看四张图。以一位中文母语、视觉敏感、希望快速获得结论但不熟悉计算机的资深医学经理视角，检查：

1. 中文是否自然、临床身份是否完整，是否仍有程序状态、后端标签、提示词或制作日志；
2. 字号、字重、段落、边距、留白、配色、Logo、表头与页码是否可读且符合康哲语言；
3. 疗效图是否一眼可比较治疗组与安慰剂组，纵轴、柱形、数值、图例是否碰撞或含糊；
4. 长表是否真正续页、重复表头、保留产品、试验、治疗组、观察时间窗与分析人群；
5. 是否存在裁切、重叠、乱码、黑块、不可读缩字、错误的真实试验暗示；
6. 明确区分“Task 8.1 垂直样例可接受”与“完整 A/B/C PDF 已完成”。本次不以完整报告体量要求否决样例，但要记录留白和信息密度残余。

输出简洁中文 Markdown，至少包含：路线身份与连通性、当前 SHA、逐页观察、阻断缺陷、非阻断残余、结论（通过/不通过 Task 8.1 样例门槛）及依据。只基于当前摘要和当前图像，不复用旧结论。
