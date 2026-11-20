import unittest
from copy import deepcopy
from genie_eval.runner import run,condition
from genie_eval.catalog import invoke,REGISTRY
from genie_eval.models import cases,reference,sop_for
from helpers import context


class RunnerTests(unittest.TestCase):
    def test_references_execute_every_fixture(self):
        from genie_eval.evaluators import scenarios
        for c in cases():
            with self.subTest(case=c['case_id']):self.assertEqual('PASS',scenarios(reference(c),c,sop_for(c))['verdict'])
    def test_input_immutable_trace_contains_branches(self):
        c,s,w=context();ticket=deepcopy(c['input_fixtures'][0]['input']);before=deepcopy(ticket);r=run(w,ticket,s)
        self.assertEqual(before,ticket);self.assertEqual('OK',r['status'])
        self.assertTrue(any(t['selected_edge'] and t['selected_edge']['port']=='true' for t in r['trace']))
        for t in r['trace']:
            for k in ['step_index','node_id','node_type','operation','input_snapshot','state_changes','selected_edge','error']:self.assertIn(k,t)
    def test_rejected_does_not_send(self):
        c,s,w=context();r=run(w,c['input_fixtures'][1]['input'],s)
        self.assertNotIn('send_reply',r['state']['effects']);self.assertEqual('Manual Review',r['state']['group'])
    def test_approval_missing_fails_explicitly(self):
        c,s,w=context();ticket=deepcopy(c['input_fixtures'][0]['input']);ticket.pop('approval_decision');r=run(w,ticket,s)
        self.assertEqual('ERROR',r['status']);self.assertEqual('DATA_MISSING',r['errors'][0]['code']);self.assertNotIn('send_reply',r['state']['effects'])
    def test_precondition_enforced_even_without_static_checker(self):
        with self.assertRaisesRegex(ValueError,'PRECONDITION'):
            invoke('send_reply',{'text':'hello'},dict(draft='hello',approval='rejected'),[])
    def test_policy_checked_before_effect(self):
        with self.assertRaisesRegex(ValueError,'POLICY_FORBIDDEN'):
            invoke('issue_refund',{'amount':10},{},[dict(operation='issue_refund',kind='forbid_operation',policy_id='no_money')])
    def test_invalid_argument_reference_type_fails(self):
        with self.assertRaisesRegex(ValueError,'ARGUMENT_RUNTIME'):
            invoke('send_reply',{'text':{'ref':'draft'}},dict(draft=42,approval='approved'),[])
    def test_steps_bounded(self):
        c,s,w=context();r=run(w,c['input_fixtures'][0]['input'],s,max_steps=1)
        self.assertEqual('STEP_LIMIT',r['errors'][0]['code'])
    def test_bad_schema_never_executes(self):
        c,s,w=context();w['edges']=[];r=run(w,{},s)
        self.assertEqual('INVALID',r['status']);self.assertEqual([],r['trace']);self.assertEqual([],r['state']['effects'])
    def test_safe_operators(self):
        self.assertFalse(condition(dict(field='x',operator='eq',value=True),{'x':1}))
        self.assertTrue(condition(dict(field='x',operator='ne',value=True),{'x':1}))
        self.assertTrue(condition(dict(field='x',operator='exists',value=True),{'x':False}))
        self.assertFalse(condition(dict(field='x',operator='exists',value=True),{}))
        with self.assertRaisesRegex(ValueError,'CONDITION_TYPE'):condition(dict(field='x',operator='gte',value=2),{'x':'3'})
    def test_validation_and_identifier_preconditions(self):
        for v in ['1234','１２３４５','abcde']:
            with self.subTest(v=v),self.assertRaisesRegex(ValueError,'PRECONDITION'):invoke('save_order',{'value':v},{},[])
        with self.assertRaisesRegex(ValueError,'PRECONDITION'):
            invoke('lookup_order',dict(order='54321',email='u@example.test'),dict(saved_order='12345',saved_email='u@example.test',mock_order={}),[])
    def test_catalog_contract_complete(self):
        for name,c in REGISTRY.items():
            for key in ['description','argument_schema','required_inputs','produced_outputs','preconditions','effects','forbidden_effects','implementation']:self.assertIn(key,c,name)
            self.assertTrue(callable(c['implementation']))
    def test_invalid_ticket_state_is_explicit(self):
        c,s,w=context();r=run(w,[],s)
        self.assertEqual('INVALID',r['status']);self.assertEqual('INPUT_STATE',r['errors'][0]['code'])
    def test_boolean_policy_is_type_strict(self):
        with self.assertRaisesRegex(ValueError,'POLICY_STATE'):
            invoke('create_ticket',{},dict(valid=1),[dict(policy_id='valid_input',operation='create_ticket',kind='requires_state',field='valid',equals=True)])
