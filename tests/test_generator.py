import json
import unittest
from src.generator import extract_json, generate_storyboard, GenerationError
from src.research import normalize_results

class GeneratorTests(unittest.TestCase):
    # 检查 JSON 提取、缺密钥保护，以及检索来源链接过滤。
    def test_fenced_json_can_be_parsed(self):
        self.assertEqual(extract_json('```json\n{"title":"主题"}\n```')['title'], '主题')

    def test_bad_output_is_clear_error(self):
        with self.assertRaises(GenerationError): extract_json('不是 JSON')

    def test_missing_key_fails_before_network(self):
        with self.assertRaisesRegex(GenerationError, 'DASHSCOPE_API_KEY'):
            generate_storyboard('囚徒困境', [], api_key='')

    def test_research_results_keep_real_urls_only(self):
        result=normalize_results([{'title':'A','url':'https://example.com/a','snippet':'解释'}, {'title':'坏地址','url':'javascript:alert(1)'}])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['url'], 'https://example.com/a')

if __name__ == '__main__': unittest.main()
