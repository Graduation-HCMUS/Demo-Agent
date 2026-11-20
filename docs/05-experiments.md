# Experimental protocol and measured evidence

The authoritative generated artifacts are `outputs/results.json`, `outputs/report.html`, `outputs/summary.md`, raw call records and test transcripts. This guide defines how to interpret them; measured outcome tables are generated from actual saved runs.

## Reproduce the deterministic experiment

```bash
export PYTHONPATH="$PWD/src"
python -m genie_eval.cli test
python -m genie_eval.cli demo --mode reference
```

Run from the experiment directory. No Ollama dependency is involved. The oracle lock is checked, each hand-authored reference is confirmed against independent contract/scenario/metamorphic expectations, then controlled graph variants are evaluated. Seven language cases cover five business scenarios. Reference language success checks shared oracle plumbing, not model language ability.

## Real generation protocol

```bash
python -m genie_eval.cli doctor --model qwen3.5:9b
python -m genie_eval.cli benchmark --mode ollama --models qwen3.5:9b \
  --timeout 300 --num-ctx 8192 --num-predict 2048
```

One direct zero-shot call per case, fixed temperature 0 and seed 17, retries zero, judge off, candidate count one. Request SOP and relevant capability/schema context are allowed; fixture inputs, reference graphs, expected states/traces and metamorphic pairs are excluded. Different model/context/budget settings define different experiments; do not pool them as identical samples.

The same command accepts `qwen3:8b` or `qwen3:4b` when installed. No model is pulled automatically. Preserve first-pass results even if invalid. A transport error or truncated JSON remains a failed attempt. Null token counts mean no count returned, not zero tokens.

`--all-methods --candidates 2` opts into direct, hierarchical and reranked generation on the selected cases plus selective/all-items judges. `--judge-models` supports separate judges; `--planner-model`/`--detail-model` support separate generation stages. No independence is inferred merely from extra calls.

## Fair comparisons and denominators

- **Reference validation:** deterministic fixtures on hand-authored reference graphs. Not generator performance.
- **Evaluator performance:** PASS/FAIL/UNKNOWN against known variant labels; report the entire confusion accounting and per-error detection.
- **First-pass structural validity:** the first returned attempt's shape/graph, before retry or selection. Failures with no workflow are included in attempt/request counts and never treated as successes.
- **Contract/policy validity:** generated candidates that pass D divided by requested candidates; parse/transport failures contribute no success.
- **Behavioral correctness:** candidates that pass all primary fixtures divided by requested candidates; metamorphic correctness is separately inspectable.
- **Selection:** selected-candidate behavioral success per candidate group. Report both pre-selection and selected results; no claim about held-out inputs.
- **Judging:** selective scope and all-items ablation are separate. Agreement uses only rubric items with independently decisive executable labels and decisive judge verdicts; unknowns and unlabeled tone items remain visible.
- **Language:** show English and Vietnamese separately. Same domain source/oracle means translations are not independent source examples.

A missing model causes nonzero benchmark exit with explicit failure; an empty/skipped benchmark is never successful. Partial runs and timeouts remain evidence of limited execution. Response caches preserve original metrics and flag reuse; new billed/local inference token use is zero only for a cache hit. Case/strategy checkpoint files allow inspection after an interrupted run.

## Measurements recorded during development

The initial local model check found no installed models; a later check found `qwen3.5:9b`, `qwen3:8b` and `qwen3:4b`. One real v1 `qwen3.5:9b` intake request timed out at 180 seconds without returning content. `ollama ps` then showed CPU execution and context 4096. This is a local observation, not a hardware requirement. That attempt is retained in `outputs/generations/intake-en-direct.json`; token counts are unknown.

Prompt v2 deterministically selects relevant capability contracts from normative SOP requirements, includes no hidden fixture data, and records an explicit configurable context limit. Bounded alternative-model runs use a separately recorded configuration. See the generated result tables for returned responses, validity, actual model names/digests, token counts and latency. No success is inferred from installation or a running request.

## Interpretation

The designed mutant suite establishes whether each implemented layer detects its known fault categories. The missing-field relation demonstrates incremental metamorphic value beyond the primary fixtures. Keywords remain useful diagnostics with explicit false positives. Additional LLM stages/judges/candidates require actual comparable measurements before a claim that their complexity improves correctness.

The TypeScript recommendation is to begin with strict contracts, policy gates, the bounded runner, independently reviewed fixtures and a small set of justified metamorphic relations. Keep direct structured-output generation as the default. Use selective semantic review for unresolved requirements; enable hierarchy/extra candidates only when gains on the same case coverage justify their latency/token cost.

A smaller real-model comparison can be reproduced after the direct benchmark with:

```bash
python scripts/selected_methods.py --model qwen3:4b --timeout 300 --num-ctx 8192 --num-predict 2048
```

This compares direct/hierarchical/N=2 on the same `intake-en` case, runs an all-items judge on its reference and branch-swapped variant (two independent executable labels), and selectively judges the unresolved `order-en` wording item. It checkpoints each independent result in `outputs/selected-methods/`. This is a **subset demonstration**, not a seven-case strategy benchmark or human semantic-accuracy evaluation. Existing responses are reused with cache labels; original and incremental costs differ. The full all-method CLI configuration remains available when broader inference cost is justified.

## Final recorded outcomes


These values were extracted from the delivered JSON, not prewritten model scores. The deterministic suite passed 23/23 reference fixtures and 10/10 metamorphic relations across five English cases and two Vietnamese counterparts. It evaluated 53 variants: 46 injected errors and seven valid equivalent graphs. Three equivalent variants retain unresolved wording criteria; all seven pass deterministic D/E/F.

| Evaluation layer | Invalid variants rejected / 46 | False accept | False reject | Unknown |
|---|---:|---:|---:|---:|
| B0 | 0 | 46 | 0 | 0 |
| B1 | 2 | 44 | 0 | 0 |
| B2 | 36 | 0 | 0 | 17 |
| B3 | 45 | 1 | 0 | 3 |
| B4 | 46 | 0 | 0 | 3 |
| B5 | 46 | 0 | 0 | 3 |

B5 is an unmeasured mutation-suite extension: its deterministic verdicts match B4, and no judge success is inferred. Real judge ablations below are separate.

| Actual run | Requests/candidates | Outcome |
|---|---:|---|
| direct, qwen3:4b, genie-zero-shot-v2 | 7 | 7 parsed workflows; schema/graph first-pass=1.0/0.0; behavioral=0.0; new generation calls=7; cache hits=0 |
| direct, qwen3.5:9b, genie-zero-shot-v1 | 1 | 0 parsed workflows; schema/graph first-pass=0.0/0.0; behavioral=0.0; new generation calls=1; cache hits=0 |
| hierarchical, qwen3:4b, genie-zero-shot-v2 | 1 | 0 parsed workflows; schema/graph first-pass=None/None; behavioral=0.0; new generation calls=1; cache hits=0 |
| multi-candidate, qwen3:4b, genie-zero-shot-v2 | 2 | 2 parsed workflows; schema/graph first-pass=1.0/0.0; behavioral=0.0; new generation calls=1; cache hits=1 |

The v2 direct qwen3:4b run used temperature 0, seed 17, context 8192, completion cap 2048, timeout 300 seconds and retries 0. All seven responses fit the JSON shape; none passed graph validity, so no behavioral success is claimed. The original v1 qwen3.5:9b request used the recorded older configuration and timed out at 180 seconds. Its tokens are unknown and it is kept separate.

The matched `intake-en` demonstration stopped hierarchical generation after a plan dependency referenced an operation name instead of a stage ID (`PLAN_DEPENDENCY`). N=2 reused seed-17 output and generated seed 18; both graphs were invalid and selection accepted neither. There is no measured generation improvement in this subset.

| Judge scope | Returned status | Decisive agreement | Unknown/limitations |
|---|---|---|---|
| All-items intake reference | RUN | 1/1 | 0 UNKNOWN |
| All-items intake swapped_branches | RUN | 0/0 | 1 UNKNOWN |
| Selective order wording | UNAVAILABLE_OR_INVALID | No independent human semantic labels | UNKNOWN; request timed out at 300 seconds; tokens unknown |

Judge agreement is one decisive agreement from two executable-label ablation items, with one abstention; it is not 100% semantic accuracy or a human calibration result. The separate selective semantic request timed out. No deterministic failure was overridden.

Every call records exact model digest, options, prompt/schema hashes, raw first-pass content, status, latency and reported tokens. Cache hits record original and incremental costs separately. Two earlier interrupted foreground invocations returned no saved response; their unobserved outcomes are not counted as success.

Local inference was observed on CPU; no hardware requirement is inferred. The installed default-model digest begins `56671c2ab938`, qwen3:4b `359d7dd4bcda`; full digests and metadata are in doctor/call records. qwen3:8b was installed but not evaluated. This designed suite and single/subset trials do not justify broad Helpdesk or language-generalization claims.

**Recommendation from these outcomes:** port strict graph/contract/policy checks and independent execution fixtures first. The source-grounded metamorphic pair adds a detection absent from ordinary fixtures. Keep glossary diagnostic. In this run, schema-constrained JSON alone was insufficient, hierarchy and a second candidate produced no accepted intake workflow, and the judge added cost without demonstrated incremental detection. Keep those optional until comparable held-out evidence supports their cost.

The raw all-items judge confusion accounting was true acceptance 1, false acceptance 0, true rejection 0, false rejection 0, UNKNOWN 1. This uses the model's raw item verdicts, not the system's effective hard-failure result.
