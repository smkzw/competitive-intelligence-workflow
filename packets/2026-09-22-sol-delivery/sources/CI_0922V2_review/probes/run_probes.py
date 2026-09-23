"""Run isolated algorithm checks. This does not run the repository test suite."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from types import SimpleNamespace as NS
from source_excerpts import classify_safety_concept,build_atrisk_crosswalk,normalize_period,validate_endpoint_timepoint_pairs,EndpointInstanceError
ROOT=Path(__file__).resolve().parents[1]
out=[]
def check(cid, input_, actual, expected):
    out.append(dict(id=cid,input=input_,actual=actual,expected=expected,pass_=actual==expected))
def forbid(cid,title,bad):
    actual=classify_safety_concept(title)
    out.append(dict(id=cid,input=title,actual=actual,expected='must not be '+bad,pass_=actual!=bad))
check('S01','Non-serious adverse events',classify_safety_concept('Non-serious adverse events'),'generic_ae')
check('S02','Non-serious adverse events and serious adverse events',classify_safety_concept('Non-serious adverse events and serious adverse events'),'composite_ae')
forbid('S03','Non-serious TEAEs','any_teae')
forbid('S04','Participants without SAEs','any_sae')
forbid('S05','Grade 4 adverse events','grade_3_plus')
forbid('S06','Grade 1 or 3 adverse events','grade_3_plus')
check('S07','TEAEs leading to discontinuation',classify_safety_concept('TEAEs leading to discontinuation'),'discontinuation_ae')

def row(title,n,period='TP1',group_id='EG1',module='adverseEventsModule'):
    return dict(title=title,num_at_risk=n,period=period,stat='serious',group_id=group_id,module=module)
cw=build_atrisk_crosswalk([row('Drug X',100,'TP1'),row('Drug X',40,'TP2','EG2')])
check('D01','different periods',cw.lookup(stat='serious',period='TP2',title='Drug X'),40)
check('D02','absent requested period',cw.lookup(stat='serious',period='TP3',title='Drug X'),None)
cw=build_atrisk_crosswalk([row('Drug X',100,'TP1','EG1','moduleA'),row('Drug X',100,'TP1','EG2','moduleB')])
check('D03','different module/group identities, same numeric denominator, no crosswalk proof',cw.lookup(stat='serious',period='TP1',title='Drug X'),None)
cw=build_atrisk_crosswalk([row('Drug X Placebo',80)])
check('D04','query drug title borrows placebo-labelled denominator',cw.lookup(stat='serious',period='TP1',title='Drug X'),None)
check('D05','normalize explicit Period 1',normalize_period('Period 1'),'TP1')

def obs(fam,oid='O1',trial='T1',text=None,role='primary'):
    return NS(field_family=fam,outcome_id=oid,trial_id=trial,source_text=text if text is not None else ('Outcome 1' if fam=='endpoint' else 'Week 12'),endpoint_key=role,row_id=f'{trial}-{oid}-{fam}')
def accepted(rows,universe):
    try:
        validate_endpoint_timepoint_pairs(rows,universe_trial_ids=universe)
        return True
    except EndpointInstanceError:return False
check('E01','valid pair',accepted([obs('endpoint'),obs('timepoint')],{'T1'}),True)
check('E02','second endpoint missing time',accepted([obs('endpoint'),obs('timepoint'),obs('endpoint','O2')],{'T1'}),False)
check('E03','T2 in universe but no endpoint or timepoint supplied',accepted([obs('endpoint'),obs('timepoint')],{'T1','T2'}),False)
check('E04','endpoint role primary, matched timepoint role secondary',accepted([obs('endpoint'),obs('timepoint',role='secondary')],{'T1'}),False)
check('E05','blank timepoint',accepted([obs('endpoint'),obs('timepoint',text=' ')],{'T1'}),False)
js=subprocess.run(['node',str(ROOT/'probes/js_probes.js')],check=True,capture_output=True,text=True)
for item in json.loads(js.stdout):
    item['pass_']=item.pop('pass')
    out.append(item)
summary=dict(round='0922V2',commit='700bd4c1fb90c49e27b6ff46fba07a5f7f296b6c',scope='Isolated source-algorithm excerpts and synthetic inputs, not repository/browser tests',total=len(out),pass_count=sum(r['pass_'] for r in out),fail_count=sum(not r['pass_'] for r in out),results=out)
(ROOT/'evidence/probe_results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='results'},ensure_ascii=False,indent=2))
for r in out:print(('PASS' if r['pass_'] else 'FAIL'),r['id'],repr(r['actual']))
