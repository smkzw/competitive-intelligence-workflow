# 1007V1 历史原件索引

当前仅认根HANDOFF→STATUS；本索引不激活历史暂停、旧PID或旧接受状态。
旧入口的全部原文由Git不可变版本保留，不逐轮复制堆入当前入口或改写历史。

- [47aaaeb原接手入口](https://github.com/smkzw/competitive-intelligence-workflow/blob/47aaaebe7742398d3c1bc5b3a713ac5f0186ea20/HANDOFF.md)：
  r10新安装分享已核、C初轮/翻译review当时PENDING；之后以当前终态回执为准，
  不把旧在途PID/占位文件当完成，也不覆写该历史状态。

- [a36原HANDOFF](https://github.com/smkzw/competitive-intelligence-workflow/blob/a36e4ff33b0b7d19951970d65e2683f018bd2496/HANDOFF.md)：
  编辑器开发门、论文v4限定确认、875安装、C阅读/样本、来源holding及之前版本。
- [a36原STATUS](https://github.com/smkzw/competitive-intelligence-workflow/blob/a36e4ff33b0b7d19951970d65e2683f018bd2496/packets/2026-09-22-sol-delivery/STATUS.md)：
  原版本完整分层状态、失败及未运行记录。新HEAD不得把旧安装失败改为通过。
- 本地可精确重开：`git show a36e4ff33b0b7d19951970d65e2683f018bd2496:HANDOFF.md`，
  同样替换路径读取STATUS。不要用checkout/reset改当前工作树。
- [既有实施复盘](implementation.md)及各owner-*.json保留版本特定证据；
  原有暂停/handoff文件保留，最新用户实施授权高于历史暂停。
- [原设计/计划历史](../../archive/pre-1007V1/)不作为新产品权威。
