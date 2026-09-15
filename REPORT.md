# BankPilot Design Report

## 1. Architecture

BankPilot separates probabilistic discovery from deterministic execution. During discovery, a trusted user goal is combined with a sanitized observation of the visible UI. The LLM may propose only `click`, `type`, `select`, `read`, `wait`, `finish`, or `escalate`, and it refers to a current observation element ID rather than supplying code or selectors. Application code validates the proposed action, binds it to the observed element, checks the domain and risk policy, executes it through a surface adapter, and records successful actions. Browser text is always treated as untrusted data, not instructions.

The recorder converts the successful trace into a typed, parameterized capability. A file-backed capability registry adds tenant, application, version, intent, lifecycle state, and approver metadata. The router first searches this catalog: an approved match goes directly to replay without an LLM; a draft match stops for approval; an unknown goal requests bounded discovery. Successful discovery registers a draft rather than making new automation immediately executable. Replay validates the artifact and runtime inputs, performs its ordered steps, extracts outputs, and verifies a success condition.

The local LegacyBank Credit Union portal exposes four independent workflows: member lookup, balance lookup, sub-account preparation, and deposit preparation. Browser automation is operational; the terminal adapter is restricted to a no-shell executable allowlist; desktop support is an accessibility-tree contract that deliberately remains disabled until platform providers and foreground-application checks exist.

## 2. Artifact schema

Schema `1.1` capabilities contain identity, application, start URL, enum-constrained parameter/output types, ordered steps, targets, named extraction mappings, and an enum-constrained success condition. Runtime data is stored as placeholders such as `{{member_id}}`, preventing discovery values from becoming replay constants. Replay rejects missing, unexpected, or incorrectly typed inputs. Targets use semantic role and accessible name plus a selector fallback.

Every declared output now has a matching extraction step: `lookup_member` returns `member_name`; `lookup_balance` returns `current_balance`; `prepare_new_subaccount` returns the reviewed `account_type`; and `prepare_deposit` returns the reviewed `amount`. Review-only workflows also require their review heading as the success condition, so extraction alone cannot create false success. A genuinely new workflow receives a deterministic discovered ID, no invented output contract, and a final-page checkpoint; a reviewer can refine its contract before approval. The canonical checked-in artifact is `evidence/example_capability.json`; sanitized schema-1.1 examples for all four operations are in `artifacts/`.

## 3. Determinism & error handling

Replay resolves placeholders from validated inputs and dispatches directly on the recorded step type. It does not ask a model to reinterpret the goal or page. Semantic targeting is tried before the recorded selector. Successful browser calls are insufficient: replay checks expected text, exact title, or URL pattern. Discovery applies the same typed checkpoint to the current observation before accepting `finish` or saving an artifact.

Expected business outcomes, transient failures, and hard failures are distinct. Verified replay of member `99999` returns `MEMBER_NOT_FOUND` immediately after the search rather than retrying extraction. The recoverable-path test injects one temporary Search Member failure at step 3, retries once, completes, and returns `recovered_steps=["step_3"]`. The hard-failure test keeps the same target unavailable, performs two bounded retries, returns `STEP_EXECUTION_FAILED` with `failed_step="step_3"`, and saves `evidence/failure_step_3.png`. A failed final condition is reported separately.

These exceptional-path tests use the committed capability fixture rather than the artifact overwritten by live discovery. This matters because the LLM may validly choose Member Lookup or Balance Lookup for a savings goal; replay adapts extraction to the recorded route, while fault-injection tests require a stable target. Assertions enforce each intended status and prevent an ordinary successful replay from being mistaken for a successful edge-case demonstration. Discovery itself is bounded by maximum steps, LLM calls, elapsed time, observation size, and repeated identical states. Model responses are schema-validated, and the JSON parser tolerates trailing prose or an accidental second object by extracting the first valid JSON object.

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

The implemented registry already enforces tenant and application scope plus draft/approved/retired lifecycle states. Tests prove an approval for tenant A is not visible to tenant B. The remaining production design records the base version, tenant overlay version, compatible vendor versions, test evidence, reviewer, and approval state. Scheduled canary replays and page fingerprints detect drift. A mismatch in application version, success condition, locator confidence, or expected page structure opens the circuit: automation stops safely, preserves evidence, and routes to a human. It never guesses through a tenant variant. Operators may select a previously approved compatible version, apply a reviewed locator override, or re-run discovery and approve a newly recorded version.

## 5. Escalation & handoff

Member `10025` demonstrates same-session human intervention. The verified run pauses after the Search Member click at step 3, displays Manual Verification Required, and preserves the live browser. The `handoff_started` event records control owner `human`, capability ID, current step, URL, page title, reason, and `evidence/handoff_required.png`. The operator clicks Complete Verification in that browser and describes the action in the terminal. `handoff_completed` transfers ownership back to `automation`, logs the action and resulting URL, and replay extracts `$3675.20` at step 4 without rebuilding the session. The run reports exactly one handoff.

The same handoff manager is injectable into ordinary replay and discovery. Exhausted retries, explicit escalation, and blocked actions can transfer the preserved live session. Resume requires a nonblank description of the human action and a changed URL/title/body fingerprint; pressing Enter alone cannot claim completion. Production would replace terminal input with an authenticated operator queue, timeout and cancel controls, least-privilege context, and explicit resume authorization.

## 6. Safety

Rendered page text, labels, values, notifications, errors, and element names are untrusted input. The observation guard considers only visible controls and rendered body text, removes control characters, normalizes whitespace, caps text and element counts, labels the envelope `untrusted_ui_data`, and escalates on common prompt-injection patterns. Trusted policy remains in the system message. Pattern matching is defense in depth; authoritative controls remain outside the model.

Discovery and replay require an approved host plus a route-specific action policy. Each route declares allowed action kinds and exact clickable targets, so generic wording such as “Proceed” grants no authority. Consequential routes and targets are not allowlisted; the mock commit endpoints independently return HTTP `403`. Terminal execution uses `shell=False` and an executable allowlist.

The logger recursively redacts sensitive fields and patterns inside arbitrary strings, including member-number, currency, SSN, and person-name patterns. Screenshot capture masks form controls and common result, notice, and error regions. Production should add institution-specific classification, encrypted evidence storage, retention policy, and access auditing.

## 7. Cuts

This is a safe sandbox prototype, not production banking software. Phase one implements capability routing, approval lifecycle, and tenant isolation using JSON files. Real authentication, core-banking connectors, regulated customer storage, actual account commitment, database-backed multi-tenancy, cloud queues, an operator web console, centralized telemetry, full desktop drivers, and screenshot-coordinate control remain future phases. Financial commitment remains blocked until authenticated roles, dual approval, idempotency, and immutable audit controls exist. Terminal support is not yet part of LLM discovery; risk classification is conservative keyword policy; and extraction handles labeled table rows rather than arbitrary documents.

Verified deterministic checks report 5/5 security boundaries, 8/8 hardening checks, 4/4 portal behaviors, 5/5 output contracts, and 3/3 router lifecycle tests. A failed extraction is retried after handoff; if it still fails, replay returns `STEP_EXECUTION_FAILED`. Final success independently requires every declared output, so a changed page cannot produce `success` with an empty output object. Unfamiliar discovery never copies raw goal text or unmatched typed values into an artifact. The complete canonical evidence set is committed: the model-driven Member Lookup discovery log, its generated savings-balance artifact, the deterministic replay log, the redacted replay screenshot, and a matching privacy-redacted transcript. The evidence can be inspected without an API key; independently rerunning model-driven discovery still requires the evaluator's own key.
