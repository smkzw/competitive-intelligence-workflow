"""A completed OS command must not hide an incomplete public catalogue query."""
import json
import subprocess
from pathlib import Path

import pytest

from ciw.cli import main


@pytest.mark.parametrize("result,code", [
    ({"queries": [{"status": "failed"}], "details": 2, "failures": []}, 1),
    ({"queries": [{"status": "ok"}], "failures": [{"number": "x"}]}, 1),
    ({"queries": [{"status": "verification_required"}], "blocked": "verification_required"}, 1),
    ({"queries": [{"status": "ok", "records": 0}], "failures": []}, 0),
    ({"queries": [{"status": "reused"}], "failures": []}, 0),
])
def test_nmpa_cli_exit_reflects_actual_query_and_detail_results(result, code, ws, monkeypatch, capsys):
    monkeypatch.setattr("ciw.sources.nmpa.capture.capture", lambda *a, **k: result)
    config = Path(__file__).parents[1] / "indications/crswnp.yaml"
    actual = main(["capture", "nmpa", str(config), "--workspace", str(ws.root), "--space", "59"])
    assert actual == code
    assert json.loads(capsys.readouterr().out) == result


def test_detail_timeout_reports_exact_missing_state_without_mask_or_control_retries():
    asset = Path(__file__).parents[1] / "src/ciw/sources/nmpa/record.mjs"
    script = r"""
const fs=require('fs'),vm=require('vm'),out=[];
(async()=>{
 for(const message of ['Timeout 45000ms','EGO_USER_CONTROL','certificate_user_verification_required']){
  let evaluations=0;
  const context={document:{body:{innerText:'Loading'},querySelectorAll:()=>[]}};
  vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
  const page={waitForFunction:async()=>{throw new Error(message)},
    evaluate:async(fn,arg)=>{evaluations++;return vm.runInContext('('+fn.toString()+')',context)(arg)}};
  try{await context.readCertificate(page,'境内生产药品','国药准字S20230030')}
  catch(error){out.push({message:error.message,state:error.certificate_state,evaluations})}
 }
 process.stdout.write(JSON.stringify(out));
})();
"""
    out = json.loads(subprocess.run(["node", "-e", script, str(asset)], check=True,
                                   capture_output=True, text=True).stdout)
    assert out[0]["state"] == {"heading_matches": False, "certificate_rows": 0, "product_rows": 0,
                              "verification": False, "network_code": None, "visible_loading_masks": 0}
    assert out[0]["evaluations"] == 1 and out[0]["message"] == "Timeout 45000ms"
    assert all(item["evaluations"] == 0 and "state" not in item for item in out[1:])
