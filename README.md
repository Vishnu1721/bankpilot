# BankPilot

BankPilot is a computer-use automation prototype in which an LLM discovers a browser workflow once, records it as a typed JSON capability, and replays that capability deterministically. The included LegacyBank Credit Union portal is mock software: it never opens an account or posts funds.

## Setup

Requires Python 3.11+ and an OpenAI API key for discovery.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env`. Deterministic replay and unit checks do not call the model.

## Start the mock portal

In terminal 1:

```bash
source .venv/bin/activate
python demo_app/app.py
```

Keep it running at `http://127.0.0.1:5001`.

## Canonical discovery-to-replay path

In terminal 2, this one command performs the assignment's complete thread:

```bash
source .venv/bin/activate
python -m tests.test_end_to_end
```

It discovers the savings-balance workflow using member `10023`, writes the resulting schema-1.1 artifact to `artifacts/lookup_savings_balance.json`, closes the discovery browser, opens a fresh browser, loads that exact file, and replays it with input `member_id=10024`. Expected output:

```text
END-TO-END PASS
Artifact: artifacts/lookup_savings_balance.json
Replay outputs: {'savings_balance': '$2150.75'}
```

The equivalent two-command path uses the same generated artifact:

```bash
python -m tests.test_discovery
python -m tests.test_replay
```

Both interactive scripts pause before closing so you can inspect the UI; press Enter to continue. Discovery creates `artifacts/lookup_savings_balance.json`; replay reads that file with member `10024` and writes `evidence/replay_success.jsonl` plus `evidence/replay_final.png`.

## Independent operations

With the portal running, each operation can be discovered separately:

```bash
python -m tests.test_member_discovery
python -m tests.test_balance_discovery
python -m tests.test_subaccount_discovery
python -m tests.test_deposit_discovery
```

Expected boundaries:

| Operation | Output | Final state |
| --- | --- | --- |
| Member lookup | `member_name` | Member Details |
| Balance lookup | `current_balance` | Balance Result |
| New sub-account | reviewed `account_type` | Review New Sub-account; not opened |
| Deposit | reviewed `amount` | Deposit Review; not posted |

Representative sanitized schema-1.1 artifacts are committed in `artifacts/`. The sub-account and deposit JSONL files in `evidence/` are sanitized from verified live mock-portal runs; new runs replace/extend runtime evidence locally.

## Verification

Run checks that do not require an API key:

```bash
python -m tests.test_security_boundaries
python -m tests.test_mock_subaccount
python -m tests.test_capability_outputs
```

Then verify deterministic success and exceptional paths while the portal is running:

```bash
python -m tests.test_replay
python -m tests.test_business_outcome
python -m tests.test_recoverable_replay
python -m tests.test_hard_failure
python -m tests.test_handoff
```

The handoff demo uses member `10025`. It records capability, current step, URL, reason, screenshot, control owner, and the human action before resuming in the same browser session.

## Safety boundaries

UI text is tagged and sanitized as untrusted model input. Discovery has explicit step, model-call, time, observation-size, and repeated-state budgets. Proposed actions are validated against the current observation and approved local domains. Stable selectors prefer test IDs, accessible labels, names, IDs, and hrefs. Consequential buttons are policy-blocked, and the mock commit routes also return `403`.

`BrowserSurface` is operational. `TerminalSurface` permits only configured executables with no shell. `DesktopSurface` is an accessibility-tree extension point and is not enabled until platform-specific controls exist.

See `REPORT.md` for the required architecture, schema, determinism, multi-tenant, handoff, safety, and cuts discussion.
