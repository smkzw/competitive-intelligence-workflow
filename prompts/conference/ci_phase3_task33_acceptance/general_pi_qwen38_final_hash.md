# Task 3.3 最终摘要绑定复核

Hard boundaries:
- 必须继续原 Pi 会话 `019ff65b-e169-7000-bb67-c32dde18cf41`。
- 只读；不得修改仓库，不得读取另一参与者输出。

Read these files only:
- `src/ci_workflow/ingestion/manual_inbox.py`
- `tests/integration/test_manual_inbox_recovery.py`
- `tests/integration/test_download_request_transitions.py`

Write exactly one output file: `runs/conference/ci_phase3_task33_acceptance/general_pi_qwen38_final_hash.md`

该文件由 runner 持久化，你不得自行写入。

Codex 已按你上一轮 P2-1 以及另一位审查者的两个 P2 做最后微修：空白但非空标识统一抛 `RequestNotRequiredError` 且零副作用；直接 `accept()` 重放会核对摘要并清理遗留收件副本；扫描已记录具体坏文件名时不再追加“未能识别文件名的附件”。对应回归已加入三个精确测试中的两个。

当前摘要：
- `manual_inbox.py` `f40b9cdcd614f04778a3900c47c4a2a5da826922701fdea0ac29f3bb16b17ec0`
- `test_manual_inbox_recovery.py` `4f39215d0f6443c350ad59f2a75ed54553bb41b6be32c297b184f96419d017b2`
- `test_download_request_transitions.py` `5270fe81131f0de678539af9d94848df97c7c7dd375af8847589ab8c846f286a`

核对摘要与 diff，运行三个精确测试。只复现这三项微修及原 P1 的未退化性；无需重做已完成的 66 个探针。若无新 P0/P1，返回 `PASS`；结尾严格为 `PASS|FAIL; P0=n; P1=n; P2=n`。
