# Eight executable approaches

The same runner and dataset serve the methods below. `PASS` is bounded evidence, `FAIL` is a contradicted criterion, and `UNKNOWN` remains unresolved. Only A/H change the generation procedure. B0–B5 compare evaluation layers on the same labeled mutations; stronger rejection does not improve the generator's original outputs.

## A — Hierarchical generation plus multiple judges

| Aspect | Implementation and interpretation |
|---|---|
| Motivation | Decomposition may make a complex request easier to map to tools; compare it rather than assume improvement. |
| Definition | Optional request → high-level stages → detailed activities → capability mapping → workflow. Optional multiple structured judges review the result through G. |
| Input | Original request, scoped SOP, requirement IDs/descriptions, capability contracts and schemas; separate planner/detail model IDs. |
| Output | Three structured plans, workflow, raw call records, metrics, validation issues; judge votes if enabled. |
| Algorithm | `generate(strategy='hierarchical')` performs three schema-constrained plan calls and one workflow call. `check_plan` checks unique stable item IDs within a plan, ordered dependencies, known requirement/capability IDs and requirement coverage. Final capability mapping must cover required operation names and exclude forbidden operations. Each item carries intent, inputs, outputs, dependencies, candidate capabilities and requirement provenance. G handles independent configurable judge IDs and disagreement. |
| Example | Decompose approval handling into scope check, ticket/draft preparation, approval, and send-or-review; no completed graph is supplied. |
| Strengths | Intermediates expose missing requirement mappings; separate models are configurable without an agent framework. |
| Weaknesses | More latency/tokens and several opportunities for plan errors; one model repeated across stages is correlated. |
| Failure modes | Invalid dependencies, invented capability IDs, incomplete mapping, or a sensible plan followed by an incorrect graph. IDs are stable within structured artifacts; cross-stage refinement identity is requested but not formally proven. |
| Cost/tokens | Four generation calls per candidate instead of one, plus enabled judges. Each call has its own cache and token record. |
| Works when | A task's activities can be separated with explicit business dependencies. |
| Cannot assure | Plan prose alone cannot establish branch semantics, policy compliance or broad generalization. |
| TypeScript | Reuse PLAN_SCHEMA, validate item IDs and dependencies with Sets/Maps, sequence Ollama calls, then use the same validators. |
| References | [Zendesk task decomposition guidance](https://support.zendesk.com/hc/en-us/articles/9424547622298); [judge bias research](https://arxiv.org/abs/2306.05685). The four-stage design is independently designed, not a claimed published algorithm. |

## B — Glossary / keyword coverage

| Aspect | Implementation and interpretation |
|---|---|
| Motivation | Cheaply find missing domain terminology before expensive reasoning. |
| Definition | Configurable canonical terms with English/Vietnamese aliases, capability names and sources. |
| Input | Workflow JSON, relevant expected capabilities, `data/glossary.json`. |
| Output | Matched aliases and a weak coverage verdict per relevant term. |
| Algorithm | `glossary` case-folds serialized workflow text and searches aliases for glossary entries associated with the case. |
| Example | `routing-en/swapped_branches` retains escalation/routing keywords and passes B while executing the wrong branch. The HTML includes a button to inspect it. |
| Strengths | Fast, transparent, zero model tokens; easy configuration and bilingual diagnostics. |
| Weaknesses | Text occurrence has little causal meaning; graph names/comments can also match. |
| Failure modes | Negation, wrong arguments, branch inversion and irrelevant keyword stuffing yield false acceptance; alternative wording can yield false rejection. |
| Cost/tokens | Local substring searches; zero inference tokens. |
| Works when | Terminology is a useful preliminary signal or missing-operation warning. |
| Cannot assure | Any execution, ordering, safety, semantic completeness or translation quality. |
| TypeScript | Lowercase/normalize strings and match aliases; keep this diagnostic separate from hard acceptance. |
| References | Terminology from [Zendesk trigger fields](https://support.zendesk.com/hc/en-us/articles/4408893545882-Ticket-trigger-conditions-and-actions-reference), [procedure examples](https://support.zendesk.com/hc/en-us/articles/9424547984026) and [n8n approval description](https://n8n.io/workflows/19465-triage-and-route-ai-powered-support-tickets-with-google-gemini-trello-and-gmail/). Matching algorithm is a local experiment. |

## C — Requirement checklist verification

| Aspect | Implementation and interpretation |
|---|---|
| Motivation | Make every requirement and its evidence inspectable, including uncertainty. |
| Definition | Source-grounded requirements carry ID, description, severity, evaluation method, expected evidence and tri-state verdict. |
| Input | Case requirement list, workflow and optionally independent execution evidence. |
| Output | Per-requirement verdict/evidence; aggregate FAIL before UNKNOWN before PASS. |
| Algorithm | `checklist` rejects unsupported or missing required operations; presence alone stays UNKNOWN. Trace requirements use scenario assertions when supplied. Symbolic wording/tone requirements stay UNKNOWN for review. |
| Example | All approval operation names can be present while a branch swap fails trace assertions; damage-empathy tone remains UNKNOWN even for the reference. |
| Strengths | Traceable to source IDs; distinguishes missing evidence from failure. |
| Weaknesses | Current trace requirements use shared case-level fixture assertions, so evidence resolution is coarse. |
| Failure modes | An omitted requirement cannot be caught by a checklist that never mentions it; weak fixtures can produce bounded passes. |
| Cost/tokens | Local checks; zero model tokens until optional G resolves semantic unknowns. |
| Works when | Requirements can be enumerated and tied to observable effects. |
| Cannot assure | Completeness of the specification or free-form meaning beyond available evidence. |
| TypeScript | Keep requirements as JSON; return a discriminated PASS/FAIL/UNKNOWN result with evidence. Never coerce UNKNOWN into a boolean. |
| References | [Zendesk examples](https://support.zendesk.com/hc/en-us/articles/9424547984026), [n8n templates](https://n8n.io/workflows/18499-route-and-respond-to-support-tickets-with-google-sheets-slack-and-gemini/) supply process requirements. WorkflowJudge DOI is unverified and is not claimed as methodological authority. |

## D — Contracts and policy

| Aspect | Implementation and interpretation |
|---|---|
| Motivation | Check deterministic facts in code before asking a model. |
| Definition | Schema/graph validation plus registered operation, argument, data-dependency, supported precondition and explicit policy checks. |
| Input | JSON graph, fixed registry and SOP input/policy contracts. |
| Output | Stable findings with category and responsible node. |
| Algorithm | `validate`: schema; endpoint/port/ID checks; reachability; Kahn DAG order; intersect must-available fields and guard facts across incoming paths; check catalog and SOP rules. `invoke` rechecks actual arguments/preconditions before effects. |
| Example | A send before approval fails both dependency/guard checks; forbidden refund is blocked as policy even if graph shape is valid. |
| Strengths | Deterministic, cheap, actionable and portable; prevents invalid workflow execution. |
| Weaknesses | Conservative guard proof; limited symbolic reasoning and state types. |
| Failure modes | Registered valid arguments can still pick the wrong permitted group; unsupported logical formulations can be rejected as unproven. |
| Cost/tokens | Graph and small-set operations; zero inference tokens. |
| Works when | An operation's executable contract or explicit rule can be stated mechanically. |
| Cannot assure | User intent or all business behavior; a structurally valid graph may route incorrectly. |
| TypeScript | Zod/JSON Schema, adjacency Maps, topological sort, must-set intersection, and explicit policy predicates. |
| References | [OMG process/decision concepts](https://www.omg.org/dmn/), [Zendesk conditions/actions](https://support.zendesk.com/hc/en-us/articles/4408893545882-Ticket-trigger-conditions-and-actions-reference); exact algorithms/local no-money policy are independent designs. |

## E — Scenario execution

| Aspect | Implementation and interpretation |
|---|---|
| Motivation | Operation names cannot establish observable behavior. |
| Definition | Execute independent fixture snapshots and compare state, required/forbidden actions and ordering. |
| Input | Workflow, SOP, pre-authored fixtures and trace constraints. |
| Output | Execution state/trace plus expected-versus-observed failures per fixture. |
| Algorithm | `scenarios` runs `runner.run`, checks recursive expected-state subsets with strict scalar types, required/forbidden effects, action order and shared notice constraints. Branch outcomes are evidenced by the selected-edge trace and required/forbidden path actions, not reference node identity. |
| Example | Rejected human approval must reach Manual Review with no `send_reply` effect. |
| Strengths | Directly tests bounded behavior; catches valid-shape wrong routes and missing effects. |
| Weaknesses | Finite fixture coverage; no proof for unseen inputs. |
| Failure modes | A graph specialized to the fixtures can pass while violating another input. A faulty oracle mislabels correct behavior. |
| Cost/tokens | Local bounded executions; zero inference tokens. |
| Works when | The desired result and important intermediate effects can be independently specified. |
| Cannot assure | Multi-turn user interaction, external integration failures, unmodeled effects or natural-language tone. |
| TypeScript | Port JSON fixtures and pure runner unchanged in semantics; use Node assertions for subset/effect/order checks. |
| References | [τ-bench abstract](https://arxiv.org/abs/2406.12045) motivates final-state checking; the actual local fixture policies come from the documented vendor process slices. |

## F — Metamorphic testing

| Aspect | Implementation and interpretation |
|---|---|
| Motivation | Add meaningful input variation when ordinary examples leave a gap. |
| Definition | Independently specify a base input, source-relevant change and expected behavioral difference. |
| Input | Relation JSON with source IDs, base input, changed fields, expected base/changed states. |
| Output | Both real executions, failures and relation verdict. |
| Algorithm | `metamorphic` runs both inputs; asserts each independent expected subset and that a relevant expected output field actually changes. It never derives expectations from the candidate. |
| Example | Adding a missing message must change intake rejection into ticket creation. A mutant validating only email passes the primary fixtures but fails this pair. |
| Strengths | Targets boundary gaps without requiring an exact reference graph. |
| Weaknesses | Relation quality and source scope determine usefulness; it is still finite testing. |
| Failure modes | An unjustified invariant rejects valid behavior; a weak output relation misses a fault. |
| Cost/tokens | Two local executions per relation; zero inference tokens. |
| Works when | Conditional process behavior implies an unambiguous response to a specified input change. |
| Cannot assure | Unspecified relations or undocumented vendor policies. No broad invariance is inferred. |
| TypeScript | Store pairs in shared JSON and run the same subset/difference assertions. |
| References | Conditional behaviors from [n8n approval](https://n8n.io/workflows/19465-triage-and-route-ai-powered-support-tickets-with-google-gemini-trello-and-gmail/), [n8n intake/routing](https://n8n.io/workflows/18499-route-and-respond-to-support-tickets-with-google-sheets-slack-and-gemini/) and [Zendesk validation examples](https://support.zendesk.com/hc/en-us/articles/9424547984026). The harness is independently designed. |

## G — Reference-guided LLM judge

| Aspect | Implementation and interpretation |
|---|---|
| Motivation | Review criteria that deterministic code cannot conclusively settle. |
| Definition | Structured, reference-checklist-guided judgment with concrete evidence and uncertainty. |
| Input | Original request, SOP, selected checklist items, capability contracts, candidate graph and compact real execution evidence. Judging may see the oracle; generation may not. |
| Output | Requirement ID, PASS/FAIL/UNKNOWN, node/edge/trace refs, short reason, uncertainty and failure category, plus per-model votes and metrics. |
| Algorithm | `judge` selects UNKNOWN items by default; `all_items=True` is the ablation. It calls configured local models with JUDGE_SCHEMA, validates complete requirement coverage and evidence IDs, converts absent/invalid evidence into UNKNOWN and disagreement into UNKNOWN. Raw per-item judge verdicts are preserved separately from effective deterministic gates; an UNKNOWN judge is never counted as a true rejection merely because code already failed. Deterministic known verdicts remain effective. `layers` never permits G to erase policy/contract/behavioral failure. |
| Example | Ask about whether the order acknowledgment preserves customer intent; a symbolic template with no rendered wording merits UNKNOWN. All-items ablation separately measures agreement on fixture-labeled requirements. |
| Strengths | Explicit rubric, actionable reasons and visible uncertainty; selective use saves tokens. |
| Weaknesses | Same-model self-enhancement, correlation, prompt sensitivity and limited reasoning remain. Valid evidence IDs do not prove the model interpreted the evidence correctly. |
| Failure modes | Hallucinated evidence, omitted rubric items, overconfident PASS, prompt injection within untrusted workflow text or model agreement on the same mistake. |
| Cost/tokens | One call per enabled judge and selected scope; no call when nothing is unresolved. All-items ablation is opt-in and more expensive. |
| Works when | There is enough natural-language evidence and a clear rubric, with independent labels for calibration where possible. |
| Cannot assure | Deterministic policy override, unseen behavior, or validated semantic accuracy without independent human labels. |
| TypeScript | Reuse schema/rubric JSON and validate evidence IDs; merge only unresolved items; keep hard failures immutable. |
| References | [Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685), [G-Eval](https://aclanthology.org/2023.emnlp-main.153/), [survey](https://arxiv.org/abs/2411.15594). This is a local rubric adaptation, not replication of their experiments. |

## H — Multiple candidates and reranking

| Aspect | Implementation and interpretation |
|---|---|
| Motivation | Selection may recover a correct candidate when a single sample fails; measure the cost and gain separately. |
| Definition | Generate N independent candidate requests, evaluate each and lexicographically rank them. |
| Input | Same request/SOP/schema, N in 1–3 and optional judges. Default N=1; extra candidates require explicit selection. |
| Output | Every original candidate and evaluation, selected index, rank tuple, acceptance status and total token/latency cost. |
| Algorithm | `generate_candidates` records temperature 0 and seeds 17+i. `rank_key` orders hard contract/policy compliance, combined scenario/metamorphic pass fraction, resolved checklist coverage, judge votes only for unresolved items, then negative node+edge count. No reference graph similarity is used. Selection does not convert INVALID/UNKNOWN into PASS. |
| Example | A branch-swapped candidate loses to a compliant approval graph even when both contain all keywords. |
| Strengths | Transparent ranking and preserved alternatives; no hidden repair of first-pass results. |
| Weaknesses | N-fold generation cost; fixed-temperature seeds may yield identical candidates. Selection uses this suite's fixtures and is not held-out generalization. |
| Failure modes | All candidates fail, a fixture-overfit candidate wins, correlated generations repeat the same defect, or a smaller incorrect graph seems attractive without hard-first ranking. |
| Cost/tokens | N direct calls, or 4N hierarchical calls, plus explicitly enabled judges. Cache reuse is labeled. |
| Works when | Candidate diversity exists and evaluators discriminate meaningful errors. |
| Cannot assure | That any correct candidate exists, that selection improves unseen inputs, or that a rejected generator became more accurate. |
| TypeScript | Keep the five-component comparison tuple and JSON evidence; sort only after all candidate evaluations. |
| References | Independent experimental generation/selection design using [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs); no source is claimed to prove this ranking optimal. |

## Mutation evaluation and comparison rules

`mutations.variants` starts from references confirmed against independent fixtures. It records the error edit and responsible nodes for swapped branches, missing actions, invalid arguments, wrong group, invalid ordering, forbidden effect and unavailable data. A redundant condition is labeled valid. The special intake mutant isolates metamorphic value. Labels are determined by the injected change, never by which validator rejects it.

B0 is schema/graph. B1 is B0+glossary. B2 is B0+contracts/policy+checklist without execution; operation presence remains UNKNOWN. B3 supplies scenario evidence. B4 adds metamorphic pairs. B5 resolves only remaining semantic uncertainty through enabled G; absent G remains unmeasured. B1 is a diagnostic branch rather than a mandatory glossary gate on B2–B5.

True/false acceptance/rejection count PASS/FAIL against independent variant labels. UNKNOWN is a fifth outcome. Detection rate is rejected invalid variants divided by all invalid variants, including unknowns in the denominator. Equivalent graphs can have deterministic behavioral PASS yet unresolved wording, and are never counted as false rejections merely for UNKNOWN. Repeated bilingual cases share labels, so pooled totals are correlated observations, not independent samples.

Local execution time is measured with `perf_counter`; layer timings sum shared measured components and are illustrative, not isolated performance benchmarks. Token nulls mean unavailable/unmeasured; zero means a deterministic check or a labeled cache hit. No confidence interval or broad Helpdesk generalization is justified by this small designed suite.
