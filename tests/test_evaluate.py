import unittest

from scratch.evaluate import metrics


class MetricsTests(unittest.TestCase):
    def test_pair_requires_both_correct(self):
        common=dict(type='visibility',difficulty='easy',options=['Visible','Blocked'])
        cases=[dict(common,pair=1,answer='Visible'),dict(common,pair=1,answer='Blocked')]
        score=metrics(cases,[{'response':'A'},{'response':'B'}])
        self.assertEqual(score['both_pair_members']['correct'],1)
        score=metrics(cases,[{'response':'A'},{'response':'B because ...'}])
        self.assertEqual(score['overall']['correct'],1)
        self.assertEqual(score['both_pair_members']['correct'],0)

    def test_incomplete_pair_has_no_pair_score(self):
        case=dict(type='repair',difficulty='hard',options=['A','B'],answer='A',pair=2)
        score=metrics([case,dict(case,answer='B')],[{'response':'A'}])
        self.assertIsNone(score['both_pair_members']['accuracy'])


class ResumeTests(unittest.TestCase):
    def test_resume_preserves_success_and_retries_failed_case(self):
        import contextlib
        import hashlib
        import io
        import json
        import os
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        from scratch import evaluate

        with TemporaryDirectory() as temp:
            root = Path(temp)
            dataset, prior, output = (root / name for name in ('cases.json', 'prior.jsonl', 'new.jsonl'))
            case = dict(type='visibility', difficulty='easy', pair=1, answer='Visible', options=['Visible', 'Blocked'])
            dataset.write_text(json.dumps({'cases': [dict(case, id=id) for id in ('a', 'b')]}))
            meta = dict(dataset=hashlib.sha256(dataset.read_bytes()).hexdigest(),
                        provider='gemini', model='test', mode='vision')
            first = dict(id='a', response='A')
            prior.write_text(''.join(json.dumps(row) + '\n' for row in (meta, first, dict(id='b', error='HTTP 429'))))
            argv = ['evaluate', '--dataset', str(dataset), '--provider', 'gemini', '--model', 'test',
                    '--max-requests', '1', '--resume-from', str(prior), '--record', str(output)]
            with patch('sys.argv', argv), patch.dict(os.environ, {'GEMINI_API_KEY': 'fixture'}), \
                    patch.object(evaluate, 'request_model', return_value='A') as send, \
                    contextlib.redirect_stdout(io.StringIO()):
                evaluate.main()
            send.assert_called_once()
            self.assertEqual(send.call_args.args[2]['id'], 'b')
            self.assertEqual(list(map(json.loads, output.read_text().splitlines()[1:])),
                             [first, dict(id='b', response='A')])
