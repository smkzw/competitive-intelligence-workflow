import json
from pathlib import Path

import pytest

from ciw.config import load_indication
from ciw.normalize.products import ProductResolver
from ciw.store import Workspace

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def cfg():
    return load_indication(ROOT / "indications" / "crswnp.yaml")


@pytest.fixture(scope="session")
def resolver(cfg):
    return ProductResolver(cfg)


@pytest.fixture
def ws(tmp_path):
    return Workspace(tmp_path / "ws")


def load_study(nct: str) -> dict:
    return json.loads((FIX / "ctgov" / f"{nct}.json").read_text(encoding="utf-8"))


@pytest.fixture
def seeded_ws(ws):
    """把所有 CT.gov 夹具按真实获取方式写入 CAS（离线流水线的输入）。"""
    for path in sorted((FIX / "ctgov").glob("NCT*.json")):
        study = json.loads(path.read_text(encoding="utf-8"))
        nct = study["protocolSection"]["identificationModule"]["nctId"]
        ws.record_source(
            kind="ctgov",
            url=f"https://clinicaltrials.gov/study/{nct}",
            data=json.dumps(study, ensure_ascii=False, sort_keys=True).encode(),
            ext="json",
            title=study["protocolSection"]["identificationModule"]["briefTitle"],
        )
    return ws
