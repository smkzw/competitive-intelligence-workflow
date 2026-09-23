# 0922V2 阶段复审包

基线：`smkzw/competitive-intelligence-workflow@700bd4c1fb90c49e27b6ff46fba07a5f7f296b6c`。

先读`0922V2_REVIEW.md`；交给开发Agent用`0922V2_AGENT_NEXT.md`；下一阶段对照`0922V2_ACCEPTANCE.md`。

`probes/run_probes.py`可用Python3和Node.js重放本轮28项隔离算法检查。运行方式：

```sh
python probes/run_probes.py
```

源码摘录保留被测试计算分支，省略无关周边依赖和注释，部分异常消息缩短；不代表可运行的全仓库，不代表生产pytest/浏览器/安装测试。检查失败表示该算法对本轮审查所定义语义预期不成立，不能视作真实数据中错误行数。

本包没有修改仓库，也没有运行任何外部Agent。HANDOFF所报告的31项测试、1054 passed+2失败及其他模型复核数字没有被本轮重跑确认。
