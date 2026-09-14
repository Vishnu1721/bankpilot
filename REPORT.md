# BankPilot Design Report

## 1. Architecture

BankPilot separates probabilistic discovery from deterministic execution. During discovery, a trusted user goal is combined with a sanitized observation of the visible UI. The LLM may propose only `click`, `type`, `select`, `read`, `wait`, `finish`, or `escalate`, and it refers to a current observation element ID rather than supplying code or selectors. Application code validates the proposed action, binds it to the observed element, checks the domain and risk policy, executes it through a surface adapter, and records successful actions. Browser text is always treated as untrusted data, not instructions.

The recorder converts the successful trace into a typed, parameterized capability. Replay then validates the artifact and runtime inputs, navigates to the recorded start URL, performs its ordered steps without an LLM, extracts declared outputs, and verifies a success condition. The local LegacyBank Credit Union portal exposes four independent workflows: member lookup, balance lookup, sub-account preparation, and deposit preparation. Browser automation is operational; the terminal adapter is restricted to a no-shell executable allowlist; desktop support is an accessibility-tree contract that deliberately remains disabled until platform providers and foreground-application checks exist.

## 2. Artifact schema

Schema `1.1` capabilities contain identity, application, start URL, typed parameters, typed outputs, ordered steps, targets, and a machine-checkable success condition. Runtime data such as `10023`, `Savings`, `Vacation`, or `200` is stored as placeholders such as `{{member_id}}`, preventing discovery values from becoming replay constants. Targets use semantic role and accessible name plus a selector fallback. The preferred selector order is `data-testid`, `aria-label`, `name`, `id`, `href`, then structural XPath.

Every declared output now has a matching extraction step: `lookup_member` returns `member_name`; `lookup_balance` returns `current_balance`; `prepare_new_subaccount` returns the reviewed `account_type`; and `prepare_deposit` returns the reviewed `amount`. Review-only workflows also require their review heading as the success condition, so extraction alone cannot create false success. The canonical checked-in artifact is `evidence/example_capability.json`; sanitized schema-1.1 examples for all four operations are in `artifacts/`.

## 3. Determinism & error handling

Replay resolves placeholders from validated inputs and dispatches directly on the recorded step type. It does not ask a model to reinterpret the goal or page. Semantic targeting is tried before the recorded selector. Successful browser calls are insufficient: replay finally checks the expected page text and returns a typed result containing status, outputs, recovered steps, and diagnostic fields.

Expected business outcomes, transient failures, and hard failures are distinct. “Member not found” returns `MEMBER_NOT_FOUND`, not a generic exception. Recoverable steps use bounded retries and record both retry and recovery events. A persistent step failure records the failed step, expected action, observed page summary, error, and screenshot; a failed final condition is reported separately. Discovery is also bounded by maximum steps, LLM calls, elapsed time, observation size, and repeated identical states. Model responses are schema-validated, and the JSON parser tolerates trailing prose or an accidental second object by extracting the first valid JSON object.

## 4. Heterogeneity & multi-tenant

The proposed deployment model composes a reviewed base vendor capability with tenant and application overlays:

```text
base vendor capability
+ tenant configuration
+ application/version profile
+ locator overrides
+ tenant safety policy
= approved tenant capability version
```

The base capability owns business semantics, parameter/output contracts, ordered actions, and generic success criteria shared across institutions using the same vendor. A tenant configuration identifies institution, allowed environments, authentication integration, and locale. The application profile declares vendor product, deployment channel, supported version range, and UI feature flags. Locator overrides replace only targets known to differ for that tenant; domain and policy overrides narrow permitted hosts, actions, amounts, roles, and approval requirements. Overrides may restrict a base policy but may not silently weaken mandatory platform controls.

Each approved capability version records the base version, tenant overlay version, compatible vendor versions, test evidence, reviewer, and approval state. Scheduled canary replays and page fingerprints detect drift. A mismatch in application version, success condition, locator confidence, or expected page structure opens the circuit: automation stops safely, preserves evidence, and routes to a human. It never guesses through a tenant variant. Operators may select a previously approved compatible version, apply a reviewed locator override, or re-run discovery and approve a newly recorded version. This design shares stable vendor behavior without pretending all institutions expose identical DOMs or policies.

## 5. Escalation & handoff

Member `10025` demonstrates same-session human intervention. When manual verification appears, automation pauses and preserves the live browser. The `handoff_started` event now records control owner `human`, capability ID, current step, URL, page title, reason, and `evidence/handoff_required.png`. The prompt asks the operator to complete verification in that same browser and records a description of the human action. `handoff_completed` transfers ownership back to `automation`, logs the action and resulting URL, and replay resumes without rebuilding the session.

Production would replace terminal input with an authenticated operator queue, timeout and cancel controls, least-privilege context, and explicit resume authorization. The prototype nevertheless demonstrates the required control transfer, preserved session, intervention evidence, and audit trail.

## 6. Safety

Rendered page text, labels, values, notifications, errors, and element names are untrusted input. The observation guard considers only visible controls and rendered body text, removes control characters, normalizes whitespace, caps text and element counts, labels the envelope `untrusted_ui_data`, and escalates on common prompt-injection patterns. Trusted policy remains in the system message. Pattern matching is defense in depth; authoritative controls remain outside the model.

Discovery and replay allow only local approved domains and a fixed action vocabulary. Model actions must reference an element in the current observation. Terminal execution uses `shell=False` and an executable allowlist; arbitrary commands are refused. Consequential banking actions stop at review: policy blocks “Confirm & Open” and “Post Deposit,” while both mock commit endpoints independently return HTTP `403` and change no data. Secrets remain in environment variables. JSONL logs include what happened and, for model decisions, the recorded `reasoning` field.

## 7. Cuts

This is a safe prototype, not production banking software. Data is local and mocked; authentication, roles, real credentials, core-banking integration, durable state, centralized audit storage, and actual money movement are excluded. Desktop execution is a contract rather than an implementation, and terminal support is not yet part of LLM discovery. Risk classification is conservative keyword policy rather than signed action metadata. Extraction handles labeled table rows rather than arbitrary documents. Multi-tenancy is a credible design, not deployed infrastructure. Artifacts are files rather than an approval registry, and browser demonstrations are locally launched rather than continuous integration jobs.

Verified deterministic checks cover untrusted-UI detection, budgets, output contracts, final-action blocking, portal routes, review-only behavior, invalid amounts, and server-side `403` enforcement. Live discovery evidence records sub-account review and deposit review without commitment. The deliberate core invariant is preserved: the LLM discovers, a typed artifact records, deterministic code replays, external policy governs, and humans control consequential actions.
