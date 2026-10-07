"""Joint replay of two pinned source-sets: prefix-only keys, one merged candidate.

The synthetic inputs deliberately share every source/entity reference key so the
namespace prefix is exercised; the real pinned replay runs outside pytest. Any
failure must leave the source roots untouched and must never overwrite output.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import tools.merge_identity_source_sets as merge_module
from ci_workflow.sources.connectors.public_pdf_availability import (
    PdfHttpPage,
    capture_public_pdf_availability,
)
from ci_workflow.storage.content_store import ContentAddressedStore
from tests.integration.test_r24_pdf_page_source_proof import _pdf_pages
from tools.merge_identity_source_sets import (
    IdentitySourceInput,
    compare_product_headers,
    merge_identity_source_sets,
)

_URL = "https://cdn.clinicaltrials.gov/large-docs/test/joint-synthetic.pdf"
_MUTATOR = Callable[[dict[str, Any]], None]


def _spec(
    label: str, digest: str, proof: dict[str, Any], *, holder: str, group: str, drug: str,
    target: str, jurisdiction: str, scope: str, observed_at: str,
) -> dict[str, Any]:
    witness = {"url": _URL, "public_pdf_availability": proof}
    return {
        "candidate_only": True,
        "sources": [
            {"key": "label", "filename": f"{label}-document.pdf", "sha256": digest,
             "page": 1, "paragraph": f"MAHLINE {label}: {holder}", **witness},
            {"key": "group", "filename": f"{label}-document.pdf", "sha256": digest,
             "page": 2, "paragraph": f"CONTROLLINE {label}: {group} controls {holder}",
             **witness},
            {"key": "target", "filename": f"{label}-document.pdf", "sha256": digest,
             "page": 3, "paragraph": f"TARGETLINE {label}: {target} is the target of {drug}",
             **witness},
        ],
        "entities": [
            {"key": "drug", "entity_type": "product", "canonical_name": drug,
             "identity_basis": f"synthetic-{label}-drug"},
            {"key": "holder", "entity_type": "organization", "canonical_name": holder,
             "identity_basis": f"synthetic-{label}-holder"},
            {"key": "group", "entity_type": "organization", "canonical_name": group,
             "identity_basis": f"synthetic-{label}-group"},
            {"key": "target", "entity_type": "target", "canonical_name": target,
             "identity_basis": f"synthetic-{label}-target"},
        ],
        "relations": [
            {"subject": "drug", "object": "holder", "predicate": "has_mah",
             "source_key": "label", "jurisdiction": jurisdiction,
             "authorization_scope": scope, "effective_from": "2024-01-01T00:00:00+00:00",
             "observed_at": observed_at},
            {"subject": "holder", "object": "group", "predicate": "controlled_by",
             "source_key": "group", "observed_at": observed_at},
            {"subject": "drug", "object": "target", "predicate": "has_target",
             "source_key": "target", "observed_at": observed_at},
        ],
        "product_entity_ids": {f"synthetic-product-{label}": "drug"},
    }


def _build_input(
    tmp_path: Path, label: str, *, holder: str, group: str, drug: str, target: str,
    jurisdiction: str, scope: str, mutate: _MUTATOR | None = None,
) -> IdentitySourceInput:
    root = tmp_path / f"{label}-root"
    root.mkdir()
    raw = _pdf_pages([
        [f"MAHLINE {label}: {holder}"],
        [f"CONTROLLINE {label}: {group} controls {holder}"],
        [f"TARGETLINE {label}: {target} is the target of {drug}"],
    ])
    digest = hashlib.sha256(raw).hexdigest()
    (root / f"{label}-document.pdf").write_bytes(raw)
    asset = ContentAddressedStore(root).put_bytes(raw, media_type="application/pdf")
    captured = capture_public_pdf_availability(
        root, _URL, asset,
        transport=lambda requested, timeout, limit: PdfHttpPage(
            200, "application/pdf", len(raw), raw, requested),
    )
    assert captured.witness is not None
    spec = _spec(label, digest, captured.witness.model_dump(mode="json"), holder=holder,
                 group=group, drug=drug, target=target, jurisdiction=jurisdiction,
                 scope=scope, observed_at=datetime.now(UTC).isoformat())
    if mutate is not None:
        mutate(spec)
    path = tmp_path / f"{label}-source-set.json"
    path.write_text(json.dumps(spec))
    return IdentitySourceInput(label=label, source_root=root, source_set=path,
                               expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def _alpha(tmp_path: Path, **overrides: Any) -> IdentitySourceInput:
    defaults: dict[str, Any] = {
        "holder": "Holder Alpha Ltd", "group": "Group Alpha Ltd", "drug": "AlphaDrug",
        "target": "TargetA", "jurisdiction": "US", "scope": "synthetic US license alpha",
    }
    return _build_input(tmp_path, "alpha", **{**defaults, **overrides})


def _beta(tmp_path: Path, **overrides: Any) -> IdentitySourceInput:
    defaults: dict[str, Any] = {
        "holder": "Holder Beta GmbH", "group": "Groupe Beta SA", "drug": "BetaDrug",
        "target": "TargetB", "jurisdiction": "EU", "scope": "synthetic EU license beta",
    }
    return _build_input(tmp_path, "beta", **{**defaults, **overrides})


def _snapshot(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}


def _expected_merge(alpha: IdentitySourceInput, beta: IdentitySourceInput) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    product_ids: dict[str, str] = {}
    for source_input in (alpha, beta):
        label = source_input.label
        original = json.loads(source_input.source_set.read_bytes())
        for item in original["sources"]:
            sources.append({**item, "key": f"{label}:{item['key']}"})
        for item in original["entities"]:
            entity = {**item, "key": f"{label}:{item['key']}"}
            if "name_source_key" in entity:
                entity["name_source_key"] = f"{label}:{entity['name_source_key']}"
            entities.append(entity)
        for item in original["relations"]:
            relations.append({
                **item,
                "subject": f"{label}:{item['subject']}",
                "object": f"{label}:{item['object']}",
                "source_key": f"{label}:{item['source_key']}",
            })
        for product_id, ref in original["product_entity_ids"].items():
            product_ids[product_id] = f"{label}:{ref}"
    return {"sources": sources, "entities": entities, "relations": relations,
            "product_entity_ids": product_ids}


def test_joint_merge_prefixes_reference_keys_only_and_matches_independent_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    alpha = _alpha(tmp_path)
    beta = _beta(tmp_path)
    before = {alpha.label: _snapshot(alpha.source_root), beta.label: _snapshot(beta.source_root)}
    output = tmp_path / "joint"
    calls: list[tuple[Path, Path, str, Path]] = []
    real = merge_module.materialize

    def spy(source_root: Path, source_set: Path, expected_sha: str, destination: Path,
            **kwargs: Any) -> dict[str, Any]:
        calls.append((Path(source_root), Path(source_set), expected_sha, Path(destination)))
        return real(source_root, source_set, expected_sha, destination, **kwargs)

    monkeypatch.setattr(merge_module, "materialize", spy)
    receipt = merge_identity_source_sets((alpha, beta), output)

    merged_path = output / "joint-identity-source-set-v1.json"
    merged_sha = hashlib.sha256(merged_path.read_bytes()).hexdigest()
    joint_calls = [call for call in calls if call[1] == merged_path]
    assert len(joint_calls) == 1
    assert joint_calls[0][0] == output / "sources"
    assert joint_calls[0][2] == merged_sha
    assert joint_calls[0][3] == output / "candidate"
    assert {(call[0], call[1]) for call in calls if call[1] != merged_path} == {
        (alpha.source_root, alpha.source_set), (beta.source_root, beta.source_set)}

    merged = json.loads(merged_path.read_bytes())
    assert merged["candidate_only"] is True
    expected = _expected_merge(alpha, beta)
    assert merged["sources"] == expected["sources"]
    assert merged["entities"] == expected["entities"]
    assert merged["relations"] == expected["relations"]
    assert merged["product_entity_ids"] == expected["product_entity_ids"]

    declared: dict[str, Path] = {}
    for source_input in (alpha, beta):
        original = json.loads(source_input.source_set.read_bytes())
        for item in original["sources"]:
            declared[item["filename"]] = source_input.source_root
            proof = item["public_pdf_availability"]
            declared[proof["expected_raw_asset"]["relative_path"]] = source_input.source_root
            declared[proof["receipt_asset"]["relative_path"]] = source_input.source_root
    staged = {path.relative_to(output / "sources").as_posix()
              for path in (output / "sources").rglob("*") if path.is_file()}
    assert staged == set(declared)
    for relative, root in declared.items():
        assert (output / "sources" / relative).read_bytes() == (root / relative).read_bytes()

    assert _snapshot(alpha.source_root) == before[alpha.label]
    assert _snapshot(beta.source_root) == before[beta.label]

    checkpoint = json.loads((output / "candidate" / "identity-checkpoint.json").read_bytes())
    assert checkpoint["source_set_sha256"] == merged_sha
    assert checkpoint["science_accepted"] is False and checkpoint["current_promoted"] is False

    from ci_workflow.reports.common.identity_projection import load_identity_context

    cutoff = datetime.now(UTC)
    joint = load_identity_context(output / "candidate", receipt["joint_candidate"]["receipt"]
                                  ["graph_asset"])
    assert set(joint.product_entity_ids) == {"synthetic-product-alpha", "synthetic-product-beta"}
    joint_headers = joint.project(tuple(sorted(joint.product_entity_ids)), cutoff=cutoff)
    for source_input in (alpha, beta):
        baseline = load_identity_context(
            output / "independent" / source_input.label,
            receipt["independent_baselines"][source_input.label]["receipt"]["graph_asset"])
        baseline_headers = baseline.project(tuple(sorted(baseline.product_entity_ids)),
                                            cutoff=cutoff)
        for product_id, header in baseline_headers.items():
            assert joint_headers[product_id]["entity_id"] == header["entity_id"]
            compare_product_headers(product_id, joint_headers[product_id], header)
    assert joint_headers["synthetic-product-alpha"]["company_label"] == (
        "公司：Group Alpha Ltd｜境外MAH所属集团（US）")
    assert joint_headers["synthetic-product-beta"]["company_label"] == (
        "公司：Groupe Beta SA｜境外MAH所属集团（EU）")
    assert {row["product_id"] for row in receipt["product_comparison"]} == (
        set(joint.product_entity_ids))
    assert all(row["normalized_equal"] is True for row in receipt["product_comparison"])
    assert str(tmp_path) not in json.dumps(receipt)


@pytest.mark.parametrize("kind", ["product", "basis_content", "basis_type"])
def test_conflicting_joint_identity_fails_closed_before_output(tmp_path: Path, kind: str) -> None:
    def mutate(spec: dict[str, Any]) -> None:
        if kind == "product":
            spec["product_entity_ids"] = {"synthetic-product-alpha": "drug"}
        elif kind == "basis_content":
            spec["entities"][0]["identity_basis"] = "synthetic-alpha-drug"
            spec["entities"][0]["canonical_name"] = "Renamed Beta Drug"
        else:
            spec["entities"][0]["entity_type"] = "drug_project"
            spec["entities"][0]["identity_basis"] = "synthetic-alpha-drug"

    alpha = _alpha(tmp_path)
    beta = _beta(tmp_path, mutate=mutate)
    output = tmp_path / "joint"
    with pytest.raises(ValueError, match="冲突|不一致"):
        merge_identity_source_sets((alpha, beta), output)
    assert not output.exists()


@pytest.mark.parametrize("damage", ["pin", "bytes", "symlink", "collision"])
def test_unverifiable_input_fails_closed_before_creating_output(
    tmp_path: Path, damage: str,
) -> None:
    alpha = _alpha(tmp_path)
    if damage == "collision":
        beta = _beta(tmp_path, mutate=lambda spec: [
            item.update({"filename": "alpha-document.pdf"}) for item in spec["sources"]])
    else:
        beta = _beta(tmp_path)
    if damage == "pin":
        alpha = replace(alpha, expected_sha256="0" * 64)
    elif damage == "bytes":
        (beta.source_root / "beta-document.pdf").write_bytes(b"tampered document")
    elif damage == "symlink":
        outside = tmp_path / "outside.pdf"
        outside.write_bytes((beta.source_root / "beta-document.pdf").read_bytes())
        (beta.source_root / "beta-document.pdf").unlink()
        (beta.source_root / "beta-document.pdf").symlink_to(outside)
    output = tmp_path / "joint"
    with pytest.raises((ValueError, RuntimeError)):
        merge_identity_source_sets((alpha, beta), output)
    assert not output.exists()


def _header_backbone(*, suffix: str, role: str = "中国MAH", scope: str = "scope") -> dict[str, Any]:
    return {
        "entity_id": "entity_product",
        "display_name": "合成药",
        "original_name": "DrugX",
        "aliases": ["AliasX"],
        "company_label": "公司：Holder Ltd｜中国MAH",
        "targets": [{"entity_id": "entity_target", "name": "IL-33",
                     "evidence_fragment_id": f"evidence-fragment_{suffix}"}],
        "companies": [{
            "legal_entity_id": "entity_holder", "legal_entity_name": "Holder Ltd",
            "group_entity_id": "entity_group", "group_chain_entity_ids": ["entity_holder"],
            "group_relations": [{
                "relation_id": f"entity-relation_{suffix}", "subject_entity_id": "entity_holder",
                "predicate": "controlled_by", "object_entity_id": "entity_group",
                "evidence_fragment_id": f"evidence-fragment_{suffix}",
                "jurisdiction": "CN", "authorization_scope": scope,
                "effective_from": None, "effective_until": None,
                "observed_at": "2026-01-01T00:00:00+00:00",
            }],
            "role": role, "jurisdiction": "CN", "authorization_scope": scope,
            "effective_from": None, "effective_until": None,
            "observed_at": "2026-01-01T00:00:00+00:00", "label": "Holder Ltd｜中国MAH",
            "evidence_fragment_ids": [f"evidence-fragment_{suffix}"],
        }],
        "unresolved_relations": [],
        "sources": [{
            "fragment_id": f"evidence-fragment_{suffix}",
            "source_version_id": f"source-version_{suffix}",
            "source_sha256": "aa", "raw_sha256": "bb",
            "url": "https://example.invalid/synthetic.pdf", "page": 1,
            "original_text": "quote", "acquired_at": "2026-01-02T00:00:00+00:00",
            "observed_publicly_available_at": "2026-01-01T12:00:00+00:00",
        }],
    }


def test_header_comparison_ignores_run_local_ids_but_detects_semantic_drift() -> None:
    joint = _header_backbone(suffix="a")
    independent = _header_backbone(suffix="b")
    compare_product_headers("synthetic-product", joint, independent)
    with pytest.raises(ValueError, match="不一致"):
        compare_product_headers("synthetic-product", joint,
                                _header_backbone(suffix="b", scope="drifted scope"))
    with pytest.raises(ValueError, match="不一致"):
        compare_product_headers("synthetic-product", joint,
                                _header_backbone(suffix="b", role="研发权益方"))
