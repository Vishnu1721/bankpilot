# BankPilot

BankPilot is a prototype computer-use system that discovers workflows in a live business UI with an LLM, records successful workflows as reusable capability artifacts, and replays those capabilities deterministically without an LLM in the replay decision loop.

The included LegacyBank Credit Union portal provides four independent employee operations:

| Operation | Example goal | Safe stopping point | Generated artifact |
| --- | --- | --- | --- |
| Member Lookup | Find member `10023` | Member Details | `artifacts/lookup_member.json` |
| Balance Lookup | Get the Savings balance for `10024` | Balance Result | `artifacts/lookup_balance.json` |
| Create Sub-account | Prepare Holiday Savings named Vacation | Review New Sub-account | `artifacts/prepare_new_subaccount.json` |
| Deposit | Prepare a $200 Savings deposit | Deposit Review | `artifacts/prepare_deposit.json` |

The dashboard operations are independent. Creating a sub-account or preparing a deposit does not require first completing the Member Lookup workflow.

## Core design

~~~text
Natural-language goal
        |
        v
LLM discovery: observe -> decide one action -> validate -> execute
        |
        v
Versioned capability JSON
        |
        v
Deterministic replay: validate -> resolve inputs -> execute -> verify
~~~

- Discovery uses an LLM with a constrained action vocabulary.
- Replay executes recorded actions and does not ask an LLM what to do next.
- Runtime values are stored as placeholders such as `{{member_id}}`.
- The final application state must satisfy a recorded success condition.
- Safety checks run in application code outside the model.

## Discovery safety

### Untrusted UI content

Everything read from the application—including page text, labels, errors, element names, and values—is tagged `untrusted_ui_data`.

Before an observation reaches the model, BankPilot:

- includes rendered text and visible controls only;
- normalizes control characters and whitespace;
- caps body text, field lengths, and element count;
- detects common prompt-injection-like instructions;
- separates trusted policy from UI data in the model input; and
- escalates instead of following UI text that appears to instruct the agent.

This is defense in depth. Deterministic action validation, element binding, domain restriction, budgets, and approval boundaries remain authoritative.

### Explicit discovery budgets

`DiscoveryBudget` independently limits:

- total steps;
- LLM calls;
- elapsed wall-clock time;
- observation characters; and
- repeated identical states.

Exceeding any limit raises `DiscoveryBudgetExceeded` and produces a structured failure event instead of allowing an unbounded loop.

### Consequential actions

Sub-account and deposit discovery stop at review:

~~~text
Enter details -> Validate -> Review -> STOP FOR HUMAN APPROVAL
~~~

The controls `Confirm & Open` and `Post Deposit` are blocked by policy. The corresponding mock commit endpoints also return HTTP `403` and never change account data.

## Supported actions and selectors

Discovery supports:

~~~text
click
type
select
read
wait
finish
escalate
~~~

The browser adapter prefers stable `data-testid`, `aria-label`, `name`, `id`, and `href` selectors. It never interpolates raw multiline card text into CSS selectors. A structural XPath is used only as a final fallback.

Model output parsing accepts exactly the first valid JSON action. Extra prose or an accidentally appended second JSON object cannot cause Python's `JSONDecodeError: Extra data` failure.

## Project structure

~~~text
bankpilot/
├── artifacts/                 Generated capability JSON
├── demo_app/                  Local credit-union portal
│   ├── app.py
│   ├── static/
│   └── templates/
├── evidence/                  JSONL logs and screenshots
├── src/
│   ├── agent/                 LLM client, discovery loop, budgets
│   ├── capability/            Schema, recorder, replay
│   ├── handoff/               Human intervention and resume
│   ├── observability/         Structured event logging
│   ├── safety/                Policy and observation guard
│   └── surface/               Browser, terminal, desktop contracts
└── tests/                     Validation and live demonstrations
~~~

## Setup

Requirements:

- Python 3.11+
- Chromium installed through Playwright
- an OpenAI API key for discovery

~~~bash
git clone https://github.com/Vishnu1721/bankpilot.git
cd bankpilot
git switch feature/safe-multisurface-discovery

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
~~~

Add the API key to `.env`:

~~~text
OPENAI_API_KEY=your_key_here
~~~

Replay and deterministic validation do not require an OpenAI API call.

## Run the portal

Terminal 1:

~~~bash
source .venv/bin/activate
python demo_app/app.py
~~~

Open `http://127.0.0.1:5001`. Keep this terminal running while executing browser discovery.

## Validation

Run deterministic safety and portal tests:

~~~bash
python -m tests.test_security_boundaries
python -m tests.test_mock_subaccount
~~~

Expected output:

~~~text
6/6 security boundary tests passed
4/4 multi-operation portal tests passed
~~~

The tests cover untrusted-UI detection, discovery budgets, concatenated model JSON recovery, final-action blocking, independent dashboard routes, review rendering, invalid deposit amounts, and server-side `403` enforcement.

## Run each discovery workflow

With the portal running, execute each demonstration separately:

~~~bash
python -m tests.test_member_discovery
python -m tests.test_balance_discovery
python -m tests.test_subaccount_discovery
python -m tests.test_deposit_discovery
~~~

Each test opens Chromium, prints the page URL and selected target at every step, saves its capability and screenshot, and waits at `Press Enter to close...` so the final UI can be inspected.

Verified results:

- Member Lookup displayed Alex Morgan for member `10023`.
- Balance Lookup returned `$2150.75` for member `10024` Savings.
- Create Sub-account reached `/sub-account/review` for Holiday Savings named Vacation without opening an account.
- Deposit reached `/deposit/review` for a `$200.00` Savings deposit with memo Cash deposit without posting funds.

## Deterministic replay and exceptional paths

~~~bash
python -m tests.test_replay
python -m tests.test_business_outcome
python -m tests.test_recoverable_replay
python -m tests.test_hard_failure
python -m tests.test_handoff
~~~

These demonstrate successful replay, `MEMBER_NOT_FOUND` as a business outcome, bounded retry and recovery, structured hard failure with screenshot evidence, and same-session human handoff for member `10025`.

## Capability schema

Capabilities use schema version `1.1` and contain:

- identity and application metadata;
- typed parameters and outputs;
- ordered `type`, `select`, `click`, `wait`, or `extract` steps;
- semantic target information and selector fallback;
- parameter placeholders; and
- a machine-checkable success condition.

Example:

~~~json
{
  "step_id": "step_2",
  "action": "select",
  "target": {
    "role": "select",
    "name": "Account Type",
    "selector": "select[name=\"account_type\"]"
  },
  "value": "{{account_type}}",
  "description": "Select a value for Account Type."
}
~~~

## Surface abstraction

`BrowserSurface` is operational through Playwright. `TerminalSurface` supplies a restricted, no-shell executable allowlist and refuses arbitrary LLM commands. `DesktopSurface` defines an accessibility-tree extension point; platform-specific accessibility providers must be implemented before desktop execution is enabled.

Pixel-coordinate clicking and unrestricted terminal commands are intentionally excluded from the safe surface contract.

## Current scope

BankPilot is a prototype, not a real banking system. It uses local mock member data, does not authenticate real users, does not move money, and must not be connected to production banking applications without a stronger authorization model, structured risk classifications, credential isolation, audit controls, and reviewed tenant policies.

See `REPORT.md` for design reasoning, evaluation, limitations, and production extensions.
