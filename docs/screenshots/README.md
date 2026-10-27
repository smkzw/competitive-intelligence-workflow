# 当前工作台实屏

2026-10-27，release `rel_af6c6423f665673b`；源码集合 `6f49b2b252bdd8bb8431586500728e96d61009972ff76206eac6e5022743696f`。

以下为Ego真实桌面浏览器，从MG-K10 CRSwNP项目进入“证据调研与方案设计→竞品调研报告”后逐项切换。1440/1920指整个浏览器CSS宽度；内嵌区分别1004/1484px。报告可通过“全宽阅读”使用完整浏览器宽度。

A/B/C同一候选、稳定重排后无页面横向溢出；C对照表在较窄内嵌区保留表内横向滚动。表内滚动不代表隐藏数据。单独全宽1440/1920也已实看。

| 图片 | SHA-256 |
|---|---|
| [current-A-1440.png](current-A-1440.png) | `4554c3a179c193d78925d3d1ce8b63e2faea2a4b97797f6b8dc5691fb3285a6c` |
| [current-A-1920.png](current-A-1920.png) | `f3c6076b5baf299df4c406d5cb467f163e23ee98a788caa4654e3ef631e4bff5` |
| [current-B-1440.png](current-B-1440.png) | `ec5974bc9c3fd5841594a255d2e2ccbb04ad690ab6b0626b958d4cf40fc5c05e` |
| [current-B-1920.png](current-B-1920.png) | `10726d47fae524de3aa4e5857e5e407be97cb458c2cf2bccb2fd944d801dbaa9` |
| [current-C-1440.png](current-C-1440.png) | `b2a99367a5640882ca4ddc9ca834677129d265158e90661d797fc836987ea354` |
| [current-C-1920.png](current-C-1920.png) | `004c227cfdb61463be6984be3059b79da0c41ef46f9d8e5688d976cd49072fce` |

同候选实际操作：DUBHE差值−1.2、95%CI−2.3至−0.1、P=0.04及“论文分组”；一次点击到PubMed；SINUS-52完整入排逐字一致、5处阈值强调、Tab不出弹窗、Esc回原行；studio154项与C集合一致，取消→重开→恢复→重开。

截图只证明所示页面与状态；不代替来源核对。旧T1与1716截图属于旧候选，保留历史，不混作当前验收。原件、运行JSON、响应、数据库和内部设计规范不随截图入库。

C筛选修复：A/B公共资产与cdc1bcc保持相同；C统计图随矩阵筛选，单研究、0例、空结果与恢复实际验证。[SINUS-52筛选后](current-C-filtered-1920.png)，SHA-256 `37bf44503d6235351609136d33ddd8deed8958e5f0a869440536233217c248c7`。该图不借用旧候选证明筛选联动。
