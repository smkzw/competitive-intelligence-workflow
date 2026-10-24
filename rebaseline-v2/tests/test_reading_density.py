"""Actual reading roots: short tokens and default content, never discarded source facts."""
from html.parser import HTMLParser
from pathlib import Path

import pytest
from test_nmpa_current_projection import workspace as workspace  # noqa: PLC0414
from test_quote_requalification import _legacy, _source
from test_quote_requalification import env as env  # noqa: PLC0414

from ciw2.render.portal import _env, render_report


class DefaultText(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.stack=[]; self.text=[]; self.feed(html)

    def handle_starttag(self, tag, attrs):
        visible=not self.stack or self.stack[-1][1]
        if self.stack and self.stack[-1][0]=='details' and tag!='summary':
            visible=False
        if tag not in {'input','br','hr','meta','link','col'}:
            self.stack.append((tag,visible))

    def handle_endtag(self, tag):
        for index in range(len(self.stack)-1,-1,-1):
            if self.stack[index][0]==tag:
                del self.stack[index:]; break

    def handle_data(self, text):
        if not self.stack or (self.stack[-1][1] and self.stack[-1][0]!='details'): self.text.append(text)


def test_shared_clinical_header_keeps_holder_and_developer_without_repeating_long_applicant():
    companies=[{'role':role,'name':name,'fact_id':fid,'source_id':'source','quote':name}
        for role,name,fid in [('中国MAH','真实法律持有人','holder'),('研发方','研发企业','developer'),
                              ('登记申请人','完整登记申请人法律实体','applicant')]]
    identity={'drug_label':'正式药名','registry_id':'TEST','indication':'特应性皮炎',
              'phase_label':'III 期','companies':companies}
    html=str(_env.get_template('_trial.html').module.clinical_trial(identity))
    visible=''.join(DefaultText(html).text)
    assert '中国MAH' in visible and '真实法律持有人' in visible and '研发企业' in visible
    assert '完整登记申请人法律实体' not in visible
    assert all(text in html for text in ('完整登记申请人法律实体','data-fact-id="applicant"','其他企业'))


def test_only_applicant_is_not_hidden_or_relabelled_as_mah():
    identity={'drug_label':'药物','registry_id':'TEST',
              'companies':[{'role':'登记申请人','name':'唯一登记申请人'}]}
    html=str(_env.get_template('_trial.html').module.clinical_trial(identity))
    visible=''.join(DefaultText(html).text)
    assert '唯一登记申请人' in visible and '登记申请人' in visible and '中国MAH' not in visible


@pytest.mark.parametrize('condition',[
    '外用药控制不佳或不建议使用外用药的6个月及以上儿童和成人中重度特应性皮炎。',
    '外用药控制不佳或不建议使用外用药的6个月及以上儿童和成人中重度特应性皮炎，并保留来源中的完整既往治疗条件。',
])
def test_long_condition_is_folded_verbatim_not_replaced_with_project_scope(condition):
    identity={'drug_label':'药物','registry_id':'TEST','indication':condition,
              'conditions_original':[condition],'scope_indication':'不能代入的项目标签','phase_label':'III 期'}
    html=str(_env.get_template('_trial.html').module.clinical_trial(identity))
    visible=''.join(DefaultText(html).text)
    assert condition not in visible and 'III 期' in visible
    assert '登记人群与适应症' in visible and condition in html
    assert '不能代入的项目标签' not in html


def test_c_value_sources_are_inline_named_and_age_is_not_duplicated(env):
    svc,rc,pid,trial=env;sid=_source(rc)
    _legacy(rc,trial,sid,field='design.sample_size',value=240,extracted_by='code:test')
    age=_legacy(rc,trial,sid,field='design.eligibility.age',value={'min':'2 years','max':'11 years'},
                extracted_by='code:test')
    html=render_report(svc.db,pid,'C')
    assert 'class="design-observation"' in html and 'class="evidence evidence-inline"' in html
    assert 'aria-label="样本量依据，1条"' in html and 'data-reading-title="样本量依据"' in html
    assert '[1]</summary>' in html
    # Current observation + its adjacent source + the unified reader; no second age-only control.
    assert html.count(f'data-fact-id="{age}"')==3


def test_short_target_pills_have_a_scoped_non_wrapping_rule_not_global_overflow_hiding(workspace):
    svc,pid,drug,_,sid=workspace
    for value in ['IL-4Rα','一个必须保留完整换行的很长很长的靶点组合名称']:
        svc.db.add_fact({'project_id':pid,'entity_id':drug,'source_id':sid,'field':'identity.target',
            'value':value,'quote':value,'tier':'standard','status':'verified','extracted_by':'code:test'})
    html=render_report(svc.db,pid,'A')
    assert 'class="tag target-token">IL-4Rα' in html
    assert 'class="tag">一个必须保留完整换行的很长很长的靶点组合名称' in html
    css=(_env.loader.searchpath[0]+'/../static/kangzhe.css')
    text=Path(css).read_text()
    assert '.target-token{white-space:nowrap}' in text
