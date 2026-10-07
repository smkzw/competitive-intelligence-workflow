"""Exact source/page identity is portable; materialization is not acceptance."""

import hashlib
import json
import shutil
from datetime import UTC, datetime

import pytest

from tests.integration.test_r24_pdf_page_source_proof import _pdf_pages


def _inputs(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    raw = _pdf_pages([["China MAH: Holder Ltd", "Group Ltd controls Holder Ltd"]])
    (source / "synthetic.pdf").write_bytes(raw)
    now = datetime.now(UTC).isoformat()
    spec = {"candidate_only": True, "sources": [{
        "key": "holder", "filename": "synthetic.pdf", "sha256": hashlib.sha256(raw).hexdigest(),
        "page": 1, "paragraph": "China MAH: Holder Ltd", "url": "https://example.org/label.pdf",
    }, {"key": "group", "filename": "synthetic.pdf", "sha256": hashlib.sha256(raw).hexdigest(),
        "page": 1, "paragraph": "Group Ltd controls Holder Ltd", "url": "https://example.org/label.pdf",
    }], "entities": [
        {"key": "product", "entity_type": "product", "canonical_name": "DrugX",
         "identity_basis": "synthetic-drug"},
        {"key": "legal", "entity_type": "organization", "canonical_name": "Holder Ltd",
         "identity_basis": "synthetic-holder"},
        {"key": "parent", "entity_type": "organization", "canonical_name": "Group Ltd",
         "identity_basis": "synthetic-parent"},
    ], "relations": [
        {"subject": "product", "object": "legal", "predicate": "has_mah", "source_key": "holder",
         "jurisdiction": "CN", "authorization_scope": "synthetic China license",
         "observed_at": now},
        {"subject": "legal", "object": "parent", "predicate": "controlled_by",
         "source_key": "group",
         "observed_at": now},
    ], "product_entity_ids": {"synthetic-product": "product"}}
    path = tmp_path / "source-set.json"
    path.write_text(json.dumps(spec))
    return source, path, hashlib.sha256(path.read_bytes()).hexdigest(), tmp_path / "candidate"


def test_candidate_reopens_after_move_without_promoting_science_or_current(tmp_path):
    from tools.materialize_identity_sources import load_identity_context, materialize

    source, path, digest, output = _inputs(tmp_path)
    receipt = materialize(source, path, digest, output)
    assert receipt["science_accepted"] is False and receipt["current_promoted"] is False
    moved = tmp_path / "moved"
    shutil.move(str(output), moved)
    context = load_identity_context(moved, receipt["graph_asset"])
    projected = context.project(("synthetic-product",), cutoff=datetime.now(UTC))
    assert projected["synthetic-product"]["company_label"] == "公司：Group Ltd｜中国MAH所属集团"
    assert len(projected["synthetic-product"]["sources"]) == 2
    assert all(s["raw_sha256"] for s in projected["synthetic-product"]["sources"])
    assert not (moved / "reports/current.json").exists()


@pytest.mark.parametrize("damage", ["page", "quote", "bytes"])
def test_bad_source_is_rejected_before_candidate_creation(tmp_path, damage):
    from tools.materialize_identity_sources import materialize

    source, path, digest, output = _inputs(tmp_path)
    spec = json.loads(path.read_text())
    if damage == "bytes":
        (source / "synthetic.pdf").write_bytes(b"wrong source")
    else:
        spec["sources"][0]["page" if damage == "page" else "paragraph"] = (
            2 if damage == "page" else "not in source"
        )
        path.write_text(json.dumps(spec))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError):
        materialize(source, path, digest, output)
    assert not output.exists()


@pytest.mark.parametrize("change", ["entity", "mapping"])
def test_materialized_context_cannot_render_modified_memory_as_pinned_source(tmp_path, change):
    from ci_workflow.reports.common.identity_projection import load_identity_context
    from tools.materialize_identity_sources import materialize

    source, path, digest, output = _inputs(tmp_path)
    receipt = materialize(source, path, digest, output)
    context = load_identity_context(output, receipt["graph_asset"])
    entity_id = context.product_entity_ids["synthetic-product"]
    if change == "entity":
        entity = context.graph.entities[entity_id]
        context.graph.entities[entity_id] = entity.model_copy(update={"canonical_name": "Invented"})
    else:
        context.product_entity_ids["synthetic-product"] = "invented-id"
    with pytest.raises(ValueError, match="身份.*改变"):
        context.project(("synthetic-product",), cutoff=datetime.now(UTC))
