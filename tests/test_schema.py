import unittest
from copy import deepcopy
from genie_eval.models import schema_errors,WORKFLOW_SCHEMA,oracle_integrity,cases,load
from genie_eval.validators import validate
from helpers import context


class SchemaTests(unittest.TestCase):
    def setUp(self):self.case,self.sop,self.w=context()
    def codes(self,w):return {i['code'] for i in validate(w,self.sop)}
    def test_all_reference_shapes(self):
        from genie_eval.models import reference,sop_for
        for c in cases():
            with self.subTest(case=c['case_id']):self.assertEqual([],validate(reference(c),sop_for(c)))
    def test_types_are_strict(self):
        self.assertTrue(schema_errors(True,{'type':'integer'}));self.assertTrue(schema_errors(1,{'const':True}))
        self.assertTrue(schema_errors(None,WORKFLOW_SCHEMA));self.assertTrue(schema_errors([],WORKFLOW_SCHEMA))
    def test_unique_ids(self):
        self.w['nodes'].append(deepcopy(self.w['nodes'][0]));self.assertIn('DUPLICATE_ID',self.codes(self.w))
    def test_endpoint(self):
        self.w['edges'][0]['target']='missing';self.assertIn('EDGE_ENDPOINT',self.codes(self.w))
    def test_condition_ports(self):
        self.w['edges'][1]['port']='next';self.assertIn('EDGE_PORTS',self.codes(self.w))
    def test_cycle(self):
        self.w['edges'].append(dict(source='out',target='in',port='next'));self.assertIn('CYCLE',self.codes(self.w))
    def test_unreachable(self):
        self.w['nodes'].append(dict(id='unused',type='output',config={}));self.assertIn('UNREACHABLE',self.codes(self.w))
    def test_one_input(self):
        self.w['nodes'][0]['type']='output';self.assertIn('INPUT_COUNT',self.codes(self.w))
    def test_unknown_operation_and_args(self):
        self.w['nodes'][2]['config']={'operation':'execute_python','args':{}};self.w['nodes'][2]['type']='custom'
        self.assertIn('UNKNOWN_OPERATION',self.codes(self.w))
        self.case,self.sop,self.w=context();next(n for n in self.w['nodes'] if n['id']=='send')['config']['args']['unknown']=1
        self.assertIn('ARGUMENT_SCHEMA',self.codes(self.w))
    def test_data_missing(self):
        next(n for n in self.w['nodes'] if n['id']=='send')['config']['args']['text']={'ref':'not_produced'}
        self.assertIn('DATA_DEPENDENCY',self.codes(self.w))
    def test_guard_not_operation_presence(self):
        next(n for n in self.w['nodes'] if n['id']=='decision')['config']['value']='rejected'
        self.assertIn('PRECONDITION_UNPROVEN',self.codes(self.w));self.assertIn('POLICY_GUARD',self.codes(self.w))
    def test_merge_requires_all_paths(self):
        # A path bypassing draft cannot borrow the other branch's produced field.
        self.w['edges'].append(dict(source='reject',target='ask',port='next'))
        self.w['edges']=[e for e in self.w['edges'] if not(e['source']=='reject' and e['target']=='out')]
        findings=validate(self.w,self.sop)
        self.assertTrue(any(x['code']=='DATA_DEPENDENCY' and 'draft' in x['message'] for x in findings))
    def test_file_explicitly_unsupported(self):
        n=next(n for n in self.w['nodes'] if n['id']=='reject');n.update(type='file',config=dict(operation='metadata',name='photo.jpg',media_type='image/jpeg',size_bytes=0))
        self.assertFalse(schema_errors(self.w,WORKFLOW_SCHEMA));self.assertIn('FILE_UNSUPPORTED',self.codes(self.w))
    def test_unsupported_condition_is_schema_failure(self):
        next(n for n in self.w['nodes'] if n['type']=='condition')['config']['operator']='python_eval'
        self.assertIn('SCHEMA',self.codes(self.w))
    def test_dataset_provenance_and_bilingual_pairs(self):
        sources={s['source_id'] for s in load('data/sources.json')};all_cases=cases()
        self.assertEqual(5,len({c['sop_id'] for c in all_cases}));self.assertEqual(2,sum(c['language']=='vi' for c in all_cases))
        for c in all_cases:
            self.assertFalse(set(c['source_ids'])-sources)
            for k in ['user_request','requirements','expected_capabilities','input_fixtures','expected_state','expected_trace_constraints','forbidden_effects','metamorphic_relations','provenance','limitations']:self.assertIn(k,c)
            if c['language']=='vi':
                en=next(x for x in all_cases if x['case_id']==c['sop_id']+'-en')
                self.assertEqual(en['input_fixtures'],c['input_fixtures']);self.assertEqual(en['metamorphic_relations'],c['metamorphic_relations'])
        self.assertEqual('PASS',oracle_integrity()['verdict'])
