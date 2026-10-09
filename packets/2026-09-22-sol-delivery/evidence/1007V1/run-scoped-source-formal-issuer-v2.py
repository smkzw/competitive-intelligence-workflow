"""One normal issuer subprocess, explicitly eligible OMP compatibility route."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PROJECT = ROOT / ".artifacts/1007-abc-current-integration-v1/working/project"
OUT = PROJECT / "runs/scoped-source-formal-v2"
TASK = "ci-1007-scoped-source-formal-v2"
PROMPT = ROOT / f"prompts/conference/{TASK}/evidence_single_object.md"
SESSION = "01a121d9-213b-7000-b55d-08b5f52a1e7f"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-after-plan-refusal", action="store_true")
    args = parser.parse_args()
    attempt = OUT
    if args.resume_after_plan_refusal:
        terminal = json.loads((OUT / "issuer-terminal.json").read_bytes())
        assert terminal["exit_code"] == 2
        assert not (OUT / "verdict.json").exists()
        assert not (PROJECT / "receipts/scientific_review/A/epochs/e1/receipt.json").exists()
        attempt = OUT / "same-session-plan-followup-v1"
        attempt.mkdir()
    if (attempt / "issuer-start.json").exists():
        raise SystemExit(
            "Issuer already attempted; collect original terminal/session, never redispatch"
        )
    preparation = json.loads((OUT / "preparation.json").read_bytes())
    assert preparation["epoch"] == 1
    subprocess.run(
        [
            "/Users/smkzw/.codex/tools/hermes_workflow_guard.py",
            "preflight",
            str(PROMPT),
            "--workspace",
            str(ROOT),
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    sys.path.insert(0, "/Users/smkzw/.codex/tools")
    from route_policy import validate_explicit_route, validate_route

    manifest = json.loads(
        (ROOT / f"context/{TASK}_evidence_single_object_route_manifest.json").read_bytes()
    )
    route = next(
        item
        for item in manifest["variants"]["off_peak"]["fallbacks"]
        if (item["agent"], item["provider"], item["model"], item["effort"])
        == ("pi", "openai-codex", "gpt-6.1-sol", "high")
    )
    validate_route(route["agent"], route["provider"], route["model"])
    validate_explicit_route(route["agent"], route["provider"], route["model"], route["effort"])
    reviewer = json.loads((PROJECT / "runs/joint-c-accepted-report-e2/verdict.json").read_bytes())[
        "reviewer_id"
    ]
    review = [
        "--print",
        "--mode",
        "json",
        "--print-thoughts",
        "--model",
        "openai-codex/gpt-6.1-sol",
        "--no-prewalk",
        "--no-rules",
        "--no-skills",
        "--config",
        "/Users/smkzw/.omp/clean-agent.yml",
        "--models",
        "openai-codex/gpt-6.1-sol",
        "--cwd",
        str(ROOT),
        "--max-time",
        "7200",
        "--auto-approve",
        "--approval-mode",
        "yolo",
        "--thinking",
        "high",
        "--resume",
        SESSION,
        "@" + str(PROMPT),
    ]
    argv = [
        str(ROOT / ".venv/bin/ci-workflow"),
        "review",
        "issue",
        "--root",
        str(PROJECT),
        "--report",
        "A",
        "--reviewer-id",
        reviewer,
        "--review-session-id",
        SESSION,
        "--host",
        "omp",
        "--host-executable",
        "/Users/smkzw/.local/bin/omp",
        "--review-command",
        ",".join(review),
        "--verdict",
        "runs/scoped-source-formal-v2/verdict.json",
    ]
    start = datetime.now(UTC).isoformat()
    with (attempt / "issuer.log").open("xb") as log:
        process = subprocess.Popen(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        record = {
            "issuer_pid": process.pid,
            "started_at": start,
            "route": route,
            "review_session_id": SESSION,
            "adapter_reason": (
                "Normal receipt hosts exclude ZCode app-server; "
                "explicit live permitted OMP continuation"
            ),
            "actual_model_effort_verified": False,
            "current_switched": False,
        }
        with (attempt / "issuer-start.json").open("x") as stream:
            json.dump(record, stream, indent=2)
        print(json.dumps(record), flush=True)
        code = process.wait()
    terminal = {
        "issuer_pid": process.pid,
        "started_at": start,
        "finished_at": datetime.now(UTC).isoformat(),
        "exit_code": code,
        "route": route,
    }
    with (attempt / "issuer-terminal.json").open("x") as stream:
        json.dump(terminal, stream, indent=2)
    print(json.dumps(terminal), flush=True)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
