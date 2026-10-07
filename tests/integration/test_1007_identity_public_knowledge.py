"""Public knowledge, observation and name boundaries are independent of mtime."""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest

from ci_workflow.capabilities.extraction_normalization import verify_reopened_fragment
from ci_workflow.capabilities.lineage_registry import ScientificLineageRegistry
from ci_workflow.domain.entities import EntityGraph, EntityIdentity, EntityRelation, EntityType
from ci_workflow.domain.evidence import DateEvidence, EvidenceLocator
from ci_workflow.reports.common.identity_projection import project_product_identity
from ci_workflow.storage.content_store import ContentAddressedStore, EvidenceRepository
from ci_workflow.storage.migrations import apply_migrations


def _published_registry(root, labels, *, published=True):
    """Synthetic publication evidence, not a local acquisition masquerading as one."""
    database = root / "identity-evidence/state/project.sqlite"
    apply_migrations(database)
    repo = EvidenceRepository(database, ContentAddressedStore(root / "identity-evidence"))
    now = datetime.now(UTC)
    locator = EvidenceLocator(document_role="synthetic_identity", paragraph="publication")
    date = DateEvidence(state="reported", value=now - timedelta(days=1), locator=locator)
    unknown = DateEvidence(state="not_publicly_disclosed", value=None, locator=locator)
    source = repo.add_source_version(source_id="synthetic-publication",
        content="\n".join(f"{label} 对应的身份原文证据" for label in labels).encode(),
        media_type="text/plain", acquired_at=now,
        published_at=date if published else unknown,
        effective_at=unknown, first_disclosed_at=unknown)
    verified = []
    for label in labels:
        text = f"{label} 对应的身份原文证据"
        fragment = repo.add_fragment(source_version_id=source.source_version_id,
            locator=EvidenceLocator(document_role="synthetic_identity", paragraph=text),
            original_text=text, created_at=now)
        verified.append(verify_reopened_fragment(fragment, reopened_original_text=text,
            source_version_id=source.source_version_id, repository=repo))
    return ScientificLineageRegistry.from_verified_fragments(tuple(verified))


def _relation(root, *, published=True, future_observed=False):
    registry = _published_registry(root, ("正式中文名", "holder"), published=published)
    refs = [item.fragment.fragment_id for item in registry.verified_fragments]
    now = registry.verified_fragments[0].source_version.acquired_at
    graph = EntityGraph()
    product = EntityIdentity.create(EntityType.PRODUCT, "Original-INN", "test-knowledge")
    holder = EntityIdentity.create(EntityType.ORGANIZATION, "Holder", "synthetic-holder-identity")
    for item in (product, holder):
        graph.add_entity(item)
    graph.add_relation(EntityRelation.create(product, "has_mah", holder, refs[1],
        jurisdiction="CN", authorization_scope="synthetic license",
        observed_at=now + timedelta(days=1) if future_observed else now,
        effective_from=now - timedelta(days=2)))
    return graph, registry, refs, now, product


def test_acquisition_alone_is_not_public_knowledge(tmp_path):
    graph, registry, _, now, product = _relation(tmp_path, published=False)
    result = project_product_identity(product.entity_id, graph, registry, cutoff=now)
    assert result["companies"] == []
    assert result["unresolved_relations"][0]["reason"] == "not_known_at_cutoff"


def test_old_effective_date_does_not_waive_future_observation(tmp_path):
    graph, registry, _, now, product = _relation(tmp_path, future_observed=True)
    result = project_product_identity(product.entity_id, graph, registry, cutoff=now)
    assert result["companies"] == []
    assert result["unresolved_relations"][0]["reason"] == "not_known_at_cutoff"


def test_substring_of_formal_name_is_not_an_exact_source_name(tmp_path):
    graph, registry, refs, now, product = _relation(tmp_path)
    graph.entities[product.entity_id] = product.model_copy(update={
        "official_chinese_name": "中文", "name_evidence_fragment_id": refs[0]})
    result = project_product_identity(product.entity_id, graph, registry, cutoff=now)
    assert result["display_name"] == "Original-INN"


def test_materialized_local_pdf_without_public_proof_remains_unresolved(tmp_path):
    from tests.integration.test_1007_identity_source_replay import _inputs
    from tools.materialize_identity_sources import load_identity_context, materialize

    source, path, _, output = _inputs(tmp_path)
    spec = json.loads(path.read_text())
    for item in spec["sources"]:
        item.pop("public_pdf_availability", None)
    path.write_text(json.dumps(spec))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = materialize(source, path, digest, output)
    result = load_identity_context(output, receipt["graph_asset"]).project(
        ("synthetic-product",), cutoff=datetime.now(UTC))["synthetic-product"]
    assert result["companies"] == []


def test_current_witness_cannot_answer_an_earlier_historical_cutoff(tmp_path):
    from tests.integration.test_1007_identity_source_replay import _inputs
    from tools.materialize_identity_sources import load_identity_context, materialize

    source, path, digest, output = _inputs(tmp_path)
    receipt = materialize(source, path, digest, output)
    context = load_identity_context(output, receipt["graph_asset"])
    current = context.project(("synthetic-product",), cutoff=datetime.now(UTC))
    assert "Group Ltd" in current["synthetic-product"]["company_label"]
    historical = context.project(("synthetic-product",),
                                 cutoff=datetime.now(UTC) - timedelta(days=1))
    assert historical["synthetic-product"]["companies"] == []


def test_forged_public_receipt_is_rejected_before_creating_candidate(tmp_path):
    from tests.integration.test_1007_identity_source_replay import _inputs
    from tools.materialize_identity_sources import materialize

    source, path, _, output = _inputs(tmp_path)
    spec = json.loads(path.read_text())
    spec["sources"][0]["public_pdf_availability"]["observed_available_at"] = (
        datetime.now(UTC) - timedelta(days=10)).isoformat()
    path.write_text(json.dumps(spec))
    with pytest.raises(ValueError):
        materialize(source, path, hashlib.sha256(path.read_bytes()).hexdigest(), output)
    assert not output.exists()


@pytest.mark.parametrize("url", [
    "https://www.sanofi.cn/assets/label.pdf",
    "https://www.sanofi.com/assets/filing.pdf",
])
def test_supported_official_company_documents_use_same_exact_byte_witness(tmp_path, url):
    from ci_workflow.sources.connectors.public_pdf_availability import (
        PdfHttpPage,
        capture_public_pdf_availability,
        verify_public_pdf_availability,
    )

    raw = b"%PDF-1.7\nsynthetic-company-document"
    asset = ContentAddressedStore(tmp_path).put_bytes(raw, media_type="application/pdf")
    result = capture_public_pdf_availability(tmp_path, url, asset,
        transport=lambda requested, timeout, limit: PdfHttpPage(
            200, "application/pdf", len(raw), raw, requested))
    assert result.witness is not None
    assert verify_public_pdf_availability(tmp_path, result.witness, url, asset,
                                         datetime.now(UTC)) == raw


def test_public_receipt_is_reopened_after_move_and_rejects_corruption(tmp_path):
    from tests.integration.test_1007_identity_source_replay import _inputs
    from tools.materialize_identity_sources import load_identity_context, materialize

    source, path, digest, output = _inputs(tmp_path)
    receipt = materialize(source, path, digest, output)
    context = load_identity_context(output, receipt["graph_asset"])
    witness = next(iter(context.public_pdf_availability.values()))
    assert witness.receipt_asset is not None
    (output / witness.receipt_asset.relative_path).write_bytes(b"corrupted-receipt")
    with pytest.raises(ValueError):
        load_identity_context(output, receipt["graph_asset"])


def test_pinned_in_memory_witness_cannot_be_backdated(tmp_path):
    from tests.integration.test_1007_identity_source_replay import _inputs
    from tools.materialize_identity_sources import load_identity_context, materialize

    source, path, digest, output = _inputs(tmp_path)
    receipt = materialize(source, path, digest, output)
    context = load_identity_context(output, receipt["graph_asset"])
    key = next(iter(context.public_pdf_availability))
    witness = context.public_pdf_availability[key]
    context.public_pdf_availability[key] = witness.model_copy(update={
        "observed_available_at": witness.observed_available_at - timedelta(days=10)})
    with pytest.raises(ValueError, match="身份.*改变"):
        context.project(("synthetic-product",), cutoff=datetime.now(UTC))
