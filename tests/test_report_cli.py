import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from genie_eval.cli import main
from genie_eval.experiments import reference_experiment
from genie_eval.report import graph_svg,write_report
from helpers import context


class ReportCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.results=reference_experiment()
    def test_report_artifacts_offline_escaping(self):
        with tempfile.TemporaryDirectory() as d:
            files=write_report(self.results,d);html=Path(files['html']).read_text()
            self.assertIn('const data=',html);self.assertNotIn('/*PAYLOAD*/',html);self.assertNotIn('<script src=',html);self.assertNotIn('<link ',html)
            self.assertEqual(len(self.results['references'])+len(self.results['mutations']),len(list((Path(d)/'graphs').glob('*.svg'))))
            saved=json.loads(Path(files['json']).read_text());self.assertEqual(0,saved['generation_comparison'][0]['attempts']);self.assertIsNone(saved['generation_comparison'][0]['behavioral_correctness'])
    def test_svg_safe_deterministic(self):
        c,s,w=context();w['nodes'][0]['id']='</script><evil>';w['edges'][0]['source']=w['nodes'][0]['id']
        a=graph_svg(w);self.assertEqual(a,graph_svg(w));self.assertNotIn('<evil>',a);self.assertIn('&lt;evil&gt;',a)
    def test_cli_list_and_schema(self):
        for command in ['list-cases','schema']:
            with contextlib.redirect_stdout(io.StringIO()) as out:self.assertEqual(0,main([command]))
            self.assertIsNotNone(json.loads(out.getvalue()))
    def test_cli_errors_nonzero(self):
        with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(2,main(['evaluate','--case','no_case']))
        with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(2,main(['evaluate','--case','intake-en','--methods','invalid']))
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as e:main(['generate','--case','intake-en','--candidates','0'])
        self.assertEqual(2,e.exception.code)
    def test_cli_evaluate_unknown_distinct_exit(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(3,main(['evaluate','--case','order-en','--output',str(Path(d)/'result.json')]))
            self.assertEqual(0,main(['evaluate','--case','intake-en','--methods','D,E,F','--output',str(Path(d)/'result.json')]))
    def test_failed_model_attempts_keep_report_denominator(self):
        from genie_eval.experiments import generate_candidates
        from genie_eval.report import generation_comparison
        from genie_eval.generator import settings
        from helpers import FakeOllama
        c,s,w=context()
        r=generate_candidates(c,s,settings('test:model'),transport=FakeOllama(installed=False))
        comparison=generation_comparison([r]);direct=next(x for x in comparison if x['strategy']=='direct')
        self.assertEqual(1,direct['requests']);self.assertEqual(0,direct['attempts']);self.assertEqual(0,direct['behavioral_correctness']);self.assertIsNone(direct['first_pass_structural_validity'])
