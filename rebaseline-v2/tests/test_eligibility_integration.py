from html.parser import HTMLParser

import pytest

from ciw2.pipeline.stages import _compact
from ciw2.render.eligibility import eligibility_reading
from ciw2.render.portal import render_report, report_data
from ciw2.service import Service


@pytest.mark.parametrize('measure,label',[('ALT/AST','ALT/AST'),
    ('ALT or AST and ALT','ALT 或 AST 且 ALT')])
def test_compound_source_connectors_are_not_reinterpreted(measure,label):
    text=f'Exclusion Criteria:\n{measure} > 3 × ULN'
    result=eligibility_reading(text)
    assert len(result['rules'])==1
    rule=result['rules'][0]
    assert rule['measure']==measure
    assert rule['label']==f'{label} > 3 × ULN'
    assert ''.join(s['text'] for s in result['segments'])==text


def test_qualified_cohort_headings_and_viga_keep_source_scope():
    text=('Inclusion Criteria for the De Novo Cohort:\n'
          '* BSA ≥10%, vIGA ≥3, EASI ≥16, and WI-NRS ≥4\n'
          'Exclusion Criteria for the Extension Cohort:\nALT > 2 x ULN\n'
          'Exclusion Criteria for the De Novo Cohort\nOther Exclusion Criteria:\nALT > 2 x ULN')
    rules=eligibility_reading(text)['rules']
    assert [r['measure'] for r in rules]==['BSA','vIGA','EASI','WI-NRS','ALT','ALT']
    assert [r['section'] for r in rules]==['inclusion']*4+['exclusion']*2
    assert rules[1]['label']=='vIGA 评分 ≥ 3'
    assert rules[0]['section_title']=='Inclusion Criteria for the De Novo Cohort'
    assert rules[-2]['section_title']=='Exclusion Criteria for the Extension Cohort'
    assert rules[-1]['section_title']=='Exclusion Criteria for the De Novo Cohort · Other Exclusion Criteria'


class CriteriaReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside=False
        self.text=[]
        self.classes=[]

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='pre' and attrs.get('class')=='criteria':
            self.inside=True
        if self.inside and tag=='span':
            self.classes.append(attrs.get('class'))

    def handle_endtag(self,tag):
        if tag=='pre':
            self.inside=False

    def handle_data(self,text):
        if self.inside:
            self.text.append(text)


def test_production_c_criteria_are_lossless_emphasized_escaped_and_not_repeated_in_summary(settings):
    svc=Service(settings)
    pid=svc.create_project('特应性皮炎',['C'])
    tid,_=svc.db.upsert_entity(pid,'trial','NCT00000001')
    text=('Inclusion Criteria:\nEASI >= 16 OR IGA >= 3 at screening and baseline.\n'
          'Exclusion Criteria:\nALT/AST > 3 × ULN without cirrhosis\n'
          '<script>alert("source")</script>\nPreserve this unparsed condition.\n')
    svc.db.add_fact({'project_id':pid,'entity_id':tid,'field':'design.eligibility_criteria',
        'value':text,'quote':text,'status':'verified','tier':'critical','extracted_by':'code:test'})
    before=svc.db.current_facts(pid)
    data=report_data(svc.db,pid,'C')
    row=data['rows'][0]
    assert row['eligibility_thresholds'][2]['measure']=='ALT/AST'
    assert len(row['eligibility_clauses'])==2
    assert row['eligibility_clauses'][0]['labels']==['EASI 评分 ≥ 16','IGA 评分 ≥ 3']
    assert 'OR' in ''.join(s['text'] for s in row['eligibility_clauses'][0]['segments'])
    html=render_report(svc.db,pid,'C')
    reader=CriteriaReader()
    reader.feed(html)
    assert ''.join(reader.text)==text
    assert {'criteria-threshold','criteria-negation','criteria-logic','criteria-heading'}<=set(reader.classes)
    assert '<script>alert("source")</script>' not in html
    assert '评分与检验阈值' in html and 'EASI 评分 ≥ 16' in html
    assert svc.db.current_facts(pid)==before
    compact=_compact(data)['rows'][0]
    assert 'eligibility_reading' not in compact and 'eligibility_clauses' not in compact
    assert compact['eligibility_thresholds'][0]['rule_text']=='EASI >= 16 OR IGA >= 3 at screening and baseline.'
