import unittest
from copy import deepcopy
from genie_eval.evaluators import aggregate,glossary,checklist,scenarios,metamorphic,contracts,layers,subset_errors
from genie_eval.mutations import variants
from helpers import context


class EvaluatorTests(unittest.TestCase):
    def test_keywords_false_positive(self):
        c,s,w=context('routing-en');bad=next(x for x in variants(w,c) if x['mutation_id']=='swapped_branches')['workflow']
        self.assertEqual('PASS',glossary(bad,c)['verdict']);self.assertEqual('FAIL',scenarios(bad,c,s)['verdict'])
    def test_names_without_execution_unknown(self):
        c,s,w=context();self.assertEqual('UNKNOWN',checklist(w,c)['verdict'])
        self.assertEqual('PASS',checklist(w,c,scenarios(w,c,s))['verdict'])
    def test_semantic_tone_unknown(self):
        c,s,w=context('damage-en');r=checklist(w,c,scenarios(w,c,s))
        self.assertEqual('UNKNOWN',r['verdict']);self.assertEqual('PASS',r['evidence'][0]['verdict'])
    def test_missing_and_unsupported_requirements(self):
        c,s,w=context();n=next(n for n in w['nodes'] if n['id']=='send');n['config']['operation']='not_registered'
        r=checklist(w,c);self.assertEqual('FAIL',r['verdict']);self.assertIn('Unsupported',str(r))
    def test_metamorphic_catches_primary_gap(self):
        c,s,w=context('intake-en');bad=next(x for x in variants(w,c) if x['mutation_id']=='missing_field_metamorphic')['workflow']
        self.assertEqual('PASS',scenarios(bad,c,s)['verdict']);self.assertEqual('FAIL',metamorphic(bad,c,s)['verdict'])
    def test_unknown_is_never_accepted_or_rejected(self):
        self.assertEqual('UNKNOWN',aggregate(['PASS','UNKNOWN']));self.assertEqual('FAIL',aggregate(['FAIL','UNKNOWN']));self.assertEqual('UNKNOWN',aggregate([]))
    def test_subset_strict_and_nested(self):
        self.assertEqual([],subset_errors({'a':{'b':1}},{'a':{'b':1,'c':2},'extra':1}))
        self.assertTrue(subset_errors({'a':True},{'a':1}))
    def test_policy_distinct_from_structure(self):
        c,s,w=context();bad=next(x for x in variants(w,c) if x['mutation_id']=='forbidden_action')['workflow']
        self.assertEqual('PASS',contracts(bad,c,s,True)['verdict'])
        self.assertTrue(any(i['category']=='policy' for i in contracts(bad,c,s)['evidence']))
    def test_judge_never_overrides_deterministic_policy_failure(self):
        c,s,w=context();bad=next(x for x in variants(w,c) if x['mutation_id']=='forbidden_action')['workflow']
        g=dict(method='G',status='RUN',verdict='PASS',evidence=[dict(requirement_id='A1',verdict='PASS')],elapsed_ms=1,prompt_tokens=5,completion_tokens=2)
        self.assertEqual('FAIL',layers(bad,c,s,g)['comparison']['B5']['verdict'])
    def test_failure_reports_expected_observed_and_responsible(self):
        c,s,w=context('routing-en');next(n for n in w['nodes'] if n['id']=='ordinary')['config']['args']['group']='Manual Review'
        r=scenarios(w,c,s);self.assertIn('expected',str(r['evidence'][0]['failures']));self.assertIn('observed',str(r['evidence'][0]['failures']))
        self.assertTrue(any(t['node_id']=='ordinary' for t in r['evidence'][0]['execution']['trace']))
    def test_branch_assertion_checks_the_named_condition(self):
        from genie_eval.runner import run
        from genie_eval.evaluators import check_execution
        c,s,w=context();fixture=deepcopy(c['input_fixtures'][1]);fixture['expected_trace_constraints']['branches']={'in_scope':'false'}
        # Rejection chooses false on approval, but true on scope: these are not interchangeable.
        failures=check_execution(run(w,fixture['input'],s),fixture,c)
        self.assertTrue(any('Expected branch in_scope: false' in x for x in failures))
    def test_malformed_graph_fails_checklist_without_crashing(self):
        c,s,w=context();w['nodes'][0]['config']=[]
        self.assertEqual('FAIL',checklist(w,c)['verdict'])
