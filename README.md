# BankPilot

BankPilot uses an LLM to discover a workflow in a live browser, saves a typed JSON capability, and replays it without an LLM. The included LegacyBank Credit Union portal is a mock: account creation and deposits stop at review, and no funds or accounts are committed.

**Quick demo:** after setup, with the portal running and an OpenAI key configured, run `python -m tests.test_end_to_end`.
It discovers with member `10023`, saves `artifacts/lookup_savings_balance.json`, then replays that file for member `10024` in a fresh browser.
Expected: `END-TO-END PASS` and `Replay outputs: {'savings_balance': '$2150.75'}`.
For a check without an API key, use the reviewer commands below.

[![Verify BankPilot](https://github.com/Vishnu1721/bankpilot/actions/workflows/verify.yml/badge.svg?branch=main)](https://github.com/Vishnu1721/bankpilot/actions/workflows/verify.yml)

## Setup

Requires Python 3.11+; CI uses Python 3.11 on Ubuntu with Chromium. No Node application setup is required. For a fresh checkout:

```bash
git clone https://github.com/Vishnu1721/bankpilot.git
cd bankpilot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

If you already have the repository, skip the clone and work from its root. Configure only the settings you need:

| Setting | Purpose |
| --- | --- |
| `OPENAI_API_KEY` in `.env` | Required for real discovery; unit tests and deterministic replay need no key. |
| `OPENAI_MODEL` in `.env` | A model available to your API account; the code default is `gpt-5.6-luna`. Override if needed. |
| CLI `--target` | Discovery entry URL, e.g. `http://127.0.0.1:5001`. There is no target-URL environment variable. Replay uses the artifact's `start_url`. |
| [SafetyPolicy](src/safety/policy.py) | Approved origins are `http://127.0.0.1:5001` and `http://localhost:5001`, with explicit route/action rules. A new application requires reviewed policy and contract changes. |

In terminal 1, start the mock portal and leave it running:

```bash
source .venv/bin/activate
python demo_app/app.py
```

Use terminal 2 from the same repository with `source .venv/bin/activate` for the commands below. There is no offline model-discovery mode; replay and the non-browser tests work without a model service.

## Reviewer checks without an API key

The checker opens actual headless Chromium, executes a supplied artifact against the running portal, and asserts status, code, outputs and recovery state. Expected values are assertions against seeded mock data, never execution results supplied to the browser. Single-quote currency values so the shell does not expand `$`.

```bash
# Two different members; balances are read from the live UI.
python -m tests.test_headless_replay --artifact artifacts/lookup_savings_balance.json --param member_id=10023 --expect-status success --expect-output 'savings_balance=$4820.35'
python -m tests.test_headless_replay --artifact artifacts/lookup_savings_balance.json --param member_id=10024 --expect-status success --expect-output 'savings_balance=$2150.75'

# Expected business outcome, not an execution crash.
python -m tests.test_headless_replay --artifact evidence/example_capability.json --param member_id=99999 --expect-status business_outcome --expect-code MEMBER_NOT_FOUND

# Invalid amount is rejected before navigation.
python -m tests.test_headless_replay --artifact artifacts/prepare_deposit.json --param member_id=10024 --param account_type=Savings --param amount=0 --param memo=Demo --expect-status business_outcome --expect-code INVALID_AMOUNT

# Explicit test-only failures at the browser adapter boundary.
python -m tests.test_headless_replay --artifact evidence/example_capability.json --param member_id=10024 --fail-target 'Search Member' --failure-mode once --expect-status success --expect-recovered-step step_3 --expect-output 'savings_balance=$2150.75'
python -m tests.test_headless_replay --artifact evidence/example_capability.json --param member_id=10024 --fail-target 'Search Member' --failure-mode persistent --expect-status failure --expect-code STEP_EXECUTION_FAILED --expect-failed-step step_3
```

Each command prints `HEADLESS REPLAY PASS` only when its assertions match; mismatches exit nonzero. Substitute your reviewed artifact, `--param` values and expected results to test another contract. JSONL defaults to `tmp/reviewer_replay.jsonl`; use `--log-path` to retain separate runs. A passing failure simulation means the engine correctly refused success.

For a visible human-verification test:

```bash
python main.py replay --artifact evidence/example_capability.json --param member_id=10025 --enable-handoff --log-path tmp/manual_replay.jsonl
```

Click **Complete Verification** in the preserved browser, return to the terminal, and describe what you did. Automation resumes in that same session and returns `$3675.20`. Blank notes/unchanged state cannot resume; `/cancel` terminates. `python -m tests.test_handoff` additionally asserts exactly one handoff and pauses before closing.

## CLI discovery → artifact → replay

Supply the goal, target and runtime inputs to real model-driven discovery:

```bash
python main.py discover \
  --goal "Look up member 10023 and return their current savings balance" \
  --target http://127.0.0.1:5001 \
  --artifact artifacts/cli_savings_balance.json \
  --param member_id=10023 \
  --log-path tmp/cli_discovery.jsonl
```

Replay the **same generated file** with a different member and no model call:

```bash
python main.py replay \
  --artifact artifacts/cli_savings_balance.json \
  --param member_id=10024 \
  --log-path tmp/cli_replay.jsonl
```

Expected replay result: `status: success`, `outputs: {"savings_balance": "$2150.75"}`. `--param` values are strings, matching these demo contracts; the Python replay API accepts typed numeric/boolean inputs for other contracts. CLI replay treats the supplied artifact as reviewed; registry approval is a separate library interface.

Both commands accept `--headless` or visible `--enable-handoff`. Discovery defaults to 10 steps/model calls and 120 seconds checked between steps; `--max-steps` and `--timeout-seconds` customize them. Use `--overwrite` to replace an existing artifact after review. See `python main.py discover --help` and `python main.py replay --help`.

## Canonical evidence run

With the portal running and `OPENAI_API_KEY` configured:

```bash
python -m tests.test_end_to_end
```

This generates `artifacts/lookup_savings_balance.json`, discovery/replay JSONL, a masked replay screenshot and a provenance manifest. Replay loads that exact file with `member_id=10024` and expects `$2150.75`. Alternatively, `python -m tests.test_discovery` followed by `python -m tests.test_replay` uses the same artifact and keeps each browser open until Enter is pressed.

The committed canonical recording follows the five-decision **Balance Lookup** route; a new discovery may choose the valid Member Lookup route. All canonical files and the historical exception evidence are linked in [evidence/README.md](evidence/README.md). That index distinguishes generated logs from privacy-edited transcripts and reconstructed historical logs.

The committed model run retains source SHA `a95e6580ada2991a5bf5ceb7ab00d11aaff40cc4`; it predates the latest hardening. To refresh it, run from a clean committed checkout, inspect the generated evidence and source SHA, update the redacted transcript to match the new route, then commit the files together. The script does **not** regenerate the transcript or commit files; a manifest completeness flag alone does not prove files are committed. No fresh model run is claimed by this documentation update.

## Other operations and capability reuse

Each discovery demo uses the running portal and a model key:

| Command | Declared output | Stop point |
| --- | --- | --- |
| `python -m tests.test_member_discovery` | `member_name` | Member Details |
| `python -m tests.test_balance_discovery` | `current_balance` | Balance Result |
| `python -m tests.test_subaccount_discovery` | reviewed `account_type` | Review New Sub-account; account not opened |
| `python -m tests.test_deposit_discovery` | reviewed `amount` | Deposit Review; funds not posted |

Committed schema-1.1 artifacts are sanitized: runtime member IDs, nicknames and amounts use declared placeholders, raw goals are replaced with generic descriptions, and safe application labels/selectors remain usable. JSONL uses redaction markers rather than replacement customer identities. These examples use synthetic mock data; sanitization is not a guarantee for every unknown UI.

`CapabilityRouter` and the file registry implement an optional lifecycle: approved tenant/application match → deterministic replay; draft match → approval required; no match → bounded discovery and a draft for review. Intent matching uses sanitized token similarity, not another LLM. Near misses can cause unnecessary discovery or selection of the wrong approved intent; stronger semantic constraints are future work. Router tests use fakes, including the address-change example, and do not prove arbitrary new operations work on a live site.

## Verification and CI

Run the complete configured non-browser suite without a portal or model key:

```bash
pytest -q tests
```

Expected: **68 passed**. [pytest.ini](pytest.ini) selects ten modules, including `test_capability_model.py`; browser/model demonstrations run separately. Four added regressions verify that fault injection reaches the current adapter and that reviewer assertions reject incorrect recovery/failure state.

| Layer | Coverage | Limits |
| --- | --- | --- |
| 68 automated checks | Contracts, privacy/persistence guards, policies, router, CLI and handoff; fake surfaces and Flask test client. | Not live browser/model evidence. |
| [GitHub Actions](.github/workflows/verify.yml) | Actual Chromium: two balances, member-not-found, invalid-amount preflight, injected recovery and exhausted retries. | No model API key or human operator. |
| `tests.test_end_to_end` | Live model discovery, saved artifact, fresh-browser replay. | Requires an API key and reviewed target. |
| `tests.test_handoff` | Human verification, preserved session, one handoff. | Interactive, outside unattended CI. |

**Verified baseline:** [Actions run 35280403340](https://github.com/Vishnu1721/bankpilot/actions/runs/35280403340) passed on 2026-09-17 for PR #10 (head `46ab7f5`, tested merge snapshot `beb4052`): 64 tests and four headless assertions. This update adds four regressions and two browser fault scenarios. The badge links to the latest `main` status; inspect the PR checks for this branch's result.

Interactive exception commands also remain available:

```bash
python -m tests.test_business_outcome
python -m tests.test_recoverable_replay
python -m tests.test_hard_failure
python -m tests.test_handoff
```

They use the stable Member Lookup fixture `evidence/example_capability.json`, independently of whichever route discovery last recorded. Expected results are respectively `MEMBER_NOT_FOUND`, success with `recovered_steps: ["step_3"]`, `STEP_EXECUTION_FAILED` at step 3, and success after one manual verification. Browser fault injection now occurs in `tests/fault_surface.py`, where replay actually resolves targets.

## Code and deliverables map

| Location | Responsibility |
| --- | --- |
| [main.py](main.py) | Evaluator CLI for goal + target discovery and parameterized replay. |
| [src/agent/](src/agent/) | Observe → decide → act, OpenAI client, discovery budgets. |
| [src/capability/](src/capability/) | Typed schema, recorder, checkpoint checks, deterministic executor, optional registry/router. |
| [src/surface/](src/surface/) | Operational browser adapter; terminal helper and unimplemented desktop seam. |
| [src/safety/](src/safety/) and [src/observability/](src/observability/) | Origin/route/action policies, untrusted UI guard, artifact checks and redacted JSONL. |
| [src/handoff/](src/handoff/) | Preserved browser session and terminal-guided operator handoff. |
| [artifacts/](artifacts/) and [evidence/](evidence/README.md) | Saved contracts, discovery/replay logs, masked canonical image, exception evidence and provenance. |
| [REPORT.md](REPORT.md) | Exactly seven required sections, including concrete heterogeneity/tenant design and cuts. |

## Safety and scope

- **Policy:** exact origin (scheme/host/port), route, action and click-target checks. Discovery and replay validate link/form destinations before clicking. Financial commit routes are blocked; the mock independently returns `403`.
- **Untrusted UI:** visible observations are normalized and capped. Suspicious instructions stop automation and request configured handoff. Step, model-call, elapsed-time and repeated-state budgets bound discovery; elapsed time is checked between calls.
- **Verified results:** replay checks member identity, output types/completeness and final text/title/URL checkpoint. After handoff, failed extraction is reattempted. Discovery must satisfy its checkpoint before saving; unfamiliar workflows need stronger reviewed assertions than a title alone.
- **Privacy:** JSONL masks sensitive fields/patterns with `[REDACTED]` and category-specific markers; artifacts and registry intents have separate persistence checks. Screenshot masking covers known data regions. Five obsolete unmasked mock screenshots were removed. Console output is not a sanitized evidence log.
- **Handoff audit:** context/control owner and a safe `human_action_type` remain; free-form notes are redacted. Changed state and an operator-reported category do not prove identity or exact human actions. Runtime handoff screenshots are not committed; the evidence index identifies historical references.

Business responses (`MEMBER_NOT_FOUND`, `ACCOUNT_LOCKED`, `INVALID_INPUT`, `INVALID_AMOUNT`) return structured outcomes. Session/authentication, unexpected-dialog and verification codes request configured handoff or stop; permission denial stops without retry. Temporary application/target failures receive bounded retries. Unknown conditions can still become generic failures.

This is not an arbitrary-site agent. New applications require reviewed policies, contracts, locators and extraction rules. Metadata detection and screenshot masks are heuristic; static destination checks cannot predict arbitrary JavaScript navigation. Full desktop automation, banking integrations, production authentication, cloud queues, an operator dashboard and multi-tenant infrastructure are not implemented or required for this prototype. The [report](REPORT.md) explains how those extensions would fit.
