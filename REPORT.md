# BankPilot Design Report

BankPilot discovers a workflow on a live mock banking UI with an LLM and saves a reusable typed capability. Replay uses that contract without an LLM, checks policy, member identity, declared outputs and final state, and can pause for a human in the same browser. This submission implements one browser surface; production banking, desktop drivers and multi-tenant infrastructure are deliberately outside scope.

## 1. Architecture

Components: `DiscoveryAgent`, `BrowserSurface`, `SafetyPolicy`, `CapabilityRecorder`, `ReplayEngine`, `CapabilityRouter`, and `HumanHandoffManager`.

Discovery observes visible controls and page text, requests one model decision, validates it, and acts through the surface adapter. The model selects an observed element ID, never arbitrary code or selectors. The provider is OpenAI's Responses API; `OPENAI_MODEL` defaults to `gpt-5.6-luna` as a configurable lightweight choice for short interactive decisions. Model comparisons and cost/latency benchmarks are not claimed. Recorder code parameterizes the trace and supplies the supported banking contracts; the LLM does not invent an executable schema.

`main.py discover` accepts a goal, target, artifact path and parameters; `replay` takes the artifact and new inputs. Synchronous local Playwright keeps one browser/page alive across steps and handoffs, simplifying ownership at the cost of blocking one process per run. The optional library router selects approved tenant/application matches or creates drafts after discovery. Direct CLI replay treats the supplied artifact as reviewed; it does not enforce registry approval.

## 2. Artifact schema

Schema `1.1` has top-level identity/application metadata, typed `parameters` and `outputs`, ordered `steps`, and a typed `success_condition`. Release versions live separately in the optional registry. An abbreviated contract excerpt is:

```json
{
  "schema_version": "1.1",
  "parameters": [{"name": "member_id", "type": "string", "required": true}],
  "outputs": [{"name": "savings_balance", "type": "string"}],
  "success_condition": {"type": "text_present", "value": "Balance Result"}
}
```

The complete [canonical artifact](artifacts/lookup_savings_balance.json) also defines its name, description, application, start URL, action targets and extraction mapping. Callers inspect that JSON to learn required inputs and returned outputs independently of the prompt. Runtime values use `{{member_id}}`; financial values remain formatted strings. Enum-constrained types, unique names, declared placeholders and extraction mappings are validated. Single-output inference precedes output-coverage validation.

The four supported operations extract member name, balance, reviewed account type or deposit amount. Unknown goals receive a generic description and final-title checkpoint, without invented outputs; they require reviewer refinement. UI-derived locator metadata is checked during recording and again at save, rejecting detected unsafe values instead of damaging selectors with redaction.

## 3. Determinism & error handling

Replay contains no model call. It resolves typed inputs and tries a unique role/accessibility-name target, then a saved CSS/XPath selector. Recorder selector candidates prefer stable attributes before positional XPath. There is no separate text-anchor tier or automatic locator repair. Initial navigation uses `start_url`; a standalone `navigate` step is not currently executable despite its schema enum.

Before extraction, displayed Member Number must match `member_id`. Success also requires all declared outputs with correct types and a text, title or URL checkpoint. Failed extraction is retried after handoff; page change alone cannot satisfy the output contract. Discovery checks its final observation before saving, although an unfamiliar workflow's title-only checkpoint is weaker than a reviewed business assertion.

Business outcomes include `MEMBER_NOT_FOUND`, `ACCOUNT_LOCKED`, `INVALID_INPUT` and `INVALID_AMOUNT`, without generic retries. Transient target failures and `APP_TEMPORARILY_UNAVAILABLE` receive two retries by default. Session/authentication, dialog and verification conditions request configured handoff or return specific failure codes; `PERMISSION_DENIED` stops. Exhausted targets, identity mismatch, missing outputs and checkpoint failures refuse success and retain failure context. Classifiers use known UI markers, not universal error understanding.

## 4. Heterogeneity & multi-tenant

`Surface` defines observation/action, targeting, labeled extraction and evidence operations. Browser replay delegates these operations to `BrowserSurface`, whose extraction uses HTML table rows. Some discovery/handoff context still accesses Playwright directly. Supporting legacy web frames or native applications requires completing that separation and replacing targeting/extraction with frame-aware locators or OS accessibility identifiers (Windows UI Automation/macOS Accessibility). `DesktopSurface` is unimplemented; `TerminalSurface` is only a restricted no-shell executable helper, not end-to-end automation.

The deployment design is **base vendor capability + tenant configuration + application/version profile + locator overrides + tenant safety policy**. The base owns business semantics and contracts; tenant configuration selects institution/environment/authentication; the profile declares vendor versions and feature flags. For example, a tenant changing “Search Member” to “Find Member” supplies a reviewed target-name/selector override and corresponding click-policy entry, retaining the same inputs, extraction and checkpoint.

The implemented file registry scopes entries by tenant/application and tracks draft/approved/retired state. Overlay composition, compatibility enforcement and deployment approval services remain design work. Proposed controls bind base/overlay versions to approval evidence, use canary replay and page fingerprints to detect drift, and stop on incompatible targets/checkpoints for review, compatible rollback or re-recording. Tenant overlays must not weaken platform restrictions. Token-similarity routing can miss valid paraphrases or select the wrong approved intent; production needs stronger intent constraints.

## 5. Escalation & handoff

With handoff enabled, manual verification, selected blocked replay steps, discovery escalation, observation-injection detection and budget exhaustion can transfer control. The manager pauses synchronously while retaining the live browser and cookies, captures a masked screenshot, and logs capability, step, URL/title, reason and control owner. This is a terminal-guided operator surface, not a dashboard or remote co-browsing service.

The human operates that same browser, describes the intervention, then returns control; blank notes and unchanged state are rejected, and `/cancel` terminates. A safe `human_action_type` records the intervention category while arbitrary notes are redacted. Categories and changed-state fingerprints are not identity verification or a recording of exact human clicks; subsequent output/checkpoint checks remain necessary. Budget exhaustion does not silently grant another discovery budget or save an unfinished capability.

Member `10025` exercises manual verification with `python -m tests.test_handoff`. Runtime `handoff_required.png` and `handoff_final.png` are not committed. The retained historical handoff log predates the new audit category; the [evidence index](evidence/README.md) distinguishes it from current behavior.

## 6. Safety

Authoritative policy is outside the model. Discovery and replay require an approved **origin (scheme, host and port)**, route, action kind and clickable target. Link and HTML form destinations, including `formaction`, are checked before clicks. Irreversible financial routes are excluded, and mock commit endpoints independently return `403`; human handoff does not enable automated commitments.

Rendered UI is untrusted data. The observation guard normalizes/caps text, omits hidden controls and escalates suspicious instructions. Discovery limits steps, model calls, observation size, repeated states and elapsed time; elapsed-time checks occur between calls, not as hard cancellation of an in-flight request.

JSONL redaction masks sensitive keys and matching SSN, numeric-identifier, currency and name patterns. Artifact metadata and registry intents have separate persistence guards. Screenshot masks cover form controls and common result/error regions. Five obsolete screenshots exposing mock member details were removed; the canonical masked image and reviewed text evidence remain. Console output is not privacy-filtered evidence. Pattern detection and DOM masks are heuristic; production requires application-specific classification, encryption, access controls and retention limits.

## 7. Cuts

Real banking integrations, production authentication, distributed queues, tenant databases, an operator dashboard, centralized logging, desktop and coordinate automation are deferred. Priorities next are browser-level navigation enforcement for script redirects, stronger semantic checkpoints/error classification, completing the surface abstraction and authenticated operator audit. Deterministic replay would continue to fail or hand off on drift; any model-assisted repair should produce a newly reviewed artifact.

The non-browser suite has 68 checks, including four new regressions for active failure injection and strict reviewer assertions. CI runs Chromium replay for two members, a missing member, invalid-amount preflight and injected recovery/hard failure. The [verified prior CI run](https://github.com/Vishnu1721/bankpilot/actions/runs/35280403340) passed its then-current 64 tests and four replay checks; this PR adds the retry checks. Neither live LLM discovery nor human intervention runs in unattended CI. Committed model evidence retains its original source SHA; regenerating it requires the operator's API key.
