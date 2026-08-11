from __future__ import annotations

import pytest


def test_registry_json_locator_reopens_exact_field() -> None:
    from ci_workflow.ingestion.locators import (
        RegistryJsonSnapshot,
        create_registry_json_locator,
        reopen_registry_json_locator,
    )

    payload = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT01234567"},
            "outcomesModule": {
                "primaryOutcomes": [
                    {
                        "measure": "NPS 较基线变化",
                        "timeFrame": "第 24 周",
                    }
                ]
            },
        }
    }
    snapshot = RegistryJsonSnapshot.create(
        source_version_id="source-version-ctgov-001",
        payload=payload,
        source_url="https://clinicaltrials.gov/study/NCT01234567",
        document_role_label_zh="美国临床试验登记平台",
    )
    field_path = "protocolSection.outcomesModule.primaryOutcomes[0].timeFrame"
    locator = create_registry_json_locator(snapshot, field_path=field_path)

    assert reopen_registry_json_locator(snapshot, locator) == "第 24 周"
    assert locator.evidence_locator.field_path == field_path
    assert locator.evidence_locator.url == snapshot.source_url
    assert locator.source_version_id == snapshot.source_version_id
    assert locator.source_content_sha256 == snapshot.content_sha256

    payload["protocolSection"]["outcomesModule"]["primaryOutcomes"][0][
        "timeFrame"
    ] = "被外部修改"
    assert reopen_registry_json_locator(snapshot, locator) == "第 24 周"

    changed_snapshot = RegistryJsonSnapshot.create(
        source_version_id="source-version-ctgov-002",
        payload={
            **snapshot.payload,
            "protocolSection": {
                **snapshot.payload["protocolSection"],
                "outcomesModule": {
                    "primaryOutcomes": [
                        {"measure": "NPS 较基线变化", "timeFrame": "第 52 周"}
                    ]
                },
            },
        },
        source_url=snapshot.source_url,
        document_role_label_zh=snapshot.document_role_label_zh,
    )
    with pytest.raises(ValueError, match="来源版本或内容摘要不一致"):
        reopen_registry_json_locator(changed_snapshot, locator)

    tampered_registry_locator = locator.model_copy(
        update={
            "evidence_locator": locator.evidence_locator.model_copy(
                update={
                    "field_path": "protocolSection.outcomesModule.primaryOutcomes[0].measure"
                }
            )
        }
    )
    with pytest.raises(ValueError, match="定位器身份校验失败"):
        reopen_registry_json_locator(snapshot, tampered_registry_locator)


def test_web_locator_reopens_exact_heading_and_paragraph() -> None:
    from ci_workflow.ingestion.locators import (
        WebPageSnapshot,
        create_web_paragraph_locator,
        reopen_web_paragraph_locator,
    )

    snapshot = WebPageSnapshot.create(
        source_version_id="source-version-web-001",
        source_url="https://example-pharma.com/news/phase-3-results",
        document_role_label_zh="企业正式披露",
        sections=(
            {
                "heading": "研究概况",
                "paragraphs": ("研究共随机 420 例受试者。",),
            },
            {
                "heading": "主要疗效",
                "paragraphs": (
                    "主要终点为第 24 周 NPS 较基线变化。",
                    "试验组变化为 -2.1，安慰剂组为 -0.8。",
                ),
            },
            {
                "heading": "主要疗效",
                "paragraphs": ("第二项研究的主要疗效结果。",),
            },
        ),
    )
    locator = create_web_paragraph_locator(
        snapshot,
        heading="主要疗效",
        heading_occurrence=1,
        paragraph_number=2,
    )

    assert reopen_web_paragraph_locator(snapshot, locator) == (
        "试验组变化为 -2.1，安慰剂组为 -0.8。"
    )
    assert locator.evidence_locator.heading == "主要疗效"
    assert locator.evidence_locator.paragraph == "第 2 段"
    assert locator.evidence_locator.url == snapshot.source_url
    assert locator.heading_occurrence == 1
    assert locator.paragraph_number == 2
    second_occurrence = create_web_paragraph_locator(
        snapshot,
        heading="主要疗效",
        heading_occurrence=2,
        paragraph_number=1,
    )
    assert reopen_web_paragraph_locator(snapshot, second_occurrence) == (
        "第二项研究的主要疗效结果。"
    )

    changed = WebPageSnapshot.create(
        source_version_id="source-version-web-002",
        source_url=snapshot.source_url,
        document_role_label_zh=snapshot.document_role_label_zh,
        sections=(
            {
                "heading": "主要疗效",
                "paragraphs": ("页面内容已经更新。",),
            },
        ),
    )
    with pytest.raises(ValueError, match="来源版本或内容摘要不一致"):
        reopen_web_paragraph_locator(changed, locator)

    tampered_web_locator = locator.model_copy(update={"heading_occurrence": 2})
    with pytest.raises(ValueError, match="定位器身份校验失败"):
        reopen_web_paragraph_locator(snapshot, tampered_web_locator)


def test_pdf_locator_reopens_page_table_row_and_cell() -> None:
    from ci_workflow.ingestion.locators import (
        PdfDocumentSnapshot,
        create_pdf_table_cell_locator,
        reopen_pdf_table_cell_locator,
    )

    snapshot = PdfDocumentSnapshot.create(
        source_version_id="source-version-pdf-001",
        source_url="https://journal.example.org/article/main.pdf",
        document_role_label_zh="论文全文",
        pages=(
            {
                "page_number": 12,
                "tables": (
                    {
                        "table_name": "表 3 安全性汇总",
                        "columns": ("安全性事件", "试验组", "安慰剂组"),
                        "rows": (
                            ("任何不良事件", "81.0%", "78.5%"),
                            ("严重不良事件", "3.0%", "4.0%"),
                        ),
                    },
                ),
            },
        ),
    )
    locator = create_pdf_table_cell_locator(
        snapshot,
        page_number=12,
        table_name="表 3 安全性汇总",
        row_number=2,
        column_name="试验组",
    )

    assert reopen_pdf_table_cell_locator(snapshot, locator) == "3.0%"
    assert locator.evidence_locator.page == 12
    assert locator.evidence_locator.table == "表 3 安全性汇总"
    assert locator.evidence_locator.row == "第 2 行：严重不良事件"
    assert locator.evidence_locator.column == "试验组"
    assert locator.evidence_locator.url == snapshot.source_url

    with pytest.raises(ValueError, match="未找到指定列"):
        create_pdf_table_cell_locator(
            snapshot,
            page_number=12,
            table_name="表 3 安全性汇总",
            row_number=2,
            column_name="不存在的组别",
        )

    changed = PdfDocumentSnapshot.create(
        source_version_id="source-version-pdf-002",
        source_url=snapshot.source_url,
        document_role_label_zh=snapshot.document_role_label_zh,
        pages=(
            {
                "page_number": 12,
                "tables": (
                    {
                        "table_name": "表 3 安全性汇总",
                        "columns": ("安全性事件", "试验组", "安慰剂组"),
                        "rows": (("严重不良事件", "2.0%", "4.0%"),),
                    },
                ),
            },
        ),
    )
    with pytest.raises(ValueError, match="来源版本或内容摘要不一致"):
        reopen_pdf_table_cell_locator(changed, locator)

    tampered_pdf_locator = locator.model_copy(update={"row_number": 1})
    with pytest.raises(ValueError, match="定位器身份校验失败"):
        reopen_pdf_table_cell_locator(snapshot, tampered_pdf_locator)
    tampered_table_name = locator.model_copy(update={"table_name": "其他表格"})
    with pytest.raises(ValueError, match="定位器身份校验失败"):
        reopen_pdf_table_cell_locator(snapshot, tampered_table_name)
    tampered_column_name = locator.model_copy(update={"column_name": "安全性事件"})
    with pytest.raises(ValueError, match="定位器身份校验失败"):
        reopen_pdf_table_cell_locator(snapshot, tampered_column_name)

    with pytest.raises(ValueError, match="同一页内表名不得重复"):
        PdfDocumentSnapshot.create(
            source_version_id="source-version-pdf-ambiguous",
            source_url=snapshot.source_url,
            document_role_label_zh=snapshot.document_role_label_zh,
            pages=(
                {
                    "page_number": 12,
                    "tables": (
                        {
                            "table_name": "表 3 安全性汇总",
                            "columns": ("事件", "试验组"),
                            "rows": (("任何不良事件", "81.0%"),),
                        },
                        {
                            "table_name": "表 3  安全性汇总",
                            "columns": ("事件", "试验组"),
                            "rows": (("严重不良事件", "3.0%"),),
                        },
                    ),
                },
            ),
        )


def test_supplement_and_user_file_preserve_parent_identity_and_hash() -> None:
    from ci_workflow.ingestion.classifier import SourceDocumentInput, classify_source
    from ci_workflow.ingestion.fragmenter import create_document_version

    main = create_document_version(
        document_identity="NCT01234567-main-publication",
        classification=classify_source(
            SourceDocumentInput(
                filename="publisher-main-article.pdf",
                media_type="application/pdf",
                source_family="publication",
                ingestion_channel="automatic",
            )
        ),
        content=b"main publication content",
        version_label="2026-07-01",
    )
    supplement_bytes = b"supplementary appendix content"
    supplement = create_document_version(
        document_identity="NCT01234567-supplement-1",
        classification=classify_source(
            SourceDocumentInput(
                filename="mmc1.pdf",
                media_type="application/pdf",
                source_family="publication",
                ingestion_channel="automatic",
                relationship_role="supplementary_material",
                parent_document_id=main.document_id,
            )
        ),
        content=supplement_bytes,
        version_label="2026-07-01",
    )
    user_file = create_document_version(
        document_identity="NCT01234567-user-copy-1",
        classification=classify_source(
            SourceDocumentInput(
                filename="系统不会要求用户重命名的原文件.pdf",
                media_type="application/pdf",
                source_family="unknown",
                ingestion_channel="manual_inbox",
                relationship_role="supplementary_material",
                parent_document_id=main.document_id,
            )
        ),
        content=supplement_bytes,
        version_label="2026-07-01",
    )

    assert supplement.parent_document_id == main.document_id
    assert user_file.parent_document_id == main.document_id
    assert supplement.document_id != main.document_id
    assert user_file.document_id != supplement.document_id
    assert supplement.content_sha256 == user_file.content_sha256
    assert supplement.original_filename == "mmc1.pdf"
    assert user_file.original_filename == "系统不会要求用户重命名的原文件.pdf"
    assert supplement.canonical_filename.startswith(
        "NCT01234567-supplement-1_论文补充材料_2026-07-01_"
    )
    assert user_file.canonical_filename.startswith(
        "NCT01234567-user-copy-1_用户补充文件_2026-07-01_"
    )
    assert supplement.canonical_filename.endswith(".pdf")
    assert user_file.canonical_filename.endswith(".pdf")
    assert supplement.source_version_id != user_file.source_version_id
