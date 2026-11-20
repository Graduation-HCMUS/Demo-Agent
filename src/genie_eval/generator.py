"""Zero-shot and hierarchical generation using Ollama's local structured-output API."""
import json
import os
import time
import urllib.request
import uuid
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
from .models import ROOT, WORKFLOW_SCHEMA, obj, STR, schema_errors, digest, save, load,parse_json,reject_constant
from .catalog import catalog
from .validators import validate

PROMPT_VERSION='genie-zero-shot-v2'


def settings(model=None, **overrides):
    result=dict(model=model or os.getenv('GENIE_MODEL','qwen3.5:9b'),host=os.getenv('OLLAMA_HOST','http://127.0.0.1:11434'),
                timeout=float(os.getenv('GENIE_TIMEOUT','120')),num_predict=int(os.getenv('GENIE_NUM_PREDICT','4096')),num_ctx=int(os.getenv('GENIE_NUM_CTX','16384')),temperature=0,seed=17,retries=0,cache=True)
    result.update({k:v for k,v in overrides.items() if v is not None})
    if result['retries']<0 or result['num_ctx']<1024 or result['num_predict']<1 or result['timeout']<=0:
        raise ValueError('Invalid retry, token-budget or timeout configuration')
    parsed=urlparse(result['host'])
    if parsed.scheme!='http' or parsed.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('Only a local HTTP Ollama host is supported; no paid/cloud inference')
    return result


def http_json(host,path,payload=None,timeout=5):
    request=urllib.request.Request(host.rstrip('/')+path,data=None if payload is None else json.dumps(payload).encode(),
                                   headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        return json.load(response,parse_constant=reject_constant)


def doctor(config=None,transport=http_json):
    config=config or settings();start=time.perf_counter()
    try:
        data=transport(config['host'],'/api/tags',timeout=min(config['timeout'],10))
        models=[dict(name=m.get('name',m.get('model')),digest=m.get('digest'),size=m.get('size'),details=m.get('details')) for m in data.get('models',[])]
        installed=next((m for m in models if m['name']==config['model']),None)
        return dict(status='READY' if installed else 'MODEL_MISSING',server_available=True,requested_model=config['model'],installed_models=models,
                    selected_model=installed,elapsed_ms=(time.perf_counter()-start)*1000,error=None if installed else 'Requested model not installed; no automatic download.')
    except (OSError,ValueError,TimeoutError) as exc:
        return dict(status='UNAVAILABLE',server_available=False,requested_model=config['model'],installed_models=[],selected_model=None,
                    elapsed_ms=(time.perf_counter()-start)*1000,error=str(exc))


def compact_sop(sop):
    keys=['sop_id','scope','trigger','inputs','ordered_activities','decision_conditions','forbidden_actions','simulation_assumptions','limitations']
    return {k:sop[k] for k in keys}


def compact_catalog(sop=None):
    # Relevant tools are selected from normative SOP requirements, never hidden fixtures.
    names=None if sop is None else {'notify'} | {op for r in sop['source_backed_requirements'] for op in r['operations']}
    return [{k:c[k] for k in ['name','description','argument_schema','required_inputs','produced_outputs','preconditions']} for c in catalog(names)]


def build_prompt(case,sop):
    # Deliberately whitelist: no case oracle, fixtures, reference graph, metamorphic pairs.
    context=dict(prompt_version=PROMPT_VERSION,user_request=case['user_request'],language=case['language'],sop=compact_sop(sop),capabilities=compact_catalog(sop),schema=WORKFLOW_SCHEMA)
    instructions=('Return only a JSON workflow for this request. Use one input, terminal outputs and a DAG. '
                  'custom config is {operation,args}; condition config is {field,operator,value}; condition edges use true/false, other edges next. '
                  'Reference state as {"ref":"field"}. Check preconditions along every path. Input fields may be absent: validate_fields handles absence. '
                  'Use only registered operations; do not execute code. file runtime unsupported. '
                  'No demonstrations, reference workflow or test fixtures are supplied. Do not invent business policies.\n')
    return instructions+json.dumps(context,ensure_ascii=False,separators=(',',':'))


def structured_call(prompt,schema,config,kind,transport=http_json,cache_dir=None):
    started=time.perf_counter();probe=doctor(config,transport)
    base=dict(kind=kind,model=config['model'],model_digest=(probe.get('selected_model') or {}).get('digest'),configuration={k:v for k,v in config.items() if k!='cache'},
              prompt_version=PROMPT_VERSION,prompt_hash=digest(prompt),schema_hash=digest(schema),cached=False,prompt_tokens=None,completion_tokens=None,latency_ms=0,
              raw_response=None,parsed=None,validation_errors=[],attempts=[],status=probe['status'],doctor=probe)
    if probe['status']!='READY':
        base['error']=probe['error'];base['latency_ms']=(time.perf_counter()-started)*1000;return base
    request_id=uuid.uuid4().hex
    base.update(request_id=request_id,started_at=datetime.now(timezone.utc).isoformat())
    key=digest(dict(model=config['model'],model_digest=base['model_digest'],prompt=prompt,schema=schema,config={k:v for k,v in config.items() if k not in ['cache','host']}))
    cache_root=Path(cache_dir or ROOT/'outputs/cache');cache_file=cache_root/(key+'.json')
    if config['cache'] and cache_file.exists():
        base=load(cache_file)
        base.update(cached=True,original_latency_ms=base['latency_ms'],original_prompt_tokens=base['prompt_tokens'],original_completion_tokens=base['completion_tokens'],
                    latency_ms=(time.perf_counter()-started)*1000,prompt_tokens=0,completion_tokens=0)
        return base
    request_file=cache_root/'requests'/f'{request_id}.json'
    save(request_file,dict(request_id=request_id,status='STARTED',model=config['model'],configuration=base['configuration'],prompt_hash=base['prompt_hash'],prompt=prompt,started_at=base['started_at']))
    base['request_record']=str(request_file)
    payload=dict(model=config['model'],messages=[dict(role='user',content=prompt)],format=schema,stream=False,think=False,
                 options=dict(temperature=config['temperature'],seed=config['seed'],num_predict=config['num_predict'],num_ctx=config['num_ctx']))
    # Each attempt is durably saved before retry; no repair demonstrations introduced.
    for index in range(config['retries']+1):
        attempt=dict(attempt_index=index,raw_response=None,parsed=None,validation_errors=[],prompt_tokens=None,completion_tokens=None,status='ERROR')
        call_start=time.perf_counter()
        try:
            response=transport(config['host'],'/api/chat',payload,timeout=config['timeout'])
            if response.get('error'):raise ValueError(response['error'])
            attempt['raw_response']=response.get('message',{}).get('content','')  # Never retain message.thinking.
            attempt['prompt_tokens']=response.get('prompt_eval_count');attempt['completion_tokens']=response.get('eval_count')
            attempt['server_total_duration_ns']=response.get('total_duration');attempt['done_reason']=response.get('done_reason')
            attempt['parsed']=parse_json(attempt['raw_response'])
            attempt['validation_errors']=schema_errors(attempt['parsed'],schema)
            attempt['status']='INVALID' if attempt['validation_errors'] else 'OK'
        except (OSError,ValueError,TypeError,TimeoutError,RecursionError) as exc:
            attempt['error']=str(exc)
        attempt['latency_ms']=(time.perf_counter()-call_start)*1000
        base['attempts'].append(attempt)
        save(cache_root/'attempts'/f'{key}-{request_id}-{index}.json',dict(prompt_hash=base['prompt_hash'],model=config['model'],**attempt))
        if attempt['status']=='OK':break
    final=base['attempts'][-1];base.update({k:final[k] for k in ['raw_response','parsed','validation_errors','status']})
    base['first_pass_status']=base['attempts'][0]['status']
    for metric in ['prompt_tokens','completion_tokens']:
        values=[a[metric] for a in base['attempts']]
        base[metric]=sum(values) if all(v is not None for v in values) else None
    base['latency_ms']=(time.perf_counter()-started)*1000
    if final.get('error'):base['error']=final['error']
    save(cache_file,base)
    save(request_file,dict(request_id=request_id,status=base['status'],model=config['model'],configuration=base['configuration'],prompt_hash=base['prompt_hash'],prompt=prompt,started_at=base['started_at'],completed_at=datetime.now(timezone.utc).isoformat(),result_file=str(cache_file)))
    return base


ITEM_SCHEMA=obj({'id':STR,'business_intent':STR,'required_inputs':{'type':'array','items':STR},'expected_outputs':{'type':'array','items':STR},
                 'dependencies':{'type':'array','items':STR},'candidate_capabilities':{'type':'array','items':STR},'requirement_ids':{'type':'array','items':STR,'minItems':1}})
PLAN_SCHEMA=obj({'items':{'type':'array','items':ITEM_SCHEMA,'minItems':1,'maxItems':24}})


def check_plan(plan,sop,phase=None):
    ids=[x['id'] for x in plan['items']];known={r['requirement_id'] for r in sop['source_backed_requirements']};caps={c['name'] for c in catalog()};errors=[]
    if len(ids)!=len(set(ids)):errors.append('PLAN_DUPLICATE_ID')
    visited=set()
    for item in plan['items']:
        if set(item['dependencies'])-visited:errors.append(f'PLAN_DEPENDENCY: {item["id"]}')
        if set(item['requirement_ids'])-known:errors.append(f'PLAN_PROVENANCE: {item["id"]}')
        if set(item['candidate_capabilities'])-caps:errors.append(f'PLAN_CAPABILITY: {item["id"]}')
        visited.add(item['id'])
    if known-set(r for x in plan['items'] for r in x['requirement_ids']):errors.append('PLAN_REQUIREMENT_COVERAGE')
    if phase=='capability_mapping':
        mapped={c for item in plan['items'] for c in item['candidate_capabilities']}
        required={op for r in sop['source_backed_requirements'] for op in r['operations']}
        if required-mapped:errors.append(f'PLAN_MAPPING_MISSING: {sorted(required-mapped)}')
        forbidden={p['operation'] for p in sop.get('forbidden_actions',[]) if p['kind']=='forbid_operation'}
        if mapped & forbidden:errors.append(f'PLAN_POLICY_FORBIDDEN: {sorted(mapped & forbidden)}')
    return errors


def generate(case,sop,config=None,strategy='direct',planner_model=None,detail_model=None,transport=http_json,cache_dir=None):
    config=config or settings();prompt=build_prompt(case,sop);calls=[];plans=[]
    if strategy not in ['direct','hierarchical']:raise ValueError(f'Unsupported generation strategy: {strategy}')
    if strategy=='hierarchical':
        for phase,model in [('high_level_stages',planner_model or config['model']),('detailed_activities',detail_model or config['model']),('capability_mapping',detail_model or config['model'])]:
            task=dict(phase=phase,request=case['user_request'],sop=compact_sop(sop),requirements=[{k:r[k] for k in ['requirement_id','description']} for r in sop['source_backed_requirements']],
                      prior_plans=plans,capabilities=compact_catalog(sop),schema=PLAN_SCHEMA)
            r=structured_call('Produce a dependency-ordered JSON plan. Preserve requirement IDs and stable item IDs where refining an existing item.\n'+json.dumps(task,ensure_ascii=False),PLAN_SCHEMA,{**config,'model':model},phase,transport,cache_dir)
            calls.append(r)
            errors=check_plan(r['parsed'],sop,phase) if r['status']=='OK' else []
            if errors:r['status']='INVALID';r['validation_errors']+=errors
            if r['status']!='OK':return dict(case_id=case['case_id'],language=case['language'],strategy=strategy,status=r['status'],workflow=None,calls=calls,plans=plans)
            plans.append(dict(phase=phase,**r['parsed']))
        prompt+='\nPlanner output (no completed workflow): '+json.dumps(plans,ensure_ascii=False)
    final=structured_call(prompt,WORKFLOW_SCHEMA,config,'workflow',transport,cache_dir);calls.append(final)
    workflow=final['parsed'] if final['status']=='OK' else None
    errors=validate(workflow,sop) if workflow is not None else final['validation_errors']
    return dict(case_id=case['case_id'],language=case['language'],strategy=strategy,status=('INVALID_WORKFLOW' if workflow is not None and errors else final['status']),workflow=workflow,validation_errors=errors,calls=calls,plans=plans,
                language_translation='none',same_model_planning=(planner_model or config['model'])==(detail_model or config['model'])==config['model'])
