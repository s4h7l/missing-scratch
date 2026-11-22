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
