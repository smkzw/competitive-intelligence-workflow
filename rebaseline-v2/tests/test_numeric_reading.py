"""Follow actual screen failures: numeric tokens and single-observation geometry."""
from pathlib import Path

from test_kangzhe71_site import _pages
from test_portal_js import run_portal


def test_b_value_and_denominator_use_nonbreaking_numeric_roles(settings):
    html = _pages(settings)['B']
    assert '<td class="numeric"><b>1.5</b></td>' in html
    assert '<td class="numeric">—</td>' in html
    css = (Path(__file__).resolve().parents[1] / 'src/ciw2/render/static/kangzhe.css').read_text()
    assert 'td.numeric{white-space:nowrap;' in css
    assert 'font-variant-numeric:tabular-nums' in css


def test_one_landscape_observation_does_not_stretch_a_card_across_twelve_columns():
    run_portal(r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const grid={style:{}},cards={},elements={},charts={};
for(const id of ['chart-heat','chart-phase']){
 cards[id]={hidden:false,style:{},parentElement:grid};elements[id]={id,style:{},closest:()=>cards[id]};
}
const row={id:'one',targets:[],phase_global:'unknown',phase_china:'approved'};
elements.charts={textContent:JSON.stringify({landscape:{rows:[row],phase_labels:{approved:'已上市'}}})};
const document={getElementById:id=>elements[id],querySelectorAll:()=>[]};
const echarts={init(n){const c={setOption(o){this.option=o;},resize(){},dispose(){}};charts[n.id]=c;return c;}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{echarts,addEventListener(){}},echarts,
 ResizeObserver:class{observe(){}},Set,Map,Math,Array,JSON});
assert.equal(cards['chart-heat'].hidden,true);
assert.equal(cards['chart-phase'].style.gridColumn,'span 6');
assert.notEqual(grid.style.gridTemplateColumns,'1fr');
assert.ok(parseInt(elements['chart-phase'].style.height)<=160);
assert.equal(charts['chart-phase'].option.series[0].data[0].value,1);
''')
