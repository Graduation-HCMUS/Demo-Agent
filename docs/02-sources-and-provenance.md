# Sources and provenance

Research used Firecrawl before implementation. All supplied starting URLs were attempted on 2026-11-20. `data/sources.json` is the machine-readable manifest: exact URL, title, publisher, date where available, relevant section, supported claim, limitations, source/artifact classification and artifact mappings. No full copyrighted templates are copied. Research paper coverage is abstract/metadata only; this is a focused engineering experiment, not a comprehensive literature review.

## Four kinds of claim

- `SOURCE_FACT`: the identified page explicitly establishes the fact.
- `SOURCE_ADAPTATION`: the fact is translated into a scoped Genie process or assertion, e.g. email approval becomes a supplied decision consumed once.
- `EXPERIMENTAL_ASSUMPTION`: a local choice required for simulation, e.g. group IDs or the intake field set. This is not a vendor policy.
- `UNVERIFIED`: evidence was unavailable; no substantive claim is made.

The workflow and fixture artifacts are adaptations with independently designed synthetic data. A source's publisher does not endorse these artifacts. Vietnamese prompts reuse the English source and oracle; they add no independent domain evidence. They were author-drafted and programmatically paired; no independent bilingual human review occurred.

## SOP → reference → cases

Every row names the entire artifact family. Load-time cases have `user_request` joined from `data/prompts.json`; the stored expectation files intentionally contain a prompt pointer, keeping bilingual prompts separate from the oracle.

| SOP / reference workflow / cases | Published reference and exact section | Extracted behavior | Genie transformation and assumptions | Omitted or unsupported behavior; Helpdesk relevance |
|---|---|---|---|---|
| `intake` / `reference-workflows/intake.json` / `intake-en` | [n8n routing template](https://n8n.io/workflows/18499-route-and-respond-to-support-tickets-with-google-sheets-slack-and-gemini/), “How it works” steps 1–2; [Zendesk planning](https://support.zendesk.com/hc/en-us/articles/4408827906202-Planning-your-workflow), “Ticket fields/forms” | Validate required submission fields and reject invalid payloads. | Choose email/message as local required fields, record status 400 and requested fields; complete intake creates a marker. Field choice and request-info event are explicit local assumptions. | No actual webhook, deduplication, authentication or Google Sheets. Request intake is a general support responsibility. |
| `routing` / `reference-workflows/routing.json` / `routing-en` | [n8n routing template](https://n8n.io/workflows/18499-route-and-respond-to-support-tickets-with-google-sheets-slack-and-gemini/), “How it works” steps 4–8; [Zendesk trigger reference](https://support.zendesk.com/hc/en-us/articles/4408893545882-Ticket-trigger-conditions-and-actions-reference), “Ticket > Group” | Routing may lead to human escalation and interaction logging. | Accept a trusted `high_risk` boolean; use local human/ordinary group identifiers and `log_ticket`. No invented numerical threshold. | No AI risk classifier, actual Slack alert, policy retrieval or daily summary. Dispatch and human handoff apply to general support. |
| `approval` / `reference-workflows/approval.json` / `approval-en`, `approval-vi` | [n8n triage template](https://n8n.io/workflows/19465-triage-and-route-ai-powered-support-tickets-with-google-gemini-trello-and-gmail/), “How it works” steps 2–7 | Scope gate; card creation; approval before sending; approved resolution or rejected manual review. | Supply scope and proposed reply in input; consume a pre-supplied human approval decision. In-memory ticket/group/reply replace Trello/Gmail. | No real waiting, scope classifier, priority labels, customer lookup or email. Human review of proposed customer communications is a Helpdesk control. |
| `order` / `reference-workflows/order.json` / `order-en`, `order-vi` | [Zendesk procedure examples](https://support.zendesk.com/hc/en-us/articles/9424547984026), “Example procedure: Order status,” detail collection and status check | Validate order/email, save identifiers, handle repeated invalid entries, look up and report status. | Five-digit order check; simple email-format check; supplied attempt counters and mock lookup object; structured status response. | Single snapshot instead of conversational retries; no live API. Delivery-time example and exact formatting omitted. Cancellation is a notice; no refund authority is inferred. Order support is a retail Helpdesk example, not all Helpdesk work. |
| `damage` / `reference-workflows/damage.json` / `damage-en` | [Zendesk procedure examples](https://support.zendesk.com/hc/en-us/articles/9424547984026), “Example procedure: Damaged item” | Gather details, ask for optional photo, submit ticket and arrange human follow-up. | Symbolic notices, input product/damage fields, local ticket and handoff; optional photo never blocks. Creation then next-step notice is the local synchronous handoff order. | No photo processing, real ticket or elapsed-time simulation. The example's stated follow-up interval is represented only as a template identifier. Tone remains unresolved. Damaged-item handling illustrates intake and escalation. |

For each family, `data/sops/<id>.json` records scope/purpose, trigger, inputs, required fields, roles, preconditions, ordered activities, decisions, actions, exceptions/escalation, expected outputs, forbidden actions, postconditions, source-backed requirements, assumptions and limitations. `data/cases/<case>.json` records independent fixtures, expected states/actions/order, forbidden effects and metamorphic relations. `data/reference-workflows/<id>.json` is hand-authored Genie DSL, never n8n JSON and never model output.

Only n8n descriptions were retrieved; the full published graph JSON was not. The Genie graphs are **derived approximations**, not exact translations. No graph equality is used to judge correctness.

## Rule and fixture lineage

Requirement IDs `I1`, `R1`, `A1`, `O1`–`O3`, `D1`–`D2` resolve to source IDs in the case files. `evaluation_method=trace` means bounded execution evidence; semantic wording items remain UNKNOWN. Required capability presence can establish absence, but cannot establish behavior.

The required-field add/correct, risk flip and approval flip metamorphic pairs are adaptations of the corresponding conditional process descriptions. Synthetic `.test` emails, product names, order numbers and dates are independently designed inputs, not published benchmark examples. The chosen email/message field set, risk flags, group names, synchronous decisions, mock state, and no-money simulator boundary are assumptions. The no-refund restriction is explicitly experimental; a vendor example mentioning a refund notice is not permission to issue one.

`data/oracle-lock.json` hashes the source/expectation/reference files. It was created before any real generator response and is checked at reference-run time. A hash proves file stability, not that its contents are correct. Programmatic bilingual equality checks prove equal oracle data, not translation quality. The pre-inference implementation plan and source read evidence establish the development sequence.

## Modeling and evaluation references

- [Zendesk best practices](https://support.zendesk.com/hc/en-us/articles/9424547622298): sequential activities, explicit conditions/actions and error handling. We adapt these process-writing concepts; do not transfer its language-performance statement to our model.
- [Zendesk workflow recipes index](https://support.zendesk.com/hc/en-us/articles/4408828320666-Workflow-recipes-reference): a discoverability index only. Linked recipes were not read and establish no detailed rule here.
- [OMG BPMN overview](https://www.omg.org/bpmn/) and [DMN overview](https://www.omg.org/dmn/): process and business-decision concepts. No BPMN XML, FEEL, DMN engine or conformance is implemented.
- [τ-bench](https://arxiv.org/abs/2406.12045), abstract: final-state goal checking motivates E; our fixtures are not its dataset and no published score is reused.
- [Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685), abstract: preference judging and bias limitations motivate caution about model judges.
- [G-Eval](https://aclanthology.org/2023.emnlp-main.153/), abstract: structured evaluation forms motivate the rubric; this is not a reproduction of its scoring or reasoning procedure.
- [LLM-as-a-Judge survey](https://arxiv.org/abs/2411.15594), abstract: reliability and bias are research concerns, not solved properties of this implementation.
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs), schema section: supplies the JSON-schema request pattern. The local standard-library HTTP adapter avoids runtime dependencies; Python client/Pydantic would also be reasonable in a larger project.
- [qwen3.5:9b listing](https://ollama.com/library/qwen3.5:9b) and [qwen3:8b listing](https://ollama.com/library/qwen3:8b): requested tags were verified. Hardware requirements and installed digests come from local runtime evidence, not a downloaded webpage.

## Unresolved provenance

[WorkflowJudge DOI supplied in the brief](https://doi.org/10.1109/AIBDF67964.2025.11440748) failed retrieval; an exact title/DOI search returned no results. Its title/author/content/results remain unverified. It is recorded but supplies no method or business rule. We do not claim that this establishes the DOI is invalid. Full n8n graphs, full research-paper methods and independent human translation/judge labels remain outside the evidence gathered.

Supplemental engineering verification (after the independent business oracle was frozen) is recorded in `docs/supplemental-sources.json`: [Ollama chat API](https://docs.ollama.com/api/chat), body controls and response metrics, and [model listing API](https://docs.ollama.com/api/tags), installed name/digest metadata. These support the transport adapter, not additional business rules or changed fixture labels. The original oracle/source lock remains unchanged.
