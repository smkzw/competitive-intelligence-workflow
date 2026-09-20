"""论文/官方披露结果必须通过可重复、可验真的事实合并路径进入 A 类内容。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ci_workflow.application.source_research_service import FreshAResearchContent

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "fixtures/positive/a-atopic-dermatitis/research-content.json"
MANIFEST = ROOT / "fixtures/positive/a-atopic-dermatitis/curated-result-evidence.json"
TOOL = ROOT / "tools/merge_curated_result_evidence.py"


def _module():
    spec = importlib.util.spec_from_file_location("merge_curated_result_evidence", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_curated_results_add_missing_trials_and_paired_numeric_context(tmp_path: Path) -> None:
    output = tmp_path / "research-content.json"
    digest = _module().merge(BASE, MANIFEST, output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    content = FreshAResearchContent.model_validate(payload)

    assert len(digest) == 64
    assert len(content.report_data.trials) == 49
    assert len(content.sources) == 86
    trial_ids = {item.id for item in content.report_data.trials}
    assert trial_ids >= {
        "nct05544591",
        "nct05509023",
        "chictr2100051917",
        "nct06035354",
        "nct05970432",
    }
    assert "nct06018428" not in trial_ids
    bemp_trial = next(item for item in content.report_data.trials if item.id == "nct05509023")
    assert bemp_trial.product_id == "bempikibart"
    assert "特应性皮炎" in bemp_trial.name

    products = {item.id: item for item in content.report_data.products}
    for product_id in (
        "ivarmacitinib",
        "icp-332",
        "ssgj-611",
        "gr1802",
        "rezpegaldesleukin",
    ):
        assert products[product_id].result_status == "有公开关键结果"
        efficacy_arms = {
            row.arm for row in content.report_data.efficacy if row.product_id == product_id
        }
        safety_arms = {
            row.arm
            for row in content.report_data.safety
            if row.product_id == product_id
            and row.term in {"任何TEAE", "任何TEAE（不含注射部位反应）", "任何SAE"}
            and row.value is not None
        }
        assert efficacy_arms >= {"治疗组", "对照组"}
        assert safety_arms >= {"治疗组", "对照组"}

    icp_rows = {
        (row.arm, row.value)
        for row in content.report_data.efficacy
        if row.product_id == "icp-332" and row.endpoint == "EASI-75"
    }
    assert icp_rows >= {("治疗组", 64.0), ("对照组", 8.0)}
    assert all(
        row.numerator is None
        for row in content.report_data.efficacy
        if row.product_id == "icp-332" and row.endpoint == "EASI-75"
    )

    rezpeg_safety = {
        (row.arm, row.term, row.value)
        for row in content.report_data.safety
        if row.product_id == "rezpegaldesleukin" and row.value is not None
    }
    assert rezpeg_safety >= {
        ("治疗组", "任何TEAE（不含注射部位反应）", 66.3),
        ("对照组", "任何TEAE（不含注射部位反应）", 57.5),
        ("治疗组", "任何SAE", 1.0),
        ("对照组", "任何SAE", 0.0),
    }

    primary_report_teae = {
        (row.product_id, row.arm, row.value, row.time_window)
        for row in content.report_data.safety
        if row.product_id
        in {
            "tralokinumab",
            "roflumilast-cream",
            "nemolizumab",
            "abrocitinib",
            "dupilumab",
            "lebrikizumab",
            "upadacitinib",
            "baricitinib",
            "ruxolitinib-cream",
            "tapinarof",
        }
        and row.term == "任何TEAE"
        and row.value is not None
    }
    assert primary_report_teae >= {
        ("tralokinumab", "治疗组", 76.4, "16周初始双盲治疗期"),
        ("tralokinumab", "对照组", 77.0, "16周初始双盲治疗期"),
        ("roflumilast-cream", "治疗组", 21.2, "4周双盲治疗期"),
        ("roflumilast-cream", "对照组", 15.8, "4周双盲治疗期"),
        ("nemolizumab", "治疗组", 50.0, "16周初始双盲治疗期"),
        ("nemolizumab", "对照组", 45.0, "16周初始双盲治疗期"),
        ("abrocitinib", "治疗组", 78.0, "12周双盲治疗期"),
        ("abrocitinib", "对照组", 57.0, "12周双盲治疗期"),
        ("dupilumab", "治疗组", 73.0, "16周双盲治疗期"),
        ("dupilumab", "对照组", 65.0, "16周双盲治疗期"),
        ("lebrikizumab", "治疗组", 45.7, "16周诱导期"),
        ("lebrikizumab", "对照组", 51.8, "16周诱导期"),
        ("upadacitinib", "治疗组", 73.3, "16周双盲治疗期"),
        ("upadacitinib", "对照组", 59.1, "16周双盲治疗期"),
        ("baricitinib", "治疗组", 58.0, "16周双盲治疗期"),
        ("baricitinib", "对照组", 54.0, "16周双盲治疗期"),
        ("ruxolitinib-cream", "治疗组", 29.2, "8周基质对照期"),
        ("ruxolitinib-cream", "对照组", 34.9, "8周基质对照期"),
        ("tapinarof", "治疗组", 45.6, "8周双盲治疗期"),
        ("tapinarof", "对照组", 25.5, "8周双盲治疗期"),
    }

    ak120_efficacy = {
        (row.arm, row.value)
        for row in content.report_data.efficacy
        if row.product_id == "ak120" and row.endpoint == "EASI-75"
    }
    assert ak120_efficacy >= {("治疗组", 57.5), ("对照组", 28.2)}
    assert products["ak120"].result_status == "已有部分公开结果"
    assert not any(
        row.product_id == "ak120" and row.term == "任何TEAE"
        for row in content.report_data.safety
    )

    replaced_products = {
        "lebrikizumab",
        "nemolizumab",
        "abrocitinib",
        "upadacitinib",
        "baricitinib",
        "tapinarof",
        "roflumilast-cream",
    }
    assert not any(
        row.product_id in replaced_products
        and row.term == "任何TEAE"
        and row.value is None
        for row in content.report_data.safety
    )

    for product_id in ("eblasakimab", "apg777", "difamilast", "ak120"):
        assert products[product_id].result_status == "已有部分公开结果"
        efficacy_arms = {
            row.arm
            for row in content.report_data.efficacy
            if row.product_id == product_id and row.value is not None
        }
        assert efficacy_arms >= {"治疗组", "对照组"}


def test_curated_source_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    module = _module()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["sources"][0]["content_sha256"] = "0" * 64
    altered = tmp_path / "manifest.json"
    altered.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    source_dir = tmp_path / "sources"
    source_dir.symlink_to(MANIFEST.parent / "sources", target_is_directory=True)

    with pytest.raises(module.MergeError, match="原始来源摘要不一致"):
        module.merge(BASE, altered, tmp_path / "research-content.json")


def test_partial_numeric_result_cannot_be_relabelled_as_no_public_result(
    tmp_path: Path,
) -> None:
    output = tmp_path / "research-content.json"
    _module().merge(BASE, MANIFEST, output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    product = next(
        item
        for item in payload["report_data"]["products"]
        if item["id"] == "eblasakimab"
    )
    product["result_status"] = "暂无公开关键结果"

    with pytest.raises(ValueError, match="报告产品结果状态"):
        FreshAResearchContent.model_validate(payload)


def test_marketed_product_without_paired_teae_fails_closed(tmp_path: Path) -> None:
    output = tmp_path / "research-content.json"
    _module().merge(BASE, MANIFEST, output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["report_data"]["safety"] = [
        row
        for row in payload["report_data"]["safety"]
        if not (
            row["product_id"] == "dupilumab"
            and row["term"] == "任何TEAE"
            and row["arm"] == "对照组"
        )
    ]

    with pytest.raises(ValueError, match="已获批竞品缺少治疗组与对照组总体TEAE"):
        FreshAResearchContent.model_validate(payload)
