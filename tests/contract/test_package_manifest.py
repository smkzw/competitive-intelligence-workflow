from __future__ import annotations

import json
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import cast

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_INTERNAL_SKILLS = {
    "intake-preflight",
    "ontology-universe",
    "source-routing",
    "ingestion-identity",
    "extraction-normalization",
    "identity-conflict",
    "coverage-gates",
    "analysis-a",
    "analysis-b",
    "analysis-c",
    "scientific-qc",
    "render-deliver",
    "visual-package-qc",
    "correction-refresh",
    "monitoring",
}
EXPECTED_CLI_CATALOG = [
    "package verify",
    "project create",
    "project verify",
    "project run",
    "capability preflight",
    "fixture run",
]


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, raw, body = text.split("---\n", 2)
    value = yaml.safe_load(raw)
    assert isinstance(value, dict)
    assert body.strip()
    return cast(dict[str, object], value)


def _yaml_object(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_package_manifest_closes_public_skill_internal_skills_and_current_components() -> None:
    manifest = _load_json(ROOT / "package-manifest.json")
    schema = _load_json(ROOT / "schemas" / "package-manifest.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    package = cast(dict[str, object], manifest["package"])
    assert package["name"] == project["name"]
    assert package["version"] == project["version"]
    assert package["cli_version"] == project["version"]
    assert package["build_stage"] == "phase-2-accepted"
    assert package["hosts"] == ["codex", "hermes", "omp"]

    public_path = ROOT / str(manifest["public_skill"])
    public_meta = _frontmatter(public_path)
    assert public_meta["name"] == "competitive-intelligence-workflow"
    assert set(public_meta) == {"name", "description"}
    assert "TODO" not in str(public_meta["description"])
    public_agent = _yaml_object(public_path.parent / "agents" / "openai.yaml")
    public_interface = cast(dict[str, object], public_agent["interface"])
    assert "$competitive-intelligence-workflow" in str(public_interface["default_prompt"])

    internal = cast(list[dict[str, object]], manifest["internal_skills"])
    assert {str(item["id"]) for item in internal} == EXPECTED_INTERNAL_SKILLS
    assert len(internal) == len(EXPECTED_INTERNAL_SKILLS)
    for item in internal:
        skill_id = str(item["id"])
        path = ROOT / str(item["path"])
        meta = _frontmatter(path)
        assert meta["name"] == skill_id
        assert set(meta) == {"name", "description"}
        assert "TODO" not in str(meta["description"])
        body = path.read_text(encoding="utf-8")
        for heading in ("## 输入合同", "## 输出合同", "## 禁止行为", "## 失败与恢复"):
            assert heading in body
        agent = _yaml_object(path.parent / "agents" / "openai.yaml")
        interface = cast(dict[str, object], agent["interface"])
        policy = cast(dict[str, object], agent["policy"])
        assert f"${skill_id}" in str(interface["default_prompt"])
        assert policy["allow_implicit_invocation"] is False

    components = cast(dict[str, list[str]], manifest["components"])
    for category in ("schemas", "contracts", "assets", "migrations"):
        assert components[category]
        for relative_path in components[category]:
            assert (ROOT / relative_path).exists(), relative_path
    assert components["policies"] == [
        "policies/gates/A-v1.yaml",
        "policies/gates/B-v1.yaml",
        "policies/gates/C-v1.yaml",
        "policies/ontology/innovation-therapy-v1.yaml",
        "policies/recovery/source-strategies-v1.yaml",
        "policies/sources/source-policy-v1.yaml",
    ]
    assert "migrations/0008_project_lineage_guards.sql" in components["migrations"]
    assert "migrations/0009_source_date_precision.sql" in components["migrations"]

    cli = cast(dict[str, object], manifest["cli"])
    assert cli["catalog"] == EXPECTED_CLI_CATALOG
    extra_command = deepcopy(manifest)
    cast(dict[str, object], extra_command["cli"])["catalog"] = [
        *EXPECTED_CLI_CATALOG,
        "project execute",
    ]
    assert list(Draft202012Validator(schema).iter_errors(extra_command))

    declared_schema = set(components["schemas"])
    actual_schema = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.glob("schemas/**/*.schema.json")
    } | {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.glob("contracts/**/*.schema.json")
    }
    assert declared_schema == actual_schema
