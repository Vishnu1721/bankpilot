# Evidence index

This directory separates the committed model-driven recording from deterministic test fixtures and historical demonstrations. The current implementation and fresh CI checks are described in the [main README](../README.md). Running a demo can overwrite tracked evidence locally; review changes before committing.

## Canonical discovery and replay

The [manifest](end_to_end_manifest.json) identifies source commit `a95e6580ada2991a5bf5ceb7ab00d11aaff40cc4` and evidence commit `f7ce538cc2409f56f2564bfc168fac92f781de71`. This recording predates the latest hardening; its source attribution has not been changed to imply a fresh run.

| File | What it proves |
| --- | --- |
| [lookup_savings_balance.json](../artifacts/lookup_savings_balance.json) | The saved schema-1.1 workflow from the canonical run, with a runtime member parameter and named balance extraction. |
| [end_to_end_discovery.jsonl](end_to_end_discovery.jsonl) | Five model decisions, observations, actions and reasons: Balance Lookup → member entry → Savings selection → View Balance → finish. Sensitive text is redacted. |
| [end_to_end_replay.jsonl](end_to_end_replay.jsonl) | Deterministic replay of that generated artifact with a different input, ending in success. |
| [end_to_end_replay.png](end_to_end_replay.png) | Balance Result page with customer values masked. |
| [end_to_end_transcript.txt](end_to_end_transcript.txt) | Privacy-edited transcript of the same Balance Lookup route; not a raw model transcript or independent second run. |
| [example_capability.json](example_capability.json) | A separate committed Member Lookup fixture used by repeatable exception/handoff tests. It is not the canonical Balance Lookup artifact. |

Use `python -m tests.test_end_to_end` with the portal running and your API key to regenerate discovery, artifact, replay, screenshot and manifest. The script records the source SHA and whether the worktree was clean at the start. It does not regenerate the transcript or commit files. Review the output, update the redacted transcript to match the actual route, and commit the complete set together; a completeness flag alone is not proof of Git tracking. A model key is not needed to inspect this evidence or replay either artifact.

## Exceptional and historical runs

| File | Provenance and limits |
| --- | --- |
| [replay_business_outcome.jsonl](replay_business_outcome.jsonl) | Sanitized reconstruction of the verified terminal run returning `business_outcome` / `MEMBER_NOT_FOUND`; its metadata explicitly marks that source. |
| [business_outcome.png](business_outcome.png) | Earlier mock-portal screenshot showing Member not found with an empty input. It has the old portal layout and is not claimed as a screenshot from the canonical run or current code. |
| [replay_recovered.jsonl](replay_recovered.jsonl) | Historical sanitized terminal-run reconstruction showing a transient Search Member error and recovery. Current fault injection is separately exercised in CI. |
| [replay_failure.jsonl](replay_failure.jsonl) | Historical sanitized reconstruction showing two retries then `STEP_EXECUTION_FAILED`. Its referenced `failure_step_3.png` was not committed. Run the documented persistent-failure check to produce a new masked image. |
| [handoff_log.jsonl](handoff_log.jsonl) | Historical sanitized reconstruction of one same-session verification handoff; predates the new structured human-action category. Its referenced `handoff_required.png` was not committed. |
| [subaccount_discovery.jsonl](subaccount_discovery.jsonl), [deposit_discovery.jsonl](deposit_discovery.jsonl) | Sanitized historical examples reaching review without committing a transaction. |

`discovery_log.jsonl`, `replay_success.jsonl` and the other interactive outputs are supplementary historical/runtime paths. Use the canonical manifest for one coherent discovery-to-replay thread instead of combining unrelated runs.

Five obsolete screenshots (`discovery_final.png`, `replay_final.png`, `handoff_final.png`, `manual_surface_test.png`, `failure_step_2.png`) exposed unmasked synthetic member details and were removed from the submission tree. Their deletion does not rewrite Git history. The current screenshot helper masks form controls and common data/error regions; rerunning an interactive demo may create new files at those names. Review any newly generated evidence before publishing it.

## Current automated evidence

[Verify BankPilot](../.github/workflows/verify.yml) starts the real mock portal and Chromium without an LLM key. It checks two members, a missing member, invalid-amount preflight rejection, recovery from an injected locator failure, and exhausted retries. These controlled failures test execution behavior; they do not claim a real production outage or manual human operation.

The workflow publishes redacted JSONL files and the masked failure screenshot as the `deterministic-replay-evidence` Actions artifact. They belong to that CI run and its checked-out commit, not to the older model-run manifest. The [documented baseline run](https://github.com/Vishnu1721/bankpilot/actions/runs/35280403340) predates the two added fault scenarios and artifact upload; check the latest PR run for those results.

JSONL uses `[REDACTED]` and category-specific markers; reusable capabilities use input placeholders and generic descriptions rather than replacement identities. Console output intentionally shows mock test results and is not privacy-filtered. Pattern-based checks and DOM masks are incomplete for unknown applications, so absence of a detected pattern is not a universal privacy guarantee.
