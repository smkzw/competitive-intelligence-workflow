"""A cancelled controller wait cannot authorize a second workspace publisher."""
import subprocess
import sys
from pathlib import Path

import pytest

from ciw.pipeline import run
from ciw.store import WorkspaceBusyError


@pytest.mark.parametrize("operation", ["run", "research", "render"])
def test_all_public_writers_reject_another_process_without_touching_current_or_progress(cfg, seeded_ws, operation):
    first = run(cfg, seeded_ws, offline=True, report_scope="C", render_reports=["C"], log=lambda *_: None)
    seeded_ws.write_stage("research-run", dict(state="running", message="healthy original"))
    pointer = (seeded_ws.releases_dir / "current.json").read_bytes()
    progress = (seeded_ws.root / "stages/research-run.json").read_bytes()
    script = """
import sys
from ciw.config import load_indication
from ciw.pipeline import run
from ciw.research import run_research
from ciw.render.site import rerender_current
from ciw.store import Workspace, WorkspaceBusyError
ws=Workspace(sys.argv[1])
try:
 if sys.argv[3]=='run': run(load_indication(sys.argv[2]),ws,offline=True)
 elif sys.argv[3]=='research': run_research('synthetic disease',ws.root)
 else: rerender_current(ws)
except WorkspaceBusyError:
 print('busy')
 raise SystemExit(23)
raise SystemExit(91)
"""
    config = Path(__file__).resolve().parents[1] / "indications/crswnp.yaml"
    with seeded_ws.writer():
        child = subprocess.run([sys.executable, "-c", script, str(seeded_ws.root), str(config), operation],
                               capture_output=True, text=True, timeout=15)
    assert child.returncode == 23 and child.stdout.strip() == "busy"
    assert seeded_ws.current_release_dir().name == first.release_id
    assert (seeded_ws.releases_dir / "current.json").read_bytes() == pointer
    assert (seeded_ws.root / "stages/research-run.json").read_bytes() == progress


def test_writer_is_reentrant_only_for_same_instance_thread_and_releases_on_error(ws):
    from queue import Queue
    from threading import Thread

    events = Queue()
    def other_thread():
        try:
            with ws.writer():
                events.put("wrong writer")
        except WorkspaceBusyError:
            events.put("busy")
    with pytest.raises(ValueError), ws.writer():
        with ws.writer():
            thread = Thread(target=other_thread)
            thread.start()
            thread.join(timeout=5)
            assert events.get_nowait() == "busy"
        raise ValueError("synthetic failure")
    with ws.writer():
        ws.write_stage("recovered", dict(ok=True))
    assert ws.read_stage("recovered") == dict(ok=True)


def test_process_exit_releases_native_lock_without_removing_stale_lock_file(ws):
    script = "import os,sys;from ciw.store import Workspace\nwith Workspace(sys.argv[1]).writer(): os._exit(7)"
    child = subprocess.run([sys.executable, "-c", script, str(ws.root)], capture_output=True, timeout=15)
    assert child.returncode == 7
    assert (ws.root / ".writer.lock").exists()
    with ws.writer():
        ws.write_stage("after-exit", dict(ok=True))
    assert ws.read_stage("after-exit")["ok"]

