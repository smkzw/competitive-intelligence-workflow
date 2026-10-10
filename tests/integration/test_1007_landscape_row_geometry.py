"""Guard the desktop row contract; actual native-details geometry needs Ego QA."""

import re
import subprocess
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[2] / "src/ci_workflow/renderers/portal/assets"


def rule(selector: str) -> str:
    css = (ASSETS / "portal.css").read_text()
    matched = re.search(re.escape(selector) + r"\s*\{([^}]+)\}", css)
    assert matched is not None
    return matched.group(1)


def test_desktop_target_band_is_one_full_width_explicit_grid_row() -> None:
    declarations = rule(".kz-a-landscape-target-band")
    assert "display:grid" in declarations
    assert "grid-column:1/-1" in declarations
    assert "grid-template-columns:120px minmax(0,1fr)" in declarations
    assert "display:contents" not in declarations


def test_desktop_stage_cells_have_the_same_columns_as_stage_headers() -> None:
    declarations = rule(".kz-a-landscape-band__cells")
    assert "display:grid" in declarations
    assert "grid-template-columns:repeat(var(--stage-count),minmax(0,1fr))" in declarations
    assert "gap:5px" in declarations
    assert "display:contents" not in declarations


def test_landscape_redraw_keeps_native_disclosure_state_and_keyboard_focus() -> None:
    probe = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function renderLandscape(');
const end=source.indexOf('\n  function renderPortfolio(',start);
class Node {
 constructor(tag,cls='',text=''){
  this.tagName=tag.toUpperCase();this.className=cls;this.textContent=text;
  this.children=[];this.attrs={};this.style={setProperty(){}};
 }
 appendChild(n){this.children.push(n);n.parentElement=this;return n;}
 setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k]??null;}
 get innerHTML(){return '';}set innerHTML(_){this.children=[];}
 querySelectorAll(selector){
  const matches=selector[0]==='.'?n=>n.className.split(' ').includes(selector.slice(1)):
   n=>n.tagName===selector.toUpperCase();
  return this.children.flatMap(n=>[...(matches(n)?[n]:[]),...n.querySelectorAll(selector)]);
 }
 querySelector(s){return this.querySelectorAll(s)[0]??null;}
 contains(n){return n===this||this.children.some(c=>c.contains(n));}
 focus(){document.activeElement=this;}
}
const document={activeElement:null},host=new Node('div');
const sandbox={document,window:{innerWidth:1440},Object,String,Math,Boolean,
 selected:{},products:[{id:'nemo',name:'Nemolizumab',target:'IL-31RA',phase:'III期'},
 {id:'dup',name:'Dupilumab',target:'IL-4Rα',phase:'III期'}],
 el:(tag,cls,text)=>new Node(tag,cls,text)};
vm.runInNewContext(source.slice(start,end),sandbox);
sandbox.renderLandscape(host);
let band=host.querySelector('.kz-a-landscape-target-band');
band.open=false;band.querySelector('summary').focus();
sandbox.renderLandscape(host);
band=host.querySelector('.kz-a-landscape-target-band');
assert.equal(band.open,false,'redraw must not erase the user collapse');
assert.equal(document.activeElement,band.querySelector('summary'),
 'focus must follow the same target');
assert.equal(host.querySelectorAll('.kz-a-landscape-target-band').length,2);
"""
    result = subprocess.run(["node", "-e", probe, str(ASSETS / "report-a.js")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
