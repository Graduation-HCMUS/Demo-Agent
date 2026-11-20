"""Offline report with deterministic inline SVG; no JavaScript/CSS dependencies."""
import html
import json
from collections import defaultdict
from pathlib import Path
from .models import ROOT,save,load,get_case,sop_for,digest
from .validators import validate


def esc(value):return html.escape(str(value),quote=True)


def graph_svg(workflow,issues=()):
    nodes=workflow.get('nodes',[]) if isinstance(workflow,dict) else [];edges=workflow.get('edges',[]) if isinstance(workflow,dict) else []
    ids={n['id'] for n in nodes};depth={id:0 for id in ids}
    # Longest depth in a DAG, bounded fallback also handles invalid cyclic inputs.
    for _ in range(len(nodes)):
        next_depth=dict(depth)
        for e in edges:
            if e['source'] in ids and e['target'] in ids:
                next_depth[e['target']]=max(next_depth[e['target']],min(len(nodes),depth[e['source']]+1))
        if next_depth==depth:break
        depth=next_depth
    levels=defaultdict(list)
    for n in nodes:levels[depth[n['id']]].append(n['id'])
    width=max(520,max((len(v) for v in levels.values()),default=1)*260+100);height=(max(depth.values(),default=0)+1)*120+50
    xy={id:((width-len(group)*260)/2+i*260+20,d*120+20) for d,group in sorted(levels.items()) for i,id in enumerate(group)}
    bad={i.get('node_id') for i in issues};parts=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Workflow graph">',
         '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="#64818c"/></marker></defs>',
         '<style>.edge{fill:none;stroke:#64818c;stroke-width:2}.node rect{fill:#edf4f5;stroke:#64818c;stroke-width:2}.node.condition rect{fill:#fff1d6}.node.invalid rect{stroke:#bf3a3a;stroke-width:3}.node.executed rect{fill:#d4f2dd;stroke:#16703e;stroke-width:3}.edge.executed{stroke:#16703e;stroke-width:4}text{font-family:system-ui,sans-serif;font-size:12px;fill:#152a35}</style>']
    for e in edges:
        if e['source'] not in xy or e['target'] not in xy:continue
        x,y=xy[e['source']];tx,ty=xy[e['target']];x+=105;tx+=105;y+=70
        key=f'{e["source"]}:{e["port"]}:{e["target"]}'
        if depth[e['target']]-depth[e['source']]>1:
            lane=12 if x<=width/2 else width-12
            path=f'M{x} {y} C{x} {y+22} {lane} {y+22} {lane} {y+35} L{lane} {ty-35} C{lane} {ty-18} {tx} {ty-18} {tx} {ty}'
            label_x,label_y=lane+5,y+55
        else:
            path=f'M{x} {y} C{x} {y+30} {tx} {ty-30} {tx} {ty}'
            label_x,label_y=(x+tx)/2+5,(y+ty)/2
        parts.append(f'<path class="edge" data-edge="{esc(key)}" d="{path}" marker-end="url(#arrow)"/><text x="{label_x}" y="{label_y}">{esc(e["port"])}</text>')
    for n in nodes:
        x,y=xy[n['id']];conf=n['config'];label=conf.get('operation',n['type'])
        if n['type']=='condition':label=f'{conf["field"]} {conf["operator"]} {conf["value"]}'
        parts.append(f'<g class="node {esc(n["type"])} {"invalid" if n["id"] in bad else ""}" data-node="{esc(n["id"])}"><title>{esc(json.dumps(n,ensure_ascii=False))}</title><rect x="{x}" y="{y}" width="210" height="70" rx="10"/><text x="{x+10}" y="{y+22}">{esc(n["id"])} · {esc(n["type"])} {"!" if n["id"] in bad else ""}</text><text x="{x+10}" y="{y+46}">{esc(str(label)[:29])}</text></g>')
    return ''.join(parts)+'</svg>'


def generation_comparison(runs):
    groups=defaultdict(list)
    for run in runs:
        calls=[call for c in run['candidates'] for call in c['calls']]
        workflow_calls=[call for call in calls if call['kind']=='workflow']
        primary=workflow_calls[0] if workflow_calls else (calls[0] if calls else {})
        conf={k:v for k,v in primary.get('configuration',{}).items() if k not in ['seed','retries','host']}
        key=(run['strategy'],primary.get('model','unknown'),primary.get('prompt_version','unknown'),json.dumps(conf,sort_keys=True))
        groups[key].append(run)
    rows=[]
    for (strategy,model,prompt_version,config_json),group in groups.items():
        candidates=[c for r in group for c in r['candidates']]
        all_calls=[call for c in candidates for call in c['calls']]
        workflow_calls=[call for call in all_calls if call['kind']=='workflow']
        first=[call['attempts'][0] for call in workflow_calls if call.get('attempts')]
        valid=sum(bool(call.get('attempts') and call['attempts'][0]['parsed'] is not None and not validate(call['attempts'][0]['parsed'],sop_for(get_case(c['case_id'])),False))
                  for c in candidates for call in c['calls'] if call['kind']=='workflow')
        measured=[c for c in candidates if c.get('evaluation')]
        def tokens(key,original=False):
            values=[call.get('original_'+key,call.get(key)) if original else call.get(key) for call in all_calls]
            return sum(values) if all(v is not None for v in values) else None
        rows.append(dict(strategy=strategy,status=('MEASURED' if measured else 'ATTEMPTED_NO_OUTPUT') if first else ('NO_WORKFLOW_OUTPUT' if any(call.get('attempts') for call in all_calls) else 'UNAVAILABLE'),model=model,prompt_version=prompt_version,configuration=json.loads(config_json),
                         returned_workflows=len(measured),case_ids=sorted({r['case_id'] for r in group}),requests=len(candidates),attempts=sum(len(call.get('attempts',[])) for call in workflow_calls),
                         actual_inference_calls=sum(r['generation_metrics']['actual_inference_calls'] for r in group),cached_calls=sum(r['generation_metrics']['cached_calls'] for r in group),
                         first_pass_schema_validity=sum(a['status']=='OK' for a in first)/len(candidates) if first else None,first_pass_structural_validity=valid/len(candidates) if first else None,
                         contract_policy_validity=sum(c['evaluation']['methods']['D']['verdict']=='PASS' for c in measured)/len(candidates),
                         behavioral_correctness=sum(c['evaluation']['methods']['E']['verdict']=='PASS' for c in measured)/len(candidates),
                         selected_behavioral_correctness=sum(bool(r['candidates'][r['selected_candidate_index']]['evaluation'] and r['candidates'][r['selected_candidate_index']]['evaluation']['methods']['E']['verdict']=='PASS') for r in group)/len(group),
                         graph_complexity=[dict(nodes=len(c['workflow']['nodes']),edges=len(c['workflow']['edges'])) for c in measured],models=sorted({call['model'] for call in all_calls}),
                         latency_ms=sum(r['generation_metrics']['latency_ms'] for r in group),prompt_tokens=tokens('prompt_tokens'),completion_tokens=tokens('completion_tokens'),
                         original_latency_ms=sum(call.get('original_latency_ms',call.get('latency_ms',0)) for call in all_calls),original_prompt_tokens=tokens('prompt_tokens',True),original_completion_tokens=tokens('completion_tokens',True)))
    for strategy in ['direct','hierarchical','multi-candidate']:
        if not any(row['strategy']==strategy for row in rows):
            rows.append(dict(strategy=strategy,status='UNMEASURED',model=None,prompt_version=None,configuration={},returned_workflows=0,case_ids=[],requests=0,attempts=0,actual_inference_calls=0,cached_calls=0,
                             first_pass_schema_validity=None,first_pass_structural_validity=None,contract_policy_validity=None,behavioral_correctness=None,selected_behavioral_correctness=None,graph_complexity=[],models=[],
                             latency_ms=None,original_latency_ms=None,prompt_tokens=None,completion_tokens=None,original_prompt_tokens=None,original_completion_tokens=None))
    return rows


def write_report(results,output_dir=None):
    out=Path(output_dir or ROOT/'outputs');out.mkdir(parents=True,exist_ok=True)
    results['generation_comparison']=generation_comparison(results.get('generation_runs',[]))
    results['actual_language_comparison']={lang:[dict(case_id=r['case_id'],strategy=r['strategy'],candidates=r['candidate_count'],
        model=(r['candidates'][0]['calls'][0]['model'] if r['candidates'] and r['candidates'][0]['calls'] else None),
        contract_passes=sum(bool(c.get('evaluation') and c['evaluation']['methods']['D']['verdict']=='PASS') for c in r['candidates']),
        behavioral_passes=sum(bool(c.get('evaluation') and c['evaluation']['methods']['E']['verdict']=='PASS') for c in r['candidates'])) for r in results.get('generation_runs',[]) if r['language']==lang] for lang in ['en','vi']}
    entries=[]
    for row in results['references']+results['mutations']:
        key=row['case_id']+'--'+row.get('mutation_id','reference');issues=row['evaluation']['methods']['D']['evidence'];svg=graph_svg(row['workflow'],issues)
        path=out/'graphs'/f'{key}.svg';path.parent.mkdir(exist_ok=True);path.write_text(svg)
        case=get_case(row['case_id']);sop=sop_for(case)
        entries.append(dict(key=key,case_id=row['case_id'],label=key,language=row['language'],kind='reference demonstration' if 'mutation_id' not in row else 'controlled mutation',
                            introduced_error=row.get('introduced_error','Independently authored source-derived reference'),expected_valid=row.get('expected_valid',True),responsible=row.get('responsible',[]),svg=svg,
                            issues=issues,requirements=row['evaluation']['methods']['C']['evidence'],fixtures=row['evaluation']['methods']['E']['evidence'],methods={k:v['verdict'] for k,v in row['evaluation']['methods'].items()},
                            source_ids=case['source_ids'],scope=sop['scope'],assumptions=sop['simulation_assumptions']))
    for group in results.get('generation_runs',[]):
        for c in group['candidates']:
            if not c.get('workflow') or not c.get('evaluation'):continue
            key=f'{c["case_id"]}--{group["strategy"]}-{digest(c["calls"][0]["configuration"])[:8]}-{c["candidate_index"]}';ev=c['evaluation'];svg=graph_svg(c['workflow'],ev['methods']['D']['evidence'])
            save(out/'graphs'/f'{key}.json',c['workflow']);(out/'graphs'/f'{key}.svg').write_text(svg)
            entries.append(dict(key=key,case_id=c['case_id'],label=key,language=c['language'],kind='actual Ollama output',introduced_error='No injected mutation',expected_valid=None,responsible=[],svg=svg,
                                issues=ev['methods']['D']['evidence'],requirements=ev['methods']['C']['evidence'],fixtures=ev['methods']['E']['evidence'],methods={k:v['verdict'] for k,v in ev['methods'].items()},source_ids=get_case(c['case_id'])['source_ids'],scope='Generated workflow',assumptions=[]))
    save(out/'results.json',results)
    source_rows=load('data/sources.json')+load('docs/supplemental-sources.json')
    data=dict(entries=entries,summary=results['evaluation_summary'],incremental=results['incremental_value'],generation=results['generation_comparison'],language=results['language_comparison'],
              actual_language=results['actual_language_comparison'],matched_generation=results.get('generation_matched_subset',[]),sources=source_rows,judge_agreement=results.get('judge_agreement'),ollama=results.get('ollama_benchmark') or results.get('doctor'),limitations=results['limitations'])
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    document=HTML.replace('/*PAYLOAD*/',payload)
    (out/'report.html').write_text(document,encoding='utf-8')
    total=sum(len(r['evaluation']['methods']['E']['evidence']) for r in results['references'])
    lines=['# Genie measured experiment','',f'Reference demonstrations: {len(results["references"])} cases, {total} fixtures; behavioral pass rate {results["reference_behavioral_pass_rate"]:.1%}.',
           f'Controlled variants: {len(results["mutations"])} (includes valid equivalent graphs).','',
           '| Configuration | Detected invalid / total | False accept | False reject | Unknown |','|---|---:|---:|---:|---:|']
    for k,t in results['evaluation_summary'].items():lines.append(f'| {k} | {t["detected_errors"]}/{t["invalid_total"]} | {t["false_acceptance"]} | {t["false_rejection"]} | {t["unknown"]} |')
    lines += ['', 'UNKNOWN is not PASS or FAIL. Semantic tone items remain unresolved without review. B5 judge was disabled in the reference comparison.', '',
              '## Actual generation', '', *[f'- {r["strategy"]} / {r["model"] or "no model run"} / {r["prompt_version"] or "unmeasured"}: {r["status"]}; cases={len(r["case_ids"])}, requests={r["requests"]}, workflow attempts={r["attempts"]}, first-pass structural={r["first_pass_structural_validity"]}, behavioral={r["behavioral_correctness"]}, selected behavioral={r["selected_behavioral_correctness"]}, new prompt/completion tokens={r["prompt_tokens"]}/{r["completion_tokens"]}.' for r in results['generation_comparison']], '',
              'Reference bilingual results only test the shared simulator oracle, not model multilingual ability.', '',
              '## Recommendation', '', 'Port the JSON contracts, fixed capabilities, policy gates, runner and independent fixtures first. Add metamorphic pairs where ordinary fixtures leave gaps. Glossary is a diagnostic only. Keep selective semantic judging and extra candidates opt-in until measured gains justify their inference cost.', '',
              '## Limits', '', *['- '+x for x in results['limitations']], '',
              'See `results.json` for exact configuration, per-fixture traces, per-error detection, wall latency and token nulls; see `docs/02-sources-and-provenance.md` for sources.']
    (out/'summary.md').write_text('\n'.join(lines)+'\n')
    return dict(html=str(out/'report.html'),json=str(out/'results.json'),summary=str(out/'summary.md'),svg_count=len(entries))


HTML='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Genie · Workflow verification lab</title><style>
:root{color-scheme:light;--ink:#142d3c;--muted:#526571;--line:#d4e0e4;--green:#166e43}*{box-sizing:border-box}body{margin:0;background:#f3f6f7;color:var(--ink);font:15px/1.55 system-ui,sans-serif}header{padding:30px 5%;background:#153e50;color:white}header h1{margin:5px 0;font-size:30px}header p{max-width:850px}main{max-width:1450px;margin:auto;padding:24px}section,.panel{background:white;border:1px solid var(--line);border-radius:12px;padding:22px;margin-bottom:22px}h2{font-size:21px;margin:0 0 14px}h3{font-size:16px}p{margin:10px 0}.subtle{color:var(--muted)}.badge{display:inline-block;padding:3px 9px;border-radius:4px;background:#e7eff3;margin:3px}.PASS{color:#12643b}.FAIL{color:#ad2424}.UNKNOWN{color:#906100}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line);vertical-align:top}th{background:#edf3f5}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f1f5f6;padding:12px;font-size:12px}select{padding:10px;max-width:100%;font:inherit;border:1px solid #9badb5;border-radius:6px}label{display:block;margin:10px 0}.grid{display:grid;grid-template-columns:minmax(360px,0.9fr) minmax(430px,1.1fr);gap:20px}.graph{max-height:650px;overflow:auto;border:1px solid var(--line);background:#fff}.graph svg{display:block;margin:auto}.scroll{overflow:auto}.warning{border-left:4px solid #d29626;padding-left:12px}a{color:#145e85}li{margin:5px 0}@media(max-width:900px){.grid{display:block}main{padding:12px}section{padding:15px}header h1{font-size:24px}}details summary{cursor:pointer;font-weight:600}
</style></head><body><header><span>GENIE / PYTHON EXPERIMENT</span><h1>Which checks catch workflow errors?</h1><p>Source-derived Helpdesk demonstrations, controlled mutations and measured evaluation layers. Reference results and actual model generation are reported separately.</p></header><main>
<section><h2>Evidence and boundaries</h2><p class="warning">This is a small synthetic snapshot suite adapted from published descriptions. It is not an official Zendesk/n8n dataset. UNKNOWN remains unresolved. B5 has no measured judge improvement unless a real judge ran.</p><div id="overview"></div><details><summary>Ollama availability</summary><pre id="ollama"></pre></details></section>
<section><h2>Evaluation comparison · B0–B5</h2><p class="subtle">B0 schema/graph; B1 adds glossary; B2 adds contracts/policies/checklist; B3 adds execution; B4 adds metamorphic inputs; B5 adds optional semantic judge. These evaluate validators, not generator improvement. Timing reuses shared measured components and is not an isolated performance benchmark.</p><div class="scroll" id="comparison"></div><details><summary>Detection by injected error type</summary><div class="scroll" id="errors"></div></details><details><summary>Incremental detections</summary><pre id="incremental"></pre></details></section>
<section><h2>Generation comparison · separate experiment</h2><p class="subtle">No inference numbers are inferred from reference graphs. Failed/unavailable model attempts remain failures. Candidate-level success and selected-candidate success have different denominators.</p><div class="scroll" id="generation"></div><details><summary>Matched-case strategy comparison (cache and original costs labeled)</summary><pre id="matched-generation"></pre></details><details><summary>Exact generation configurations and case coverage</summary><pre id="generation-config"></pre></details><details><summary>Judge agreement and ablation cost</summary><pre id="judge-agreement"></pre></details></section>
<section><h2>English and Vietnamese</h2><div class="scroll" id="language"></div><p class="subtle">Vietnamese prompts share the corresponding English oracle. Author-drafted translation has no independent bilingual human review. Reference success does not imply equal model performance.</p></section>
<section><h2>Inspect a workflow and execution</h2><label>Workflow <select id="workflow"></select></label><label>Fixture <select id="fixture"></select></label><div id="identity"></div><div id="badges"></div><div class="grid"><div><h3>Graph · green marks the executed path</h3><div class="graph" id="graph"></div><details><summary>Validation issues</summary><pre id="issues"></pre></details></div><div><h3>Expected and observed behavior</h3><div id="failures"></div><details open><summary>Final state</summary><pre id="final"></pre></details><details><summary>Expected state</summary><pre id="expected"></pre></details></div></div><h3>Execution trace</h3><div class="scroll" id="trace"></div><h3>Checklist and source evidence</h3><div id="requirements"></div></section>
<section><h2>Keyword coverage can pass incorrect behavior</h2><div id="keyword-example"></div></section>
<section><h2>Sources and limitations</h2><ul id="limits"></ul><div id="sources"></div></section></main><script>
const data=/*PAYLOAD*/;
const $=id=>document.getElementById(id);const h=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=x=>x===null||x===undefined?'unmeasured':typeof x==='number'?Number.isInteger(x)?String(x):x.toFixed(3):String(x);
function table(headers,rows){return '<table><thead><tr>'+headers.map(x=>'<th>'+h(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(x=>'<td>'+h(fmt(x))+'</td>').join('')+'</tr>').join('')+'</tbody></table>'}
$('overview').textContent=data.entries.filter(x=>x.kind==='reference demonstration').length+' reference language cases · '+data.entries.filter(x=>x.kind==='controlled mutation').length+' controlled variants · zero external report assets';
$('ollama').textContent=JSON.stringify(data.ollama,null,2);
$('comparison').innerHTML=table(['Layer','Detected / invalid','True accept','False accept','True reject','False reject','Unknown','Behavioral pass rate*','ms','Prompt tokens','Completion tokens'],Object.entries(data.summary).map(([k,v])=>[k,v.detected_errors+'/'+v.invalid_total,v.true_acceptance,v.false_acceptance,v.true_rejection,v.false_rejection,v.unknown,(data.entries.filter(e=>e.kind==='controlled mutation'&&e.methods.E==='PASS').length/data.entries.filter(e=>e.kind==='controlled mutation').length).toFixed(3),v.elapsed_ms,v.prompt_tokens,v.completion_tokens]));
$('comparison').insertAdjacentHTML('beforeend','<p class="subtle">*Same candidate suite, independently executed E verdict; layers do not change workflows. B5 null tokens mean disabled/unmeasured, not zero-cost inference.</p>');
$('errors').innerHTML=table(['Layer','Mutation','Detected','Total','Unknown'],Object.entries(data.summary).flatMap(([k,v])=>Object.entries(v.by_error_type).map(([m,t])=>[k,m,t.detected,t.total,t.unknown])));
$('incremental').textContent=JSON.stringify(data.incremental,null,2);
$('generation').innerHTML=table(['Strategy / model / prompt','Status','Cases','Requests','Returned workflows','Workflow attempts','New inference calls','Cache hits','First-pass schema shape','First-pass graph','Contract/policy','Behavioral','Selected behavioral','Models','Complexity nodes/edges','ms','Prompt tokens','Completion tokens'],data.generation.map(r=>[r.strategy+' / '+fmt(r.model)+' / '+fmt(r.prompt_version),r.status,r.case_ids.join(', '),r.requests,r.returned_workflows,r.attempts,r.actual_inference_calls,r.cached_calls,r.first_pass_schema_validity,r.first_pass_structural_validity,r.contract_policy_validity,r.behavioral_correctness,r.selected_behavioral_correctness,r.models.join(', '),r.graph_complexity.map(x=>x.nodes+'/'+x.edges).join(', '),r.latency_ms,r.prompt_tokens,r.completion_tokens]));
$('matched-generation').textContent=JSON.stringify(data.matched_generation,null,2);$('generation-config').textContent=JSON.stringify(data.generation,null,2);$('judge-agreement').textContent=JSON.stringify(data.judge_agreement,null,2);
$('language').innerHTML=table(['Language','Reference cases','Reference fixtures','Reference passed','Actual candidate requests','Actual contract passes','Actual behavior passes'],Object.entries(data.language).map(([k,v])=>[k,v.cases,v.fixtures,v.passed_fixtures,data.actual_language[k].reduce((s,r)=>s+r.candidates,0),data.actual_language[k].reduce((s,r)=>s+r.contract_passes,0),data.actual_language[k].reduce((s,r)=>s+r.behavioral_passes,0)]));
$('language').insertAdjacentHTML('beforeend','<details><summary>Actual language results by model/case/strategy</summary><pre>'+h(JSON.stringify(data.actual_language,null,2))+'</pre></details>');
$('workflow').innerHTML=data.entries.map((e,i)=>'<option value="'+i+'">'+h(e.label)+'</option>').join('');
function render(){const e=data.entries[Number($('workflow').value)];const f=e.fixtures[Number($('fixture').value)||0];$('identity').innerHTML='<p><b>'+h(e.kind)+'</b> · '+h(e.language)+' · '+h(e.scope)+'</p><p>'+h(e.introduced_error)+'</p><p class="subtle">Responsible or affected nodes: '+h(e.responsible.join(', ')||e.issues.map(i=>i.node_id).filter(Boolean).join(', ')||'graph-level issue or no injected fault')+'</p>';
$('badges').innerHTML=Object.entries(e.methods).map(([k,v])=>'<span class="badge '+h(v)+'">'+h(k)+': '+h(v)+'</span>').join('');$('graph').innerHTML=e.svg;$('issues').textContent=JSON.stringify(e.issues,null,2);
const trace=f.execution.trace;const visited=new Set(trace.map(t=>t.node_id));const taken=new Set(trace.filter(t=>t.selected_edge).map(t=>t.selected_edge.source+':'+t.selected_edge.port+':'+t.selected_edge.target));
$('graph').querySelectorAll('[data-node]').forEach(n=>{if(visited.has(n.dataset.node))n.classList.add('executed')});$('graph').querySelectorAll('[data-edge]').forEach(n=>{if(taken.has(n.dataset.edge))n.classList.add('executed')});
$('final').textContent=JSON.stringify(f.execution.state,null,2);$('expected').textContent=JSON.stringify({state:f.expected_state,trace:f.expected_trace_constraints,forbidden:f.forbidden_effects},null,2);
$('failures').innerHTML='<p class="'+h(f.verdict)+'"><b>'+h(f.verdict)+'</b></p>'+ (f.failures.length?'<ul>'+f.failures.map(x=>'<li>'+h(x)+'</li>').join('')+'</ul>':'<p>All bounded fixture assertions passed.</p>');
$('trace').innerHTML=table(['Step','Node/type','Operation','Changes','Selected edge','Error'],trace.map(t=>[t.step_index,t.node_id+' / '+t.node_type,t.operation,JSON.stringify(t.state_changes),JSON.stringify(t.selected_edge),t.error||'']));
$('requirements').innerHTML=e.requirements.map(r=>'<details><summary class="'+h(r.verdict)+'">'+h(r.requirement_id)+' · '+h(r.verdict)+' · '+h(r.description)+'</summary><p>Expected evidence: '+h(r.expected_evidence)+'</p><p>Sources: '+r.source_ids.map(id=>{const s=data.sources.find(x=>x.source_id===id);return '<a href="'+h(s.url)+'">'+h(s.title)+'</a> ('+h(s.relevant_section)+')'}).join(', ')+'</p><pre>'+h(JSON.stringify(r.evidence,null,2))+'</pre></details>').join('');}
function changeWorkflow(){const e=data.entries[Number($('workflow').value)];$('fixture').innerHTML=e.fixtures.map((f,i)=>'<option value="'+i+'">'+h(f.fixture_id)+' · '+h(f.verdict)+'</option>').join('');render()}
$('workflow').addEventListener('change',changeWorkflow);$('fixture').addEventListener('change',render);changeWorkflow();
const kw=data.entries.find(e=>e.label.endsWith('swapped_branches')&&e.methods.B==='PASS'&&e.methods.E==='FAIL');$('keyword-example').innerHTML=kw?'<p>'+h(kw.label)+': glossary PASS, behavior FAIL. Operation names survive the branch swap; independent inputs expose the wrong effects.</p><button id="show-kw">Inspect this failure</button>':'<p>No keyword false-positive example found.</p>';if(kw)$('show-kw').onclick=()=>{$('workflow').value=data.entries.indexOf(kw);changeWorkflow();$('workflow').scrollIntoView({behavior:'smooth'})};
$('limits').innerHTML=data.limitations.map(x=>'<li>'+h(x)+'</li>').join('');$('sources').innerHTML=data.sources.map(s=>'<details><summary>'+h(s.source_id)+' · '+h(s.access_status)+' · '+h(s.title)+'</summary><p><a href="'+h(s.url)+'">'+h(s.publisher)+'</a> · '+h(s.relevant_section)+'</p><p>'+h(s.establishes)+'</p><p class="subtle">'+h(s.limitations)+'</p></details>').join('');
</script></body></html>'''
