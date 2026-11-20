"""Bounded A/G/H demonstrations on the same intake case, plus one selective semantic judge.

Run after the direct benchmark. Existing responses are reused and labeled cached.
No examples/gold are added to generation; judge-only evidence stays in judge calls.
"""
import argparse
from genie_eval.models import get_case,sop_for,reference,save,ROOT
from genie_eval.generator import settings,doctor
from genie_eval.experiments import generate_candidates
from genie_eval.evaluators import layers
from genie_eval.judge import judge
from genie_eval.mutations import variants


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',default='qwen3:4b');parser.add_argument('--timeout',type=float,default=300)
    parser.add_argument('--num-ctx',type=int,default=8192);parser.add_argument('--num-predict',type=int,default=2048)
    args=parser.parse_args();config=settings(args.model,timeout=args.timeout,num_ctx=args.num_ctx,num_predict=args.num_predict)
    directory=ROOT/'outputs/selected-methods';save(directory/'configuration.json',config)
    probe=doctor(config);save(directory/'doctor.json',probe)
    if probe['status']!='READY':print(probe,flush=True);return 2
    result=dict(configuration=config,doctor=probe,generation_runs=[],judge_selective=None,judge_all_ablation=[])
    c=get_case('intake-en');s=sop_for(c)
    for name,strategy,n in [('direct','direct',1),('hierarchical','hierarchical',1),('multi-candidate','direct',2)]:
        group=generate_candidates(c,s,config,n=n,strategy=strategy)
        result['generation_runs'].append(group);save(directory/(name+'.json'),group);save(directory/'results.json',result)
        print(name,[candidate['status'] for candidate in group['candidates']],group['generation_metrics'],flush=True)
    for mutation in [None,'swapped_branches']:
        w=reference(c) if mutation is None else next(v['workflow'] for v in variants(reference(c),c) if v['mutation_id']==mutation)
        ev=layers(w,c,s)['methods'];g=judge(w,c,s,ev['C'],ev['E']['evidence'],config,all_items=True)
        item=dict(case_id=c['case_id'],mutation_id=mutation,expected_valid=mutation is None,judge=g)
        result['judge_all_ablation'].append(item);save(directory/('judge-all-'+(mutation or 'reference')+'.json'),item);save(directory/'results.json',result)
        print('judge-all',mutation or 'reference',g['status'],g['agreement'],flush=True)
    order=get_case('order-en');sop=sop_for(order);w=reference(order);ev=layers(w,order,sop)['methods']
    g=judge(w,order,sop,ev['C'],ev['E']['evidence'],config)
    result['judge_selective']=dict(case_id=order['case_id'],judge=g);save(directory/'judge-selective.json',result['judge_selective']);save(directory/'results.json',result)
    print('judge-selective',g['status'],g['verdict'],flush=True)
    return 0 if any(c['workflow'] is not None for r in result['generation_runs'] for c in r['candidates']) else 2


if __name__=='__main__':raise SystemExit(main())
