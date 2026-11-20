import unittest
from genie_eval.experiments import reference_experiment,rank_key


class MutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.results=reference_experiment()
    def test_every_invalid_variant_detected_by_b4(self):
        for row in self.results['mutations']:
            if not row['expected_valid']:
                with self.subTest(case=row['case_id'],mutation=row['mutation_id']):self.assertEqual('FAIL',row['evaluation']['comparison']['B4']['verdict'])
    def test_equivalent_graphs_are_behaviorally_accepted(self):
        valid=[x for x in self.results['mutations'] if x['expected_valid']]
        self.assertEqual(7,len(valid))
        for row in valid:
            for method in ['D','E','F']:self.assertEqual('PASS',row['evaluation']['methods'][method]['verdict'])
            self.assertNotEqual('FAIL',row['evaluation']['comparison']['B4']['verdict'])
    def test_matrix_accounts_for_every_label(self):
        n=len(self.results['mutations'])
        for matrix in self.results['evaluation_summary'].values():
            self.assertEqual(n,sum(matrix[k] for k in ['true_acceptance','true_rejection','false_acceptance','false_rejection','unknown']))
    def test_all_required_error_types_present(self):
        wanted={'swapped_branches','missing_action','incorrect_arguments','incorrect_routing_target','invalid_ordering','forbidden_action','invalid_data_dependency','equivalent_graph'}
        self.assertTrue(wanted <= {x['mutation_id'] for x in self.results['mutations']})
    def test_incremental_metamorphic_value_measured(self):
        x=next(x for x in self.results['incremental_value'] if x['to_layer']=='B4')
        self.assertIn('intake-en/missing_field_metamorphic',x['new_rejections'])
    def test_ranking_prioritizes_contract_before_behavior_or_size(self):
        ref=self.results['references'][0]
        good=dict(workflow=ref['workflow'],evaluation=ref['evaluation'])
        bad=next(x for x in self.results['mutations'] if x['mutation_id']=='forbidden_action')
        self.assertGreater(rank_key(good),rank_key(bad));self.assertGreater(rank_key(good),rank_key({}))
    def test_ranking_includes_metamorphic_failures(self):
        invalid=next(x for x in self.results['mutations'] if x['mutation_id']=='missing_field_metamorphic')
        valid=next(x for x in self.results['mutations'] if x['case_id']=='intake-en' and x['mutation_id']=='equivalent_graph')
        self.assertGreater(rank_key(valid),rank_key(invalid))
