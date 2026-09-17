"""Record one real discovery and replay, publishing evidence only on success."""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.agent.budget import DiscoveryBudget
from src.agent.discovery import DiscoveryAgent
from src.agent.llm import LLMClient
from src.capability.models import Capability
from src.capability.replay import ReplayEngine
from src.capability.results import ReplayStatus
from src.surface.browser import BrowserSurface


START_URL = "http://127.0.0.1:5001"
ARTIFACT_PATH = "artifacts/lookup_savings_balance.json"
MANIFEST_PATH = "evidence/end_to_end_manifest.json"
EVIDENCE_FILES = {
    "artifact": ARTIFACT_PATH,
    "discovery_log": "evidence/end_to_end_discovery.jsonl",
    "replay_log": "evidence/end_to_end_replay.jsonl",
    "replay_screenshot": "evidence/end_to_end_replay.png",
    "transcript": "evidence/end_to_end_transcript.txt",
}


def source_provenance():
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    worktree_clean = not subprocess.check_output(
        ["git", "status", "--porcelain"], text=True
    ).strip()
    if not worktree_clean:
        raise RuntimeError(
            "Evidence recording requires a clean checkout. Commit or preserve "
            "your local changes first; existing evidence has not been replaced."
        )
    return source_commit


def read_events(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_transcript(discovery_log, replay_log, output_path):
    """Render the recorded, already-redacted events without inventing decisions."""
    lines = [
        "Generated from the discovery and replay JSONL; sensitive values are redacted.",
        "This is an event transcript, not a raw provider response or terminal capture.",
    ]
    for label, path in (("DISCOVERY", discovery_log), ("REPLAY", replay_log)):
        lines.extend(["", label])
        for event in read_events(path):
            if event["event"] == "observation":
                lines.append(f"Step {event['step']}: {event['url']} | {event['title']}")
            elif event["event"] == "agent_decision":
                lines.append(f"Decision: {event['action']} | Reason: {event['reasoning']}")
            elif event["event"] == "action_executed":
                lines.append(f"Executed: {event['action']}")
            elif event["event"] == "step_started":
                lines.append(f"{event['step_id']}: {event['action']}")
            elif event["event"] == "output_extracted":
                lines.append(f"Output: {event['name']} = {event['value']}")
            elif event["event"] in {"discovery_completed", "replay_completed"}:
                lines.append(f"{event['event']}: {event['status']}")
    Path(output_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def publish_evidence(staged, source_commit, model, command):
    """Verify the staged run, then replace the canonical files and manifest."""
    if set(staged) != set(EVIDENCE_FILES):
        raise ValueError("The evidence set is incomplete.")
    Capability.model_validate_json(staged["artifact"].read_text())
    for name, completed in (("discovery_log", "discovery_completed"),
                            ("replay_log", "replay_completed")):
        events = read_events(staged[name])
        if not events or events[-1].get("event") != completed or events[-1].get("status") != "success":
            raise ValueError(f"{name} does not end in successful completion.")
    for path in staged.values():
        if not path.is_file() or not path.stat().st_size:
            raise ValueError("The evidence set is incomplete.")

    manifest = {
        "source_commit": source_commit,
        "source_worktree_clean_at_start": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "discovery_mode": "model-driven",
        "replay_mode": "deterministic-no-llm",
        "llm_provider": "openai",
        "llm_model": model,
        **EVIDENCE_FILES,
        "files_sha256": {
            EVIDENCE_FILES[name]: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in staged.items()
        },
        "provenance": (
            "Generated from a clean source checkout by the documented command. "
            "The transcript renders the redacted JSONL from this same run. "
            "Generation does not commit files; inspect Git history for publication."
        ),
    }
    for name, path in staged.items():
        destination = Path(EVIDENCE_FILES[name])
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    # Write the manifest last so its hashes describe the complete published set.
    Path(MANIFEST_PATH).write_text(json.dumps(manifest, indent=2) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", help="Run Chromium without a window.")
    args = parser.parse_args(argv)
    source_commit = source_provenance()
    llm = LLMClient()  # Check credentials before touching the saved evidence.
    command = "python -m tests.test_end_to_end" + (" --headless" if args.headless else "")
    Path("tmp").mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="end_to_end_", dir="tmp") as directory:
        staged = {name: Path(directory) / Path(path).name for name, path in EVIDENCE_FILES.items()}
        discovery_surface = BrowserSurface(headless=args.headless)
        try:
            discovery_surface.start()
            discovery_surface.navigate(START_URL)
            agent = DiscoveryAgent(
                discovery_surface,
                llm=llm,
                budget=DiscoveryBudget(max_steps=8, max_llm_calls=8),
                log_path=str(staged["discovery_log"]),
            )
            agent.run(
                goal="Look up member 10023 and return their current savings balance.",
                artifact_path=str(staged["artifact"]),
                parameters={"member_id": "10023"},
            )
        finally:
            discovery_surface.close()

        replay_surface = BrowserSurface(headless=args.headless)
        try:
            replay_surface.start()
            engine = ReplayEngine(replay_surface, log_path=str(staged["replay_log"]))
            capability = engine.load_capability(staged["artifact"])
            result = engine.run(capability, inputs={"member_id": "10024"})
            if result.status != ReplayStatus.SUCCESS or result.outputs != {"savings_balance": "$2150.75"}:
                raise RuntimeError("Replay did not return the expected successful result; evidence was not replaced.")
            replay_surface.screenshot(str(staged["replay_screenshot"]))
        finally:
            replay_surface.close()

        write_transcript(staged["discovery_log"], staged["replay_log"], staged["transcript"])
        if source_provenance() != source_commit:
            raise RuntimeError("Source commit changed during the run; evidence was not replaced.")
        publish_evidence(staged, source_commit, llm.model, command)

    print("\nEND-TO-END PASS")
    print(f"Artifact: {ARTIFACT_PATH}")
    print(f"Replay outputs: {result.outputs}")
    print(f"Evidence manifest: {MANIFEST_PATH}")
    print(f"Source commit: {source_commit}")


if __name__ == "__main__":
    main()
