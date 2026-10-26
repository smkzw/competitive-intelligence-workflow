"""The two approved source-backed classification axes share table/chart membership."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_molecular_and_mechanism_filters_and_graph_groups_are_distinct():
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable: production JS not run')
    root=Path(__file__).resolve().parents[1]
    script=(root/'tests/fixtures/landscape-classification.js').read_text()
    result=subprocess.run([node,'-e',script,str(root/'src/ciw2/render/static')],capture_output=True,text=True,check=False)
    assert result.returncode==0,result.stderr
