import unittest
from src.render import draw_scene

class RenderTests(unittest.TestCase):
    def test_renders_expected_frame_size(self):
        scene={'text':'合作与背叛','visual_description':'两个选择','duration_seconds':8,'type':'concept','data':{}}
        frame=draw_scene('囚徒困境',scene,0.5,1,4)
        self.assertEqual(frame.size,(1280,720))
        self.assertNotEqual(frame.getbbox(),None)

    def test_matrix_data_changes_rendered_image(self):
        base={'text':'收益矩阵','visual_description':'四种结果','duration_seconds':8,'type':'matrix','data':{'cells':['3 / 3','0 / 5','5 / 0','1 / 1']}}
        changed={**base,'data':{'cells':['8 / 8','0 / 5','5 / 0','1 / 1']}}
        a=draw_scene('囚徒困境',base,0.7,1,1)
        b=draw_scene('囚徒困境',changed,0.7,1,1)
        self.assertNotEqual(a.tobytes(),b.tobytes())
    def test_internal_visual_instructions_are_not_shown(self):
        scene={'text':'合作与背叛','visual_description':'画一个蓝色盒子','duration_seconds':8,'type':'concept','data':{}}
        different={**scene,'visual_description':'画一个红色盒子'}
        self.assertEqual(draw_scene('囚徒困境',scene,0.5,1,1).tobytes(),draw_scene('囚徒困境',different,0.5,1,1).tobytes())
    def test_comparison_and_concept_use_different_visual_layouts(self):
        scene={'text':'两个选项','visual_description':'左右比较','duration_seconds':8,'type':'concept','data':{}}
        compared={**scene,'type':'comparison'}
        from PIL import ImageChops
        self.assertIsNotNone(ImageChops.difference(draw_scene('主题',scene,0.5,1,1),draw_scene('主题',compared,0.5,1,1)).getbbox())
