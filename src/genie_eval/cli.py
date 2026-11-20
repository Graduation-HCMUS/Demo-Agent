"""Reference commands never contact Ollama; model commands never pull models."""
import argparse
import json
import sys
import unittest
from pathlib import Path
from .models import ROOT,load,save,cases,get_case,sop_for,reference,WORKFLOW_SCHEMA
from .generator import settings,doctor
from .evaluators import evaluate,aggregate
from .experiments import reference_experiment,benchmark,generate_candidates,judge_variant_comparison
from .judge import judge
from .report import write_report


def model_options(p):
    p.add_argument('--model');p.add_argument('--timeout',type=float);p.add_argument('--num-predict',type=int)
    p.add_argument('--num-ctx',type=int);p.add_argument('--retries',type=int,default=0);p.add_argument('--no-cache',action='store_true')


def optional_methods(p):
    p.add_argument('--judge',action='store_true',help='Opt in to selective judging of unresolved requirements')
    p.add_argument('--judge-all',action='store_true',help='All-items judge ablation; implies --judge')
    p.add_argument('--judge-models',nargs='+')


def config_for(args,model=None):
    return settings(model or getattr(args,'model',None),timeout=getattr(args,'timeout',None),num_predict=getattr(args,'num_predict',None),num_ctx=getattr(args,'num_ctx',None),
                    retries=getattr(args,'retries',0),cache=not getattr(args,'no_cache',False))


def emit(value):print(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False))


def parser():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    d=sub.add_parser('doctor');model_options(d)
    sub.add_parser('list-cases');sub.add_parser('test');sub.add_parser('schema')
    d=sub.add_parser('demo');d.add_argument('--mode',choices=['reference'],default='reference');d.add_argument('--output-dir',type=Path,default=ROOT/'outputs')
    g=sub.add_parser('generate');g.add_argument('--case',required=True);model_options(g);optional_methods(g)
    g.add_argument('--strategy',choices=['direct','hierarchical'],default='direct');g.add_argument('--candidates',type=int,choices=[1,2,3],default=1)
    g.add_argument('--planner-model');g.add_argument('--detail-model');g.add_argument('--output',type=Path)
    e=sub.add_parser('evaluate');e.add_argument('--case',required=True);e.add_argument('--workflow',type=Path,help='Omit for labeled reference demonstration')
    e.add_argument('--methods',default='all',help='all or comma-separated B,C,D,E,F,G');model_options(e);optional_methods(e);e.add_argument('--output',type=Path)
    b=sub.add_parser('benchmark');b.add_argument('--mode',choices=['reference','ollama'],default='ollama');b.add_argument('--models',nargs='+')
    b.add_argument('--case',action='append');b.add_argument('--all-methods',action='store_true',help='Opt in to hierarchy, N candidates, selective judges and all-items ablation')
    b.add_argument('--candidates',type=int,choices=[2,3],default=2);b.add_argument('--planner-model');b.add_argument('--detail-model');model_options(b);b.add_argument('--judge-models',nargs='+')
    b.add_argument('--output-dir',type=Path,default=ROOT/'outputs')
    r=sub.add_parser('report');r.add_argument('--results',type=Path,default=ROOT/'outputs/results.json');r.add_argument('--output-dir',type=Path,default=ROOT/'outputs')
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        if args.command=='doctor':
            r=doctor(config_for(args));save('outputs/doctor.json',r);emit(r);return 0 if r['status']=='READY' else 2
        if args.command=='list-cases':
            emit([dict(case_id=c['case_id'],language=c['language'],sop_id=c['sop_id'],source_ids=c['source_ids']) for c in cases()]);return 0
        if args.command=='schema':emit(WORKFLOW_SCHEMA);return 0
        if args.command=='test':
            suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
            if suite.countTestCases()==0:raise ValueError('No tests discovered; refusing empty test success')
            result=unittest.TextTestRunner(verbosity=2).run(suite);return 0 if result.wasSuccessful() else 1
        if args.command=='demo' or args.command=='benchmark' and args.mode=='reference':
            results=reference_experiment();emit(write_report(results,args.output_dir));return 0
        if args.command=='generate':
            c=get_case(args.case);r=generate_candidates(c,sop_for(c),config_for(args),args.candidates,args.strategy,args.judge or args.judge_all,args.judge_all,
                  args.judge_models,args.planner_model,args.detail_model)
            path=args.output or ROOT/'outputs/generations'/f'{args.case}-{r["strategy"]}.json';save(path,r)
            winner=r['candidates'][r['selected_candidate_index']]
            emit(dict(output=str(path),status=winner['status'],selection_accepted=r['selection_accepted'],metrics=r['generation_metrics'],judge_metrics=r['judge_metrics'],
                      errors=winner.get('validation_errors',[]),message='Selection stays unresolved when semantic checklist items are UNKNOWN.'))
            if not winner['workflow']:return 2
            ev=winner['evaluation']['methods'];return 1 if any(ev[m]['verdict']=='FAIL' for m in ['D','E','F']) else 0
        if args.command=='evaluate':
            c=get_case(args.case);sop=sop_for(c);w=load(args.workflow.resolve()) if args.workflow else reference(c)
            methods=['B','C','D','E','F','G'] if args.methods=='all' else args.methods.split(',')
            if not methods or set(methods)-set('BCDEFG'):raise ValueError('methods must be all or comma-separated B,C,D,E,F,G')
            results=evaluate(w,c,sop,methods)
            if 'G' in methods:
                if args.judge or args.judge_all:
                    required=evaluate(w,c,sop,('C','E'));results['G']=judge(w,c,sop,required['C'],required['E']['evidence'],config_for(args),args.judge_models,args.judge_all)
                else:results['G']=dict(method='G',status='DISABLED',verdict='UNKNOWN',evidence=[],prompt_tokens=None,completion_tokens=None,elapsed_ms=0)
            verdict=aggregate(r['verdict'] for k,r in results.items() if not (k=='G' and r.get('status')=='DISABLED'))
            r=dict(case_id=c['case_id'],input_kind='supplied workflow' if args.workflow else 'reference demonstration',verdict=verdict,results=results)
            path=args.output or ROOT/'outputs/evaluations'/f'{args.case}.json';save(path,r);emit(dict(output=str(path),verdict=verdict,methods={k:v['verdict'] for k,v in results.items()}))
            return {'PASS':0,'FAIL':1,'UNKNOWN':3}[verdict]
        if args.command=='benchmark':
            results=reference_experiment();model_runs=[];selected=[get_case(id) for id in args.case] if args.case else None
            for model in args.models or [config_for(args)['model']]:
                model_runs.append(benchmark(config_for(args,model),selected,args.all_methods,args.candidates,args.judge_models,args.planner_model,args.detail_model))
            if args.all_methods and any(r['doctor']['status']=='READY' for r in model_runs):
                judge_config=config_for(args,next(r['doctor']['requested_model'] for r in model_runs if r['doctor']['status']=='READY'))
                judge_variant_comparison(results,judge_config,args.case,args.judge_models,True)
            results['ollama_benchmark']=model_runs;results['generation_runs']=[g for r in model_runs for g in r['generation_runs']]
            save(args.output_dir/'ollama-benchmark.json',model_runs)
            paths=write_report(results,args.output_dir);emit(dict(outputs=paths,models=[dict(model=r['doctor']['requested_model'],status=r['status'],error=r['error'],actual_generation_calls=r['actual_generation_calls']) for r in model_runs]))
            return 0 if model_runs and all(r['status']=='COMPLETED' for r in model_runs) else 2
        if args.command=='report':
            if not args.results.exists():raise ValueError('No saved results; run demo --mode reference first')
            emit(write_report(load(args.results.resolve()),args.output_dir));return 0
    except (ValueError,OSError,KeyError,TypeError,RecursionError) as exc:
        print(f'genie-eval: {exc}',file=sys.stderr);return 2
    return 2


if __name__=='__main__':raise SystemExit(main())
