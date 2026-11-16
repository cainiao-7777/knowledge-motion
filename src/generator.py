"""Qwen storyboard generation through the Bailian OpenAI-compatible API."""
import json
import os
import re
import urllib.request
from src.storyboard import validate_storyboard, StoryboardError

class GenerationError(RuntimeError):
    pass

def read_api_key():
    key = os.environ.get('DASHSCOPE_API_KEY', '')
    if key or os.name != 'nt':
        return key
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as registry:
            value, _ = winreg.QueryValueEx(registry, 'DASHSCOPE_API_KEY')
        return value if isinstance(value, str) else ''
    except OSError:
        return ''

def extract_json(text):
    text = re.sub(r'^\s*```(?:json)?\s*|\s*```\s*$', '', text, flags=re.I)
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise GenerationError('模型返回的内容不是有效 JSON，请重试') from exc
    if not isinstance(value, dict):
        raise GenerationError('模型返回的 JSON 必须是对象')
    return value

def generate_storyboard(topic, sources, api_key=None, model=None, previous=None, revision=None):
    key = read_api_key() if api_key is None else api_key
    if not key:
        raise GenerationError('请先设置 DASHSCOPE_API_KEY 环境变量')
    if not topic or not topic.strip():
        raise GenerationError('请输入知识主题')
    if not sources:
        raise GenerationError('未找到资料来源，请重试检索')
    model = model or os.getenv('BAILIAN_MODEL', 'qwen4-max')
    endpoint = os.getenv('BAILIAN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1').rstrip('/') + '/chat/completions'
    source_text = '\n'.join(f"{s['title']} {s['url']} {s.get('snippet','')}" for s in sources)
    prompt = ('为普通大众制作无旁白中文知识动画，依据资料编写约60秒共5幕。只输出JSON对象：'
              '{"title":"标题","palette":{"background":"#101326","accent":"#c8adff"},"scenes":[{"text":"不超过30字的屏幕文字",'
              '"caption":"不超过45字的补充解释，供观众阅读",'
              '"visual_description":"供系统使用的画面描述，不会显示给观众","duration_seconds":12,"type":"concept","data":{"left":"对比左侧短标签","right":"对比右侧短标签"}}]}。'
              'palette按主题设计背景与强调色，均为六位十六进制颜色且保持较高对比度。只有明确涉及两项对比的分镜才填写data中的left和right（每个最多7个字），其余data使用空对象。所有type均为concept，使用文字解释，不要虚构事实、数字和引用。\n主题：'+topic+'\n资料：\n'+source_text)
    if previous is not None and revision:
        prompt += '\n这是现有分镜，请依据修改意见修改，保留无关内容：\n' + json.dumps(previous, ensure_ascii=False) + '\n修改意见：' + revision
    body = json.dumps({'model':model,'messages':[{'role':'user','content':prompt}], 'max_tokens':2500, 'temperature':0.5},ensure_ascii=False).encode('utf-8')
    request=urllib.request.Request(endpoint,data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=120) as response:
            result=json.load(response)
        content=result['choices'][0]['message']['content']
        return validate_storyboard(extract_json(content))
    except StoryboardError as exc:
        raise GenerationError(f'分镜校验失败：{exc}') from exc
    except (OSError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise GenerationError('百炼调用失败或响应格式不正确，请检查网络、模型和额度') from exc
