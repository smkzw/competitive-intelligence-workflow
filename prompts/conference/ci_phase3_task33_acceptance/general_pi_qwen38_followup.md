# Task 3.3 同会话复验

Hard boundaries:
- 只读验收；不得修改仓库文件。
- 不得读取另一位参与者输出。
- 临时探针只写系统临时目录，并在完成后清理。

Read these files only:
- `src/ci_workflow/ingestion/manual_inbox.py`
- `src/ci_workflow/application/project_service.py`
- `schemas/download-request.schema.json`
- `tests/integration/test_manual_inbox_recovery.py`
- `tests/integration/test_user_filename_auto_rename.py`
- `tests/integration/test_download_request_transitions.py`
- `policies/gates/B-v1.yaml`

Write exactly one output file: `runs/conference/ci_phase3_task33_acceptance/general_pi_qwen38_followup.md`

该文件由 runner 持久化；你只需在最终回复返回完整内容，不得自行写入。

继续你刚才的 Task 3.3 独立验收会话，不重做无关探索，也不要读取另一位参与者的输出。Codex 已复现并修复你报告的两个 P1，同时处理同源 P2：

- 大写 `.PDF/.HTML/.TXT` 扩展名按原文件名直接识别；错误说明不再向用户暴露媒体类型术语。
- `matched` 状态重新扫描可直接续跑到归档；`accepted` 状态若遗留同摘要收件副本会清理，事件、作业和来源版本不得重复。
- 其他活跃请求只在同项目、同运行内参与歧义判断；旧运行不会阻断新运行的专属收件目录。
- 缺 DOI、PMID、登记号时以明确业务原因不发起下载请求。
- 隔离处理说明保留每轮文件记录；项目初始化与重生成的空列表文案统一。
- accepted 模型与 JSON Schema 均要求保留原文件名。
- 新增国外资料只有登记号时的英文标题核对回归。

请读取当前 diff 和三个精确测试，运行：

`uv run pytest tests/integration/test_manual_inbox_recovery.py tests/integration/test_user_filename_auto_rename.py tests/integration/test_download_request_transitions.py -q`

随后用最小临时目录探针复现你原 P1-1、P1-2、跨运行同资料请求、接受后遗留收件副本、英文标题核对和隔离说明历史。核对事件/作业/SQLite/归档摘要没有重复或漂移。若仍有 P0/P1，给出精确复现；P2 要区分当前任务缺陷与后续任务边界。

保持只读，不修改仓库。返回完整会议输出结构，结尾必须为：

`PASS|FAIL; P0=n; P1=n; P2=n`
