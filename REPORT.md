# BankPilot Design Report

## 1. Executive summary

BankPilot demonstrates a two-phase approach to computer-use automation:

1. an LLM discovers how to complete a workflow through a constrained UI interface; and
2. the successful workflow becomes a typed capability that can be replayed deterministically without an LLM deciding subsequent actions.

The current prototype operates a local LegacyBank Credit Union employee portal. It supports independent Member Lookup, Balance Lookup, Create Sub-account, and Deposit workflows. Read-only workflows may finish when the requested information is visible. Consequential workflows stop at a review screen and require human approval; the mock application never creates an account or posts funds.

## 2. Architecture

### Discovery

~~~text
Trusted user goal
      |
      v
Observe visible UI -> sanitize/tag untrusted data -> LLM proposes one action
      |                                             |
      +---------------- policy validation <---------+
                            |
                            v
                    Surface executes action
                            |
                            v
                  Record successful workflow
~~~

The LLM may propose `click`, `type`, `select`, `read`, `wait`, `finish`, or `escalate`. It cannot return executable Python, JavaScript, shell commands, or Playwright selectors. The proposed element ID must exist in the current observation before application code executes it.

### Capability recording

The recorder converts successful discovery into schema-versioned JSON. It stores ordered actions and stable targets rather than the raw model transcript. Runtime values are parameterized:

~~~text
discovery value: 10024
artifact value:  {{member_id}}
~~~

This prevents a discovered member identifier, account type, amount, or memo from becoming an unintended constant in future runs.

### Replay

~~~text
Capability JSON -> schema validation -> input resolution -> ordered execution
       -> output extraction -> success-condition validation -> typed result
~~~

Replay does not ask the LLM what to do next. The artifact is the execution contract. This improves repeatability, latency, cost, reviewability, and safety.

## 3. Multi-operation portal

The original prototype began with one member-search workflow. The expanded portal uses an operations dashboard so each business request begins independently.

| Capability | Inputs | Completion condition | Risk boundary |
| --- | --- | --- | --- |
| `lookup_member` | `member_id` | Member Details visible | Read only |
| `lookup_balance` | `member_id`, `account_type` | Balance Result visible | Read only |
| `prepare_new_subaccount` | `member_id`, `account_type`, `nickname` | Review New Sub-account visible | Stop before creation |
| `prepare_deposit` | `member_id`, `account_type`, `amount`, `memo` | Deposit Review visible | Stop before posting |

This separation prevents one large, ambiguous capability from accumulating unrelated permissions. It also makes artifacts easier to review, version, test, and authorize independently.

## 4. Artifact schema

The current Pydantic-validated schema version is `1.1`. A capability contains:

~~~text
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
~~~

Step types include `type`, `select`, `click`, `wait`, and `extract`. Interactive targets carry semantic role/name information plus a selector fallback. Replay attempts semantic targeting and then the recorded selector.

The success condition is evaluated after recorded actions finish. Browser calls completing without an exception is insufficient: the expected final application state must be visible.

## 5. Untrusted UI threat model

UI text is not trusted merely because it appears inside an allowlisted application. A label, error, notification, hidden element, or compromised data record could contain instructions aimed at the model.

BankPilot treats page text, titles, labels, element names, and values as `untrusted_ui_data`. The observation guard:

- uses rendered body text and visible controls;
- removes control characters and normalizes whitespace;
- caps text length, field length, and element count;
- detects common instructions to ignore policy, change role, reveal secrets, or execute code; and
- escalates when instruction-like UI content is detected.

Trusted policy is placed in the system message. The user goal and UI observation are serialized separately, and the UI envelope explicitly states that its contents are data rather than instructions.

Pattern detection is not presented as a complete prompt-injection solution. The authoritative controls are outside the model: action allowlists, current-observation element binding, approved domains, discovery budgets, risk policy, and human approval.

## 6. Bounded discovery

Restricting the action vocabulary does not by itself prevent an infinite or costly discovery loop. `DiscoveryBudget` therefore enforces separate limits on:

| Limit | Purpose |
| --- | --- |
| `max_steps` | Bounds total observe/act iterations |
| `max_llm_calls` | Bounds model usage and cost |
| `max_elapsed_seconds` | Bounds wall-clock execution |
| `max_observation_chars` | Bounds UI data sent for reasoning |
| `max_same_state` | Detects repeated no-progress states |

Configuration and consumption are logged. Crossing a limit raises `DiscoveryBudgetExceeded` and terminates the run explicitly.

## 7. Browser targeting and model-output robustness

The browser adapter normalizes visible controls into element ID, role, name, selector, and value. Stable selector priority is:

~~~text
data-testid -> aria-label -> name -> id -> href -> structural XPath
~~~

Raw rendered card text is never inserted into a CSS selector. This prevents multiline text, quotes, `$`, `+`, and other CSS-sensitive characters from creating malformed selectors.

The model is instructed to return one JSON action. As defensive parsing, BankPilot extracts exactly the first valid JSON object. Appended prose or an accidental second object no longer causes `JSONDecodeError: Extra data`. Pydantic still validates the parsed action before use.

## 8. Consequential-action safety

The model proposes actions, but application code decides whether they may execute.

### Domain and action restrictions

The demo allows only `127.0.0.1` and `localhost`. Discovery and replay recognize only approved action types. The model cannot supply arbitrary selectors or code.

### Review-before-commit

Sub-account creation and deposits use a two-layer boundary:

1. policy blocks `Confirm & Open` and `Post Deposit`; and
2. the mock commit endpoints return HTTP `403` without changing data.

The requested capability is therefore preparation—not autonomous financial commitment.

### Production direction

Keyword matching is intentionally conservative and suitable only for a prototype. Production actions should carry explicit classifications such as `READ_ONLY`, `LOW_RISK_WRITE`, `FINANCIAL_ACTION`, `DESTRUCTIVE_ACTION`, and `PRIVILEGED_ACTION`. Tenant policy could then allow, deny, require approval, or require step-up authentication.

## 9. Determinism and error handling

Replay resolves placeholders from validated runtime input and dispatches directly on recorded step types. It distinguishes:

- success;
- expected business outcomes such as `MEMBER_NOT_FOUND`;
- recoverable transient conditions;
- hard execution failures; and
- human intervention requirements.

Retries are bounded. A recovered step is recorded in the final result. Persistent failures include the failed step, expected behavior, observed page summary, error information, and screenshot evidence.

After execution, replay validates the capability success condition to prevent false success caused by technically successful browser calls ending on the wrong page.

## 10. Human handoff

Member `10025` demonstrates same-session intervention. Automation pauses on the verification page, the browser remains open, a human completes the required action, and replay resumes in the same page and session.

The prototype records `handoff_started` and `handoff_completed`. A production implementation would replace terminal input with an operator queue containing the reason, current step, screenshot, safe context, ownership, timeout, and resume/cancel authorization.

## 11. Surface abstraction

The shared `Surface` contract separates workflow semantics from interaction technology.

- `BrowserSurface` is operational through Playwright.
- `TerminalSurface` provides a restricted executable allowlist, calls subprocesses with `shell=False`, and refuses arbitrary LLM-generated commands.
- `DesktopSurface` defines an accessibility-tree extension point with application allowlisting. Platform accessibility providers are not yet implemented.

Pixel-coordinate clicking and unrestricted shell execution are deliberately excluded. Desktop execution should use stable accessibility elements and foreground-application checks before it is enabled.

## 12. Observability

Discovery and replay emit JSONL events. Discovery output now includes page title, URL, chosen action, target name, selector, and post-action URL. This makes unexpected navigation diagnosable.

Representative events include:

~~~text
discovery_started
observation
agent_decision
action_executed
discovery_completed
discovery_failed
replay_started
step_started
step_retry
step_recovered
output_extracted
business_outcome
handoff_started
handoff_completed
replay_completed
replay_failed
~~~

Failure paths capture screenshots when possible. Secrets remain in environment variables and are excluded from artifacts and source control.

## 13. Evaluation

The following deterministic validations were executed successfully:

~~~text
6/6 security boundary tests passed
4/4 multi-operation portal tests passed
~~~

Observed live discovery results:

| Scenario | Observed result |
| --- | --- |
| Member Lookup | Member `10023`, Alex Morgan |
| Balance Lookup | Member `10024`, Savings, `$2150.75` |
| Create Sub-account | Holiday Savings / Vacation reached `/sub-account/review`; not opened |
| Deposit | `$200.00` to Savings with Cash deposit memo reached `/deposit/review`; not posted |

The project also demonstrates deterministic replay with a new member parameter, a recognized member-not-found business outcome, bounded recovery after one retry, structured hard failure evidence, and one same-session human handoff.

## 14. Deliberate cuts and limitations

The project is a safe prototype rather than a production banking automation platform.

- Member and account data are local mock records rather than a database-backed core.
- Authentication, authorization, roles, and real credentials are not implemented.
- No real account is opened and no money is moved.
- Desktop support is an interface and policy boundary, not a platform implementation.
- Terminal execution is restricted and is not yet connected to the discovery action vocabulary.
- The risk classifier is keyword-based rather than policy-metadata-based.
- Extraction currently uses simple labeled table rows.
- Artifacts are local JSON rather than a reviewed capability registry.
- Logs and screenshots are local rather than a centralized observability backend.
- Browser integration tests are manually launched rather than continuously executed in CI.

## 15. Production extensions

A production path would add:

- a capability registry with ownership, versions, approval, rollback, and migration;
- tenant application profiles and locator overrides;
- structured permissions and risk metadata;
- durable workflow state and operator handoff queues;
- secret-manager and identity-provider integration;
- typed currency, date, table, list, and record extraction;
- ranked locator candidates with controlled healing;
- browser integration tests, fuzzing, and policy property tests in CI; and
- centralized traces, metrics, audit events, retention, and access control.

The core invariant remains:

~~~text
LLM discovers -> typed artifact records -> deterministic engine replays
       -> policy remains outside the model -> humans approve consequential actions
~~~
