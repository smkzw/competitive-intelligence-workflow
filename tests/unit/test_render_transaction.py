"""ci-r2：共享未发布渲染目录事务边界的失败关闭与可恢复语义。

- ``begin()`` 只在目标版本目录可证明未发布时开放：版本根不存在任何
  ``*.manifest.json`` 清单、不存在 ``html.coverage-projection.json``、
  产物清单存储、当前运行清单和科学复核状态没有记录绑定当前站点或清单；
  否则拒绝覆盖并保持既有字节不变。
- 中断残留（无清单的 ``html/``、``.render-staging.*``、清单临时文件）
  是可证明未发布的，下一轮事务精确清理后恢复；未知内容失败关闭。
- ``commit()`` 以 staging 原子换名 + 清单原子写入为提交点；换名前发现
  完成绑定或目录被并发占用时失败关闭。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import pytest

from ci_workflow.storage.render_transaction import (
    RenderTransactionError,
    UnpublishedRenderTransaction,
)


def _make_transaction(
    tmp_path: Path,
    *,
    report: Literal["A", "B", "C"] = "A",
    version: str = "v1",
    run_id: str = "run-0001",
) -> UnpublishedRenderTransaction:
    return UnpublishedRenderTransaction(
        tmp_path, report=report, report_version=version, run_id=run_id
    )


def _residue(tmp_path: Path, report: str = "A", version: str = "v1") -> Path:
    residue = tmp_path / "reports" / report / version / "html"
    residue.mkdir(parents=True)
    (residue / "index.html").write_text(f"{report}{version}中断残留", encoding="utf-8")
    return residue


# ── begin：可恢复与拒绝覆盖 ────────────────────────────────────────────────


def test_begin_recovers_interrupted_residue(tmp_path: Path) -> None:
    residue = _residue(tmp_path)
    transaction = _make_transaction(tmp_path)

    staging = transaction.begin()

    assert staging.is_dir()
    assert staging == tmp_path / "reports" / "A" / "v1" / ".render-staging.run-0001"
    assert not residue.exists()


def test_begin_recovers_foreign_staging_residue(tmp_path: Path) -> None:
    version_root = tmp_path / "reports" / "A" / "v1"
    foreign = version_root / ".render-staging.run-crashed"
    foreign.mkdir(parents=True)
    (foreign / "index.html").write_text("上一轮崩溃的 staging", encoding="utf-8")

    assert _make_transaction(tmp_path).begin().is_dir()
    assert not foreign.exists()


def test_begin_refuses_any_existing_manifest(tmp_path: Path) -> None:
    version_root = tmp_path / "reports" / "A" / "v1"
    manifest = version_root / "html.manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes(b'{"status": "generated"}\n')

    with pytest.raises(RenderTransactionError, match="拒绝覆盖"):
        _make_transaction(tmp_path).begin()
    assert manifest.read_bytes() == b'{"status": "generated"}\n'


def test_begin_refuses_manifest_even_when_site_was_removed(tmp_path: Path) -> None:
    version_root = tmp_path / "reports" / "A" / "v1"
    version_root.mkdir(parents=True)
    (version_root / "html.manifest.json").write_bytes(b'{"status": "accepted"}\n')

    with pytest.raises(RenderTransactionError, match="拒绝覆盖"):
        _make_transaction(tmp_path).begin()


def test_begin_refuses_coverage_projection(tmp_path: Path) -> None:
    version_root = tmp_path / "reports" / "A" / "v1"
    version_root.mkdir(parents=True)
    (version_root / "html.coverage-projection.json").write_bytes(b"{}\n")

    with pytest.raises(RenderTransactionError, match="覆盖投影"):
        _make_transaction(tmp_path).begin()


def test_begin_refuses_artifact_store_binding(tmp_path: Path) -> None:
    store = tmp_path / "manifests" / "artifacts"
    store.mkdir(parents=True)
    (store / "accepted-1.json").write_text(
        '{"artifact": {"relative_path": "reports/A/v1/html"}}', encoding="utf-8"
    )

    with pytest.raises(RenderTransactionError, match="产物清单存储"):
        _make_transaction(tmp_path).begin()


def test_begin_allows_bindings_for_other_versions(tmp_path: Path) -> None:
    store = tmp_path / "manifests" / "artifacts"
    store.mkdir(parents=True)
    (store / "accepted-b.json").write_text(
        '{"artifact": {"relative_path": "reports/B/v1/html"}}', encoding="utf-8"
    )

    assert _make_transaction(tmp_path).begin().is_dir()


def test_begin_fails_closed_on_unreadable_artifact_record(tmp_path: Path) -> None:
    store = tmp_path / "manifests" / "artifacts"
    store.mkdir(parents=True)
    (store / "broken.json").write_text("{不是合法JSON", encoding="utf-8")

    with pytest.raises(RenderTransactionError, match="无法证明未发布"):
        _make_transaction(tmp_path).begin()


@pytest.mark.parametrize(
    ("relative", "payload", "message"),
    [
        (
            "manifests/current_run.json",
            '{"outputs":[{"relative_path":"reports/A/v1/html.manifest.json"}]}',
            "当前运行清单",
        ),
        (
            "state/scientific_review/A/review_request.json",
            '{"portal_binding":{"site_relative":"reports/A/v1/html"}}',
            "科学复核状态",
        ),
    ],
)
def test_begin_refuses_run_or_review_binding_after_manifest_loss(
    tmp_path: Path,
    relative: str,
    payload: str,
    message: str,
) -> None:
    residue = _residue(tmp_path)
    binding = tmp_path / relative
    binding.parent.mkdir(parents=True, exist_ok=True)
    binding.write_text(payload, encoding="utf-8")

    with pytest.raises(RenderTransactionError, match=message):
        _make_transaction(tmp_path).begin()
    assert (residue / "index.html").is_file()


@pytest.mark.parametrize(
    "relative",
    [
        "manifests/current_run.json",
        "state/scientific_review/A/review_request.json",
    ],
)
def test_begin_fails_closed_on_unreadable_run_or_review_state(
    tmp_path: Path, relative: str
) -> None:
    _residue(tmp_path)
    binding = tmp_path / relative
    binding.parent.mkdir(parents=True, exist_ok=True)
    binding.write_text("{损坏", encoding="utf-8")

    with pytest.raises(RenderTransactionError, match="无法证明未发布"):
        _make_transaction(tmp_path).begin()


def test_begin_allows_run_and_review_bindings_for_other_version(tmp_path: Path) -> None:
    current_run = tmp_path / "manifests/current_run.json"
    current_run.parent.mkdir(parents=True)
    current_run.write_text(
        '{"outputs":[{"relative_path":"reports/A/v2/html.manifest.json"}]}',
        encoding="utf-8",
    )
    review = tmp_path / "state/scientific_review/A/review_request.json"
    review.parent.mkdir(parents=True)
    review.write_text(
        '{"portal_binding":{"site_relative":"reports/A/v2/html"}}',
        encoding="utf-8",
    )

    assert _make_transaction(tmp_path).begin().is_dir()


def test_begin_refuses_unknown_residue(tmp_path: Path) -> None:
    version_root = tmp_path / "reports" / "A" / "v1"
    version_root.mkdir(parents=True)
    (version_root / "operator-notes.txt").write_text("人工放入的文件", encoding="utf-8")

    with pytest.raises(RenderTransactionError, match="无法证明未发布"):
        _make_transaction(tmp_path).begin()
    assert (version_root / "operator-notes.txt").exists()


def _residue_tree(root: Path) -> dict[str, tuple[str, bytes | str]]:
    """比较完整目录结构、文件字节和链接本身，不跟随链接读取目标。"""
    tree: dict[str, tuple[str, bytes | str]] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            tree[relative] = ("symlink", os.readlink(path))
        elif path.is_dir():
            tree[relative] = ("directory", "")
        else:
            tree[relative] = ("file", path.read_bytes())
    return tree


def _mixed_residue(tmp_path: Path) -> Path:
    site = _residue(tmp_path)
    version_root = site.parent
    staging = version_root / ".render-staging.run-crashed"
    (staging / "empty-directory").mkdir(parents=True)
    (staging / "index.html").write_bytes(b"staging\x00original\n")
    (version_root / ".html.manifest.json.crashed.tmp").write_bytes(b"partial\n")
    return version_root


def test_begin_preserves_all_residue_when_unknown_file_sorts_last(tmp_path: Path) -> None:
    version_root = _mixed_residue(tmp_path)
    unknown = version_root / "zzz-operator-notes.txt"
    unknown.write_bytes(b"operator\x00notes\n")
    assert sorted(version_root.iterdir())[-1] == unknown
    before = _residue_tree(tmp_path)

    with pytest.raises(RenderTransactionError, match="未知内容"):
        _make_transaction(tmp_path).begin()

    assert _residue_tree(tmp_path) == before


@pytest.mark.parametrize("kind", ["directory", "symlink", "dangling_symlink", "staging_file"])
def test_begin_preserves_all_residue_when_later_entry_is_invalid(tmp_path: Path, kind: str) -> None:
    version_root = _mixed_residue(tmp_path)
    invalid = version_root / "zzz-unknown"
    if kind == "directory":
        invalid.mkdir()
        (invalid / "notes.txt").write_bytes(b"keep\n")
    elif kind in {"symlink", "dangling_symlink"}:
        target = tmp_path / "link-target"
        if kind == "symlink":
            target.write_bytes(b"target\n")
        invalid.symlink_to(target)
    else:
        invalid = version_root / ".render-staging.zzz-invalid"
        invalid.write_bytes(b"not a directory\n")
    assert version_root / ".render-staging.run-crashed" < invalid
    before = _residue_tree(tmp_path)

    with pytest.raises(RenderTransactionError, match="未知内容|符号链接"):
        _make_transaction(tmp_path).begin()

    assert _residue_tree(tmp_path) == before


def test_begin_cleans_all_valid_mixed_residue(tmp_path: Path) -> None:
    version_root = _mixed_residue(tmp_path)
    neighbor = _residue(tmp_path, version="v2")
    neighbor_before = _residue_tree(neighbor.parent)

    staging = _make_transaction(tmp_path).begin()

    assert list(version_root.iterdir()) == [staging]
    assert staging.is_dir()
    assert list(staging.iterdir()) == []
    assert _residue_tree(neighbor.parent) == neighbor_before


@pytest.mark.parametrize("link_at_version", [False, True])
def test_begin_preserves_residue_when_version_path_is_symlinked(
    tmp_path: Path, link_at_version: bool
) -> None:
    project = tmp_path / "project"
    outside = tmp_path / "outside-project"
    version_root = _mixed_residue(outside)
    if link_at_version:
        link = project / "reports/A/v1"
        target = version_root
    else:
        link = project / "reports"
        target = outside / "reports"
    link.parent.mkdir(parents=True)
    link.symlink_to(target, target_is_directory=True)
    before = _residue_tree(tmp_path)

    with pytest.raises(RenderTransactionError, match="不是可控|越出项目根"):
        _make_transaction(project).begin()

    assert _residue_tree(tmp_path) == before


def test_begin_refuses_symlink_residue(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("不可触碰", encoding="utf-8")
    version_root = tmp_path / "reports" / "A" / "v1"
    version_root.mkdir(parents=True)
    (version_root / "html").symlink_to(outside)

    with pytest.raises(RenderTransactionError, match="符号链接"):
        _make_transaction(tmp_path).begin()
    assert (outside / "secret.txt").exists()


def test_begin_rejects_unsafe_identity(tmp_path: Path) -> None:
    with pytest.raises(RenderTransactionError, match="身份不合法|安全路径段"):
        _make_transaction(tmp_path, version="1")
    with pytest.raises(RenderTransactionError, match="身份不合法|安全路径段"):
        _make_transaction(tmp_path, version="../escape")  # type: ignore[arg-type]
    with pytest.raises(RenderTransactionError, match="身份不合法|安全路径段"):
        _make_transaction(tmp_path, run_id="../escape")
    with pytest.raises(RenderTransactionError, match="身份不合法|安全路径段"):
        _make_transaction(tmp_path, run_id="")


def test_recovery_cleans_only_its_own_version_directory(tmp_path: Path) -> None:
    own = _residue(tmp_path, "A", "v1")
    neighbor = _residue(tmp_path, "A", "v2")
    other_report = _residue(tmp_path, "B", "v1")

    _make_transaction(tmp_path).begin()

    assert not own.exists()
    assert (neighbor / "index.html").exists()
    assert (other_report / "index.html").exists()


# ── commit：原子提交点与失败关闭 ───────────────────────────────────────────


def test_commit_renames_staging_and_writes_manifest(tmp_path: Path) -> None:
    transaction = _make_transaction(tmp_path)
    staging = transaction.begin()
    (staging / "index.html").write_text("完整站点", encoding="utf-8")

    site_root, manifest_path = transaction.commit(b'{"manifest": true}\n')

    assert site_root == tmp_path / "reports" / "A" / "v1" / "html"
    assert (site_root / "index.html").read_text(encoding="utf-8") == "完整站点"
    assert manifest_path == tmp_path / "reports" / "A" / "v1" / "html.manifest.json"
    assert manifest_path.read_bytes() == b'{"manifest": true}\n'
    assert not staging.exists()


def test_commit_requires_begin(tmp_path: Path) -> None:
    with pytest.raises(RenderTransactionError, match="尚未开始"):
        _make_transaction(tmp_path).commit(b'{"manifest": true}\n')


def test_commit_fails_closed_when_binding_appeared(tmp_path: Path) -> None:
    transaction = _make_transaction(tmp_path)
    staging = transaction.begin()
    (staging / "index.html").write_text("候选站点", encoding="utf-8")
    manifest = tmp_path / "reports" / "A" / "v1" / "html.manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_bytes('{"外部": true}\n'.encode())

    with pytest.raises(RenderTransactionError, match="拒绝覆盖"):
        transaction.commit(b'{"manifest": true}\n')
    assert manifest.read_bytes() == '{"外部": true}\n'.encode()
    assert (staging / "index.html").exists()


def test_commit_fails_closed_when_html_slot_filled(tmp_path: Path) -> None:
    transaction = _make_transaction(tmp_path)
    staging = transaction.begin()
    (staging / "index.html").write_text("候选站点", encoding="utf-8")
    concurrent = tmp_path / "reports" / "A" / "v1" / "html"
    concurrent.mkdir(parents=True)
    (concurrent / "index.html").write_text("并发产物", encoding="utf-8")

    with pytest.raises(RenderTransactionError, match="换名失败"):
        transaction.commit(b'{"manifest": true}\n')
    assert (concurrent / "index.html").read_text(encoding="utf-8") == "并发产物"


def test_completed_transaction_refuses_second_run(tmp_path: Path) -> None:
    transaction = _make_transaction(tmp_path)
    staging = transaction.begin()
    (staging / "index.html").write_text("完成站点", encoding="utf-8")
    transaction.commit(b'{"manifest": true}\n')

    with pytest.raises(RenderTransactionError, match="拒绝覆盖"):
        _make_transaction(tmp_path, run_id="run-0002").begin()


def test_crash_between_rename_and_manifest_is_recoverable(tmp_path: Path) -> None:
    first = _make_transaction(tmp_path)
    staging = first.begin()
    (staging / "index.html").write_text("前半提交", encoding="utf-8")
    version_root = tmp_path / "reports" / "A" / "v1"
    os.replace(staging, version_root / "html")
    (version_root / ".html.manifest.json.abc123.tmp").write_bytes(b"partial")

    second = _make_transaction(tmp_path, run_id="run-0002")
    staging2 = second.begin()
    (staging2 / "index.html").write_text("重渲染站点", encoding="utf-8")
    site_root, manifest_path = second.commit(b'{"manifest": true}\n')

    assert (site_root / "index.html").read_text(encoding="utf-8") == "重渲染站点"
    assert manifest_path.is_file()
    assert not list(version_root.glob(".html.manifest.json.*.tmp"))
