from __future__ import annotations

import pytest


def test_classifier_identifies_registry_web_pdf_supplement_slides_release_and_manual_file() -> None:  # noqa: E501
    from ci_workflow.ingestion.classifier import SourceDocumentInput, classify_source

    cases = (
        (
            SourceDocumentInput(
                filename="NCT01234567.json",
                media_type="application/json",
                source_family="clinical_trial_registry",
                ingestion_channel="automatic",
            ),
            "registry_record",
            "临床试验登记记录",
        ),
        (
            SourceDocumentInput(
                filename="study-page.html",
                media_type="text/html",
                source_family="general_web",
                ingestion_channel="automatic",
            ),
            "web_page",
            "网页资料",
        ),
        (
            SourceDocumentInput(
                filename="main-article.pdf",
                media_type="application/pdf",
                source_family="publication",
                ingestion_channel="automatic",
            ),
            "publication_pdf",
            "论文全文",
        ),
        (
            SourceDocumentInput(
                filename="supplement-1.pdf",
                media_type="application/pdf",
                source_family="publication",
                ingestion_channel="automatic",
                relationship_role="supplementary_material",
                parent_document_id="document-main-001",
            ),
            "supplementary_material",
            "论文补充材料",
        ),
        (
            SourceDocumentInput(
                filename="EAACI-2026-presentation.pptx",
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                source_family="conference",
                ingestion_channel="automatic",
            ),
            "conference_slides",
            "学术会议演示材料",
        ),
        (
            SourceDocumentInput(
                filename="phase-3-topline.html",
                media_type="text/html",
                source_family="company_disclosure",
                ingestion_channel="automatic",
            ),
            "company_release",
            "企业正式披露",
        ),
        (
            SourceDocumentInput(
                filename="publisher-original-name.pdf",
                media_type="application/pdf",
                source_family="unknown",
                ingestion_channel="manual_inbox",
            ),
            "user_provided_file",
            "用户补充文件",
        ),
    )

    for source, expected_role, expected_label in cases:
        result = classify_source(source)
        assert result.document_role == expected_role
        assert result.document_role_label_zh == expected_label
        assert result.original_filename == source.filename
        assert result.classification_state == "classified"

    pending = classify_source(
        SourceDocumentInput(
            filename="无法确认的资料.bin",
            media_type="application/octet-stream",
            source_family="unknown",
            ingestion_channel="automatic",
        )
    )
    assert pending.document_role == "review_pending"
    assert pending.document_role_label_zh == "资料类型待确认"
    assert pending.classification_state == "review_pending"

    with pytest.raises(ValueError, match="补充材料必须关联主文档"):
        SourceDocumentInput(
            filename="orphan-supplement.pdf",
            media_type="application/pdf",
            source_family="publication",
            ingestion_channel="automatic",
            relationship_role="supplementary_material",
        )
