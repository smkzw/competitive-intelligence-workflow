"""Synthetic root-family cases from the independent primary-MN user task."""
from ciw.analyze.design import build_design
from ciw.analyze.design_excerpts import design_excerpts
from ciw.analyze.results import build_results
from ciw.config import ConceptCfg, DesignTopicCfg
from ciw.models import Design, GroupValue, Locator, OutcomeResult, TimePoint, Trial
from ciw.research import QueryPlan, _mark_planned_concepts, registry_config
from ciw.store import Workspace


def example(text=""):
    return Trial(trial_id="synthetic-basket", registry="ctgov", locator=Locator(source_id="s"),
                 conditions=["CRSwNP", "Asthma"], design=Design(eligibility_text=text))


def test_threshold_topic_covers_unplanned_cutoffs_and_retains_manual_configuration(tmp_path):
    original = dict(name_en="Example disease", name_zh="示例疾病", conditions=["Example disease"],
                    design_topics=[dict(label="量表入排阈值", terms=["Score ≥60 points", "Score ≥30 points"],
                                        aliases=["评分"], kind="eligibility_threshold")])
    cfg, _ = registry_config(QueryPlan.model_validate(original), {})
    t = example("Score ≥40 points; independent assay <20 units.")
    found = design_excerpts(t, cfg.design_topics)
    assert found and "≥40" in found[0]["snippets"][0]["text"]
    assert cfg.design_topics[0].aliases == ["评分"]
    ws = Workspace(tmp_path)
    ws.write_stage("research-query-plan", dict(plan=original))
    # Exact legacy plan-derived patterns may be upgraded; deliberate user patterns must stay.
    cfg.design_topics[0].patterns = [r"Score\ ≥60\ points", r"Score\ ≥30\ points"]
    _mark_planned_concepts(cfg, ws)
    assert design_excerpts(t, cfg.design_topics)
    cfg.design_topics[0].patterns = ["Manual qualification"]
    _mark_planned_concepts(cfg, ws)
    assert cfg.design_topics[0].patterns == ["Manual qualification"]


def test_topic_excerpt_targets_clause_not_unrelated_paragraph_start():
    t = example("Biopsy may be waived when Assay-A ≥20 units. Serum albumin <30 g/L is required.")
    topics = [DesignTopicCfg(label="白蛋白入排阈值", patterns=["serum albumin"])]
    snippet = design_excerpts(t, topics)[0]["snippets"][0]
    assert snippet["text"].startswith("Serum albumin")
    assert "Biopsy" not in snippet["text"]
    assert "Biopsy" in snippet["context"] and "Assay-A" in t.design.eligibility_text


def test_regimen_background_and_followup_select_their_actual_clauses():
    t = example()
    t.design.detailed_description = (
        "Disease burden is substantial. The treatment regimen is 200 mg intravenously every 4 weeks. "
        "Participants have a post-treatment follow-up period of 20 weeks.")
    from ciw.models import Arm
    t.arms = [Arm(arm_id="a", label="Drug", description=(
        "Participants continue background therapy throughout treatment. "
        "Nonresponders receive standard of care rescue therapy."))]
    topics = [DesignTopicCfg(label="给药方案", patterns=["treatment regimen"]),
              DesignTopicCfg(label="背景治疗", patterns=["background therapy", "standard of care"]),
              DesignTopicCfg(label="停药后随访", patterns=["follow-up period"])]
    found = {t["label"]: t["snippets"] for t in design_excerpts(t, topics)}
    assert found["给药方案"][0]["text"].startswith("The treatment regimen")
    assert found["停药后随访"][0]["text"].startswith("Participants have")
    assert len(found["背景治疗"]) == 1 and "rescue" not in found["背景治疗"][0]["text"]
    assert all("Disease burden" not in s["text"] for snippets in found.values() for s in snippets)


def test_mixed_study_stays_available_with_explicit_whole_study_scope_and_search_labels(cfg):
    local = cfg.model_copy(deep=True)
    local.design_topics = [DesignTopicCfg(label="评分阈值", patterns=["Score"], aliases=["严重度评分"])]
    t = example("Score ≥40 points")
    row = build_design(local, [t], {})["rows"][0]
    assert row["condition_scope"]["other_conditions"] == ["Asthma"]
    assert row["condition_scope"]["target_conditions"] == ["CRSwNP"]
    assert row["population_extent"] == "全研究"
    assert "严重度评分" in row["search_text"] and "评分阈值" in row["search_text"]
    assert row["eligibility"] == t.design.eligibility_text  # no whole-record deletion


def test_mixed_study_other_and_unknown_outcomes_do_not_enter_target_plots(cfg):
    local = cfg.model_copy(deep=True)
    local.concepts = [ConceptCfg(id="score", label="评分", patterns=["Score"])]
    t = example()
    def outcome(rid, description, population=""):
        return OutcomeResult(result_id=rid, trial_id=t.trial_id, outcome_index=0, type="PRIMARY",
            title="Score change", description=description, population=population, concept_id="score",
            domain="efficacy", measure_kind="mean", unit="points", locator=Locator(source_id="s"),
            time=TimePoint(raw="Week 12", label="第12周", key="W12", weeks=12),
            groups=[GroupValue(group_id="g", title="Drug", n=10, value=3)])
    results = [outcome("target", "CRSwNP cohort only"), outcome("other", "Asthma cohort only"),
               outcome("unknown", "Full analysis set"), outcome("pooled", "CRSwNP and Asthma cohorts")]
    before = [r.model_dump() for r in results]
    body = build_results(local, {t.trial_id: t}, {}, results, None)
    assert {r["result_id"] for q in body["questions"] for r in q["rows"]} == {"target"}
    assert {r["result_id"] for r in body["observations"]} == {"target", "other", "unknown", "pooled"}
    assert {p["result_id"] for c in body["longitudinal"] for line in c["lines"] for p in line["points"]} <= {"target"}
    statuses = {r["result_id"]: r["condition_scope"]["status"] for r in body["observations"]}
    assert statuses == {"target": "target", "other": "other", "unknown": "unresolved", "pooled": "mixed"}
    assert [r.model_dump() for r in results] == before


def test_safety_mixed_registration_keeps_all_source_values_and_marks_scope(cfg):
    from ciw.analyze.results import build_safety
    from ciw.models import CountN, SafetyGroup, SafetySummary
    t = example()
    safety = SafetySummary(trial_id=t.trial_id, locator=Locator(source_id="s"), groups=[
        SafetyGroup(group_id="one", title="CRSwNP cohort", serious=CountN(n=0, N=20)),
        SafetyGroup(group_id="two", title="Asthma cohort", serious=CountN(n=2, N=30)),
        SafetyGroup(group_id="all", title="All treated", serious=CountN(n=2, N=50))])
    rows = build_safety({t.trial_id: t}, {}, [safety], cfg)
    assert {r["group_title"]: (r["sae_n"], r["N"], r["condition_scope"]["status"]) for r in rows} == {
        "CRSwNP cohort": (0, 20, "target"), "Asthma cohort": (2, 30, "other"),
        "All treated": (2, 50, "unresolved")}


def test_explicit_analysis_population_outranks_study_background_and_negation_not_rewritten(cfg):
    from ciw.analyze.condition_scope import result_scope, study_scope
    t = example()
    r = OutcomeResult(result_id="x", trial_id=t.trial_id, outcome_index=0, type="PRIMARY",
        title="Score", description="The study recruits CRSwNP and Asthma cohorts.",
        population="CRSwNP cohort", measure_kind="mean", locator=Locator(source_id="s"))
    assert result_scope(cfg, t, r)["status"] == "target"
    t.conditions = ["CRSwNP"]
    t.design.eligibility_text = "Exclusion: Asthma."
    assert not study_scope(cfg, t)["multiple_conditions"]


def test_chinese_topic_and_alias_search_uses_the_same_filtered_matrix_and_chart_rows():
    import json
    import subprocess
    from pathlib import Path
    script = r"""
const fs=require('fs'),vm=require('vm'),els={},saved={},callbacks={};
const get=id=>els[id]||(els[id]={id,value:'',checked:false,style:{},parentElement:{},
 addEventListener:(event,fn)=>callbacks[id]=fn});
const rows=[{trial_id:'one',title:'Proteinuria',eligibility:'Proteinuria >5 g/day',
 search_text:'尿蛋白入排阈值 蛋白尿',products:[],primary:[],primary_concepts:[],phase:'III',masking:'',
 enrollment:20,start:'2026-01-01'},
 {trial_id:'two',title:'Other criterion',eligibility:'Other criterion',search_text:'其他指标',
 products:[],primary:[],primary_concepts:[],phase:'III',masking:'',enrollment:10,start:'2026-01-01'}];
const window={U:{D:{c:{rows},indication:{}},esc:s=>s||'',src:()=>'',options(){},drawer(){},
 chart:(id,opt)=>saved[id]=opt,table:(el,cols,rs)=>saved[el.id]=rs,OWN:'orange',PAL:['blue']}};
const document={getElementById:get};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,document});
const result=[];for(const q of ['尿蛋白','蛋白尿','absent','']){get('q').value=q;callbacks.q();
 result.push({count:get('count').textContent,ids:saved.matrix.map(r=>r.trial_id),
 allSizeIds:saved['size-data'].map(r=>r.trial_id),plotHidden:!!get('size-chart').hidden});}
process.stdout.write(JSON.stringify(result));
"""
    asset = Path(__file__).resolve().parents[1] / "src/ciw/render/static/c.js"
    result = json.loads(subprocess.run(["node", "-e", script, str(asset)], capture_output=True,
                                       text=True, check=True).stdout)
    assert [row["ids"] for row in result] == [["one"], ["one"], [], ["one", "two"]]
    assert all(row["ids"] == row["allSizeIds"] for row in result)
    assert result[2]["plotHidden"] and not result[3]["plotHidden"]


def test_zero_safety_denominator_cannot_fall_through_to_another_population(cfg):
    from ciw.analyze.results import build_safety
    from ciw.models import CountN, SafetyGroup, SafetySummary
    t = example()
    safety = SafetySummary(trial_id=t.trial_id, locator=Locator(source_id="s"), groups=[
        SafetyGroup(group_id="g", title="CRSwNP cohort", serious=CountN(n=0, N=0), other=CountN(n=1, N=20))])
    row = build_safety({t.trial_id: t}, {}, [safety], cfg)[0]
    assert row["N"] == 0 and row["sae_n"] == 0 and row["sae_pct"] is None
