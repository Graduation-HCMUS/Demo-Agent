# Porting the experiment to Genie TypeScript

The portable core is JSON contracts and deterministic behavior, not a Python framework. Keep the AI generation adapter separate from the workflow runner. A model returns a definition; it does not supply executable code or authority to bypass approval.

| Python concept | TypeScript equivalent | Porting detail |
|---|---|---|
| Pydantic workflow schema (suggested in brief); actual standard-library `WORKFLOW_SCHEMA` here | Zod or typed JSON Schema | Preserve strict configs, discriminated node types and explicit branch ports; use a full schema library instead of expanding the local subset checker. |
| Python function registry | TypeScript operation registry | Map operation IDs to argument schema, state inputs/outputs, preconditions/effects and a fixed implementation. |
| Python DAG runner | TypeScript workflow runner | Copy input state, validate graph, invoke known functions, follow one edge, record traces and stop at output. |
| Evaluator function | TypeScript validator function | Preserve PASS/FAIL/UNKNOWN and structured evidence, with hard failures immutable. |
| Ollama Python call (actual `urllib` HTTP adapter here) | Ollama JavaScript client or `fetch` | Supply JSON Schema via `format`, `stream:false`, fixed options, explicit timeout and no automatic model pull. |
| pytest fixtures (suggested); actual `unittest` fixtures here | Node test runner fixtures | Reuse JSON inputs/expected states/traces and controlled graph edits; assert behavior rather than snapshots of implementation. |
| JSON experiment results | Shared language-independent JSON contract | Preserve model/config/digest, cache provenance, unknown metrics, attempt records, evaluation evidence and denominators. |

## Directly reusable artifacts

SOP JSON, source IDs/URLs, glossary entries, prompt text, expectation fixtures, metamorphic pairs, reference DSL graphs and exported schema can be reused after normal domain review. TypeScript should use the exact operation IDs (`request_approval`, `send_reply`, etc.) in both English and Vietnamese requests. The language changes the request, not the tool interface.

`run` is a short interpreter, not a graph orchestration framework. Port its adjacency lookup, selected-edge handling, bounded steps, state-copy semantics and explicit errors. Precompute outgoing-edge maps if desired; that does not change the contract. The Python references and fixtures give a cross-language conformance suite: compare final states and effect order while permitting different internal node arrangements.

Data dependency analysis intersects predecessor field sets at merges. Guard facts are also intersected. A value/approval proven on only one incoming path must not authorize a later action. JavaScript equality differs from Python in details; use explicit scalar type checks so `true` never equals `1`. JSON booleans/numbers and absent/null state must behave consistently.

A TypeScript discriminated result is enough:

```ts
type Verdict = 'PASS' | 'FAIL' | 'UNKNOWN';
type Finding = {
  code: string;
  category: 'structure' | 'contract' | 'policy';
  node_id: string | null;
  message: string;
};
```

Aggregate by FAIL first, then UNKNOWN, then PASS. The Python `aggregate([])` returns UNKNOWN; the caller must explicitly identify a not-needed optional judge. Do not translate UNKNOWN to `true`, drop it from a denominator, or overwrite deterministic FAIL with model opinion.

## Components requiring redesign before production

Local in-memory effects are demonstrations. A real ticket integration needs authorization, authenticated identity, error handling, durability/idempotency and a genuine human-approval lifecycle. The experiment deliberately does not build these. `approval_decision`, `high_risk`, counters and `mock_order` are trusted fixture inputs, not production trust boundaries.

The `file` contract is shape-only and explicitly unsupported at runtime. Do not infer that the Python lab safely processes attachments. The `issue_refund` mutation capability does not provide any real financial integration or permission.

The report's simple SVG layout and its fixture selectors are educational artifacts. The production React editor can display the same graph/trace JSON using its existing rendering components. There is no need to migrate the report's inline HTML scripting as an application architecture.

Before reusing the suite as an acceptance gate, domain reviewers should validate the source-derived SOP scope, group mappings, missing-field policy, translation and semantic labels. Add realistic held-out inputs. Keep any test fixtures used to rerank candidates separate from later generalization evaluation; this lab reports selection only on its own finite suite.

## Suggested order for the TypeScript team

1. Adopt DSL/trace/result contracts and a strict operation registry.
2. Port graph/argument/dependency/policy checks and the deterministic runner.
3. Port independently reviewed scenarios and metamorphic pairs; retain equivalent-graph acceptance.
4. Add direct schema-constrained generation and immutable first-pass telemetry.
5. Add selective semantic judging only where deterministic checks leave a meaningful question.
6. Measure hierarchy and multiple candidates against direct generation on the same cases before paying their token/latency cost.

[Ollama's structured-output documentation](https://docs.ollama.com/capabilities/structured-outputs) includes a JavaScript/Zod pattern. [OMG DMN](https://www.omg.org/dmn/) motivates keeping explicit decision rules separate from process rendering; this migration does not require a DMN engine.
