"""Measured reference/mutation runs and opt-in model strategy comparisons."""
import platform
import time
from datetime import datetime,timezone
from .models import cases,reference,sop_for,oracle_integrity,save,ROOT,digest
from .evaluators import layers
from .generator import generate,settings,doctor
from .mutations import variants
from .judge import judge


def metrics(calls):
    def total(k):
        values=[c.get(k) for c in calls];return sum(values) if all(v is not None for v in values) else None
    return dict(prompt_tokens=total('prompt_tokens'),completion_tokens=total('completion_tokens'),latency_ms=sum(c.get('latency_ms',0) for c in calls),
                actual_inference_calls=sum(len(c.get('attempts',[])) for c in calls if not c.get('cached')),cached_calls=sum(bool(c.get('cached')) for c in calls))


def rank_key(candidate):
    e=candidate.get('evaluation')
    if not e or not candidate.get('workflow'):return (-1,-1,-1,-1,-1)
    methods=e['methods'];hard=int(methods['D']['verdict']=='PASS')
    tests=methods['E']['evidence']+methods['F']['evidence']
    behavior=sum(x['verdict']=='PASS' for x in tests)/len(tests)
    checklist=methods['C']['evidence'];coverage=sum(x['verdict']=='PASS' for x in checklist)/len(checklist)
    unresolved={x['requirement_id'] for x in checklist if x['verdict']=='UNKNOWN'}
    judge_items=[x for x in methods['G'].get('evidence',[]) if x['requirement_id'] in unresolved]
    judge_score=sum(1 if x['verdict']=='PASS' else -1 if x['verdict']=='FAIL' else 0 for x in judge_items)
    complexity=len(candidate['workflow']['nodes'])+len(candidate['workflow']['edges'])
    return (hard,behavior,coverage,judge_score,-complexity)


def generate_candidates(case,sop,config=None,n=1,strategy='direct',use_judge=False,judge_all=False,judge_models=None,planner_model=None,detail_model=None,transport=None,cache_dir=None):
    if n not in [1,2,3]:raise ValueError('candidate count must be 1, 2 or 3')
    config=config or settings();candidates=[]
    for index in range(n):
        kwargs=dict(planner_model=planner_model,detail_model=detail_model,cache_dir=cache_dir)
        if transport is not None:kwargs['transport']=transport
        # Fixed temperature; different recorded seeds distinguish candidates/cache entries.
        generated=generate(case,sop,{**config,'seed':config['seed']+index},strategy,**kwargs)
        generated['candidate_index']=index;generated['evaluation']=None
        if generated['workflow']:
            generated['evaluation']=layers(generated['workflow'],case,sop)
            if use_judge:
                methods=generated['evaluation']['methods'];g=judge(generated['workflow'],case,sop,methods['C'],methods['E']['evidence'],config,judge_models,judge_all,transport,cache_dir)
                generated['evaluation']=layers(generated['workflow'],case,sop,g)
        generated['rank_key']=rank_key(generated);candidates.append(generated)
    selected=max(range(n),key=lambda i:candidates[i]['rank_key'])
    calls=[call for c in candidates for call in c['calls']]
    judge_calls=[call for c in candidates if c['evaluation'] for call in c['evaluation']['methods']['G'].get('calls',[])]
    winner=candidates[selected]
    # A top-ranked invalid workflow is still invalid. Selection is not approval.
    return dict(case_id=case['case_id'],language=case['language'],strategy='multi-candidate' if n>1 else strategy,candidate_count=n,candidates=candidates,
                selected_candidate_index=selected,selection_accepted=bool(winner['evaluation'] and winner['evaluation']['comparison']['B5' if use_judge else 'B4']['verdict']=='PASS'),
                generation_metrics=metrics(calls),judge_metrics=metrics(judge_calls))


def summarize(rows):
    totals={k:dict(true_acceptance=0,false_acceptance=0,true_rejection=0,false_rejection=0,unknown=0,elapsed_ms=0,prompt_tokens=0,completion_tokens=0,detected_errors=0,invalid_total=0,by_error_type={}) for k in ['B0','B1','B2','B3','B4','B5']}
    for row in rows:
        for layer,r in row['evaluation']['comparison'].items():
            t=totals[layer];v=r['verdict'];valid=row['expected_valid'];t['elapsed_ms']+=r['elapsed_ms']
            for token in ['prompt_tokens','completion_tokens']:
                if r[token] is None:t[token]=None
                elif t[token] is not None:t[token]+=r[token]
            if v=='UNKNOWN':t['unknown']+=1
            elif valid:t['true_acceptance' if v=='PASS' else 'false_rejection']+=1
            else:t['false_acceptance' if v=='PASS' else 'true_rejection']+=1
            if not valid:
                t['invalid_total']+=1
                if v=='FAIL':t['detected_errors']+=1
                err=t['by_error_type'].setdefault(row['mutation_id'],dict(total=0,detected=0,unknown=0))
                err['total']+=1;err['detected']+=v=='FAIL';err['unknown']+=v=='UNKNOWN'
    for t in totals.values():t['detection_rate']=t['detected_errors']/t['invalid_total'] if t['invalid_total'] else None
    return totals


def reference_experiment():
    started=time.perf_counter();integrity=oracle_integrity()
    if integrity['verdict']!='PASS':raise ValueError(f'Oracle lock changed: {integrity}')
    refs=[];mutants=[]
    for case in cases():
        sop=sop_for(case);w=reference(case);ev=layers(w,case,sop)
        if ev['methods']['E']['verdict']!='PASS' or ev['methods']['F']['verdict']!='PASS' or ev['methods']['D']['verdict']!='PASS':
            raise ValueError(f'Reference not independently confirmed: {case["case_id"]}')
        refs.append(dict(case_id=case['case_id'],language=case['language'],sop_id=case['sop_id'],workflow=w,evaluation=ev))
        for variant in variants(w,case):
            mutants.append(dict(case_id=case['case_id'],language=case['language'],sop_id=case['sop_id'],**variant,evaluation=layers(variant['workflow'],case,sop)))
    summary=summarize(mutants)
    language={lang:dict(cases=sum(c['language']==lang for c in refs),fixtures=sum(len(c['evaluation']['methods']['E']['evidence']) for c in refs if c['language']==lang),
                        passed_fixtures=sum(e['verdict']=='PASS' for c in refs if c['language']==lang for e in c['evaluation']['methods']['E']['evidence']),
                        interpretation='Reference demonstration only; no measured model language comparison.') for lang in ['en','vi']}
    incremental=[]
    for a,b in [('B0','B1'),('B0','B2'),('B2','B3'),('B3','B4'),('B4','B5')]:
        changed=[f'{x["case_id"]}/{x["mutation_id"]}' for x in mutants if x['evaluation']['comparison'][a]['verdict']!='FAIL' and x['evaluation']['comparison'][b]['verdict']=='FAIL']
        incremental.append(dict(from_layer=a,to_layer=b,new_rejections=changed))
    return dict(result_schema_version='1.0',created_at=datetime.now(timezone.utc).isoformat(),mode='reference',python=platform.python_version(),
                oracle_integrity=integrity,references=refs,mutations=mutants,evaluation_summary=summary,incremental_value=incremental,language_comparison=language,
                generation_runs=[],generation_comparison=[dict(strategy=s,status='UNMEASURED',attempts=0,first_pass_structural_validity=None,behavioral_correctness=None,latency_ms=None,prompt_tokens=None,completion_tokens=None) for s in ['direct','hierarchical','multi-candidate']],
                judge_agreement=None,reference_behavioral_pass_rate=sum(e['verdict']=='PASS' for r in refs for e in r['evaluation']['methods']['E']['evidence'])/sum(len(r['evaluation']['methods']['E']['evidence']) for r in refs),
                elapsed_ms=(time.perf_counter()-started)*1000,limitations=['Synthetic, source-derived snapshot suite, not an official dataset.','B2 and later preserve semantic UNKNOWN; no silent acceptance.','B5 without an enabled model judge is an unmeasured extension.','Reference bilingual success measures shared oracle plumbing, not model language ability.'])


def benchmark(config,selected_cases=None,all_methods=False,candidates=2,judge_models=None,planner_model=None,detail_model=None,transport=None,cache_dir=None,checkpoint_dir=None):
    kwargs={} if transport is None else {'transport':transport}
    probe=doctor(config,**kwargs);runs=[]
    checkpoint=ROOT/'outputs/checkpoints'/f'{digest(config)[:16]}.json' if checkpoint_dir is None and transport is None else (None if checkpoint_dir is None else checkpoint_dir)
    def record(status):
        if checkpoint is not None:save(checkpoint,dict(mode='ollama',status=status,doctor=probe,configuration=config,generation_runs=runs))
    record('STARTED')
    if probe['status']=='READY':
        for case in selected_cases or cases():
            strategies=[('direct',1)]+([('hierarchical',1),('direct',candidates)] if all_methods else [])
            for strategy,n in strategies:
                runs.append(generate_candidates(case,sop_for(case),config,n,strategy,all_methods,False,judge_models,planner_model,detail_model,transport,cache_dir))
                if all_methods:
                    for candidate in runs[-1]['candidates']:
                        if candidate['evaluation']:
                            m=candidate['evaluation']['methods'];candidate['judge_all_ablation']=judge(candidate['workflow'],case,sop_for(case),m['C'],m['E']['evidence'],config,judge_models,True,transport,cache_dir)
                record('RUNNING')
    actual_calls=sum(r['generation_metrics']['actual_inference_calls'] for r in runs)
    any_output=any(c['workflow'] for r in runs for c in r['candidates'])
    complete=bool(runs) and all(c['workflow'] is not None for r in runs for c in r['candidates'])
    record('COMPLETED' if complete else 'FAILED')
    return dict(mode='ollama',doctor=probe,status='COMPLETED' if complete else 'PARTIAL_FAILED' if any_output else 'FAILED',generation_runs=runs,actual_generation_calls=actual_calls,
                configuration=config,error=None if complete else probe.get('error') or 'Some or all generation requests failed; inspect candidate records.')


def judge_confusion(judgments):
    """Raw judge decisions versus decisive independent checklist labels, not effective hard gates."""
    totals=dict(true_acceptance=0,false_acceptance=0,true_rejection=0,false_rejection=0,unknown=0,unlabeled_items=0)
    for judgment in judgments:
        for item in judgment.get('evidence',[]):
            expected=item['deterministic_verdict'];actual=item['verdict']
            if expected=='UNKNOWN':totals['unlabeled_items']+=1
            elif actual=='UNKNOWN':totals['unknown']+=1
            elif expected=='PASS':totals['true_acceptance' if actual=='PASS' else 'false_rejection']+=1
            else:totals['false_acceptance' if actual=='PASS' else 'true_rejection']+=1
    return totals


def judge_variant_comparison(results,config,selected_case_ids=None,model_ids=None,all_items_ablation=False,transport=None,cache_dir=None):
    """Opt-in B5 on the same controlled variants; all-items G is a separate ablation."""
    selective_calls=[];ablation_calls=[];agreements=[]
    for row in results['references']+results['mutations']:
        if selected_case_ids and row['case_id'] not in selected_case_ids:continue
        case=next(c for c in cases() if c['case_id']==row['case_id']);sop=sop_for(case);m=row['evaluation']['methods']
        if all(m[k]['verdict']=='PASS' for k in ['D','E','F']):
            g=judge(row['workflow'],case,sop,m['C'],m['E']['evidence'],config,model_ids,False,transport,cache_dir)
            row['evaluation']=layers(row['workflow'],case,sop,g);selective_calls+=g.get('calls',[])
        else:
            row['evaluation']['methods']['G']['status']='SKIPPED_DETERMINISTIC_FAILURE'
        if all_items_ablation:
            g=judge(row['workflow'],case,sop,m['C'],m['E']['evidence'],config,model_ids,True,transport,cache_dir)
            row['judge_all_ablation']=g;ablation_calls+=g.get('calls',[])
            agreements.append(g.get('agreement',{}))
    results['evaluation_summary']=summarize(results['mutations'])
    results['judge_agreement']=dict(eligible_items=sum(a.get('eligible_items',0) for a in agreements),agree=sum(a.get('agree',0) for a in agreements),
        unknown_items=sum(x['verdict']=='UNKNOWN' for r in results['references']+results['mutations'] for x in r.get('judge_all_ablation',{}).get('evidence',[])),
        ablation_confusion=judge_confusion([row['judge_all_ablation'] for row in results['references']+results['mutations'] if 'judge_all_ablation' in row]),basis='All-items judge compared with independent deterministic checklist/fixture labels; no independent human labels for tone.',
        selective_metrics=metrics(selective_calls),all_items_ablation_metrics=metrics(ablation_calls))
    # Refresh B5 incremental value after judging, rather than retaining baseline numbers.
    for item in results['incremental_value']:
        if item['to_layer']=='B5':item['new_rejections']=[f'{r["case_id"]}/{r["mutation_id"]}' for r in results['mutations'] if r['evaluation']['comparison']['B4']['verdict']!='FAIL' and r['evaluation']['comparison']['B5']['verdict']=='FAIL']
    return results
