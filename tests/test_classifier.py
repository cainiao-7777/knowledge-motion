import unittest
from src.classifier import parse_labels, ClassificationError

class ClassificationTests(unittest.TestCase):
    def test_parses_exact_number_of_known_labels(self):
        self.assertEqual(parse_labels('["concept","comparison","summary"]',3),['concept','comparison','summary'])
    def test_rejects_unknown_or_missing_labels(self):
        with self.assertRaises(ClassificationError): parse_labels('["unknown"]',1)
        with self.assertRaises(ClassificationError): parse_labels('["concept"]',2)
    def test_accepts_schema_object(self):
        self.assertEqual(parse_labels('{"labels":["concept","summary"]}',2),['concept','summary'])
