"""One normal issuer call through the existing explicitly permitted OMP route."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = PROJECT / "runs/source-definition-formal-v4"
TASK = "ci-1007-source-context-and-domain-closure-v3"
PROMPT = ROOT / f"prompts/conference/{TASK}/evidence_single_object_formal_v4.md"
SESSION = "01a12888-7dc4-7000-a48d-db6a45b44ef1"
TOOLS = Path.home() / ".codex/tools"


def main() -> None:
    if (OUT / "issuer-start.json").exists():
        raise SystemExit("Existing issuer: collect original terminal/session; never redispatch")
    preparation = json.loads((OUT / "preparation.json").read_bytes())
    assert preparation["state"] == "SOURCE_ONLY_NEW_EPOCH_READY_NOT_ACCEPTED_NOT_CURRENT"
    subprocess.run([
        str(TOOLS / "hermes_workflow_guard.py"), "preflight", str(PROMPT),
        "--workspace", str(ROOT),
    ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    sys.path.insert(0, str(TOOLS))
    from route_policy import validate_explicit_route, validate_route

    manifest = json.loads((ROOT / f"context/{TASK}_evidence_single_object_route_manifest.json")
                          .read_bytes())
    route = next(item for item in manifest["variants"]["off_peak"]["fallbacks"] if
                 (item["agent"], item["provider"], item["model"], item["effort"]) ==
                 ("pi", "openai-codex", "gpt-6.1-sol", "high"))
    validate_route(route["agent"], route["provider"], route["model"])
    validate_explicit_route(route["agent"], route["provider"], route["model"], route["effort"])
    reviewer = json.loads((PROJECT / "runs/joint-c-accepted-report-e2/verdict.json").read_bytes())[
        "reviewer_id"]
    review = [
        "--print", "--mode", "json", "--model", "openai-codex/gpt-6.1-sol",
        "--no-prewalk", "--no-rules", "--no-skills", "--config",
        str(Path.home() / ".omp/clean-agent.yml"), "--models", "openai-codex/gpt-6.1-sol",
        "--cwd", str(ROOT), "--max-time", "7200", "--auto-approve",
        "--approval-mode", "yolo", "--thinking", "high", "--resume", SESSION,
        "@" + str(PROMPT),
    ]
    argv = [
        str(ROOT / ".venv/bin/ci-workflow"), "review", "issue", "--root", str(PROJECT),
        "--report", "A", "--reviewer-id", reviewer, "--review-session-id", SESSION,
        "--host", "omp", "--host-executable", str(Path.home() / ".local/bin/omp"),
        "--review-command", ",".join(review), "--verdict",
        "runs/source-definition-formal-v4/verdict.json",
    ]
    start = datetime.now(UTC).isoformat()
    with (OUT / "issuer.log").open("xb") as log:
        process = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        record = {
            "issuer_pid": process.pid, "started_at": start, "route": route,
            "review_session_id": SESSION, "epoch": preparation["epoch"],
            "adapter_reason": "Normal issuer eligible OMP same-model completed C03 continuation",
            "context_independence": "Distinct producer; reduced same-review-context repair",
            "actual_runtime_identity": "VERIFY_AT_TERMINAL", "current_switched": False,
        }
        with (OUT / "issuer-start.json").open("x") as stream:
            json.dump(record, stream, indent=2)
        print(json.dumps(record), flush=True)
        code = process.wait()
    terminal = {
        "issuer_pid": process.pid, "started_at": start,
        "finished_at": datetime.now(UTC).isoformat(), "exit_code": code,
        "route": route, "review_session_id": SESSION,
    }
    with (OUT / "issuer-terminal.json").open("x") as stream:
        json.dump(terminal, stream, indent=2)
    print(json.dumps(terminal), flush=True)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
