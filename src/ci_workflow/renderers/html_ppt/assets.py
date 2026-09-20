"""Locked Task 8.4 runtime, Kangzhe FX, and logo inlining."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]

ASSET_SPECS: dict[str, tuple[str, str]] = {
    "runtime_js": (
        "assets/html-ppt/runtime.js",
        "affadf9e344ec9da62cdd27942a41218983d2cb88a377eca540b7da622a990f7",
    ),
    "runtime_css": (
        "assets/html-ppt/runtime.css",
        "09df452da708ac80a9660bb49ff8603cfac85aec7e607852c99ca09a209517d0",
    ),
    "gx_fx_css": (
        "contracts/kangzhe/design_specs/assets/htmlppt/gx_fx.css",
        "7e2ba09538f2e9c59c07f2ad2c8f708828c71f5f8e71771c5aa337da6bb5a572",
    ),
    "gx_fx_js": (
        "contracts/kangzhe/design_specs/assets/htmlppt/gx_fx.js",
        "92cdb59102b888db0d046caeae34700cc29c97275dba626a652560603cb9c86b",
    ),
    "logo": (
        "contracts/kangzhe/design_specs/assets/logo_bot.svg",
        "8d16d3ae8353dd31f46a50d401e66f9e62af40be6cc42cdf5050866a4e6e1cae",
    ),
}

INPUT_SPECS: dict[str, tuple[str, str]] = {
    "A": (
        "fixtures/positive/a-atopic-dermatitis/research-content.json",
        "988c1607e08c7f9747a6feb493dcdaf66b6ccd7c26cafefe96e956622196fa1a",
    ),
    "B": (
        "fixtures/positive/b-pnh/inputs/report-data.json",
        "eeae14ce581aeacc6c098cde5f45571e4d0f88d2cc5877cba5429654448381d1",
    ),
    "C": (
        "fixtures/positive/c-atopic-dermatitis/inputs/report-data.json",
        "a59d7f88b3d8a2e163422c01f0d0981aa64bf2610cc6bb41852c58e9561ed2e6",
    ),
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require_hash(path: Path, expected: str, *, label: str) -> bytes:
    payload = path.read_bytes()
    digest = sha256_bytes(payload)
    if digest != expected:
        raise ValueError(f"{label} 哈希不符：{path} 实际 {digest} 期望 {expected}")
    return payload


@dataclass(frozen=True)
class InlineAssets:
    runtime_js: str
    runtime_css: str
    gx_fx_css: str
    gx_fx_js: str
    logo_data_url: str
    hashes: dict[str, str]


def load_inline_assets(*, root: Path | None = None) -> InlineAssets:
    base = root or REPO_ROOT
    texts: dict[str, str] = {}
    hashes: dict[str, str] = {}
    logo_url = ""
    for key, (rel, expected) in ASSET_SPECS.items():
        path = base / rel
        payload = require_hash(path, expected, label=key)
        hashes[key] = expected
        if key == "logo":
            logo_url = "data:image/svg+xml;base64," + base64.b64encode(payload).decode("ascii")
        else:
            texts[key] = payload.decode("utf-8")
    return InlineAssets(
        runtime_js=texts["runtime_js"],
        runtime_css=texts["runtime_css"],
        gx_fx_css=texts["gx_fx_css"],
        gx_fx_js=texts["gx_fx_js"],
        logo_data_url=logo_url,
        hashes=hashes,
    )


def load_locked_json(report: str, *, root: Path | None = None) -> tuple[dict[str, Any], str]:
    base = root or REPO_ROOT
    try:
        rel, expected = INPUT_SPECS[report]
    except KeyError as exc:
        raise ValueError(f"未知报告类型：{report}") from exc
    path = base / rel
    payload = require_hash(path, expected, label=f"input-{report}")
    import json

    data = json.loads(payload.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{report} 输入根节点必须是对象")
    return data, expected
