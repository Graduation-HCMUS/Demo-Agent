import tempfile
import unittest
from genie_eval.generator import settings
from genie_eval.judge import judge
from genie_eval.evaluators import checklist,scenarios,layers
from helpers import context,FakeOllama


def vote(id,verdict='PASS',nodes=None):
    return dict(requirement_id=id,verdict=verdict,node_ids=nodes or [],edge_refs=[],trace_refs=[],reason='Short test evidence statement',uncertainty=0.2,failure_category='none')


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.c,self.s,self.w=context('order-en');self.e=scenarios(self.w,self.c,self.s);self.check=checklist(self.w,self.c,self.e)
        self.config=settings('test:model');self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
    def call(self,fake,**kwargs):
        return judge(self.w,self.c,self.s,self.check,self.e['evidence'],self.config,transport=fake,cache_dir=self.temp.name,**kwargs)
    def test_selective_only_unresolved_items(self):
        fake=FakeOllama();r=self.call(fake)
        self.assertEqual(['O3'],[x['requirement_id'] for x in r['evidence']]);self.assertEqual('UNKNOWN',r['verdict']);self.assertEqual(1,len(fake.chat_calls))
        self.assertNotIn('input_snapshot',fake.chat_calls[0]['messages'][0]['content'])
    def test_not_needed_avoids_inference(self):
        c,s,w=context();e=scenarios(w,c,s);fake=FakeOllama()
        r=judge(w,c,s,checklist(w,c,e),e['evidence'],self.config,transport=fake,cache_dir=self.temp.name)
        self.assertEqual('NOT_NEEDED',r['status']);self.assertEqual([],fake.chat_calls)
    def test_invalid_evidence_becomes_unknown(self):
        fake=FakeOllama(responses=[{'items':[vote('O3',nodes=['not_a_node'])]}]);r=self.call(fake)
        self.assertEqual('UNKNOWN',r['evidence'][0]['verdict'])
    def test_missing_items_invalid_not_pass(self):
        fake=FakeOllama(responses=[{'items':[]}]);r=self.call(fake)
        self.assertEqual('UNAVAILABLE_OR_INVALID',r['status']);self.assertEqual('UNKNOWN',r['verdict'])
    def test_all_items_ablation_agreement_denominator(self):
        fake=FakeOllama(responses=[{'items':[vote('O1',nodes=['lookup']),vote('O2',nodes=['reply']),vote('O3','UNKNOWN')]}]);r=self.call(fake,all_items=True)
        self.assertEqual(3,len(r['evidence']));self.assertEqual(2,r['agreement']['eligible_items']);self.assertEqual(2,r['agreement']['agree'])
    def test_multi_model_disagreement_unknown(self):
        fake=FakeOllama(responses=[{'items':[vote('O3',nodes=['ack'])]},{'items':[vote('O3','FAIL',nodes=['ack'])]}]);r=self.call(fake,model_ids=['test:model','test:judge'])
        self.assertEqual('UNKNOWN',r['evidence'][0]['verdict']);self.assertEqual(2,len(r['calls']));self.assertEqual(222,r['prompt_tokens'])
    def test_unavailable_model_unknown(self):
        r=self.call(FakeOllama(installed=False));self.assertEqual('UNAVAILABLE_OR_INVALID',r['status']);self.assertEqual('UNKNOWN',r['verdict']);self.assertIsNone(r['prompt_tokens']);self.assertFalse(r['calls'][0].get('judge_errors'))
    def test_mutation_judge_ablation_keeps_independent_labels(self):
        from genie_eval.experiments import reference_experiment,judge_variant_comparison
        results=reference_experiment();fake=FakeOllama()
        judge_variant_comparison(results,self.config,['approval-en'],all_items_ablation=True,transport=fake,cache_dir=self.temp.name)
        agreement=results['judge_agreement'];self.assertIn('unknown_items',agreement)
        # Double returns UNKNOWN, so no decisive agreement is fabricated.
        self.assertEqual(0,agreement['eligible_items']);self.assertGreater(agreement['unknown_items'],0)
        for row in results['mutations']:
            if row['case_id']=='approval-en' and not row['expected_valid']:
                self.assertEqual('FAIL',row['evaluation']['comparison']['B5']['verdict'])
    def test_raw_unknown_not_counted_as_judge_rejection(self):
        from genie_eval.experiments import judge_confusion
        effective_failed=dict(verdict='FAIL',evidence=[dict(requirement_id='I1',deterministic_verdict='FAIL',verdict='UNKNOWN',effective_verdict='FAIL')])
        result=judge_confusion([effective_failed]);self.assertEqual(1,result['unknown']);self.assertEqual(0,result['true_rejection'])
