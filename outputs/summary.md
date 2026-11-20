# Genie measured experiment

Reference demonstrations: 7 cases, 23 fixtures; behavioral pass rate 100.0%.
Controlled variants: 53 (includes valid equivalent graphs).

| Configuration | Detected invalid / total | False accept | False reject | Unknown |
|---|---:|---:|---:|---:|
| B0 | 0/46 | 46 | 0 | 0 |
| B1 | 2/46 | 44 | 0 | 0 |
| B2 | 36/46 | 0 | 0 | 17 |
| B3 | 45/46 | 1 | 0 | 3 |
| B4 | 46/46 | 0 | 0 | 3 |
| B5 | 46/46 | 0 | 0 | 3 |

UNKNOWN is not PASS or FAIL. Semantic tone items remain unresolved without review. B5 judge was disabled in the reference comparison.

## Actual generation

- direct / qwen3:4b / genie-zero-shot-v2: MEASURED; cases=7, requests=7, workflow attempts=7, first-pass structural=0.0, behavioral=0.0, selected behavioral=0.0, new prompt/completion tokens=10917/3810.
- direct / qwen3.5:9b / genie-zero-shot-v1: ATTEMPTED_NO_OUTPUT; cases=1, requests=1, workflow attempts=1, first-pass structural=0.0, behavioral=0.0, selected behavioral=0.0, new prompt/completion tokens=None/None.
- hierarchical / qwen3:4b / genie-zero-shot-v2: NO_WORKFLOW_OUTPUT; cases=1, requests=1, workflow attempts=0, first-pass structural=None, behavioral=0.0, selected behavioral=0.0, new prompt/completion tokens=1181/304.
- multi-candidate / qwen3:4b / genie-zero-shot-v2: MEASURED; cases=1, requests=2, workflow attempts=2, first-pass structural=0.0, behavioral=0.0, selected behavioral=0.0, new prompt/completion tokens=1347/319.

Reference bilingual results only test the shared simulator oracle, not model multilingual ability.

## Recommendation

Port the JSON contracts, fixed capabilities, policy gates, runner and independent fixtures first. Add metamorphic pairs where ordinary fixtures leave gaps. Glossary is a diagnostic only. Keep selective semantic judging and extra candidates opt-in until measured gains justify their inference cost.

## Limits

- Synthetic, source-derived snapshot suite, not an official dataset.
- B2 and later preserve semantic UNKNOWN; no silent acceptance.
- B5 without an enabled model judge is an unmeasured extension.
- Reference bilingual success measures shared oracle plumbing, not model language ability.
- Real strategy demonstrations use the explicitly listed case coverage; broader strategy superiority is not established.
- An earlier v1 default-model timeout is a separate configuration, retained rather than pooled with v2 success claims.

See `results.json` for exact configuration, per-fixture traces, per-error detection, wall latency and token nulls; see `docs/02-sources-and-provenance.md` for sources.
