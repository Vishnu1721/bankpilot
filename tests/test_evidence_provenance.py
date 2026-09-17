"""Test evidence bookkeeping with explicit fakes; these are not model-run evidence."""

import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.capability.results import ReplayResult, ReplayStatus
from src.observability.logger import EventLogger
from tests import test_end_to_end as recording


@pytest.mark.parametrize("status", ["", " M src/agent/discovery.py\n"])
def test_recording_requires_a_clean_source_checkout(monkeypatch, status):
    monkeypatch.setattr(recording.subprocess, "check_output", Mock(side_effect=["a" * 40, status]))
    if status:
        with pytest.raises(RuntimeError, match="clean checkout"):
            recording.source_provenance()
    else:
        assert recording.source_provenance() == "a" * 40


@pytest.mark.parametrize("route", ["/member", "/balance"])
def test_transcript_follows_recorded_route_and_redaction(tmp_path, route):
    discovery = tmp_path / "discovery.jsonl"
    logger = EventLogger(discovery)
    logger.log("observation", step=1, title="Result", url="http://localhost:5001" + route)
    logger.log("agent_decision", step=1, action="finish", reasoning="Read member 10023 balance $4820.35")
    logger.log("discovery_completed", status="success")
    replay = tmp_path / "replay.jsonl"
    logger = EventLogger(replay)
    logger.log("output_extracted", name="savings_balance", value="$2150.75")
    logger.log("replay_completed", status="success")
    transcript = tmp_path / "transcript.txt"

    recording.write_transcript(discovery, replay, transcript)

    text = transcript.read_text()
    assert route in text
    assert ("/balance" if route == "/member" else "/member") not in text
    assert "[REDACTED" in text
    assert not any(value in text for value in ["10023", "$4820.35", "$2150.75"])
    assert "replay_completed: success" in text


@pytest.fixture
def staged_run(tmp_path):
    """Build test-only files in pytest's temporary directory, never evidence/."""
    artifact = Path("evidence/example_capability.json").read_bytes()
    staged = {}
    for name, target in recording.EVIDENCE_FILES.items():
        path = tmp_path / "staged" / Path(target).name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"test-only placeholder")
        staged[name] = path
    staged["artifact"].write_bytes(artifact)
    for name, event in [("discovery_log", "discovery_completed"), ("replay_log", "replay_completed")]:
        staged[name].write_text(json.dumps({"event": event, "status": "success"}) + "\n")
    return staged


def test_manifest_hashes_match_published_files_without_claiming_git_commit(monkeypatch, tmp_path, staged_run):
    monkeypatch.chdir(tmp_path)
    recording.publish_evidence(staged_run, "a" * 40, "fake-model", "test-only command")
    manifest = json.loads(Path(recording.MANIFEST_PATH).read_text())
    assert manifest["source_commit"] == "a" * 40
    assert manifest["source_worktree_clean_at_start"] is True
    assert manifest["llm_model"] == "fake-model"
    assert "committed_evidence_complete" not in manifest
    assert "evidence_commit" not in manifest
    for path, digest in manifest["files_sha256"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("log", ["discovery_log", "replay_log"])
def test_incomplete_log_preserves_previous_recording(monkeypatch, tmp_path, staged_run, log):
    monkeypatch.chdir(tmp_path)
    Path("evidence").mkdir()
    Path(recording.MANIFEST_PATH).write_text("old evidence")
    staged_run[log].write_text('{"event":"run_failed","status":"failure"}\n')
    with pytest.raises(ValueError, match="successful completion"):
        recording.publish_evidence(staged_run, "a" * 40, "fake-model", "test")
    assert Path(recording.MANIFEST_PATH).read_text() == "old evidence"
    assert not Path(recording.ARTIFACT_PATH).exists()


def test_missing_screenshot_prevents_publication(monkeypatch, tmp_path, staged_run):
    monkeypatch.chdir(tmp_path)
    staged_run["replay_screenshot"].unlink()
    with pytest.raises(ValueError, match="incomplete"):
        recording.publish_evidence(staged_run, "a" * 40, "fake-model", "test")
    assert not Path(recording.MANIFEST_PATH).exists()


def test_missing_model_key_does_not_open_browser_or_replace_evidence(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(recording, "source_provenance", lambda: "a" * 40)
    monkeypatch.setattr(recording, "LLMClient", Mock(side_effect=ValueError("OPENAI_API_KEY is missing")))
    browser = Mock()
    monkeypatch.setattr(recording, "BrowserSurface", browser)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        recording.main([])
    browser.assert_not_called()
    assert not Path(recording.MANIFEST_PATH).exists()


def test_failure_with_expected_outputs_cannot_replace_good_evidence(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("evidence").mkdir()
    Path(recording.MANIFEST_PATH).write_text("old evidence")
    monkeypatch.setattr(recording, "source_provenance", lambda: "a" * 40)
    monkeypatch.setattr(recording, "LLMClient", Mock(return_value=Mock(model="fake-model")))
    discovery_browser, replay_browser = Mock(), Mock()
    monkeypatch.setattr(recording, "BrowserSurface", Mock(side_effect=[discovery_browser, replay_browser]))
    monkeypatch.setattr(recording, "DiscoveryAgent", Mock())
    engine = Mock()
    engine.run.return_value = ReplayResult(status=ReplayStatus.FAILURE,
        outputs={"savings_balance": "$2150.75"}, code="SUCCESS_CONDITION_FAILED")
    monkeypatch.setattr(recording, "ReplayEngine", Mock(return_value=engine))
    with pytest.raises(RuntimeError, match="expected successful result"):
        recording.main(["--headless"])
    assert Path(recording.MANIFEST_PATH).read_text() == "old evidence"
    discovery_browser.close.assert_called_once()
    replay_browser.close.assert_called_once()
    replay_browser.screenshot.assert_not_called()
