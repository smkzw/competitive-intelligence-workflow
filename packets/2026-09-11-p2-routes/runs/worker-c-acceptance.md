# Worker-C 主线程验收（2026-09-11）

- 写集核验：仅白名单三文件（pubmed_fetch.py 新建 424 行、test_pubmed_fetch.py 新建 384 行、cli.py 追加 fetch-pubmed handler+子命令）。git status 中其他 cli 相关变更经 mtime+暂停索引核验为暂停前既有 WIP，非本次越界。
- 测试：tests/integration/sources/test_pubmed_fetch.py 45 passed（主线程亲跑）。
- 静态：ruff 两文件通过；pubmed_fetch.py strict-mypy 通过。
- 真实网络 smoke（主线程执行）：`nemolizumab AND prurigo nodularis` 单页 200 → search 1 页 + efetch 1 页 + 99 条真实记录（首条 PMID 42696343）；来源声明 101 而返回 99，状态诚实置 incomplete（需恢复，不认定完成）；universe_closed=False、temporal_scope=current_records 限制串在位。窄词空结果 → no_records；页数预算耗尽 → incomplete 不触发 efetch，均为正确 fail-closed 语义。
- 结论：P2「路线机制真会执行」最低真实证据成立。闭包/论文判定/独立复核不在本切片范围。
