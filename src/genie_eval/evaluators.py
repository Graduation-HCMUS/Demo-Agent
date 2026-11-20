"""Independently callable glossary, checklist, contract, scenario, metamorphic layers."""
import json
import time
from .models import load,WORKFLOW_SCHEMA,schema_errors
from .runner import run
from .validators import validate
from .catalog import REGISTRY


def aggregate(verdicts):
    verdicts=list(verdicts)
    return 'FAIL' if 'FAIL' in verdicts else ('UNKNOWN' if 'UNKNOWN' in verdicts or not verdicts else 'PASS')


def result(method, verdict, evidence, started):
    return dict(method=method,verdict=verdict,evidence=evidence,elapsed_ms=(time.perf_counter()-started)*1000,prompt_tokens=0,completion_tokens=0)


def glossary(workflow,case):
    started=time.perf_counter();text=json.dumps(workflow,ensure_ascii=False).casefold();items=[]
    for term in load('data/glossary.json'):
        if set(term['related_capabilities']) & set(case['expected_capabilities']):
            aliases=[term['canonical_term'],*term['english_aliases'],*term['vietnamese_aliases'],*term['related_capabilities']]
            found=[a for a in aliases if a.casefold() in text]
            items.append(dict(term=term['canonical_term'],matched=found,verdict='PASS' if found else 'FAIL'))
    return result('B',aggregate(x['verdict'] for x in items),items,started)


def contracts(workflow,case,sop,structural_only=False):
    started=time.perf_counter();findings=validate(workflow,sop,contracts=not structural_only)
    return result('B0' if structural_only else 'D','FAIL' if findings else 'PASS',findings,started)


def subset_errors(expected,actual,path='state'):
    errors=[]
    if isinstance(expected,dict):
        if not isinstance(actual,dict):return [f'{path}: expected object, observed {actual!r}']
        for k,v in expected.items():
            if k not in actual:errors.append(f'{path}.{k}: missing; expected {v!r}')
            else:errors += subset_errors(v,actual[k],f'{path}.{k}')
    elif type(expected) is not type(actual) or expected!=actual:
        errors.append(f'{path}: expected {expected!r}; observed {actual!r}')
    return errors


def check_execution(execution,fixture,case):
    failures=[];trace=execution['trace'];effects=execution['state']['effects'];constraints=fixture.get('expected_trace_constraints',{})
    if execution['status']!='OK':failures.append(f'Execution {execution["status"]}: {execution["errors"]}')
    failures+=subset_errors(fixture.get('expected_state',{}),execution['state'])
    for op in constraints.get('required_actions',[]):
        if op not in effects:failures.append(f'Required action missing: {op}')
    for op in set(fixture.get('forbidden_effects',[])+case.get('forbidden_effects',[])):
        if op in effects:failures.append(f'Forbidden action observed: {op}')
    for a,b in constraints.get('action_order',[]):
        if a not in effects or b not in effects or effects.index(a)>=effects.index(b):failures.append(f'Expected action order: {a} before {b}; observed {effects}')
    for field,wanted in constraints.get('branches',{}).items():
        branches=[t for t in trace if t['node_type']=='condition' and (t.get('condition') or {}).get('field')==field]
        if not any(t['selected_edge'] and t['selected_edge']['port']==wanted for t in branches):failures.append(f'Expected branch {field}: {wanted}')
    for c in case.get('shared_trace_constraints',[]):
        for t in trace:
            if t['operation']!=c['when_action']:continue
            if c.get('when_ticket_created') and not t['input_snapshot'].get('ticket_created'):continue
            if c['require_notice'] not in t['input_snapshot'].get('messages',[]):
                failures.append(f'{t["node_id"]}: {c["require_notice"]} must precede {c["when_action"]}')
    return failures


def scenarios(workflow,case,sop):
    started=time.perf_counter();evidence=[]
    for fixture in case['input_fixtures']:
        execution=run(workflow,fixture['input'],sop)
        failures=check_execution(execution,fixture,case)
        evidence.append(dict(fixture_id=fixture['fixture_id'],expected_state=fixture['expected_state'],expected_trace_constraints=fixture['expected_trace_constraints'],
                             forbidden_effects=fixture['forbidden_effects'],execution=execution,failures=failures,verdict='FAIL' if failures else 'PASS'))
    return result('E',aggregate(x['verdict'] for x in evidence),evidence,started)


def checklist(workflow,case,execution_result=None):
    started=time.perf_counter();items=[]
    shape_errors=schema_errors(workflow,WORKFLOW_SCHEMA)
    if shape_errors:
        return result('C','FAIL',[dict(r,verdict='FAIL',evidence=shape_errors) for r in case['requirements']],started)
    operations={n.get('config',{}).get('operation') for n in workflow.get('nodes',[]) if isinstance(n,dict)} if isinstance(workflow,dict) else set()
    for requirement in case['requirements']:
        item=dict(requirement);missing=set(item['operations'])-operations
        unsupported=operations-{None}-set(REGISTRY)
        if unsupported:
            verdict='FAIL';evidence=[f'Unsupported operations: {sorted(unsupported)}']
        elif missing:
            verdict='FAIL';evidence=[f'Missing required operations: {sorted(missing)}']
        elif item['evaluation_method']=='semantic':
            verdict='UNKNOWN';evidence=['Symbolic messages cannot establish tone or intent; optional judge or human review needed.']
        elif execution_result is None:
            verdict='UNKNOWN';evidence=['Operation names present; execution evidence not supplied.']
        else:
            verdict=execution_result['verdict'];evidence=[dict(fixture_id=e['fixture_id'],verdict=e['verdict'],failures=e['failures']) for e in execution_result['evidence']]
        item.update(verdict=verdict,evidence=evidence);items.append(item)
    return result('C',aggregate(x['verdict'] for x in items),items,started)


def metamorphic(workflow,case,sop):
    started=time.perf_counter();evidence=[]
    for rel in case['metamorphic_relations']:
        base=rel['base_input'];changed={**base,**rel['changed_fields']}
        left=run(workflow,base,sop);right=run(workflow,changed,sop)
        failures=[]
        for label,execution,expected in [('base',left,rel['expected_base']),('changed',right,rel['expected_changed'])]:
            if execution['status']!='OK':failures.append(f'{label}: {execution["status"]}: {execution["errors"]}')
            failures += subset_errors(expected,execution['state'],label)
        # Also check a real behavioral change, not graph equality or arbitrary state noise.
        observed_difference=any(left['state'].get(k)!=right['state'].get(k) for k in set(rel['expected_base'])|set(rel['expected_changed']))
        if not observed_difference:failures.append('Expected behavioral difference absent')
        evidence.append(dict(relation_id=rel['relation_id'],source_ids=rel['source_ids'],changed_fields=rel['changed_fields'],base=left,changed=right,
                             expected_base=rel['expected_base'],expected_changed=rel['expected_changed'],failures=failures,verdict='FAIL' if failures else 'PASS'))
    return result('F',aggregate(x['verdict'] for x in evidence),evidence,started)


def evaluate(workflow,case,sop,methods=('B','C','D','E','F')):
    selected=set(methods);results={}
    if 'B' in selected:results['B']=glossary(workflow,case)
    if 'D' in selected:results['D']=contracts(workflow,case,sop)
    if 'E' in selected:results['E']=scenarios(workflow,case,sop)
    if 'F' in selected:results['F']=metamorphic(workflow,case,sop)
    if 'C' in selected:results['C']=checklist(workflow,case,results.get('E'))
    return results


def layers(workflow,case,sop,judge_result=None):
    b0=contracts(workflow,case,sop,True);b=glossary(workflow,case);d=contracts(workflow,case,sop);e=scenarios(workflow,case,sop);f=metamorphic(workflow,case,sop)
    c_static=checklist(workflow,case);c_trace=checklist(workflow,case,e)
    g=judge_result or dict(method='G',verdict='UNKNOWN',evidence=[],elapsed_ms=0,prompt_tokens=None,completion_tokens=None,status='DISABLED')
    # Selective judging resolves only UNKNOWN checklist items. It never erases a FAIL.
    resolved=[]
    judge_items={x['requirement_id']:x for x in g.get('evidence',[])}
    for item in c_trace['evidence']:
        resolved.append(judge_items.get(item['requirement_id'],item)['verdict'] if item['verdict']=='UNKNOWN' else item['verdict'])
    groups={'B0':[b0],'B1':[b0,b],'B2':[b0,d,c_static],'B3':[b0,d,c_trace,e],'B4':[b0,d,c_trace,e,f],
            'B5':[b0,d,dict(c_trace,verdict=aggregate(resolved)),e,f]}
    comparison={k:dict(verdict=aggregate(x['verdict'] for x in v),elapsed_ms=sum(x['elapsed_ms'] for x in v)+(g['elapsed_ms'] if k=='B5' else 0),
                       prompt_tokens=g['prompt_tokens'] if k=='B5' else 0,completion_tokens=g['completion_tokens'] if k=='B5' else 0,
                       judge_status=g.get('status','RUN') if k=='B5' else 'NOT_APPLICABLE') for k,v in groups.items()}
    return dict(comparison=comparison,methods={'B0':b0,'B':b,'C':c_trace,'C_static':c_static,'D':d,'E':e,'F':f,'G':g})
