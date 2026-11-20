# Verification and completion audit

This document indexes evidence against the original brief. Actual measured totals belong to generated JSON and transcripts. Tests are executable checks, not proof of unmodeled behavior. Optional LLM paths are verified with clearly identified transport doubles and separately recorded local inference; these evidence classes must not be pooled.

## Scope and evidence map

| Brief section | Owning artifacts / authoritative evidence | Assessment |
|---|---|---|
| 1: isolated Python experiment and research question | `implementation-plan.md`, `README.md`, `src/genie_eval/`, final Git scope check | All deliverables live in this directory; no application integration. |
| 2: research before implementation, starting URLs, provenance, SOP/template distinctions | `data/sources.json`, `docs/02-sources-and-provenance.md`, original research tool results | All starting URLs attempted; WorkflowJudge unavailable, paper coverage abstract-only and n8n graph approximation explicit. |
| 3: 4–6 scenarios, bilingual prompts, independent expectations, mutations | Five `data/sops/`, seven `data/cases/`, separate `data/prompts.json`, oracle lock, `mutations.py` | Five scenarios, English primary plus two Vietnamese counterparts; no independent bilingual human review. |
| 4: DSL, contracts, DAG runner, trace, safe conditions, file boundary | `models.py`, `catalog.py`, `validators.py`, `runner.py`, schema/runner tests | JSON-only registered effects; no eval; file runtime explicitly unsupported. |
| 5: configurable direct zero-shot structured generation | `generator.py`, generation tests, real call/checkpoint records | Fixed-temperature single-call default; no hidden oracle; failures/raw first pass retained. |
| 6: real executable A–H | `generator.py`, `evaluators.py`, `judge.py`, `experiments.py`, method tests | All have callable implementations and CLI routes; model-dependent verification status reported separately. |
| 7: mutation confusion accounting, valid equivalent graphs, B0–B5 | `mutations.py`, `experiments.py`, `outputs/results.json`, mutation tests | Independent labels; UNKNOWN is separate; no exact graph equality. |
| 8: graph/trace/comparison/language/failure visuals | `report.py`, offline HTML, SVGs, browser verification JSON/screenshots | Local-file browser opening, selector/path/trace checks and mobile layout tested with network offline. |
| 9: minimal Python architecture/dependencies | `pyproject.toml`, source tree | Standard-library runtime; bundled browser used only for QA. |
| 10: low-level plan, ordered implementation and verification | `implementation-plan.md`, source/test/report evidence | Plan written before implementation; executed rather than left as a proposal. |
| 11: token budgets, timeouts, retries, cache, selective judge | `generator.py`, generation/judge tests, request records | Relevant SOP tools selected deterministically; explicit model/context/budget; no default extra candidates/judges. |
| 12: CLI commands and nonzero failures | `cli.py`, CLI tests, command verification evidence | doctor/list/test/demo/generate/evaluate/benchmark/report implemented; empty benchmark cannot succeed. |
| 13: concepts/methods/provenance/TypeScript education | `docs/01`–`07`, README | Every method documents inputs/outputs/algorithm/example/pros/limits/cost/port/references. |
| 14: measured final report and separate denominators | Generated JSON/HTML/summary and `docs/05-experiments.md` | Reference validation, validator detection, first-pass generation, judge agreement and selection are separate; unmeasured/null values explicit. |
| 15: quality boundaries | Source inspection, tests, Git scope evidence | No production infrastructure, paid inference, customer data, generated code execution, commits or pushes. |
| 16: twenty completion items | Evidence table below | Each item must be confirmed from final current artifacts. |
| 17: final delivery | README commands/tree, final reply links/table/status | Exact commands, artifacts, tests, limitations, source gaps and TS recommendation supplied. |

## Definition-of-done evidence

| Item | Evidence to inspect |
|---|---|
| 1: source-backed SOPs/references | `data/sources.json`; five SOPs; source guide family mappings |
| 2: auditable case provenance | Every case source ID resolves; oracle-integrity test; assumptions/translation status |
| 3: executable references | Per-reference D/E/F in `outputs/results.json`; fixture traces and runner tests |
| 4: Ollama when available | `outputs/doctor.json`; real request/response/config/digest records; no success inferred from installation |
| 5: English/Vietnamese paths | Separate prompt IDs, shared oracle pairs, per-language results and bilingual generation test |
| 6: structure/contracts | Schema and runner tests; per-node stable findings |
| 7: checklist | Missing/unsupported requirements, trace satisfaction and semantic UNKNOWN tests |
| 8: glossary | Keyword-pass/behavior-fail test and HTML failure example |
| 9: scenarios | Every reference fixture and negative mutation; expected/actual state/order/forbidden effects |
| 10: metamorphic | Source-mapped pairs and missing-message defect caught beyond primary fixtures |
| 11: mutations | Confusion accounting totals, all required fault types and equivalent graphs |
| 12: optional judge | Schema/evidence/coverage/disagreement/hard-failure tests; real judge status where selected |
| 13: optional hierarchy | Four-call transport test, plan schema/provenance failure tests; actual runtime status where selected |
| 14: candidates/ranking | N=2 transport test, hard-first and metamorphic-aware ranking, N=1–3 CLI validation |
| 15: independent methods | README function table and individual evaluate/strategy/judge/candidate CLI switches |
| 16: automatic comparison | reference/benchmark/report commands; no hard-coded success tables |
| 17: visual graph/trace | Browser fixture-switch checks, executed path, failure screenshot |
| 18: offline HTML | Browser verification `offline=true`, zero remote requests/page errors |
| 19: deterministic automated tests | Final `outputs/test-run.txt` executed transcript, not an inventory checkbox |
| 20: educational/source/TS documentation | README; docs 01–07; source/method/migration tables |

## Explicit limits retained at delivery

WorkflowJudge content is unverified. Full n8n graphs and independent bilingual/human semantic labels are unavailable. Local SOPs and synthetic fixtures are adaptations, not official datasets. Behavioral passes apply to this bounded snapshot suite. Same-model judging is correlated. A returned JSON response may still fail graph, contract or behavior checks. Failed, interrupted or unmeasured inference cannot be counted as success. See the generated report for exact measured runtime status.

## Final evidence snapshot

Final inspection confirmed 81 executed tests passed, 23/23 reference fixtures and 10/10 reference relations passed, all 46 injected invalid variants were rejected by B4, and all seven equivalent variants passed D/E/F (three semantic aggregate verdicts remain UNKNOWN). The final offline browser test covered 69 workflow choices, a real generated graph with issue markers, fixture path changes, failure explanations and a 390px layout with no overflow, page errors or remote requests. Both model experiment jobs are terminal and no STARTED request records remain.

Seven real qwen3:4b direct responses were schema-shaped but graph-invalid. Hierarchy stopped on invalid stage dependency; N=2 accepted neither candidate. Two all-items judge responses gave one decisive agreement and one abstention; the selective judge timed out. This is measured experimental completion, not a claim of successful workflow generation or complete semantic assurance. `outputs/verification.json` records artifact hashes, final counts, rechecked generated graph verdicts and the precise retained limits.
