# From a process description to an executable graph

The source describes business behavior; the local SOP bounds the experiment; the JSON graph implements that slice. The independent fixtures judge the implementation. They are separate artifacts. For example, approval before replying is a behavioral requirement regardless of whether a graph has one output or several terminal outputs.

## DSL contract

`models.WORKFLOW_SCHEMA` is the exported language-independent schema. Every workflow has `schema_version`, `workflow_id`, `name`, `nodes`, and `edges`. Every node has `id`, `type`, and `config`; every edge has `source`, `target`, and `port`.

| Node | Config | Runtime behavior |
|---|---|---|
| `input` | Empty object | Entry; exactly one |
| `output` | Empty object | Successful terminal; one or more permitted |
| `condition` | `field`, `operator`, `value` | Read a state field; choose exactly `true` or `false` |
| `custom` | `operation`, `args` | Invoke a registered local capability |
| `file` | `operation: metadata`, `name`, `media_type`, nonnegative `size_bytes` | Shape/contract only; rejected as `FILE_UNSUPPORTED` at execution validation |

Non-condition nonterminal nodes have one `next` edge; output has none. A condition has one edge per explicit boolean port, even when both edges target the same node. Every node is reachable from input and the whole graph is acyclic. The schema bounds nodes at 128 and edges at 256; execution defaults to 128 steps.

A real node from the approval reference:

```json
{"id":"send","type":"custom","config":{"operation":"send_reply","args":{"text":{"ref":"draft"}}}}
```

A real decision and edge:

```json
{"id":"decision","type":"condition","config":{"field":"approval","operator":"eq","value":"approved"}}
```

```json
{"source":"decision","target":"send","port":"true"}
```

References are JSON objects with exactly the `ref` property; they resolve from state, never from Python expressions. Fields are flat names, not dotted path evaluation. Arguments allow literal values only where their operation schema permits. `eq`/`ne` distinguish booleans from numbers; `exists` tests presence/non-null and does not use `value`; `gte` requires actual numeric operands. An absent field compares unequal; an absent numeric operand errors. There is no `eval`, script node, loop, scheduler or concurrency.

## Capability and state contracts

`catalog.REGISTRY` contains functions plus their descriptions, argument schemas, required/produced state fields, preconditions, effects and restrictions. Domain-specific implementations stay in the catalog, and business choices stay in SOP/policy data. `runner.run` knows only node types and graph traversal.

`create_ticket` writes a boolean marker. `request_approval` requires a created ticket, a draft and a supplied approved/rejected decision. `send_reply` requires the approved state. `lookup_order` requires saved identifiers, verifies that arguments equal those saved values and reads a synthetic lookup object. No operation calls Zendesk, n8n, email, Slack, a payment system, or a file reader.

`issue_refund` exists only to make a forbidden-effect mutation executable as a known contract; every SOP forbids it before invocation. It is an explicitly experimental policy, not an assertion that Zendesk universally forbids refunds. No operation can transfer money.

Inputs may omit declared fields so validation/missing-information branches can run. Static data availability means a name belongs to the input contract or is definitely produced; it does not mean an optional field is populated. Runtime validation and preconditions settle actual presence/type/format. Initial `effects` and `messages` are reset by the runner, so caller-supplied effect histories do not establish execution.

## Validation algorithm

1. Validate the exact schema subset used in this experiment. The standard-library checker supports `type`, `const`, `enum`, `oneOf`, object `properties`/`required`/`additionalProperties`, array `items`/length bounds, string minimum length and numeric bounds. It is not a general-purpose JSON Schema validator.
2. Check IDs, edge endpoints, ports, input/output cardinality and reachability.
3. Use Kahn topological sorting; reject cycles including disconnected cycles.
4. In topological order, intersect predecessor field sets. A value produced on one branch is insufficient at a merge if another path omits it.
5. Track supported equality facts along true/false edges, intersecting at merges. Known ticket creation establishes its precondition fact; writes invalidate old facts. Reject unproven operation preconditions and SOP guards.
6. Validate registered operations and argument schemas; reject forbidden operations as policy issues, separate from structural findings.
7. At invocation, resolve arguments, validate concrete runtime types, check required fields/preconditions/policy again, then apply the effect.

The must-analysis is intentionally conservative. It proves a small set of equality guards, not arbitrary logical equivalence or SMT constraints. A safe graph using a different complex guard may be rejected as unproven. The deliberately different valid graph in this suite inserts a redundant branch and remains accepted by the implemented rules.

Findings contain stable `code`, `category`, `node_id` and `message`. Examples: `SCHEMA`, `DUPLICATE_ID`, `EDGE_ENDPOINT`, `EDGE_PORTS`, `UNREACHABLE`, `CYCLE` (structure); `UNKNOWN_OPERATION`, `ARGUMENT_SCHEMA`, `DATA_DEPENDENCY`, `PRECONDITION_UNPROVEN`, `FILE_UNSUPPORTED` (contract); `POLICY_FORBIDDEN`, `POLICY_GUARD` (policy).

## Execution and evidence

```python
from genie_eval.models import get_case, reference, sop_for
from genie_eval.runner import run
case = get_case("approval-en")
execution = run(reference(case), case["input_fixtures"][0]["input"], sop_for(case))
assert execution["status"] == "OK"
```

The runner copies ticket data, validates before any operation, follows a single selected edge and stops at output. Each trace step has index, node/type, operation, pre-step snapshot, state changes, selected edge and error. `INVALID` means validation blocked execution; `ERROR` means runtime/precondition/step-limit failure; `OK` only means execution reached output. Oracle assertions are a separate evaluator. A successfully executed wrong route is still a failed scenario.

The process structure borrows ideas from [BPMN](https://www.omg.org/bpmn/) and explicit decisions from [DMN](https://www.omg.org/dmn/). It does not implement either standard. [Zendesk procedure-writing guidance](https://support.zendesk.com/hc/en-us/articles/9424547622298) motivates ordered actions and explicit conditions; actual local restrictions are auditable in each SOP.
