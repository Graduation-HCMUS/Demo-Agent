"""Rebuild the final report from preserved real runs plus freshly measured reference checks."""
import argparse
from pathlib import Path
from genie_eval.models import ROOT,load,get_case,sop_for
from genie_eval.evaluators import layers
from genie_eval.experiments import reference_experiment,metrics,judge_confusion
from genie_eval.report import write_report,generation_comparison


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',type=Path,default=ROOT/'outputs/ollama-benchmark.json')
    parser.add_argument('--selected',type=Path)
    parser.add_argument('--include-initial-timeout',action='store_true')
    args=parser.parse_args();baseline=load(args.baseline.resolve());r=reference_experiment()
    r['ollama_benchmark']=baseline;r['generation_runs']=[g for b in baseline for g in b['generation_runs']]
    r['limitations'].append('Real strategy demonstrations use the explicitly listed case coverage; broader strategy superiority is not established.')
    if args.include_initial_timeout:
        r['generation_runs'].append(load('outputs/generations/intake-en-direct.json'))
        r['limitations'].append('An earlier v1 default-model timeout is a separate configuration, retained rather than pooled with v2 success claims.')
    if args.selected:
        selected=load(args.selected.resolve());r['selected_demonstration']=selected
        r['generation_matched_subset']=generation_comparison(selected['generation_runs'])
        # Its direct N=1 response is the baseline's cached comparison anchor, not a new sample.
        r['generation_runs'] += [g for g in selected['generation_runs'] if g['strategy']!='direct']
        all_judges=[];agreements=[]
        for item in selected['judge_all_ablation']:
            rows=r['mutations'] if item['mutation_id'] else r['references']
            row=next(x for x in rows if x['case_id']==item['case_id'] and x.get('mutation_id')==item['mutation_id'])
            row['judge_all_ablation']=item['judge'];all_judges+=item['judge'].get('calls',[]);agreements.append(item['judge'].get('agreement',{}))
        selective=selected.get('judge_selective')
        if selective:
            row=next(x for x in r['references'] if x['case_id']==selective['case_id'])
            row['evaluation']=layers(row['workflow'],get_case(row['case_id']),sop_for(get_case(row['case_id'])),selective['judge'])
        r['judge_agreement']=dict(eligible_items=sum(a.get('eligible_items',0) for a in agreements),agree=sum(a.get('agree',0) for a in agreements),
            unknown_items=sum(x['verdict']=='UNKNOWN' for item in selected['judge_all_ablation'] for x in item['judge']['evidence']),
            ablation_confusion=judge_confusion([item['judge'] for item in selected['judge_all_ablation']]),basis='Two all-items intake labels from independent executable expectations; no human semantic calibration.',
            all_items_ablation_metrics=metrics(all_judges),selective_metrics=metrics(selective['judge'].get('calls',[])) if selective else None)
    r['execution_incidents']=[dict(status='INTERRUPTED_NO_RESULT',description='Earlier foreground invocations lost their process handles after tool resets and returned no saved response. Their unobserved HTTP/token outcomes are excluded from measured success, not treated as successful inference.',generation_attempts=None,prompt_tokens=None,completion_tokens=None)]
    paths=write_report(r);print(paths)


if __name__=='__main__':main()
