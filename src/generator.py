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
    text = re.sub(r'^\s*```(?:json)?\s*|\s*```\s*$', '', text.strip(), flags=re.I)
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        start=text.find('{')
        if start<0:
            raise GenerationError('模型返回的内容不是有效 JSON，请重试') from exc
        try:
            value,_=json.JSONDecoder().raw_decode(text[start:])
        except json.JSONDecodeError:
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
    prompt = ('你是知识短片导演、视觉设计师和严谨的科普作者。制作无旁白中文知识动画，观众为普通大众，依据资料讲清主题。'
              '不要套用预设的幕数、镜头顺序、叙事弧线、画面布局、色板或示例模板。先理解这个主题，再自行决定需要讲几个信息点、如何推进、哪里停顿或转折、每幕时长、构图、视觉隐喻和整体风格。'
              '成片总时长目标约一分钟，按内容自然分段，镜头数量和各幕时长可变，不要求等长。'
              '讲解要有层次，不要停留在定义、口号或剧情简介：选择值得解释的核心问题，说明背景、机制、矛盾或人物处境如何联系，给出资料支持的具体例子，并指出结论成立的条件或适用边界。'
              '每幕推进新信息，避免重复摘要；有限时长里讲透一个核心问题，不罗列浅层知识点。'
              '只输出JSON对象，包含字段：title（标题）；narrative_arc（本主题实际采用的叙事推进说明）；art_direction（本主题专属的风格描述、视觉隐喻、自由描述构图composition、背景色background、强调色accent、辅助色secondary、纹理motif）；scenes（按本主题需要决定数量的分镜数组）。'
              '每个scene包含text（语义完整、尽量精炼的观众主文字，复杂内容可自然换行）、caption（可有层次地补充背景、因果或边界，最多约90个中文字）、visual_description（具体构图、元素、运动和转场意图）、duration_seconds（本幕时长）及data（只有图形确实需要的数据才填写）。不要留下半句话或未完成的列表项。'
              '不要在输出中照抄字段说明或使用占位文字。风格由主题决定：文学作品可以考虑人物视角、留白、纸本文学或心理意象；科学概念可考虑空间、尺度或过程，但这些只是可能性，不是规定。请为当前主题重新判断，不要沿用其他主题的配色和叙事。'
              '渲染器会依据visual_description与data把分镜转成可用的图形画面；描述应具体可画。图形数据必须来自资料或明确标为示意，不得伪造数字、引用或因果。'
              '没有资料支持的细节要收窄结论，并在caption说明不确定性。'
              '\n用户主题：'+topic+'\n检索资料与来源：\n'+source_text)
    if previous is not None and revision:
        prompt += '\n这是现有分镜，请依据修改意见修改，保留无关内容：\n' + json.dumps(previous, ensure_ascii=False) + '\n修改意见：' + revision
    response_schema={
        'type':'json_schema',
        'json_schema':{
            'name':'knowledge_video_storyboard',
            'strict':True,
            'schema':{
                'type':'object','additionalProperties':False,
                'properties':{
                    'title':{'type':'string'},
                    'narrative_arc':{'type':'string'},
                    'art_direction':{
                        'type':'object','additionalProperties':False,
                        'properties':{
                            'style':{'type':'string'},'visual_metaphor':{'type':'string'},'composition':{'type':'string'},
                            'background':{'type':'string'},'accent':{'type':'string'},
                            'secondary':{'type':'string'},'motif':{'type':'string'}
                        },
                        'required':['style','visual_metaphor','composition','background','accent','secondary','motif']
                    },
                    'scenes':{
                        'type':'array',
                        'items':{
                            'type':'object','additionalProperties':False,
                            'properties':{
                                'text':{'type':'string'},'caption':{'type':'string'},
                                'visual_description':{'type':'string'},
                                'duration_seconds':{'type':'number'},
                                'data':{'type':'object','additionalProperties':True}
                            },
                            'required':['text','caption','visual_description','duration_seconds','data']
                        }
                    }
                },
                'required':['title','narrative_arc','art_direction','scenes']
            }
        }
    }
    body = json.dumps({'model':model,'messages':[{'role':'user','content':prompt}], 'max_tokens':5000, 'temperature':0.7, 'enable_thinking':False, 'response_format':response_schema},ensure_ascii=False).encode('utf-8')
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
