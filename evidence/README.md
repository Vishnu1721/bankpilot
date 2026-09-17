# Evidence

## Final submission status

**Model recording refresh is still pending.** The committed [manifest](end_to_end_manifest.json) attributes the existing run to source `a95e6580ada2991a5bf5ceb7ab00d11aaff40cc4`. Keep that attribution until a real discovery run replaces these files. The recording is inspectable, but it does not demonstrate all later code changes.

**Main CI is verified.** [Run 35283225107](https://github.com/Vishnu1721/bankpilot/actions/runs/35283225107) tested main commit `02724287c0031ba174fed14c4688a90b3e244975`: 68 tests and six Chromium scenarios passed. Its [downloadable evidence](https://github.com/Vishnu1721/bankpilot/actions/runs/35283225107/artifacts/10523645846) contains redacted replay logs and a masked failure screenshot. CI does not run model discovery or a human operator.

## Canonical model recording

These files belong to one discovery-to-replay thread. The currently committed route is Balance Lookup; a fresh run may choose Member Lookup.

| File | Contents |
| --- | --- |
| [lookup_savings_balance.json](../artifacts/lookup_savings_balance.json) | Saved schema-1.1 capability with runtime member input and named balance extraction. |
| [end_to_end_discovery.jsonl](end_to_end_discovery.jsonl) | Observations, five model decisions, reasons and executed actions from the recorded run. |
| [end_to_end_replay.jsonl](end_to_end_replay.jsonl) | Successful deterministic replay of that artifact for a different member. |
| [end_to_end_replay.png](end_to_end_replay.png) | Result page with customer values masked. |
| [end_to_end_transcript.txt](end_to_end_transcript.txt) | Privacy-edited transcript of the same route. Future refreshes generate it directly from the redacted JSONL. |
| [end_to_end_manifest.json](end_to_end_manifest.json) | Producing source SHA and run modes. The updated recorder also adds the model, capture time and file hashes. |

### Refresh from the final code

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

Update the status paragraph above with the new source SHA and remove the pending-refresh note in README/REPORT only after inspecting the actual run. Open and merge the evidence PR, then check that the latest [main Actions run](https://github.com/Vishnu1721/bankpilot/actions/workflows/verify.yml?query=branch%3Amain) is green. An evidence commit naturally follows the source commit that produced it; do not substitute the later commit SHA for the recorded source.

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
