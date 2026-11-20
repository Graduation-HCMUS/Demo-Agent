# Genie workflow verification lab

This isolated Python PoC compares ways to check LLM-generated Helpdesk workflows. It has five source-derived scenarios, five English cases and two Vietnamese equivalents, a safe JSON DAG runner, eight executable approaches, controlled mutations, and an offline visual report. It changes no application or root tooling.

Start with [concepts](docs/01-concepts.md), then open [the report](outputs/report.html). Sources, assumptions, and unavailable evidence are documented in [the provenance guide](docs/02-sources-and-provenance.md). These are locally adapted demonstrations, not an official Zendesk/n8n dataset.

## Install and run

Python 3.11+ is the only runtime requirement. No packages, model downloads, server, database, Docker, API keys, or paid services are needed for reference mode. From this repository:

```bash
cd /home/ltp/Code/Graduation/Demo-Agent
python3 -m venv .venv
source .venv/bin/activate
export PYTHONPATH="$PWD/src"
python -m genie_eval.cli list-cases
python -m genie_eval.cli test
python -m genie_eval.cli demo --mode reference
python -m genie_eval.cli report
```

Open `outputs/report.html` as a local file in a browser. Workflow and fixture selectors show the executed path, state changes, failed assertions, requirements, and sources. No network connection is needed to render it. Source links naturally require connectivity if followed.

The JSON schema is available through `python -m genie_eval.cli schema`; save it with `> outputs/workflow.schema.json` if needed.

## Optional local inference

Ollama must already be running with the requested model installed. `doctor` checks `/api/tags`; it never pulls a model. Initially none were installed; a later verified check found all three requested tags. Current measured outcomes belong in [the experiment report](docs/05-experiments.md), not this setup description.

```bash
python -m genie_eval.cli doctor --model qwen3.5:9b
python -m genie_eval.cli generate --case intake-en --model qwen3.5:9b
python -m genie_eval.cli generate --case approval-vi --model qwen3:8b
python -m genie_eval.cli generate --case approval-en --strategy hierarchical \
  --planner-model qwen3.5:9b --detail-model qwen3.5:9b
python -m genie_eval.cli generate --case approval-en --candidates 2
python -m genie_eval.cli evaluate --case intake-en --methods all
python -m genie_eval.cli evaluate --case order-en --methods D,E,F
python -m genie_eval.cli evaluate --case order-en --methods all --judge
python -m genie_eval.cli evaluate --case approval-en --methods G --judge-all \
  --judge-models qwen3.5:9b qwen3:8b
python -m genie_eval.cli benchmark --mode ollama --models qwen3.5:9b
```

`evaluate` with no `--workflow` is explicitly a reference demonstration. To evaluate a new DSL JSON document, add `--workflow /absolute/path/workflow.json`. A generation bundle is not itself a workflow; its `candidates[i].workflow` field contains the DSL document.

All approaches, including both judge scopes, can be selected together:

```bash
python -m genie_eval.cli benchmark --mode ollama --models qwen3.5:9b \
  --all-methods --candidates 2 --case approval-en
```

Omit `--case` to use all seven cases. This explicitly enables many extra calls: three planning/mapping calls plus one workflow call per hierarchical candidate, two direct candidates, selective judging, and all-items judge ablations on generated and reference/mutated workflows. Start with one case when checking runtime. `--candidates 3` is also supported. Separate planner/detail/judge models are optional; using one model repeatedly does not establish independent reasoning.

Generation defaults: direct zero-shot, one candidate, temperature 0, seed 17, no retries, no judge, 4096 completion tokens, context 16384, 120-second request timeout. `--timeout`, `--num-predict`, `--num-ctx`, `--retries`, `--model`, and `--no-cache` are configurable. `.env.example` documents environment variables; the program does not load dotenv files. Changed seeds distinguish candidates at fixed temperature but need not produce different graphs.

Raw first-pass content and metrics are preserved before retries. The adapter drops Ollama's `thinking` field. Cache hits are labeled, record zero new inference tokens, and retain original token/latency metrics separately. All model input stays on a loopback HTTP Ollama host. No generation prompt contains reference workflows, fixture inputs, expected states, metamorphic pairs, or judge traces.

## Methods

| Method | Entry point | What establishes success |
|---|---|---|
| A: hierarchy + multiple judges | `generate(..., strategy='hierarchical')`; `judge(..., model_ids=[...])` | Structured plans/provenance, then normal evaluation; judge consensus is evidence, not proof |
| B: glossary | `glossary(workflow, case)` | Weak terminology coverage only |
| C: checklist | `checklist(workflow, case, execution_result)` | Per-requirement PASS/FAIL/UNKNOWN with evidence |
| D: contracts/policy | `contracts(workflow, case, sop)` | Schema, graph, operations, data flow, supported guards and explicit local policy |
| E: scenarios | `scenarios(workflow, case, sop)` | Independent final-state, required/forbidden effect and ordering assertions |
| F: metamorphic | `metamorphic(workflow, case, sop)` | Independently specified changed-input behavior |
| G: reference-guided judge | `judge(...)` | Typed evidence rubric; defaults to unresolved items; deterministic failures prevail |
| H: candidates/ranking | `generate_candidates(..., n=2)` | Independent evaluations ranked before complexity; a winner can remain invalid/unknown |

See [method definitions, examples, failure modes and costs](docs/04-evaluation-methods.md). Transport-double tests verify optional integrations without claiming model performance. Actual model results are separately labeled.

## Exit codes and outputs

Exit 0 means the requested required checks completed successfully; 1 means a deterministic evaluation failed; 2 means invalid command/input, unavailable model, transport failure, or incomplete benchmark; 3 means required evaluation remains UNKNOWN. `demo` succeeds when the bounded deterministic reference checks pass, while keeping unresolved semantic items visible. `evaluate --methods all` enumerates B–G but keeps G disabled unless `--judge`/`--judge-all` is selected. Disabled optional G does not itself fail required deterministic checks. `evaluate --methods C` without E evidence returns UNKNOWN for operation-name presence.

```text

├── README.md, implementation-plan.md, pyproject.toml, .env.example
├── docs/01-concepts.md … 08-verification.md
├── data/
│   ├── sources.json, glossary.json, prompts.json, oracle-lock.json
│   ├── sops/                  # 5 source-derived process slices
│   ├── cases/                 # 7 independent oracle bundles; prompts joined by ID
│   └── reference-workflows/    # 5 hand-authored Genie DSL graphs
├── src/genie_eval/             # contracts, runner, generation, evaluators, report, CLI
├── scripts/                   # selected-method run and final report assembly
├── tests/                     # stdlib unittest; transport doubles clearly identified
└── outputs/
    ├── report.html, results.json, summary.md
    ├── graphs/*.svg
    ├── test-run.txt, doctor.json
    ├── generations/, evaluations/, ollama-benchmark.json
    └── cache/                 # ignored; first-pass attempts and reusable responses
```

The source JSON and fixtures are reusable in TypeScript. [Migration guidance](docs/06-python-to-typescript.md) explains the runner and policy semantics. [Limitations](docs/07-limitations.md) distinguishes bounded assurance from broader Helpdesk correctness.

To reproduce the delivered combined report after the documented real runs:

```bash
python scripts/assemble_report.py --selected outputs/selected-methods/results.json --include-initial-timeout
python -m genie_eval.cli report
```

The earlier timeout file is optional historical evidence; omit `--include-initial-timeout` on a fresh checkout without that recorded attempt. `--output-dir` on demo/benchmark/report can keep independent runs in separate directories.
