# Limitations and threats to validity

## Source and domain scope

Five source-derived process slices cannot establish broad Helpdesk generalization. Two vendor example procedures and two published template descriptions establish only their described behavior. Full n8n graph JSON was not retrieved; Genie graphs are derived approximations. Linked Zendesk recipes and full research-paper methods were not read. WorkflowJudge's supplied DOI could not be retrieved/verified and is not used as authority.

The intake field choice, group names, risk flag, synchronous approval snapshot, simple email check, mock lookup and no-money boundary are explicitly local assumptions. They are not universal Zendesk/n8n policies. Order/damage scenarios are retail-support examples. The business domain is broader than the suite.

## Oracle and coverage

Fixtures and mutation labels are independently constructed from the scoped SOP before real generation, but remain human-designed interpretations. The oracle lock proves stability, not correctness. English/Vietnamese pairs share the same oracle and source, so they are correlated cases. Translations lack independent bilingual human review.

Finite scenario/metamorphic coverage cannot prove a workflow safe for every input. The special missing-message mutant illustrates a real primary-fixture coverage gap. Other untested combinations can remain. Trace requirements currently share case-level scenario evidence rather than fully isolating assertions for each requirement. Symbolic notification identifiers cannot establish empathy or faithful free-form wording.

`required_fields` in the SOP lists the snapshot fields the procedure reasons about, including counters and supplied lookup/approval data. Some fields may be absent so missing-information paths can execute; this is not a blanket claim that all fields are mandatory on every branch. Runtime operations enforce actual requirements when reached.

Mutation detection is measured against deliberately designed fault types. It is not the natural error distribution of LLMs, and mutations of one reference are not independent draws. Pooled language variants duplicate some faults. Equivalent-graph variants are valid on this specification/fixture scope, not proven equivalent for every possible unmodeled input.

## Contracts and execution

The JSON Schema checker implements only the keywords used in the exported schemas. It is not a standards-complete validator. Must-data/guard analysis supports a small set of facts and can conservatively reject behavior expressed through unsupported logical forms. It is not symbolic execution, model checking or a proof system.

The runner supports one deterministic DAG path per ticket snapshot. No multi-turn conversations, loops, parallel execution, real APIs, retries of external tools, scheduling, persistence or production error recovery are simulated. The only retry option concerns LLM generation calls. `file` has a metadata shape but unsupported runtime; no attachment processing is claimed.

Input flags/counters/approval decisions and lookup responses are trusted simulator data. A production system must obtain and authorize them independently. The local registry has no external side effects; its successful simulation does not demonstrate a working integration.

## LLM evidence and metrics

Installed model names do not prove a successful inference. A timeout with no response has unknown tokens and no parseable workflow. Raw responses, model digests, configurations and original attempt records are the authority for real model claims. No reference workflow is substituted for unavailable output.

Temperature zero and a fixed seed do not guarantee identical output across runtime versions/hardware. Different seeds at temperature zero may generate identical candidates. Cache hits are not fresh model trials and are explicitly labeled. First-pass metrics use the first attempt, not the repaired/retried result. An interrupted request with no returned content cannot establish model success or token usage.

Judges can share generator biases, hallucinate interpretations, or agree incorrectly. Valid evidence IDs only establish referential integrity, not valid reasoning. Same-model multi-stage/multi-judge use is correlated. Deterministic failure always prevails. Agreement measured against executable fixture labels does not establish agreement with independent human semantic labels; tone criteria have no such labels here.

Selective judging is the low-token default; all-items ablations are explicitly more expensive. A checker rejecting more candidates does not improve first-pass generation accuracy. Reranking success is selection on this finite suite, not held-out generalization. Strategy comparisons require the same case/config coverage; partial/subset runs are reported as such.

Wall latencies depend on cold model loading, CPU/GPU allocation, context, token budget, cache and other local activity. Layer durations sum reused component timings and are illustrative. Token nulls remain unknown. No published paper/model scores are imported into local result tables.

## Next evidence to collect

Review SOP scope and bilingual prompts with domain/bilingual reviewers; acquire legitimate full-template access if exact translation matters; add independent human semantic labels and held-out tickets; evaluate repeated uncached first-pass generations on identical case coverage; study runtime/configuration sensitivity. Production integrations, formal verification, training/fine-tuning and RAG are future work, outside this PoC.
