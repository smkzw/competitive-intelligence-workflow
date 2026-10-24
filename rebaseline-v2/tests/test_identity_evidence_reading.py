"""Identity reading only: fewer entry points, every original fact/source still reachable."""
from html.parser import HTMLParser

import pytest

from ciw2.render.labels import registry_label
from ciw2.render.portal import _env


class Evidence(HTMLParser):
    def __init__(self,html):
        super().__init__();self.facts=[];self.quotes=0;self.entries=0;self.links=[];self.feed(html)

    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if values.get('data-fact-id'):self.facts.append(values['data-fact-id'])
        if tag=='blockquote':self.quotes+=1
        if tag=='details' and values.get('class')=='shared-evidence':self.entries+=1
        if tag=='a':self.links.append(values.get('href'))


def ref(fid,field='identity.target',value='IL-X',sid='source-v1',quote='Drug A targets IL-X.'):
    return {'fact_id':fid,'source_id':sid,'field':field,'value':value,'quote':quote,
            'url':'https://example.org/source','context':{}}


@pytest.mark.parametrize('raw,expected',(('monoclonal antibody','单克隆抗体'),('mAb','单克隆抗体'),
    ('ADC','抗体偶联药物'),('bispecific antibody','双特异性抗体'),('small molecule','小分子药物')))
def test_type_translation_is_exact_display_only(raw,expected):
    assert registry_label(raw,'drug_modality')==expected
    assert registry_label(raw+' extra','drug_modality')==raw+' extra'


def test_identical_source_quote_is_shown_once_with_all_fact_ids_and_context_dates():
    refs=[ref('target'),ref('modality','identity.modality','monoclonal antibody'),
          ref('same-quote-new-version',sid='source-v2')]
    refs[0]['context']['as_of']='2024-01-01';refs[1]['context']['as_of']='2025-01-01'
    html=str(_env.get_template('_trial.html').module.profile_evidence(refs))
    parsed=Evidence(html)
    assert parsed.quotes==2 and parsed.facts==['target','modality','same-quote-new-version']
    assert '单克隆抗体' in html and '2024-01-01' in html and '2025-01-01' in html
    assert len(parsed.links)==2  # Same URL is not the same immutable source version.


def test_consolidated_identity_preserves_name_company_group_and_original_source():
    formal=ref('name','identity.name_zh','正式药名',quote='名称 正式药名')
    formal.update(name='正式药名',registration_number='合成证号',approval_date='2024-01-01')
    holder={'fact_id':'holder','source_id':'source-v1','role':'中国MAH','name':'持有人',
        'quote':'持有人与集团的原文','url':'https://example.org/source','legal_entity':'法律实体',
        'group_refs':[{'fact_id':'group','source_id':'source-v1','name':'集团','as_of':'2025-01-01',
            'quote':'集团关系原文','url':'https://example.org/source','legal_entity':'法律实体'}]}
    profile=ref('developer','identity.developer','研发方',quote='研发来源原文')
    company={'fact_id':'developer','source_id':'source-v1','role':'研发方','name':'研发方',
             'quote':'研发来源原文','url':'https://example.org/source'}
    identity={'name_refs':[formal],'profile_refs':[profile],'companies':[holder,company]}
    html=str(_env.get_template('_trial.html').module.identity_evidence(identity))
    parsed=Evidence(html)
    assert parsed.entries==1 and set(parsed.facts)=={'name','holder','group','developer'}
    assert len(parsed.facts)==4
    assert all(text in html for text in ('正式药名','持有人','集团关系原文','法律实体','合成证号','2024-01-01'))
    identity.update(drug_label='正式药名',registry_id='SYNTHETIC-1',indication='合成人群',phase_label='II 期')
    clinical=str(_env.get_template('_trial.html').module.clinical_trial(identity))
    assert Evidence(clinical).entries==1
    assert all(text in clinical for text in ('正式药名','中国MAH','持有人','研发方','合成人群','II 期','SYNTHETIC-1'))


def test_source_strings_remain_plain_escaped_text():
    raw='<img src=x onerror=alert(1)>'
    html=str(_env.get_template('_trial.html').module.profile_evidence([
        ref('unsafe','identity.modality',raw,quote=raw)]))
    assert '<img' not in html and '&lt;img' in html


def test_current_role_projection_wins_over_a_neutral_field_caption_without_rewriting_the_fact():
    raw=ref('historical-group','status.china_mah_group','Group',quote='Historical group relationship.')
    qualified={'fact_id':raw['fact_id'],'source_id':raw['source_id'],'url':raw['url'],'quote':raw['quote'],
               'name':'Group','role':'许可记录持有人所属集团','legal_entity':'Legal Holder','as_of':'2024-01-01'}
    identity={'name_refs':[],'companies':[],'profile_refs':[raw],'group_refs':[qualified]}
    html=str(_env.get_template('_trial.html').module.identity_evidence(identity))
    assert '许可记录持有人所属集团' in html and '中国MAH所属集团' not in html
    assert Evidence(html).facts==['historical-group'] and Evidence(html).quotes==1
    assert raw['field']=='status.china_mah_group' and raw['value']=='Group'
