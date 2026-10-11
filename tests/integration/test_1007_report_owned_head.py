"""Shared motion adapts real report content; it does not inject a lecture/banner."""

import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("kind", ("a", "b", "c"))
def test_motion_preserves_report_owned_header_and_lifecycle(kind):
    source = (Path(__file__).resolve().parents[2]
              / "src/ci_workflow/renderers/portal/assets/kangzhe-site.js")
    probe = r"""
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict');
let mounted=0,disposed=0,entered=0;const events={};
const head={children:[],appendChild(n){this.children.push(n);}};
const body={dataset:{kzDesign:'6.0'},classList:{
 contains(c){return c==='kz-'+process.argv[2]+'-site';},toggle(){}}};
const document={body,hidden:false,
 querySelector(selector){return selector==='.portal-page-head'?head:null;},
 querySelectorAll(){return [];},addEventListener(){},
 createElement(){return {setAttribute(){},append(){},appendChild(){}};}};
const window={KZMotion:{mountPage(target){assert.equal(target,body);mounted++;
 return {enter(){entered++;},finish(){},dispose(){disposed++;}};},
 Film:function(){return {snapshot(){return {};},pause(){},resume(){},dispose(){}};}},
 addEventListener(name,fn){events[name]=fn;}};
class Observer {observe(){} disconnect(){}}
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),
 {window,document,AbortController,MutationObserver:Observer,queueMicrotask});
assert.equal(head.children.length,0,'report heading must not acquire boilerplate/story');
assert.equal(mounted,1,'retain functional page motion');
assert.equal(entered,1);
events.pageshow();assert.equal(mounted,1,'no duplicate mount');
events.pagehide();assert.equal(disposed,1);
events.pageshow();assert.equal(mounted,2,'bfcache restores the same lifecycle');
assert.equal(head.children.length,0,'restore must not inject a narrative');
assert.equal(window.__KZ_SITE_SCENE__,undefined,'do not claim a nonexistent Film');
"""
    result = subprocess.run(["node", "-e", probe, str(source), kind],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
