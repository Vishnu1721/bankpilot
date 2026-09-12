# BankPilot Design Report

## 1. Architecture

BankPilot separates workflow discovery from workflow execution. The central design decision is that an LLM is useful for discovering how to operate an unfamiliar interface, but repeated execution should not depend on the LLM making the same decisions again.

The system therefore has two primary execution modes:

```text
                     DISCOVERY
Natural-Language Goal
        |
        v
+-------------------+
| Discovery Agent   |
|       LLM         |
+---------+---------+
          |
          | observe / decide / act
          v
+-------------------+
| Surface Adapter   |
|    Playwright     |
+---------+---------+
          |
          v
+-------------------+
| LegacyBank UI     |
+---------+---------+
          |
          | successful execution
          v
+-------------------+
| Capability        |
| Recorder          |
+---------+---------+
          |
          v
   Capability JSON


                       REPLAY
   Capability JSON
          |
          v
+-------------------+
| Replay Engine     |
|     NO LLM        |
+---------+---------+
          |
          v
+-------------------+
| Surface Adapter   |
|    Playwright     |
+---------+---------+
          |
          v
+-------------------+
| LegacyBank UI     |
+---------+---------+
          |
          v
      Typed Result
```

### Discovery Agent

The discovery agent receives a natural-language goal and repeatedly observes the live UI, asks the LLM for exactly one next action, validates that action against the safety policy, and executes it through the surface adapter.

The LLM is restricted to:

```text
click
type
read
wait
finish
escalate
```

It does not receive arbitrary Python, JavaScript, shell, or unrestricted Playwright execution.

This keeps the model in a planning role while deterministic application code retains control over actual execution.

### Surface Adapter

`BrowserSurface` encapsulates browser-specific interaction through Playwright.

It exposes a small interface for:

- navigation
- UI observation
- typing
- clicking
- screenshots

During observation, interactive elements are normalized into application-independent objects containing an element ID, semantic role, accessible/display name, selector, and current value.

This gives the discovery agent a simplified representation rather than exposing the entire browser automation API.

### Capability Recorder

A successful discovery is converted into a structured capability.

The recorder deliberately does not persist the raw LLM transcript. Model reasoning is useful during discovery but is not a stable execution contract.

Instead, the recorder produces deterministic descriptions and parameterizes runtime values.

For example, discovery may type:

```text
10023
```

but the capability stores:

```text
{{member_id}}
```

### Replay Engine

Replay loads and validates the capability artifact, resolves runtime parameters, executes recorded actions, extracts outputs, and verifies the success condition.

The replay engine does not import or call the LLM client. The next action comes entirely from the ordered capability steps.

This separation provides the key invariant of the design:

> LLM reasoning is used to discover a capability, but the capability—not the model transcript—is the execution contract for future runs.

### Cross-Cutting Components

Safety, observability, recovery, and human handoff are separated from the discovery logic where possible.

This allows the same policy and execution concepts to evolve independently of a particular model or application.

---

## 2. Artifact schema

The capability artifact is a versioned JSON document validated using Pydantic models.

A representative artifact is available at:

```text
evidence/example_capability.json
```

The top-level structure contains:

```text
schema_version
capability_id
name
description
application
start_url
parameters
outputs
steps
success_condition
```

### Versioning

`schema_version` identifies the capability schema contract.

The current prototype uses:

```json
"schema_version": "1.0"
```

Future schema changes can therefore be validated or migrated before replay.

### Typed Parameters

Inputs are explicitly declared rather than inferred from the discovery transcript.

Example:

```json
{
  "name": "member_id",
  "type": "string",
  "required": true,
  "description": "Member number to search for."
}
```

The runtime discovery value is converted into a placeholder:

```json
"value": "{{member_id}}"
```

During replay, the placeholder is resolved from the new input dictionary.

This allows one discovered capability to be reused with different member identifiers.

### Typed Outputs

The capability also declares its expected output:

```json
{
  "name": "savings_balance",
  "type": "string",
  "description": "Current savings balance."
}
```

The current prototype represents the balance as a string because the mock UI displays a formatted currency value. A production schema could introduce richer types such as currency, decimal, date, account identifier, or domain-specific records.

### Ordered Actions

The artifact records an ordered sequence such as:

```text
step_1 → type
step_2 → click
step_3 → extract
```

Each action contains enough information for replay without consulting the LLM.

### Target Identification

Interactive targets contain both semantic and structural information:

```json
{
  "role": "button",
  "name": "Search",
  "selector": "button[type=\"submit\"]"
}
```

Replay prefers semantic role/name identification and can fall back to the recorded selector.

This is more robust than storing only an absolute DOM path or screen coordinate.

### Data Extraction

The demonstration capability contains an explicit extraction step:

```json
{
  "action": "extract",
  "value": "Savings Balance"
}
```

The replay engine locates the corresponding table row and extracts the value.

This is intentionally separate from clicking and typing because returning structured data is part of the capability contract.

### Success Condition

The capability contains a machine-checkable success condition:

```json
{
  "type": "text_present",
  "value": "Member Details"
}
```

Replay is therefore not considered successful merely because every browser operation executed without throwing an exception. The final application state must also satisfy the recorded condition.

### Decoupling from the Model Transcript

The raw model reasoning is not the artifact.

For example, an LLM may say during discovery that a particular member number is already entered. That sentence is not persisted as an execution instruction.

Instead the artifact contains deterministic descriptions such as:

```text
Enter value into Member Id.
Click Search.
Extract the current savings balance.
```

This makes the artifact reviewable and reusable independently of the model that discovered it.

---

## 3. Determinism & error handling

Replay is designed around deterministic execution.

Given the same:

```text
capability
runtime parameters
application state
```

the replay engine executes the same ordered steps without asking an LLM what to do next.

### No LLM in the Replay Decision Loop

The discovery path uses `LLMClient`.

The replay path reads the capability and dispatches directly on recorded step types such as:

```text
TYPE
CLICK
WAIT
EXTRACT
```

There is no model call for deciding the next replay action.

This is important for repeatability, latency, cost, reviewability, and safety.

### Parameter Resolution

A template such as:

```text
{{member_id}}
```

is deterministically resolved from replay inputs.

For example:

```text
{{member_id}} + member_id=10024
```

becomes the runtime value used by the TYPE action.

### Expected Business Outcomes

A valid application response is not automatically an automation failure.

The demonstration includes an unknown member lookup. LegacyBank correctly returns:

```text
Member not found
```

BankPilot classifies this as:

```json
{
  "status": "business_outcome",
  "code": "MEMBER_NOT_FOUND"
}
```

This distinguishes domain outcomes from execution failures.

### Recoverable Conditions

Some failures may be transient.

Replay therefore supports bounded deterministic retries. The demonstration injects a controlled temporary target failure.

The execution behaves as:

```text
step fails
   |
   v
bounded wait
   |
   v
retry
   |
   v
target becomes available
   |
   v
continue replay
```

The final result records the recovered step:

```json
"recovered_steps": [
  "step_2"
]
```

Retries are bounded to avoid infinite loops and hidden nondeterministic behavior.

### Hard Failures

If the condition remains unresolved after the configured retry limit, replay returns a structured failure.

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

The failure includes:

- failing step
- error code
- message
- expected operation
- observed page summary
- recovered steps before failure
- screenshot path when capture succeeds

This is more useful than returning only a generic browser exception.

### Success Validation

After all recorded steps execute, the replay engine evaluates the capability success condition.

This protects against false success where browser calls technically succeed but the application ends in an unexpected state.

### Observability

Replay emits JSONL events including:

```text
replay_started
step_started
step_completed
step_retry
step_recovered
output_extracted
business_outcome
replay_completed
replay_failed
```

This allows a run to be reconstructed without depending solely on terminal output.

---

## 4. Heterogeneity & multi-tenant

The prototype implements a browser surface, but the architecture separates workflow semantics from the underlying UI mechanism.

The capability describes operations such as:

```text
type
click
extract
wait
```

rather than directly storing executable Python or arbitrary Playwright programs.

### Surface Abstraction

The current implementation uses:

```text
BrowserSurface → Playwright → LegacyBank
```

A broader system could introduce additional adapters:

```text
BrowserSurface
DesktopSurface
TerminalSurface
MobileSurface
```

Each adapter would expose normalized observations and a constrained action vocabulary.

The discovery and capability layers would therefore not need to understand the complete implementation details of every UI technology.

### Imperfect DOMs

The mock LegacyBank interface intentionally does not rely on test-specific IDs for every interaction.

The capability records both semantic target information and selector fallback information.

For heterogeneous browser applications, target resolution could evolve into a ranked strategy:

```text
stable application identifier
        ↓
semantic role + name
        ↓
label relationship
        ↓
recorded selector
        ↓
relative structural locator
        ↓
visual locator
        ↓
human escalation
```

This would support older enterprise applications where accessibility metadata and DOM structure are inconsistent.

### Multi-Tenant Reuse

A production system should not create independent executable code for every tenant.

Instead, the capability should remain a logical workflow while tenant-specific differences are supplied through configuration.

Conceptually:

```text
Capability
   |
   +--- tenant configuration
   |
   +--- application profile
   |
   +--- surface adapter
   |
   +--- policy profile
```

Tenant configuration could contain:

- approved domains
- application base URL
- locator overrides
- feature flags
- timeout profiles
- authentication strategy
- tenant-specific business outcome mappings

The capability would continue to express the business workflow.

### Capability Identity

A production registry could identify capabilities using:

```text
capability_id
schema_version
capability_version
application
tenant compatibility
```

This would allow controlled rollout, review, rollback, and migration across customers.

### Limits of the Prototype

The submitted implementation demonstrates the architectural boundary rather than implementing a full multi-tenant registry or multiple surface technologies.

The primary implemented surface is browser-based Playwright automation against LegacyBank.

---

## 5. Escalation & handoff

BankPilot supports human intervention without discarding the active browser session.

This is important for workflows containing steps that should not or cannot be automated safely.

### Demonstrated Scenario

Member `10025` requires manual verification.

The flow is:

```text
Replay starts
    |
    v
member lookup
    |
    v
Manual Verification Required
    |
    v
AUTOMATION PAUSES
    |
    v
human uses existing browser
    |
    v
human completes verification
    |
    v
human signals completion
    |
    v
AUTOMATION RESUMES
    |
    v
Savings Balance extracted
```

The browser is not closed during handoff.

The human operates the same Playwright-created browser page, preserving the live application context.

After the human completes verification and confirms continuation in the terminal, replay observes the resulting state and continues.

### Same-Session Resume

The handoff manager intentionally retains:

```text
browser
page
current navigation state
session state
```

No new replay is started from the beginning.

The demonstrated result completes with:

```text
Human handoffs: 1
```

and extracts the requested balance after intervention.

### Handoff Observability

The handoff path logs:

```text
handoff_started
handoff_completed
```

alongside normal replay events.

This provides evidence that manual intervention occurred rather than silently treating the workflow as fully automated.

### Production Extension

A production implementation could replace the terminal confirmation with a task queue or operator console.

The handoff package would provide the operator with:

- reason for escalation
- current application
- current workflow step
- screenshot
- relevant non-sensitive context
- allowed intervention instructions
- resume/cancel controls

The execution session could be held by a worker while the human task is outstanding, or serialized using an approved session continuation mechanism where supported.

---

## 6. Safety

Safety is enforced outside the LLM rather than relying solely on model instructions.

The model proposes an action, but application code decides whether that action may execute.

### Domain Allowlist

Navigation is restricted to approved hosts.

The demonstration permits:

```text
127.0.0.1
localhost
```

An attempt to navigate to an unapproved domain such as `example.com` raises a safety violation.

This prevents a discovered or replayed workflow from silently leaving its approved application boundary.

### Action Allowlist

Discovery is restricted to the defined action vocabulary:

```text
click
type
read
wait
finish
escalate
```

The model cannot request arbitrary code execution.

Replay similarly executes only recognized capability step types.

### Risky Actions

The prototype identifies potentially destructive or sensitive operations using a conservative set of risky terms, including operations related to:

```text
deletion
money transfer
withdrawal
account closure
payment approval
```

For example, clicking:

```text
Delete Account
```

is blocked by the safety policy.

### Safety During Replay

Safety is not limited to discovery.

Replay checks:

- start URL
- current URL
- replay action
- target information

This prevents a reviewed artifact from bypassing runtime safety controls.

### Secret and Data Handling

Secrets are loaded from environment variables rather than committed source code.

`.env` is excluded by `.gitignore`.

Structured logs redact keys associated with secrets and sensitive identifiers.

The capability artifact parameterizes the member identifier rather than storing the discovery value as a reusable workflow constant.

The implementation deliberately avoids persisting the full raw UI body or raw LLM transcript in discovery logs.

### Production Safety Model

The current risky-action classifier is keyword-based and is appropriate only for this prototype.

A production implementation should attach structured risk metadata to capability operations, for example:

```text
READ_ONLY
LOW_RISK_WRITE
FINANCIAL_ACTION
DESTRUCTIVE_ACTION
PRIVILEGED_ACTION
```

Policy could then require:

```text
allow
deny
human approval
step-up authentication
```

based on tenant configuration, user permissions, environment, and capability version.

High-risk capabilities should also require explicit review before publication to a capability registry.

---

## 7. Cuts

This submission intentionally focuses on the core architectural problem rather than attempting to build a complete enterprise automation platform.

### Local Mock Application

I used a local LegacyBank application instead of automating a real banking website.

This provides a safe, deterministic environment for demonstrating discovery, replay, business outcomes, failures, and handoff without depending on third-party terms of service, authentication, rate limits, or changing production UI.

### Browser Surface Only

The architecture discusses multiple surface types, but only the Playwright browser adapter is implemented.

Given more time, I would implement the same normalized surface contract for another heterogeneous surface, such as a desktop application or terminal interface.

### Simple Extraction Strategy

The demonstration extracts the savings balance from a table row identified by its label.

A production system should support typed extraction rules such as:

```text
text
currency
date
table
record
list
```

and multiple extraction strategies.

### Prototype Locator Strategy

Replay currently uses semantic role/name targeting with selector fallback.

A production locator system should maintain ranked locator candidates, confidence, application-specific overrides, and controlled healing/versioning rather than silently modifying capabilities.

### Keyword-Based Risk Detection

Risky-action detection is intentionally simple.

A production implementation should use explicit operation risk classifications and authorization policies rather than relying primarily on target text.

### In-Process Human Handoff

The prototype pauses on terminal input while keeping the browser alive.

A production system would use an operator queue, durable workflow state, ownership/lease management, timeout handling, and auditable resume authorization.

### Authentication

The demonstration does not automate real authentication or persist credentials.

Production authentication should integrate with an approved secret manager and tenant identity model while keeping credentials outside capability artifacts and logs.

### Capability Registry

Artifacts are stored as local JSON files.

A production implementation would use a registry providing:

```text
versioning
review status
ownership
tenant compatibility
audit history
rollback
migration
deprecation
```

### Observability Backend

The prototype uses JSONL logs and screenshots because they are simple, inspectable evidence for the take-home.

Production execution would emit structured traces, metrics, and events to a centralized observability system with retention and access controls.

### Testing Scope

The project contains focused validation and scenario tests, including:

```text
successful discovery
successful replay
parameterization
business outcome
recoverable condition
hard failure
safety enforcement
human handoff
```

Given more time, I would add broader unit coverage, browser integration tests in CI, schema migration tests, fuzz testing for artifacts, and property-based testing for parameter substitution and policy boundaries.

### Final Tradeoff

The main priority was to make the central architecture concrete and defensible:

```text
LLM discovers
      ↓
structured artifact captures capability
      ↓
deterministic engine replays it
      ↓
safety remains outside the model
      ↓
failures are explicit
      ↓
humans can intervene without losing context
```

The deliberately omitted production infrastructure is separable from that core design rather than being required to demonstrate it.