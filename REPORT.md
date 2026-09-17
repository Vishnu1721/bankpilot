# BankPilot Design Report

## 1. Architecture

BankPilot separates probabilistic discovery from deterministic execution. During discovery, a trusted user goal is combined with a sanitized observation of the visible UI. The LLM may propose only `click`, `type`, `select`, `read`, `wait`, `finish`, or `escalate`, and it refers to a current observation element ID rather than supplying code or selectors. Application code validates the proposed action, binds it to the observed element, checks the domain and risk policy, executes it through a surface adapter, and records successful actions. Browser text is always treated as untrusted data, not instructions.

The recorder converts the successful trace into a typed, parameterized capability. A file-backed capability registry adds tenant, application, version, intent, lifecycle state, and approver metadata. The router first searches this catalog: an approved match goes directly to replay without an LLM; a draft match stops for approval; an unknown goal requests bounded discovery. Successful discovery registers a draft rather than making new automation immediately executable. Replay validates the artifact and runtime inputs, performs its ordered steps, extracts outputs, and verifies a success condition.

The mock portal exposes member lookup, balance lookup, sub-account preparation, and deposit preparation. Browser automation is the only complete surface. `TerminalSurface` is a restricted no-shell adapter and `DesktopSurface` is a fail-closed accessibility-tree seam; neither is claimed as implemented automation.

The executable `main.py` exposes `discover` and `replay` commands. Discovery
accepts `--goal`, `--target`, `--artifact`, and repeatable runtime parameters;
replay accepts a saved artifact plus new invocation parameters without an LLM
call. Both paths use the same safety and execution engines as the demos.

## 2. Artifact schema

Schema `1.1` capabilities contain identity, application, start URL, enum-constrained parameter/output types, ordered steps, targets, named extraction mappings, and an enum-constrained success condition. Runtime data is stored as placeholders such as `{{member_id}}`, preventing discovery values from becoming replay constants. Replay rejects missing, unexpected, or incorrectly typed inputs. Targets use semantic role and accessible name plus a selector fallback.

Every output has a named extraction step: member name, balance, reviewed account type, or reviewed deposit amount. Review workflows also require the expected review heading, so extraction alone cannot produce success. An unfamiliar workflow receives a deterministic ID, no invented output contract, and a final-page checkpoint for reviewer refinement. Sanitized schema-1.1 examples are committed in `artifacts/` and `evidence/example_capability.json`.

UI-derived target roles, accessible names, selectors, descriptions, and generic
page-title checkpoints pass through a separate artifact metadata guard. It
rejects runtime values and sensitive-looking identifiers, contact details,
currency, likely person names, or control characters. Unsafe locator metadata
is not redacted into a broken locator; recording fails closed for human review.

## 3. Determinism & error handling

Replay resolves placeholders from validated inputs and dispatches directly on the recorded step type. It does not ask a model to reinterpret the goal or page. Semantic targeting is tried before the recorded selector. Successful browser calls are insufficient: replay checks expected text, exact title, or URL pattern. Discovery applies the same typed checkpoint to the current observation before accepting `finish` or saving an artifact.

Business outcomes, recoverable conditions, and hard failures are distinct. Member `99999` returns `MEMBER_NOT_FOUND`; a temporary target failure retries and records the recovered step; an exhausted retry returns `STEP_EXECUTION_FAILED` with step, expected/observed state, and a screenshot. Final-condition and output-contract failures have separate codes.

Additional runtime classifications include `PERMISSION_DENIED`,
`SESSION_EXPIRED`, `AUTHENTICATION_REQUIRED`, `UNEXPECTED_DIALOG`,
`ACCOUNT_LOCKED`, `VERIFICATION_FAILED`, and
`APP_TEMPORARILY_UNAVAILABLE`. Permission errors stop without retry; session,
authentication, dialog, and verification conditions request same-session
handoff when configured; temporary application failures receive only bounded
retries.

Exceptional tests use a stable committed fixture because discovery may validly choose Member Lookup or Balance Lookup. Discovery is bounded by steps, model calls, elapsed time, observation size, and repeated states. Model responses are schema-validated before execution.

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

The base capability owns business semantics, contracts, actions, and success criteria. Tenant configuration supplies institution, environments, authentication and locale; an application profile supplies vendor/version and feature flags. Locator overrides replace known differences, while tenant policy may narrow but never silently weaken platform controls.

The registry enforces tenant/application scope and draft/approved/retired states; tests prevent tenant crossover. Privacy-safe intent matching conservatively re-discovers below its threshold, though production needs typed intent constraints to reduce false positives. Base/overlay versions, supported vendor versions, reviewer and test evidence would be recorded together. Canary replay and page fingerprints detect drift; version, checkpoint or locator mismatch opens the circuit and routes to review, override, compatible rollback, or re-recording.

## 5. Escalation & handoff

Member `10025` demonstrates same-session human intervention. The verified run pauses after the Search Member click at step 3, displays Manual Verification Required, and preserves the live browser. The `handoff_started` event records control owner `human`, capability ID, current step, URL, page title, and reason. Each runtime handoff generates `evidence/handoff_required.png`; the committed representative completed-run screenshot is `evidence/handoff_final.png`. The operator clicks Complete Verification in that browser and describes the action in the terminal. `handoff_completed` transfers ownership back to `automation`, records a safe `human_action_type` such as `completed_manual_verification`, redacts the arbitrary operator note, and replay extracts `$3675.20` at step 4 without rebuilding the session. The run reports exactly one handoff.

The manager is shared by replay and discovery. Exhausted retries, escalation and blocked actions can transfer the live session. Resume requires a nonblank operator note and changed URL/title/body fingerprint; `/cancel` terminates and records a safe audit category. Production would add an authenticated operator queue, timeouts and explicit resume authorization.

Observation-guard blocks, including prompt-injection-like UI content, use this
same path when a handoff manager is attached. The model is not called with the
blocked observation.

## 6. Safety

All rendered text, labels, values and errors are untrusted. The guard uses visible controls and body text, removes control characters, normalizes and caps content, labels it `untrusted_ui_data`, and escalates suspicious instructions. Authoritative policy remains outside the model.

Discovery and replay require an approved host plus a route-specific action policy. Each route declares allowed action kinds and exact clickable targets, so generic wording such as “Proceed” grants no authority. Consequential routes and targets are not allowlisted; the mock commit endpoints independently return HTTP `403`. Terminal execution uses `shell=False` and an executable allowlist.

Discovery resolves a click's destination before recording or executing it and
checks that URL against the exact origin and route policy. This closes the gap
where an approved link label could be changed to point outside the allowlist.

The logger recursively redacts sensitive fields and patterns inside arbitrary strings, including member-number, currency, SSN, and person-name patterns. Screenshot capture masks form controls and common result, notice, and error regions. Production should add institution-specific classification, encrypted evidence storage, retention policy, and access auditing.

## 7. Cuts

This is a sandbox prototype. Real authentication, banking connectors, regulated storage, commitments, database-backed tenancy, queues, operator console, centralized telemetry, desktop drivers and coordinate control are deferred. Financial commitment stays blocked pending authenticated roles, dual approval, idempotency and immutable audit. Terminal discovery is absent; risk classification is conservative; extraction targets labeled table rows.

`pytest -q tests` reports 64 passing checks, including parameterized CLI wiring and cancellation tests using explicit fakes. A configurable headless checker accepts reviewer-supplied artifacts, inputs and expected results; CI exercises two members, not-found and invalid-amount outcomes without an LLM. Runtime extraction reads the page, not the expected fixture values. Browser/model runs are separate from unit checks. Committed model evidence retains its original source provenance; a fresh post-merge discovery needs an API key. Metadata privacy detection is heuristic and static destinations cannot predict arbitrary JavaScript navigation; production needs stronger classification and browser-level enforcement.
