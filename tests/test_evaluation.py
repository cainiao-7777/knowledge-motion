import unittest
from src.evaluation import score_answers

class EvaluationTests(unittest.TestCase):
    def test_calculates_score_and_records_wrong_answers(self):
        items=[{'id':1,'answer':'A'},{'id':2,'answer':'B'}]
        report=score_answers(items,['A','C'])
        self.assertEqual(report['correct'],1)
        self.assertEqual(report['total'],2)
        self.assertEqual(report['accuracy'],0.5)
        self.assertEqual(report['wrong_ids'],[2])
    def test_rejects_incomplete_predictions(self):
        with self.assertRaises(ValueError): score_answers([{'id':1,'answer':'A'}],[])
