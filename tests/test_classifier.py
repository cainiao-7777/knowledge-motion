import unittest
from src.classifier import parse_labels, ClassificationError

class ClassificationTests(unittest.TestCase):
    # 检查分类标签解析、输出数量以及缺数据时的安全降级。
    def test_parses_exact_number_of_known_labels(self):
        self.assertEqual(parse_labels('["concept","comparison","summary"]',3),['concept','comparison','summary'])
    def test_rejects_unknown_or_missing_labels(self):
        with self.assertRaises(ClassificationError): parse_labels('["unknown"]',1)
        with self.assertRaises(ClassificationError): parse_labels('["concept"]',2)
    def test_accepts_schema_object(self):
        self.assertEqual(parse_labels('{"labels":["concept","summary"]}',2),['concept','summary'])
    def test_classifies_each_scene_independently(self):
        import io,json
        from unittest.mock import patch
        from src.classifier import classify_scenes
        scenes=[{'text':'定义','visual_description':'解释概念'},{'text':'对照','visual_description':'比较两种选择'}]
        replies=[io.BytesIO(json.dumps({'response':'{"label":"concept"}'}).encode()),io.BytesIO(json.dumps({'response':'{"label":"comparison"}'}).encode())]
        with patch('src.classifier.urllib.request.urlopen',side_effect=replies) as call:
            self.assertEqual(classify_scenes(scenes),['concept','comparison'])
            self.assertEqual(call.call_count,2)
    def test_missing_flow_data_uses_safe_concept_layout(self):
        from src.classifier import apply_scene_labels
        scene={'text':'讲解','visual_description':'流程','data':{}}
        report=apply_scene_labels([scene],['flow'])
        self.assertEqual(scene['type'],'concept')
        self.assertEqual(report[0]['predicted'],'flow')
        self.assertEqual(report[0]['chosen'],'concept')
