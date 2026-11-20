import json
import tempfile
import unittest
from pathlib import Path
from genie_eval.generator import settings,doctor,build_prompt,generate,structured_call,check_plan,WORKFLOW_SCHEMA
from genie_eval.experiments import generate_candidates,benchmark
from helpers import context,FakeOllama


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.c,self.s,self.w=context();self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.config=settings('test:model',timeout=1,num_predict=512)
    def test_default_and_local_only_settings(self):
        self.assertEqual(0,self.config['retries']);self.assertEqual(0,self.config['temperature'])
        with self.assertRaisesRegex(ValueError,'local'):settings('test:model',host='https://external.example.test')
    def test_prompt_whitelist_prevents_oracle_leak(self):
        case=dict(self.c,input_fixtures='SECRET_FIXTURE',expected_state='SECRET_STATE',requirements='SECRET_CHECKLIST',metamorphic_relations='SECRET_RELATION')
        prompt=build_prompt(case,self.s)
        for secret in ['SECRET_FIXTURE','SECRET_STATE','SECRET_CHECKLIST','SECRET_RELATION','expected_trace_constraints','reference-approval']:self.assertNotIn(secret,prompt)
        self.assertIn(self.c['user_request'],prompt);self.assertIn('schema',prompt)
    def test_missing_model_no_generation_no_pull(self):
        fake=FakeOllama(installed=False);r=generate(self.c,self.s,self.config,transport=fake,cache_dir=self.temp.name)
        self.assertEqual('MODEL_MISSING',r['status']);self.assertIsNone(r['workflow']);self.assertEqual([],fake.chat_calls)
    def test_doctor_connection_failure(self):
        def offline(*a,**kw):raise OSError('offline')
        self.assertEqual('UNAVAILABLE',doctor(self.config,offline)['status'])
    def test_structured_output_metrics_and_reasoning_not_saved(self):
        fake=FakeOllama(self.w);r=generate(self.c,self.s,self.config,transport=fake,cache_dir=self.temp.name)
        self.assertEqual('OK',r['status']);self.assertEqual([],r['validation_errors']);self.assertEqual(1,len(fake.chat_calls))
        payload=fake.chat_calls[0];self.assertEqual(WORKFLOW_SCHEMA,payload['format']);self.assertIs(False,payload['think']);self.assertFalse(payload['stream'])
        call=r['calls'][0];self.assertEqual(111,call['prompt_tokens']);self.assertEqual(22,call['completion_tokens'])
        for p in Path(self.temp.name).rglob('*.json'):self.assertNotIn('SECRET_REASONING_MUST_NOT_BE_SAVED',p.read_text())
    def test_retry_disabled_and_first_attempt_durable(self):
        fake=FakeOllama(responses=['broken json',self.w]);r=generate(self.c,self.s,self.config,transport=fake,cache_dir=self.temp.name)
        self.assertEqual('ERROR',r['status']);self.assertEqual(1,len(fake.chat_calls));self.assertEqual('broken json',r['calls'][0]['attempts'][0]['raw_response'])
    def test_configurable_retries_preserve_first_pass(self):
        fake=FakeOllama(responses=['broken json',self.w]);r=generate(self.c,self.s,{**self.config,'retries':1},transport=fake,cache_dir=self.temp.name)
        call=r['calls'][0];self.assertEqual('OK',call['status']);self.assertEqual('ERROR',call['first_pass_status']);self.assertEqual(2,len(call['attempts']));self.assertEqual(222,call['prompt_tokens'])
        self.assertEqual(2,len(list((Path(self.temp.name)/'attempts').glob('*.json'))))
    def test_cache_records_zero_new_tokens_and_changes_key(self):
        fake=FakeOllama(self.w)
        a=generate(self.c,self.s,self.config,transport=fake,cache_dir=self.temp.name)['calls'][0]
        b=generate(self.c,self.s,self.config,transport=fake,cache_dir=self.temp.name)['calls'][0]
        self.assertTrue(b['cached']);self.assertEqual(0,b['prompt_tokens']);self.assertEqual(111,b['original_prompt_tokens']);self.assertEqual(1,len(fake.chat_calls))
        generate(self.c,self.s,{**self.config,'seed':18},transport=fake,cache_dir=self.temp.name);self.assertEqual(2,len(fake.chat_calls))
        changed=dict(self.s,scope='Changed business scope')
        generate(self.c,changed,self.config,transport=fake,cache_dir=self.temp.name);self.assertEqual(3,len(fake.chat_calls))
    def test_timeout_explicit_failure(self):
        fake=FakeOllama(responses=[TimeoutError('timed out')]);r=generate(self.c,self.s,self.config,transport=fake,cache_dir=self.temp.name)
        self.assertEqual('ERROR',r['status']);self.assertIn('timed out',r['calls'][0]['error'])
    def test_hierarchy_four_calls_and_configurable_models(self):
        fake=FakeOllama(self.w);r=generate(self.c,self.s,self.config,'hierarchical','test:planner','test:detail',fake,self.temp.name)
        self.assertEqual('OK',r['status']);self.assertEqual(3,len(r['plans']));self.assertEqual(4,len(fake.chat_calls))
        self.assertEqual(['test:planner','test:detail','test:detail','test:model'],[c['model'] for c in fake.chat_calls]);self.assertFalse(r['same_model_planning'])
        for plan in r['plans']:self.assertEqual([],check_plan(plan,self.s))
    def test_bad_plan_provenance_stops_workflow_call(self):
        plan={'items':[dict(id='x',business_intent='intent',required_inputs=[],expected_outputs=[],dependencies=['missing'],candidate_capabilities=['bad'],requirement_ids=['invented'])]}
        fake=FakeOllama(responses=[plan]);r=generate(self.c,self.s,self.config,'hierarchical',transport=fake,cache_dir=self.temp.name)
        self.assertEqual('INVALID',r['status']);self.assertEqual(1,len(fake.chat_calls));self.assertIsNone(r['workflow'])
    def test_multi_candidate_ranking_and_cost(self):
        from genie_eval.mutations import variants
        bad=next(x for x in variants(self.w,self.c) if x['mutation_id']=='swapped_branches')['workflow']
        fake=FakeOllama(responses=[bad,self.w]);r=generate_candidates(self.c,self.s,self.config,n=2,transport=fake,cache_dir=self.temp.name)
        self.assertEqual(1,r['selected_candidate_index']);self.assertTrue(r['selection_accepted']);self.assertEqual(2,r['generation_metrics']['actual_inference_calls'])
        self.assertEqual(222,r['generation_metrics']['prompt_tokens']);self.assertNotEqual(fake.chat_calls[0]['options']['seed'],fake.chat_calls[1]['options']['seed'])
    def test_benchmark_empty_model_is_failure(self):
        r=benchmark(self.config,[self.c],transport=FakeOllama(installed=False));self.assertEqual('FAILED',r['status']);self.assertEqual([],r['generation_runs']);self.assertEqual(0,r['actual_generation_calls'])
    def test_bilingual_request_preserved(self):
        c,s,w=context('approval-vi');fake=FakeOllama(w);r=generate(c,s,self.config,transport=fake,cache_dir=self.temp.name)
        self.assertIn(c['user_request'],fake.chat_calls[0]['messages'][0]['content']);self.assertEqual('none',r['language_translation'])
    def test_all_methods_orchestration_and_ablation(self):
        fake=FakeOllama(self.w)
        r=benchmark(self.config,[self.c],all_methods=True,transport=fake,cache_dir=self.temp.name)
        self.assertEqual('COMPLETED',r['status']);self.assertEqual(3,len(r['generation_runs']))
        self.assertEqual({'direct','hierarchical','multi-candidate'},{g['strategy'] for g in r['generation_runs']})
        self.assertTrue(all('judge_all_ablation' in c for g in r['generation_runs'] for c in g['candidates']))
    def test_no_cache_preserves_distinct_attempt_records(self):
        fake=FakeOllama(self.w)
        for _ in range(2):generate(self.c,self.s,{**self.config,'cache':False},transport=fake,cache_dir=self.temp.name)
        self.assertEqual(2,len(list((Path(self.temp.name)/'attempts').glob('*.json'))))
        self.assertEqual(2,len(list((Path(self.temp.name)/'requests').glob('*.json'))))
    def test_non_json_numeric_constant_is_recorded_as_failure(self):
        fake=FakeOllama(responses=['NaN']);r=generate(self.c,self.s,self.config,transport=fake,cache_dir=self.temp.name)
        self.assertEqual('ERROR',r['status']);self.assertEqual('NaN',r['calls'][0]['raw_response']);self.assertIn('Invalid JSON constant',r['calls'][0]['error'])
    def test_mapping_requires_actual_capability_coverage(self):
        plan={'items':[dict(id='x',business_intent='approval',required_inputs=[],expected_outputs=[],dependencies=[],candidate_capabilities=[],requirement_ids=['A1'])]}
        errors=check_plan(plan,self.s,'capability_mapping');self.assertTrue(any('PLAN_MAPPING_MISSING' in e for e in errors))
        plan['items'][0]['candidate_capabilities']=['issue_refund'];self.assertTrue(any('PLAN_POLICY_FORBIDDEN' in e for e in check_plan(plan,self.s,'capability_mapping')))
