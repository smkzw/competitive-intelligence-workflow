from __future__ import annotations


def test_ctgov_pagination_versions_and_study_identity() -> None:
    from ci_workflow.sources.connectors.clinicaltrials_gov import (
        ClinicalTrialsGovCapture,
        build_next_page_url,
    )

    first = ClinicalTrialsGovCapture.from_api_payload(
        {
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT02912468",
                            "briefTitle": "SINUS-24",
                        },
                        "statusModule": {
                            "lastUpdatePostDateStruct": {
                                "date": "2019-07-25",
                                "type": "ACTUAL",
                            }
                        },
                    },
                    "derivedSection": {
                        "miscInfoModule": {"versionHolder": "2026-08-10"}
                    },
                }
            ],
            "nextPageToken": "第二页令牌/含特殊字符=",
        },
        acquired_at="2026-08-10T09:00:00+08:00",
    )
    second = ClinicalTrialsGovCapture.from_api_payload(
        {
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "nct02912468",
                            "briefTitle": "SINUS-24 updated",
                        },
                        "statusModule": {
                            "lastUpdatePostDateStruct": {
                                "date": "2020-01-02",
                                "type": "ACTUAL",
                            }
                        },
                    },
                    "derivedSection": {
                        "miscInfoModule": {"versionHolder": "2026-08-11"}
                    },
                }
            ]
        },
        acquired_at="2026-08-11T09:00:00+08:00",
    )
    same_scientific_record_next_day = ClinicalTrialsGovCapture.from_api_payload(
        {
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT02912468",
                            "briefTitle": "SINUS-24",
                        },
                        "statusModule": {
                            "lastUpdatePostDateStruct": {
                                "date": "2019-07-25",
                                "type": "ACTUAL",
                            }
                        },
                    },
                    "derivedSection": {
                        "miscInfoModule": {"versionHolder": "2026-08-11"}
                    },
                }
            ]
        },
        acquired_at="2026-08-11T09:00:00+08:00",
    )

    assert first.next_page_token == "第二页令牌/含特殊字符="
    assert (
        build_next_page_url(
            "https://clinicaltrials.gov/api/v2/studies?query.cond=CRSwNP&pageSize=1000",
            first.next_page_token,
        )
        == "https://clinicaltrials.gov/api/v2/studies?query.cond=CRSwNP&pageSize=1000&"
        "pageToken=%E7%AC%AC%E4%BA%8C%E9%A1%B5%E4%BB%A4%E7%89%8C%2F%E5%90%AB%E7%89%B9%E6%AE%8A%E5%AD%97%E7%AC%A6%3D"
    )
    assert first.studies[0].nct_id == "NCT02912468"
    assert second.studies[0].nct_id == "NCT02912468"
    assert first.studies[0].source_study_id == second.studies[0].source_study_id
    assert first.studies[0].source_version_id != second.studies[0].source_version_id
    assert (
        first.studies[0].source_version_id
        == same_scientific_record_next_day.studies[0].source_version_id
    )
    assert first.studies[0].platform_version_holder == "2026-08-10"
    assert first.studies[0].registry_posted_version_date == "2019-07-25"
    assert first.studies[0].history_url.endswith("NCT02912468?tab=history")


def test_ctgov_results_and_design_fields_keep_registry_locators() -> None:
    from ci_workflow.sources.connectors.clinicaltrials_gov import (
        ClinicalTrialsGovStudyVersion,
        extract_registry_observations,
    )

    study = ClinicalTrialsGovStudyVersion.from_api_record(
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT02912468",
                    "briefTitle": "SINUS-24",
                },
                "statusModule": {
                    "lastUpdatePostDateStruct": {
                        "date": "2019-07-25",
                        "type": "ACTUAL",
                    }
                },
                "eligibilityModule": {
                    "eligibilityCriteria": "NPS 双侧总分至少 5 分",
                },
                "armsInterventionsModule": {
                    "armGroups": [
                        {
                            "label": "度普利尤单抗",
                            "interventionNames": ["DRUG: Dupilumab"],
                        }
                    ]
                },
                "outcomesModule": {
                    "primaryOutcomes": [
                        {
                            "measure": "第 24 周 NPS 较基线变化",
                            "timeFrame": "基线至第 24 周",
                        }
                    ]
                },
            },
            "resultsSection": {
                "participantFlowModule": {
                    "groups": [{"id": "FG000", "title": "度普利尤单抗"}]
                },
                "outcomeMeasuresModule": {
                    "outcomeMeasures": [
                        {
                            "title": "第 24 周 NPS 较基线变化",
                            "type": "PRIMARY",
                            "classes": [
                                {
                                    "categories": [
                                        {
                                            "measurements": [
                                                {
                                                    "groupId": "FG000",
                                                    "value": "-2.06",
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ],
                        }
                    ]
                },
                "adverseEventsModule": {
                    "seriousEvents": [{"term": "哮喘", "organSystem": "呼吸系统"}]
                },
            },
            "derivedSection": {
                "miscInfoModule": {"versionHolder": "2026-08-11"}
            },
        },
        acquired_at="2026-08-11T09:00:00+08:00",
    )

    observations = extract_registry_observations(study)
    mutable_copy = study.raw_record
    mutable_copy["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = "被篡改"
    assert (
        extract_registry_observations(study)[0].original_value
        == "NPS 双侧总分至少 5 分"
    )
    by_path = {item.locator.field_path: item for item in observations}
    eligibility_path = "protocolSection.eligibilityModule.eligibilityCriteria"
    result_path = (
        "resultsSection.outcomeMeasuresModule.outcomeMeasures[0].classes[0]."
        "categories[0].measurements[0].value"
    )
    safety_path = "resultsSection.adverseEventsModule.seriousEvents[0].term"

    assert by_path[eligibility_path].claim_domain == "trial_design"
    assert by_path[eligibility_path].original_value == "NPS 双侧总分至少 5 分"
    assert by_path[result_path].claim_domain == "trial_results"
    assert by_path[result_path].original_value == "-2.06"
    assert by_path[safety_path].claim_domain == "trial_results"
    assert all(item.source_version_id == study.source_version_id for item in observations)
    assert all(item.locator.document_role == "ClinicalTrials.gov 登记记录" for item in observations)
    assert all(item.locator.url == study.record_url for item in observations)


def test_ctgov_publications_section_creates_cross_reference_edges() -> None:
    from ci_workflow.sources.connectors.clinicaltrials_gov import (
        ClinicalTrialsGovStudyVersion,
        create_publication_cross_references,
    )

    study = ClinicalTrialsGovStudyVersion.from_api_record(
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT02912468",
                    "briefTitle": "SINUS-24",
                },
                "statusModule": {
                    "lastUpdatePostDateStruct": {
                        "date": "2019-07-25",
                        "type": "ACTUAL",
                    }
                },
                "referencesModule": {
                    "references": [
                        {
                            "pmid": "31543428",
                            "type": "RESULT",
                            "citation": "Dupilumab efficacy and safety in CRSwNP.",
                        },
                        {
                            "pmid": "37026112",
                            "type": "DERIVED",
                            "citation": "Post hoc analysis of SINUS-24 and SINUS-52.",
                        },
                        {
                            "type": "BACKGROUND",
                            "citation": "Background paper without PMID.",
                        },
                        {
                            "pmid": "40000009",
                            "type": "DERIVED",
                        },
                    ]
                },
            },
            "derivedSection": {
                "miscInfoModule": {"versionHolder": "2026-08-11"}
            },
        },
        acquired_at="2026-08-11T09:00:00+08:00",
    )

    edges = create_publication_cross_references(study)
    assert [(item.nct_id, item.pmid) for item in edges] == [
        ("NCT02912468", "31543428"),
        ("NCT02912468", "37026112"),
        ("NCT02912468", "40000009"),
    ]
    assert [item.platform_reference_type for item in edges] == [
        "RESULT",
        "DERIVED",
        "DERIVED",
    ]
    assert all(item.publication_role == "unclassified" for item in edges)
    assert edges[1].citation is not None
    assert edges[1].citation.startswith("Post hoc")
    assert edges[1].locator.field_path == (
        "protocolSection.referencesModule.references[1]"
    )
    assert edges[1].locator.url == study.record_url
    assert edges[2].citation is None
    assert edges[2].citation_state == "not_publicly_disclosed"
