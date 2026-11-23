import unittest

from scratch.publish_reports import paired_findings


class PairedFindingsTests(unittest.TestCase):
    def test_counts_repeated_answers_and_prioritizes_false_coverage(self):
        options = ['Visible', 'Blocked']
        cases = [
            dict(id=str(index), pair=index // 2, type='visibility', options=options, answer=answer)
            for index, answer in enumerate(options * 4)
        ]
        rows = [dict(response=response) for response in ['B', 'B', 'A', 'A', 'A', 'B', 'unclear', 'B']]
        result = paired_findings(cases, rows)

        self.assertEqual(result['answer_flips'], 4)
        self.assertEqual(result['exactly_one_correct'], 3)
        self.assertEqual(result['repeated_answer'], 2)
        self.assertEqual(result['example']['pair'], 1)
        self.assertEqual(result['example']['failure'], 'False coverage')
        self.assertEqual(result['example']['cases'][1]['expected'], 'Blocked')
        self.assertEqual(result['example']['cases'][1]['predicted'], 'Visible')
