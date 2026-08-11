from __future__ import annotations

from pathlib import Path

import pytest


def test_cde_route_versions_drug_and_regulatory_status() -> None:
    from ci_workflow.sources.connectors.china_registries import (
        ChinaRegulatoryRecordVersion,
        build_china_regulatory_timeline,
    )

    accepted = ChinaRegulatoryRecordVersion.create(
        source_system="CDE",
        external_record_id="CXSL2600001",
        product_name="测试创新药注射液",
        application_number="CXSL2600001",
        indication="慢性鼻窦炎伴鼻息肉",
        event_type="application_accepted",
        status_label_zh="已受理",
        occurred_on="2026-01-05",
        published_at="2026-01-06T09:00:00+08:00",
        acquired_at="2026-08-10T09:00:00+08:00",
        content_snapshot="CXSL2600001 已受理，适应症为慢性鼻窦炎伴鼻息肉。",
        source_url="https://www.cde.org.cn/example/CXSL2600001",
        locator_label="受理品种信息第 1 行",
    )
    under_review = ChinaRegulatoryRecordVersion.create(
        source_system="CDE",
        external_record_id="CXSL2600001",
        product_name="测试创新药注射液",
        application_number="CXSL2600001",
        indication="慢性鼻窦炎伴鼻息肉",
        event_type="review_in_progress",
        status_label_zh="审评中",
        occurred_on="2026-02-01",
        published_at="2026-02-02T09:00:00+08:00",
        acquired_at="2026-08-11T09:00:00+08:00",
        content_snapshot="CXSL2600001 当前处于审评中。",
        source_url="https://www.cde.org.cn/example/CXSL2600001",
        locator_label="审评任务公示第 1 行",
    )
    approved = ChinaRegulatoryRecordVersion.create(
        source_system="NMPA",
        external_record_id="国药准字S20260001",
        product_name="测试创新药注射液",
        application_number="国药准字S20260001",
        indication="慢性鼻窦炎伴鼻息肉",
        event_type="marketing_approved",
        status_label_zh="批准上市",
        occurred_on="2026-07-01",
        published_at="2026-07-02T09:00:00+08:00",
        acquired_at="2026-08-11T09:00:00+08:00",
        content_snapshot="国药准字S20260001 已批准上市。",
        source_url="https://www.nmpa.gov.cn/example/S20260001",
        locator_label="药品批准信息",
    )

    assert accepted.source_record_id == under_review.source_record_id
    assert accepted.source_version_id != under_review.source_version_id
    assert accepted.is_marketing_approval is False
    assert under_review.is_marketing_approval is False
    assert approved.is_marketing_approval is True
    assert accepted.authority == "CDE"
    assert approved.authority == "NMPA"
    assert accepted.locator.paragraph == "受理品种信息第 1 行"
    assert accepted.locator.url == accepted.source_url

    timeline = build_china_regulatory_timeline((approved, under_review, accepted))
    assert [item.event_type for item in timeline] == [
        "application_accepted",
        "review_in_progress",
        "marketing_approved",
    ]
    assert len({item.event_id for item in timeline}) == 3
    assert all(item.jurisdiction == "CN" for item in timeline)

    with pytest.raises(ValueError, match="CDE 专有事项不能归属 NMPA"):
        ChinaRegulatoryRecordVersion.create(
            source_system="NMPA",
            external_record_id="错误映射-001",
            product_name="测试创新药注射液",
            application_number="错误映射-001",
            indication="慢性鼻窦炎伴鼻息肉",
            event_type="review_in_progress",
            status_label_zh="审评中",
            occurred_on="2026-02-01",
            published_at="2026-02-02T09:00:00+08:00",
            acquired_at="2026-08-11T09:00:00+08:00",
            content_snapshot="错误映射记录",
            source_url="https://www.nmpa.gov.cn/example/invalid",
            locator_label="错误映射",
        )

    with pytest.raises(ValueError, match="对应机构官方网站"):
        ChinaRegulatoryRecordVersion.model_validate(
            {**accepted.model_dump(), "source_url": "https://evil.invalid/record"}
        )


def test_chinadrugtrials_route_versions_trial_fields_and_results() -> None:
    from ci_workflow.sources.connectors.china_registries import (
        ChinaDrugTrialVersion,
        build_china_trial_search_url,
        extract_china_trial_observations,
    )

    first = ChinaDrugTrialVersion.from_public_record(
        {
            "ctr_number": "CTR20260001",
            "trial_status": "进行中 招募中",
            "protocol_number": "CMS-K10-301",
            "protocol_version": "V1.0",
            "updated_on": "2026-03-01",
            "first_disclosed_on": "2026-03-01",
            "sections": {
                "试验题目": "测试创新药治疗慢性鼻窦炎伴鼻息肉的 III 期研究",
                "目标适应症": "慢性鼻窦炎伴鼻息肉",
                "入选标准": ["筛选期双侧 NPS 总分至少 5 分"],
                "试验分组": [
                    {"组别": "试验组", "用法用量": "每 4 周皮下注射 300 mg"},
                    {"组别": "安慰剂组", "用法用量": "每 4 周皮下注射"},
                ],
                "主要终点": [
                    {"指标": "NPS 较基线变化", "时间点": "第 24 周"}
                ],
            },
        },
        acquired_at="2026-08-10T09:00:00+08:00",
        source_url="https://www.chinadrugtrials.org.cn/example/CTR20260001",
    )
    with_results = ChinaDrugTrialVersion.from_public_record(
        {
            "ctr_number": "ctr20260001",
            "trial_status": "已完成",
            "protocol_number": "CMS-K10-301",
            "protocol_version": "V2.0",
            "updated_on": "2026-08-01",
            "first_disclosed_on": "2026-08-01",
            "sections": {
                "试验题目": "测试创新药治疗慢性鼻窦炎伴鼻息肉的 III 期研究",
                "目标适应症": "慢性鼻窦炎伴鼻息肉",
                "入选标准": ["筛选期双侧 NPS 总分至少 5 分"],
                "试验分组": [
                    {"组别": "试验组", "用法用量": "每 4 周皮下注射 300 mg"},
                    {"组别": "安慰剂组", "用法用量": "每 4 周皮下注射"},
                ],
                "主要终点": [
                    {"指标": "NPS 较基线变化", "时间点": "第 24 周"}
                ],
                "试验结果摘要": {
                    "主要疗效": "试验组 -2.1，安慰剂组 -0.8",
                    "严重不良事件": "试验组 3.0%，安慰剂组 4.0%",
                },
            },
        },
        acquired_at="2026-08-11T09:00:00+08:00",
        source_url="https://www.chinadrugtrials.org.cn/example/CTR20260001",
    )

    assert first.ctr_number == "CTR20260001"
    assert first.source_trial_id == with_results.source_trial_id
    assert first.source_version_id != with_results.source_version_id
    assert first.result_disclosure_state == "not_publicly_disclosed"
    assert with_results.result_disclosure_state == "reported"
    assert first.protocol_version == "V1.0"
    assert with_results.protocol_version == "V2.0"
    assert first.first_disclosed_precision == "calendar_day"
    assert first.first_disclosed_at.isoformat() == "2026-03-01T00:00:00+08:00"
    assert first.content_sha256

    with pytest.raises(ValueError, match="官方平台链接"):
        ChinaDrugTrialVersion.model_validate(
            {**first.model_dump(), "source_url": "https://evil.invalid/CTR20260001"}
        )
    with pytest.raises(ValueError, match="摘要与已保存正文不一致"):
        ChinaDrugTrialVersion.model_validate(
            {**first.model_dump(), "raw_record_json": '{"forged":true}'}
        )
    with pytest.raises(ValueError, match="必须按北京时间保存"):
        ChinaDrugTrialVersion.model_validate(
            {
                **first.model_dump(),
                "first_disclosed_at": "2026-03-01T00:00:00+00:00",
            }
        )

    observations = extract_china_trial_observations(with_results)
    by_path = {item.locator.field_path: item for item in observations}
    design_path = "sections.主要终点[0].时间点"
    result_path = "sections.试验结果摘要.主要疗效"
    assert by_path[design_path].claim_domain == "trial_design"
    assert by_path[design_path].original_value == "第 24 周"
    assert by_path[result_path].claim_domain == "trial_results"
    assert by_path[result_path].original_value == "试验组 -2.1，安慰剂组 -0.8"
    assert by_path[result_path].locator.url == with_results.source_url
    assert build_china_trial_search_url("ctr20260001").endswith(
        "clinicaltrials.searchlist.dhtml?keywords=CTR20260001"
    )

    mutable_copy = with_results.raw_record
    mutable_copy["sections"]["主要终点"][0]["时间点"] = "被篡改"
    fresh_paths = {
        item.locator.field_path: item for item in extract_china_trial_observations(with_results)
    }
    assert fresh_paths[design_path].original_value == "第 24 周"


def test_dxy_drug_assistant_and_official_china_pages_keep_source_roles() -> None:
    from ci_workflow.sources.connectors.china_registries import (
        ChinaDrugReferenceVersion,
    )
    from ci_workflow.sources.policy import ClaimDomain, SourceAuthority, SourcePolicy

    policy = SourcePolicy.from_yaml(Path("policies/sources/source-policy-v1.yaml"))

    dxy = ChinaDrugReferenceVersion.create(
        policy=policy,
        source_system="dxy_drug_assistant",
        external_record_id="drug-10001",
        product_name="测试创新药注射液",
        content_label_zh="国内说明书用法用量",
        published_at="2026-06-01T09:00:00+08:00",
        acquired_at="2026-08-11T09:00:00+08:00",
        content_sha256="4" * 64,
        source_url="https://drugs.dxy.cn/example/drug-10001",
        locator_label="说明书：用法用量",
    )
    nmpa = ChinaDrugReferenceVersion.create(
        policy=policy,
        source_system="nmpa_official",
        external_record_id="国药准字S20260001",
        product_name="测试创新药注射液",
        content_label_zh="药品批准证明文件",
        published_at="2026-07-02T09:00:00+08:00",
        acquired_at="2026-08-11T09:00:00+08:00",
        content_sha256="5" * 64,
        source_url="https://www.nmpa.gov.cn/example/S20260001",
        locator_label="药品批准信息",
    )
    cde = ChinaDrugReferenceVersion.create(
        policy=policy,
        source_system="cde_official",
        external_record_id="CXSL2600001",
        product_name="测试创新药注射液",
        content_label_zh="审评任务公示",
        published_at="2026-02-02T09:00:00+08:00",
        acquired_at="2026-08-11T09:00:00+08:00",
        content_sha256="6" * 64,
        source_url="https://www.cde.org.cn/example/CXSL2600001",
        locator_label="审评任务公示第 1 行",
    )

    assert dxy.source_role == "secondary_drug_reference"
    assert dxy.source_role_label_zh == "专业药品资料（二次参考）"
    assert dxy.may_establish_official_regulatory_status is False
    assert nmpa.source_role == "official_marketing_authority"
    assert nmpa.source_role_label_zh == "国家药品监督管理局官方信息"
    assert nmpa.may_establish_official_regulatory_status is True
    assert cde.source_role == "official_review_authority"
    assert cde.source_role_label_zh == "国家药品监督管理局药品审评中心官方信息"
    assert cde.may_establish_official_regulatory_status is True
    assert dxy.locator.url == dxy.source_url
    assert dxy.policy_id == policy.policy_id
    assert dxy.policy_version == policy.version
    assert len({dxy.source_version_id, nmpa.source_version_id, cde.source_version_id}) == 3

    with pytest.raises(ValueError, match="丁香园用药助手不能标记为官方监管来源"):
        dxy.model_copy(
            update={
                "source_role": "official_marketing_authority",
                "may_establish_official_regulatory_status": True,
            }
        ).__class__.model_validate(
            {
                **dxy.model_dump(),
                "source_role": "official_marketing_authority",
                "may_establish_official_regulatory_status": True,
            }
        )

    dxy_source = policy.source("dxy_drug_assistant")
    drifted_authorities = dict(dxy_source.authorities)
    drifted_authorities[
        ClaimDomain.CHINA_DEVELOPMENT_REGULATORY_STATUS
    ] = SourceAuthority.DIRECT
    drifted_source = dxy_source.model_copy(update={"authorities": drifted_authorities})
    drifted_policy = policy.model_copy(
        update={
            "sources": tuple(
                drifted_source if item.source_id == drifted_source.source_id else item
                for item in policy.sources
            )
        }
    )
    with pytest.raises(ValueError, match="限定为二次参考"):
        ChinaDrugReferenceVersion.create(
            policy=drifted_policy,
            source_system="dxy_drug_assistant",
            external_record_id="drug-10001",
            product_name="测试创新药注射液",
            content_label_zh="国内说明书用法用量",
            published_at="2026-06-01T09:00:00+08:00",
            acquired_at="2026-08-11T09:00:00+08:00",
            content_sha256="4" * 64,
            source_url="https://drugs.dxy.cn/example/drug-10001",
            locator_label="说明书：用法用量",
        )


def test_cde_guidance_preserves_version_status_population_context_locator_and_supersession() -> None:  # noqa: E501
    from ci_workflow.sources.connectors.china_registries import (
        capture_cde_guideline_basis,
    )
    from ci_workflow.sources.connectors.regulators import (
        select_current_guideline_basis,
        validate_guideline_lineage,
    )

    current_seed = capture_cde_guideline_basis(
        document_id="chronic-rhinosinusitis-drug-development",
        title="慢性鼻窦炎治疗药物临床试验技术指导原则",
        guidance_status="final",
        version_date="2025-06-01",
        population_context="成人慢性鼻窦炎受试者",
        development_context="确证性药物临床试验主要终点",
        source_url="https://www.cde.org.cn/example/crs-guidance-2025.pdf",
        locator_label="第 8 页：主要疗效终点",
        locator_page=8,
        content_sha256="d" * 64,
        captured_at="2026-08-11T09:00:00+08:00",
        lifecycle_status="active",
    )
    old_final = capture_cde_guideline_basis(
        document_id="chronic-rhinosinusitis-drug-development",
        title="慢性鼻窦炎治疗药物临床试验技术指导原则",
        guidance_status="final",
        version_date="2021-06-01",
        population_context="成人慢性鼻窦炎受试者",
        development_context="确证性药物临床试验主要终点",
        source_url="https://www.cde.org.cn/example/crs-guidance-2021.pdf",
        locator_label="第 6 页：主要疗效终点",
        locator_page=6,
        content_sha256="e" * 64,
        captured_at="2026-08-10T09:00:00+08:00",
        lifecycle_status="superseded",
        superseded_by_version_id=current_seed.guideline_version_id,
    )
    current = capture_cde_guideline_basis(
        document_id="chronic-rhinosinusitis-drug-development",
        title="慢性鼻窦炎治疗药物临床试验技术指导原则",
        guidance_status="final",
        version_date="2025-06-01",
        population_context="成人慢性鼻窦炎受试者",
        development_context="确证性药物临床试验主要终点",
        source_url="https://www.cde.org.cn/example/crs-guidance-2025.pdf",
        locator_label="第 8 页：主要疗效终点",
        locator_page=8,
        content_sha256="d" * 64,
        captured_at="2026-08-11T09:00:00+08:00",
        lifecycle_status="active",
        supersedes_version_ids=(old_final.guideline_version_id,),
    )
    draft = capture_cde_guideline_basis(
        document_id="crs-endpoint-draft",
        title="慢性鼻窦炎临床试验终点技术建议（征求意见稿）",
        guidance_status="draft",
        version_date="2026-07-01",
        population_context="成人慢性鼻窦炎受试者",
        development_context="探索性终点建议",
        source_url="https://www.cde.org.cn/example/crs-endpoint-draft.pdf",
        locator_label="第 4 页：终点建议",
        locator_page=4,
        content_sha256="f" * 64,
        captured_at="2026-08-11T09:00:00+08:00",
        lifecycle_status="active",
    )

    assert current.jurisdiction == "CN"
    assert current.agency == "CDE"
    assert current.guidance_status == "final"
    assert current.population_context == "成人慢性鼻窦炎受试者"
    assert current.locator.page == 8
    assert current.locator.paragraph == "第 8 页：主要疗效终点"
    assert old_final.can_drive_current_default is False
    assert draft.can_drive_current_default is False
    validate_guideline_lineage((old_final, current, draft))
    assert select_current_guideline_basis(
        (old_final, current, draft),
        jurisdiction="CN",
        population_context="成人慢性鼻窦炎受试者",
    ) == (current,)
