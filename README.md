# BankPilot

BankPilot is a prototype computer-use automation system that discovers workflows in browser-based business applications and converts successful executions into reusable capability artifacts.

During **discovery**, an LLM operates a live application through a constrained observe → decide → act loop. After a successful run, BankPilot records the workflow as a structured, typed, versioned JSON capability.

During **replay**, BankPilot executes that saved capability deterministically with new parameters. The LLM is not used in the replay decision loop.

The project also demonstrates safety guardrails, structured error handling, bounded recovery, human-in-the-loop escalation, same-session resume, and execution evidence.

---

## Architecture

```text
Natural-Language Goal
        |
        v
+---------------------+
|   Discovery Agent   |
|       (LLM)         |
+----------+----------+
           |
           | constrained actions
           v
+---------------------+
|   Surface Adapter   |
|     Playwright      |
+----------+----------+
           |
           v
+---------------------+
|     LegacyBank      |
|      Mock UI        |
+----------+----------+
           |
           | successful workflow
           v
+---------------------+
| Capability Recorder |
+----------+----------+
           |
           v
+-----------------------------+
| Versioned Capability JSON   |
| parameters / targets /      |
| actions / outputs / success |
+-------------+---------------+
              |
              v
+-----------------------------+
| Deterministic Replay Engine |
|         NO LLM              |
+-------------+---------------+
              |
              v
   SUCCESS / BUSINESS OUTCOME
   / RECOVERY / FAILURE
```

Cross-cutting components include:

- safety policy
- domain and action allowlists
- risky-action blocking
- structured event logging
- screenshots on failures
- human handoff
- same-browser-session resume

---

## Demonstrated Workflow

The included LegacyBank application simulates a legacy banking administration interface.

The primary goal is:

```text
Look up a member and return their current savings balance.
```

During discovery, BankPilot can execute a request such as:

```text
Look up member 10023 and return their current savings balance.
```

The LLM discovers the workflow:

```text
TYPE member number
CLICK Search
EXTRACT Savings Balance
```

The resulting artifact does not persist the discovery value as a hardcoded workflow value.

Instead it records:

```json
"value": "{{member_id}}"
```

The same capability can therefore be replayed with another input such as `10024`.

---

## Discovery vs Replay

### Discovery

Discovery uses an LLM to determine the next action from the current UI observation.

The model is restricted to a small action vocabulary:

```text
click
type
read
wait
finish
escalate
```

The model does not receive unrestricted Python, JavaScript, shell, or Playwright execution access.

The discovery loop is:

```text
observe
   ↓
LLM decides one action
   ↓
safety validation
   ↓
execute
   ↓
observe again
```

A successful workflow is converted into a capability artifact.

### Replay

Replay loads the saved capability and executes its steps directly.

```text
Capability JSON
      ↓
Validate parameters
      ↓
Resolve {{member_id}}
      ↓
Locate recorded target
      ↓
Execute recorded action
      ↓
Extract output
      ↓
Validate success condition
```

There is **no LLM call in the replay decision loop**.

---

## Capability Artifact

An example generated artifact is available at:

```text
evidence/example_capability.json
```

The artifact contains:

- schema version
- capability identifier
- application and start URL
- typed input parameters
- typed outputs
- ordered actions
- semantic target information
- selector fallback information
- parameter placeholders
- extraction instructions
- success condition

Example:

```json
{
  "step_id": "step_1",
  "action": "type",
  "target": {
    "role": "textbox",
    "name": "Member Id",
    "selector": "input[name=\"member_id\"]"
  },
  "value": "{{member_id}}",
  "description": "Enter value into Member Id."
}
```

The capability is intentionally decoupled from the raw LLM transcript.

---

## Project Structure

```text
bankpilot/
├── artifacts/
├── demo_app/
│   ├── app.py
│   ├── static/
│   └── templates/
├── evidence/
├── src/
│   ├── agent/
│   ├── capability/
│   ├── handoff/
│   ├── observability/
│   ├── safety/
│   └── surface/
├── tests/
├── .env.example
├── .gitignore
├── main.py
├── README.md
├── REPORT.md
└── requirements.txt
```

---

## Requirements

- Python 3.11+
- Chromium installed through Playwright
- OpenAI API key for discovery
- macOS/Linux/Windows environment capable of running Playwright

Replay itself does not require an OpenAI API call.

---

## Installation

Clone the repository and enter the project directory.

```bash
git clone <YOUR_REPOSITORY_URL>
cd bankpilot
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it.

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install the Playwright Chromium browser:

```bash
playwright install chromium
```

Create your local environment file:

```bash
cp .env.example .env
```

Then add your OpenAI API key to `.env`:

```text
OPENAI_API_KEY=your_key_here
```

The `.env` file is excluded from Git and must never be committed.

---

## Start LegacyBank

BankPilot includes a local mock application so that computer-use behavior can be demonstrated safely and reproducibly.

In Terminal 1:

```bash
source .venv/bin/activate
python demo_app/app.py
```

LegacyBank runs at:

```text
http://127.0.0.1:5001
```

Keep this terminal running.

---

## Run LLM Discovery

In Terminal 2:

```bash
source .venv/bin/activate
python -m tests.test_discovery
```

A Chromium browser opens.

BankPilot uses the LLM-driven observe → decide → act loop to complete the workflow.

A successful run generates:

```text
artifacts/lookup_savings_balance.json
```

and discovery evidence under:

```text
evidence/
```

Discovery requires a configured OpenAI API key.

---

## Run Deterministic Replay

Run:

```bash
python -m tests.test_replay
```

The saved capability is replayed using a different member parameter.

Expected output includes:

```text
Extracted: $2150.75

REPLAY COMPLETED
```

and a structured result similar to:

```json
{
  "status": "success",
  "outputs": {
    "savings_balance": "$2150.75"
  }
}
```

No LLM is used to decide replay actions.

---

## Business Outcomes

BankPilot distinguishes an expected business outcome from an automation failure.

Run:

```bash
python -m tests.test_business_outcome
```

The demo searches for an unknown member.

Expected result:

```json
{
  "status": "business_outcome",
  "code": "MEMBER_NOT_FOUND",
  "message": "Member not found"
}
```

This is not classified as an automation failure because the application behaved correctly and returned a valid business outcome.

---

## Recoverable Conditions

Run:

```bash
python -m tests.test_recoverable_replay
```

The test introduces a controlled temporary UI failure.

BankPilot performs bounded deterministic retries:

```text
Recoverable condition at step_2
Retrying...
Recovered after 1 retry
```

The workflow then completes successfully.

The final result records:

```json
"recovered_steps": [
  "step_2"
]
```

---

## Hard Failures

Run:

```bash
python -m tests.test_hard_failure
```

This test simulates a target that remains unavailable.

BankPilot retries within its configured limit and then produces a structured hard failure.

Example:

```json
{
  "status": "failure",
  "code": "STEP_EXECUTION_FAILED",
  "failed_step": "step_2",
  "expected": "Action 'click' on target 'Search'.",
  "evidence_path": "evidence/failure_step_2.png"
}
```

The result includes:

- failed step
- expected behavior
- observed page state
- error information
- screenshot evidence

---

## Human-in-the-Loop Handoff

Run:

```bash
python -m tests.test_handoff
```

Member `10025` requires manual verification.

BankPilot:

```text
automation executes
        ↓
manual verification detected
        ↓
automation pauses
        ↓
browser remains open
        ↓
human completes verification
        ↓
human presses Enter
        ↓
automation resumes
        ↓
output extracted
```

The intervention occurs in the **same live browser session**.

Expected final output:

```text
Extracted: $3675.20

Human handoffs: 1
```

---

## Safety

BankPilot applies safety checks before browser actions and replay operations.

The current prototype includes:

- domain allowlisting
- constrained action vocabulary
- replay action validation
- risky-action detection
- secret-aware logging
- parameterized capability values

For example, navigation to an unapproved domain is blocked.

A risky action such as:

```text
Delete Account
```

is also blocked by the current policy.

The prototype's risky-action classifier is intentionally conservative and keyword-based. A production implementation should replace this with structured action risk metadata and policy evaluation.

---

## Observability

BankPilot emits structured JSONL execution events.

Evidence includes logs for:

```text
discovery
successful replay
recovered replay
business outcome
hard failure
human handoff
```

Example events include:

```text
replay_started
step_started
step_completed
step_retry
step_recovered
output_extracted
handoff_started
handoff_completed
replay_completed
replay_failed
```

Failure paths also capture screenshots.

---

## Evidence

The `/evidence` directory contains representative artifacts from the demonstrated workflows, including:

```text
example_capability.json
discovery_log.jsonl
replay_success.jsonl
replay_recovered.jsonl
replay_business_outcome.jsonl
replay_failure.jsonl
handoff_log.jsonl
discovery_final.png
replay_final.png
business_outcome.png
failure_step_2.png
handoff_final.png
```

The evidence demonstrates both successful and exceptional execution paths.

---

## Validation

Core architecture and policy checks can be run without an OpenAI API call:

```bash
python -m tests.test_validation
```

The validation suite covers:

- generic parameterization
- capability schema validation
- domain allowlisting
- blocked domains
- safe actions
- risky-action blocking
- replay parameter resolution

Parameterization can also be checked independently:

```bash
python -m tests.test_parameterization
```

---

## Security Notes

Do not commit:

```text
.env
API keys
credentials
session secrets
raw sensitive customer data
```

Runtime secrets are loaded from environment variables.

The checked-in capability example uses parameter placeholders such as:

```text
{{member_id}}
```

rather than persisting the discovery member value as a workflow constant.

---

## Design Scope

BankPilot is intentionally a focused prototype.

The implementation prioritizes:

1. real LLM-driven discovery against a live UI
2. a reusable capability representation
3. deterministic no-LLM replay
4. structured error handling
5. human escalation and same-session resume
6. safety boundaries
7. observable execution

Production extensions and deliberate cuts are discussed in `REPORT.md`.