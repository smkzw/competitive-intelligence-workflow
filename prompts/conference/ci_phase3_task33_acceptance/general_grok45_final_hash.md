# Task 3.3 最终摘要绑定复核

Hard boundaries:
- 必须继续原 Grok Build 会话 `17ca0d78-0348-40fe-a1fe-ce2984131c0c`。
- 只读；不得修改仓库，不得读取另一参与者输出。

Read these files only:
- `src/ci_workflow/ingestion/manual_inbox.py`
- `tests/integration/test_manual_inbox_recovery.py`
- `tests/integration/test_download_request_transitions.py`

Write exactly one output file: `runs/conference/ci_phase3_task33_acceptance/general_grok45_final_hash.md`

该文件由 runner 持久化，你不得自行写入。

Codex 已关闭你上一轮两个 P2，并吸收另一审查者的同源 P2：直接 `accept()` 重放会核对摘要并清理遗留收件副本；已有具体坏文件名时不再追加泛化占位说明；空白但非空的 DOI/PMID/登记号统一给出类型化业务拒绝且零副作用。

当前摘要：
- `manual_inbox.py` `f40b9cdcd614f04778a3900c47c4a2a5da826922701fdea0ac29f3bb16b17ec0`
- `test_manual_inbox_recovery.py` `4f39215d0f6443c350ad59f2a75ed54553bb41b6be32c297b184f96419d017b2`
- `test_download_request_transitions.py` `5270fe81131f0de678539af9d94848df97c7c7dd375af8847589ab8c846f286a`

核对摘要与 diff，运行三个精确测试。只复验这三项微修与原 P1 未退化；无需重做已完成的 70 个探针。若无新 P0/P1，返回 `PASS`；结尾严格为 `PASS|FAIL; P0=n; P1=n; P2=n`。
