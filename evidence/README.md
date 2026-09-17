# Evidence

## Final submission status

**The refreshed model recording is committed.** The [manifest](end_to_end_manifest.json) records a clean run from source `1ad029ede8d3af355d1f16b98af320aa31b9a838` on September 17, 2026. It used `python -m tests.test_end_to_end`, OpenAI model `gpt-5.6-luna`, and deterministic replay without model calls. [PR #13](https://github.com/Vishnu1721/bankpilot/pull/13) merged the recording into `main` as `d56825f`. All five recorded file hashes match the committed files. Later documentation edits do not change the producing source SHA.

**Main CI is verified.** [Run 35286790051](https://github.com/Vishnu1721/bankpilot/actions/runs/35286790051) tested main commit `d56825fdd40830d337aadb4575fb4c101bed3eb5`: 78 tests and six Chromium scenarios passed. Its `deterministic-replay-evidence` artifact contains redacted replay logs and a masked failure screenshot. CI does not run model discovery or a human operator.

## Canonical model recording

These files belong to one discovery-to-replay thread. The currently committed route is Balance Lookup; a fresh run may choose Member Lookup.

| File | Contents |
| --- | --- |
| [lookup_savings_balance.json](../artifacts/lookup_savings_balance.json) | Saved schema-1.1 capability with runtime member input and named balance extraction. |
| [end_to_end_discovery.jsonl](end_to_end_discovery.jsonl) | Observations, five model decisions, reasons and executed actions from the recorded run. |
| [end_to_end_replay.jsonl](end_to_end_replay.jsonl) | Successful deterministic replay of that artifact for a different member. |
| [end_to_end_replay.png](end_to_end_replay.png) | Result page with customer values masked. |
| [end_to_end_transcript.txt](end_to_end_transcript.txt) | Event transcript generated directly from this run's redacted JSONL. |
| [end_to_end_manifest.json](end_to_end_manifest.json) | Producing source SHA, run modes, model, capture time and file hashes. |

### Record a future implementation change

Merge code changes first. Use a clean checkout with your local `.env` containing `OPENAI_API_KEY`; do not paste the key into a transcript or commit it. Keep `python demo_app/app.py` running in another terminal.

```bash
git switch main
git pull --ff-only origin main
git status --short
# Proceed when the status above is empty.
git switch -c evidence/final-model-run
python -m tests.test_end_to_end
```

Use a new branch name if `evidence/final-model-run` already exists. Add `--headless` for a run without browser windows. The command requires a clean source checkout, stages discovery and replay, verifies success, then writes the complete set. It preserves existing canonical files if credentials are missing or execution fails. The transcript is generated from this run's already-redacted events; it cannot silently describe a different route. The manifest records hashes instead of claiming uncommitted files have been published.

Review the JSON, logs, transcript and masked screenshot, then commit the set:

```bash
git diff -- artifacts/lookup_savings_balance.json evidence/
git add artifacts/lookup_savings_balance.json \
  evidence/end_to_end_discovery.jsonl evidence/end_to_end_replay.jsonl \
  evidence/end_to_end_replay.png evidence/end_to_end_transcript.txt \
  evidence/end_to_end_manifest.json
git commit -m "Record discovery and replay from final implementation"
git push -u origin evidence/final-model-run
```

Update the status above and the README/REPORT references only after inspecting the new run. Open and merge the evidence PR, then check that the latest [main Actions run](https://github.com/Vishnu1721/bankpilot/actions/workflows/verify.yml?query=branch%3Amain) is green. An evidence commit naturally follows the source commit that produced it; do not substitute the later commit SHA for the recorded source. Documentation-only changes do not require another model recording.

## Supplementary and historical runs

These are separate from the canonical model recording:

| File | Status |
| --- | --- |
| [example_capability.json](example_capability.json) | Stable Member Lookup fixture for exception and handoff tests. |
| [replay_business_outcome.jsonl](replay_business_outcome.jsonl), [business_outcome.png](business_outcome.png) | Sanitized terminal-run reconstruction and an earlier portal screenshot showing Member not found. The screenshot uses the old layout. |
| [replay_recovered.jsonl](replay_recovered.jsonl), [replay_failure.jsonl](replay_failure.jsonl) | Historical sanitized reconstructions. Current recovery/failure behavior is exercised in CI. The failure log's `failure_step_3.png` was not committed. |
| [handoff_log.jsonl](handoff_log.jsonl) | Historical same-session handoff reconstruction, before the new audit category. Its `handoff_required.png` was not committed. |
| [subaccount_discovery.jsonl](subaccount_discovery.jsonl), [deposit_discovery.jsonl](deposit_discovery.jsonl) | Sanitized historical runs reaching review without financial commitment. |

Other interactive log paths are supplementary. Do not combine them with the canonical manifest as though they were one run. Five obsolete screenshots exposing synthetic member details were removed from this tree; their deletion did not rewrite history. Rerunning an interactive demo can create new images at those paths.

Logs use `[REDACTED]` and category-specific markers; capabilities use placeholders rather than customer values. Screenshot masks cover known data regions. Review new evidence before sharing it: pattern checks are incomplete for unfamiliar UIs, and console output is not privacy-filtered.
