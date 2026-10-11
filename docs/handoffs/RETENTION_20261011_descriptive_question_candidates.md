# 本批候选压缩保全索引

仅本批Owner新建的v1/v2展开副本已移除，全部412+412原文件均在经过逐文件
SHA-256对照的byte-only压缩包中。v3失败、v4当前候选仍展开保留。其他历史
和未知文件未清理；未遍历旧中文工程或会话数据库。原失败不改为PASS。

| 候选 | 本地受控压缩包 | 压缩包SHA-256 | 文件数 | 原字节 | 压缩字节 |
|---|---|---|---:|---:|---:|
| v1 | `.artifacts/1007-descriptive-question-recovery-v1/candidate-v1-byte-only.tar.gz` | `e474b4940526bdf507565e37b9def4ebd875258107ebb2cb02aae1a18758e053` | 412 | 294579692 | 20839218 |
| v2 | `.artifacts/1007-descriptive-question-recovery-v1/candidate-v2-byte-only.tar.gz` | `698d9aae7f05f694f3dcb2a1078ec2d3f32b94cea1c78cda855cd3b6f5100af6` | 412 | 295436194 | 21694843 |

原文件manifest SHA：v1 `e5c545f43085fd880d5032a86001c38efbacd626e955a75173579993b3701746`；
v2 `90f3fabcf1bccf696e78926593fa58d8eb76161593be59526049e73829ebff9a`。
两包净回收约547.48MB。首次非byte-only包含Mac元数据，验证失败；源保留到
第二次严格验证通过，仅之后删除展开副本和两个本批不合格冗余包。

恢复：显式定位授权英文根，先检查目标目录不存在、核压缩hash并查看成员
无绝对路径、`..`或链接；然后用系统tar解至该根的`.artifacts`。例如v1：

```sh
shasum -a 256 .artifacts/1007-descriptive-question-recovery-v1/candidate-v1-byte-only.tar.gz
tar -tzf .artifacts/1007-descriptive-question-recovery-v1/candidate-v1-byte-only.tar.gz
tar -xzf .artifacts/1007-descriptive-question-recovery-v1/candidate-v1-byte-only.tar.gz -C .artifacts
```

不解压覆盖已有目录。复用包内actual与失败QA/PNG，不重跑已终态任务。
这些本地压缩包不进入PUBLIC GitHub；仓库保留本索引和可确定重建配方。
