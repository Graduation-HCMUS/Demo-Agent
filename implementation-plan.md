# Genie implementation plan

Written before implementation on 2026-11-20. Repository inspection: empty clean `main`, no applicable AGENTS.md, Python 3.14.10. All work stays here. No JS/TS, CI, deployment, commits, downloads or paid inference.

## Decisions and execution order

Use Python 3.11+ standard library only: JSON contracts, urllib for the documented Ollama HTTP API, unittest, inline SVG/HTML. An explicit small JSON Schema validator supports precisely the keywords used by our schemas; it is not a general JSON Schema implementation. This avoids installing Pydantic/client dependencies in the offline reference path. Schema remains portable to Zod. Separate source-derived expectations from prompts, and freeze them before any generation.

Research already retrieved the supplied Zendesk, n8n, OMG, arXiv, ACL and Ollama pages. WorkflowJudge DOI retrieval failed and an exact search returned no results: mark UNVERIFIED and do not reproduce claimed methods/results. Only abstracts/landing pages were read for research papers. Ollama server has no installed models, so real inference measurements may be unavailable. Preserve this evidence.

### 1. Research manifest and independent dataset

- Objective: auditable provenance and five bounded scenarios, seven language cases (five English, order/approval also Vietnamese).
- Inputs: verified vendor descriptions, process/decision concepts, evaluator research abstracts.
- Outputs/files: `data/sources.json`, `data/sops/*.json`, `data/cases/*.json`, `data/prompts.json`, `data/glossary.json`, `data/reference-workflows/*.json`, `docs/02-sources-and-provenance.md`.
- Contract: every source includes id/title/publisher/url/type/date/section/establishes/limitations/uses/classification/access; every SOP includes scope, trigger, fields, roles, preconditions, ordered activities, decisions, exceptions, outputs, forbidden actions, postconditions, requirements, assumptions. Each case contains all requested expectation fields; prompts live separately and are joined only at load time. Each fixture has id/input/expected state/trace/forbidden effects. Requirements identify source, severity, method and evidence.
- Algorithm: summarize published behavior; extract a narrow slice; explicitly label omitted behavior and simulator choices; construct synthetic input pairs and oracle assertions before writing a generator. Hash all oracle files in run outputs.
- Scenarios: intake rejects absent customer email/message (field choice assumption); routing uses supplied high_risk boolean (risk classification out of scope); approval gates customer reply and routes rejection to manual review; order validates five-digit number/email, requests correction or escalates after two invalid attempts, then looks up and reports status; damaged item gathers details, requests optional photo and creates/escalates ticket (no refund authority).
- Edge cases: missing/invalid fields, false approval, out-of-scope request, cancelled order, optional photo; simulator is a single snapshot, not multi-turn conversation.
- Errors: unresolved provenance prevents vendor attribution; absent source marked unavailable.
- Dependencies: research tools only. Tests: source IDs resolve, bilingual cases share oracle, required metadata present, prompt files have no fixtures.
- Acceptance/evidence: five SOPs, seven cases, exact URLs/sections and explicit assumptions; JSON manifest plus dataset hash before inference.

### 2. Shared schema, contracts, runner

- Objective: safe JSON-only DAG execution.
- Inputs: workflow `{schema_version,workflow_id,name,nodes,edges}`; ticket JSON; SOP input fields/policies.
- Outputs/files: `src/genie_eval/{models,catalog,validators,runner}.py`, schema JSON, tests.
- Node contract: `{id,type,config}` with input/output/condition/custom/file; edge `{source,target,port}`; conditions use eq/ne/exists/gte and true/false ports. Values may reference state with `{ref: field}`. No executable code, eval, networking or persistent state in runner.
- Algorithm: schema -> IDs/endpoints/ports -> one input, terminal outputs, reachability -> Kahn DAG order -> must-available data intersection at merges -> registry argument/required-input/precondition/effect checks -> static policy findings. Runtime validates, copies state, follows one edge, applies registered pure local operation, records before/changes/selected edge/error, stops at output or explicit bounded failure.
- Operations: only validate fields, request info, escalate, route, create ticket, request approval, send reply, save order/email, lookup/report status, notify/photo request and forbidden-effect demonstration. Each declares argument schema, required/produced fields, preconditions, effects, implementation and restrictions. `file` declares metadata schema but runtime unsupported; no file contents read.
- Edge cases: bool vs int, duplicate IDs/edges/ports, unreachable nodes, disconnected cycles, merge data absent on one branch, unknown operators/args/ops, unsafe refs, malformed JSON, output outgoing edge, input incoming edge, >128 nodes/steps.
- Errors: stable code/category/node/message; runner never executes structurally invalid workflows; dynamic policy violations blocked before effects.
- Dependencies: stdlib. Tests: meaningful graph/contract/runtime negative cases, trace integrity, input immutability, no arbitrary evaluation, file rejection.
- Acceptance/evidence: reference executions pass independent fixtures; unit test transcript.

### 3. Reference graphs and controlled mutants

- Objective: evaluate validators against known injected faults without graph equality.
- Inputs: independent oracle + hand-authored references.
- Outputs: reference graphs and `mutations.py` manifest of transformations/error labels/responsible nodes.
- Algorithm: assert references pass first; deep copy and apply swapped branch, missing action, bad argument, wrong target, bad order, forbidden effect, missing data dependency. Insert an identity condition with both branches reaching the same successor as a valid graph-equivalence variant. Add a special untested-input mutant for metamorphic incremental coverage.
- Edge cases: equivalent graph accepted, keywords remain in swapped graph, mutation must actually alter target.
- Tests/acceptance: invalid variants fail at expected layers; equivalent variants pass; UNKNOWN tracked separately. Save every graph, label, detection and fixture evidence.

### 4. Direct zero-shot Ollama adapter

- Objective: one schema-constrained local inference call by default, no gold leakage.
- Files/functions: `generator.py`: doctor, build_prompt, structured_call, generate; `cli.py` generate/doctor.
- Inputs: request, selected SOP, compact relevant catalog, schema, model/config; never oracle/fixtures/reference graph. Model default qwen3.5:9b, alternatives configurable.
- Outputs: immutable first attempt raw content (no thinking), parsed workflow, validation errors, model/digest, language, prompt version/hash/settings, reported token counts, wall latency, cached flag and explicit status.
- Algorithm: inspect `/api/tags`; fail if model absent; POST `/api/chat` with `format` schema, temperature 0, think false, timeout/token cap. Hash model/digest/prompt/schema/settings for cache. Retries default zero; each attempt saved before next. Cache hits marked and retain original metrics separately from current latency/cost.
- Errors: connection, model missing, timeout, malformed/invalid output; nonzero CLI failures; never substitute reference data.
- Tests: mocked transport shape, no-leak prompt, cache key changes, timeout/error, first-pass preservation; real doctor and generation attempt if possible.
- Evidence: doctor JSON; real responses only if available.

### 5. Evaluators and alternative generators

- Objective: executable A-H sharing utilities, independent callable functions and CLI method selection.
- Files: `evaluators.py`, `judge.py`, `generator.py`, `experiments.py`, `mutations.py`.
- B glossary: normalized alias/operation text coverage; weak signal. C checklist: operations only establish presence; fixture/trace checks establish bounded behavior; semantic tone stays UNKNOWN. D contracts/policies: distinct issue categories. E scenarios: recursive subset state, required/forbidden actions, ordering, condition branch evidence and errors. F metamorphic: independently specified changed-input pairs and expected effect differences; run both, never learn oracle from workflow. G rubric judge: requirement IDs, verdict, concrete evidence, short reason, uncertainty/category; selective UNKNOWN only by default, all-items ablation and multiple configurable judge IDs; deterministic FAIL cannot be overridden. A hierarchy: structured stages -> activities -> capability mapping -> workflow, each item id/intent/inputs/outputs/dependencies/capabilities/requirement provenance; planner/detail models separately configured. H candidates: N default 1 (2/3 supported), no repairs by default; rank hard compliance, behavior, checklist, unresolved judge, complexity.
- Contract: evaluator `{method,verdict,evidence,elapsed_ms,prompt_tokens,completion_tokens}`; tri-state aggregation FAIL > UNKNOWN > PASS. B0-B5 cumulatively combine layers; B1 glossary is separate from B2 as specified. B5 disabled judge remains UNKNOWN when semantics unresolved.
- Tests: keyword false positive, ordering, preconditions, missing requirements, relation success/failure, incomplete judge output, hard-fail precedence, ranking, hierarchy schema/provenance, mocked all-method orchestration (not inference evidence).
- Acceptance/evidence: actual deterministic mutation confusion matrices including unknowns, per-error detections and incremental rejections; LLM methods explicitly measured or unmeasured. Generator strategies evaluated separately from validator configurations.

### 6. Offline visualization and reports

- Objective: reviewable automatic artifacts without server or external assets.
- Inputs: recorded runs/mutations/traces; no prewritten performance numbers.
- Files: `report.py`, `outputs/{report.html,results.json,summary.md,graphs/*.svg}`.
- Algorithm: deterministic topological layered SVG layout; escape all untrusted text; inline CSS/JS and JSON with safe script escaping. Case/workflow/fixture selectors highlight executed edges/nodes; display state deltas/failures/SOP links. Tables show B0-B5 confusion, detection by error, behavior rate/latency/tokens, strategy/model comparison and separate language results. Null/unmeasured values remain explicit. Include keyword-pass/behavior-fail example and expected/observed/responsible node/source.
- Edge cases: invalid graph layout fallback; long labels; no LLM results; offline navigation; JSON containing HTML/script text.
- Tests: deterministic SVG, escaping, no remote scripts/styles, report contains all result IDs; browser opening when available.
- Acceptance/evidence: offline HTML, JSON/SVG/Markdown, browser/sanity inspection recorded.

### 7. CLI, documentation and final verification

- CLI: doctor, list-cases, test, demo --mode reference, generate, evaluate --methods, benchmark --mode ollama --models, report. Unknown args nonzero; failed required checks nonzero; no skipped-empty success. All-method config opt-in enables hierarchy, N=2 and judges, never downloads.
- Docs: README; concepts with Vietnamese terminology; source transformation per SOP/case; each A-H motivation/definition/input/output/algorithm/example/strengths/weaknesses/failure modes/cost/applicability/limits/TS mapping/references; experiment commands, measured report/limitations, migration map.
- Verification: unittest -> references -> mutations -> deterministic benchmark -> doctor -> model attempt or explicit unavailable evidence -> report -> browser/offline sanity -> final git scope check. Record exact commands and measured totals. No broad test expansion without a concern.
- Final acceptance: all deterministic paths work without dependencies; optional LLM code tested through transport mocks, real execution claimed only with responses; docs and generated evidence distinguish reference validation, evaluator detection, generation and selection.
