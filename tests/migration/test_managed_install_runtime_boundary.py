"""Only a recorded private installed venv may link to its managed base Python."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def managed_target():
    # Lexical target only: this fixture neither reads nor executes global Python.
    return Path.home() / ".local/share/uv/python/cpython-3.13-boundary-test/bin/python3.13"


def private_install(root, directory="install"):
    """Self-contained receipts; real runtime probes live in installation evidence."""
    install = root / ".artifacts" / directory
    digest = "a" * 64
    version = install / "versions" / digest
    version.mkdir(parents=True)
    raw_lock = b"version = 1\n"
    (version / "uv.lock").write_bytes(raw_lock)
    (install / "installation.json").write_text(json.dumps({
        "schema_version": "1.0", "bundle_digest": digest,
        "runtime_lock_sha256": hashlib.sha256(raw_lock).hexdigest(),
    }))
    config = install / "runtime/venv/pyvenv.cfg"
    config.parent.mkdir(parents=True)
    config.write_text(
        f"home = {managed_target().parent}\nimplementation = CPython\n"
        "version_info = 3.13.13\ninclude-system-site-packages = false\n"
    )
    link = install / "runtime/venv/bin/python"
    link.parent.mkdir()
    link.symlink_to(managed_target())
    return install, version, config, link


def scanner():
    import sys

    spec = importlib.util.spec_from_file_location(
        "boundary_scanner", ROOT / "tools/check_no_legacy_refs.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_recorded_managed_base_is_not_product_source_escape(tmp_path):
    module = scanner()
    _, _, _, link = private_install(tmp_path)
    assert module._recorded_managed_base(tmp_path, link, module._lexical_symlink_target(link))
    assert not module.scan(tmp_path, Path("/forbidden-never-touch-legacy"))


@pytest.mark.parametrize("damage", ["none", "receipt", "lock"])
def test_nested_recorded_install_requires_the_same_local_proof(tmp_path, damage):
    install, version, _, link = private_install(tmp_path, "owner/fresh-install")
    if damage == "receipt":
        (install / "installation.json").unlink()
    elif damage == "lock":
        (version / "uv.lock").write_text("unrecorded lock")
    module = scanner()
    allowed = module._recorded_managed_base(
        tmp_path, link, module._lexical_symlink_target(link),
    )
    assert allowed is (damage == "none")
    findings = module.scan(tmp_path, Path("/forbidden-never-touch-legacy"))
    assert bool(findings) is (damage != "none")


@pytest.mark.parametrize("scope", ["src", "assets", ".artifacts/unrecorded/runtime/venv/bin"])
def test_arbitrary_external_links_still_fail(tmp_path, scope):
    directory = tmp_path / scope
    directory.mkdir(parents=True)
    link = directory / "python"
    link.symlink_to(managed_target(), target_is_directory=False)
    result = scanner().scan(tmp_path, Path("/forbidden-never-touch-legacy"))
    assert any(item.code == "EXTERNAL_RUNTIME_SYMLINK" for item in result)


@pytest.mark.parametrize("damage", ["none", "receipt", "lock", "config", "version_parent"])
def test_local_install_record_cannot_hide_an_arbitrary_runtime_link(tmp_path, damage):
    install, version, cfg, _ = private_install(tmp_path)
    lock = version / "uv.lock"
    record = install / "installation.json"
    if damage == "receipt":
        record.unlink()
    elif damage == "lock":
        lock.write_text("unrecorded lock")
    elif damage == "config":
        cfg.write_text("home = /unapproved/base\n")
    elif damage == "version_parent":
        # Keep its bytes recoverable; never follow this external alias.
        (install / "versions").rename(install / "saved-versions")
        (install / "versions").symlink_to("/forbidden-never-touch-legacy")
    result = scanner().scan(tmp_path, Path("/forbidden-never-touch-legacy"))
    external = any(item.code == "EXTERNAL_RUNTIME_SYMLINK" for item in result)
    assert external is (damage != "none")
