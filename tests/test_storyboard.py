import unittest
from src.storyboard import validate_storyboard, StoryboardError
from src.timeline import align_scenes

class StoryboardTests(unittest.TestCase):
    def test_rejects_blank_scenes_and_missing_matrix_values(self):
        with self.assertRaises(StoryboardError):
            validate_storyboard({'title':'例子','scenes':[]})
        with self.assertRaises(StoryboardError):
            validate_storyboard({'title':'例子','scenes':[{'text':'收益','visual_description':'表格','duration_seconds':5,'type':'matrix','data':{}}]})

    def test_valid_storyboard_preserves_chinese(self):
        data={'title':'囚徒困境','scenes':[{'text':'合作','visual_description':'标题','duration_seconds':5,'type':'concept','data':{}}]}
        self.assertEqual(validate_storyboard(data)['scenes'][0]['text'],'合作')

    def test_timeline_keeps_total_and_snaps_to_beat(self):
        result=align_scenes([7,7,6], [0,4,8,12,16,20])
        self.assertEqual(result, [0,8,16,20])

if __name__ == '__main__': unittest.main()
