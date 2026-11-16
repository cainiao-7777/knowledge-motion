import unittest
from src.style import choose_palette

class PaletteTests(unittest.TestCase):
    def test_accepts_high_contrast_colors(self):
        result=choose_palette({'background':'#121426','accent':'#c9aaff'})
        self.assertEqual(result['background'],'#121426')
        self.assertEqual(result['accent'],'#c9aaff')
    def test_unsafe_or_bright_background_uses_safe_default(self):
        result=choose_palette({'background':'red;evil','accent':'#000000'})
        self.assertEqual(result['background'],'#0a0c17')
        self.assertEqual(result['accent'],'#a690ef')
