"""Qwen storyboard generation through the Bailian OpenAI-compatible API."""
import json
import os
import re
import urllib.request
from src.storyboard import validate_storyboard, StoryboardError
from src.language import to_simplified, simplify_tree

class GenerationError(RuntimeError):
    pass

def read_api_key():
    # 优先读当前进程环境变量；Windows 用户变量在新进程启动时补读。
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
    # 模型有时会在 JSON 前后加说明；先直接解析，失败再从首个对象开始解析。
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

def complete_visual_descriptions(storyboard):
    """Supply a safe visual brief when the model omits a non-factual field."""
    # 只补画面构图说明，不代替模型捏造知识内容或数字。
    warnings=[]
    art=storyboard.get('art_direction',{})
    metaphor=art.get('visual_metaphor','') if isinstance(art,dict) else ''
    style=art.get('style','') if isinstance(art,dict) else ''
    composition=art.get('composition','') if isinstance(art,dict) else ''
    # JSON schema 仍可能漏掉非事实字段；只用已有文本/风格补画面说明。
    for index,scene in enumerate(storyboard.get('scenes',[]),1):
        description=scene.get('visual_description')
        if isinstance(description,str) and description.strip():
            continue
        subject=scene.get('text') or scene.get('caption') or '本幕重点'
        direction='；'.join(part[:100] for part in (style,metaphor,composition) if isinstance(part,str) and part.strip())
        scene['visual_description']=f'以“{subject[:80]}”为本幕视觉焦点，按照本片主题视觉设计呈现。'+(f' 视觉方向：{direction}' if direction else '')
        warnings.append(f'第{index}幕缺少画面描述，已按本片主题视觉设计补齐。')
    if warnings:
        storyboard['normalization_warnings']=warnings
    return storyboard

def plan_search_queries(topic, api_key=None, model=None):
    """Turn a one-line request into a concise topic and web-search query list."""
    key=read_api_key() if api_key is None else api_key
    if not key:
        raise GenerationError('请先设置 DASHSCOPE_API_KEY 环境变量')
    model=model or os.getenv('BAILIAN_MODEL','qwen4-max')
    prompt=('把用户的一句话需求拆成搜索用的核心主题和2到4个简短关键词。'
            '删除风格、时长和制作要求，保留人名、书名、作品名、领域术语；必要时加一个消歧词。'
            '不要回答主题，不要杜撰人物或事实，所有文字使用简体中文。只返回包含 main_topic 和 queries 的 JSON。'
            '\n用户输入：'+to_simplified(topic))
    schema={'type':'json_schema','json_schema':{'name':'search_query_plan','strict':True,'schema':{
        'type':'object','additionalProperties':False,
        'properties':{'main_topic':{'type':'string'},'queries':{'type':'array','items':{'type':'string'},'minItems':2,'maxItems':4}},
        'required':['main_topic','queries']}}}
    endpoint=os.getenv('BAILIAN_BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1').rstrip('/')+'/chat/completions'
    body=json.dumps({'model':model,'messages':[{'role':'user','content':prompt}],'max_tokens':600,'temperature':0.2,'enable_thinking':False,'response_format':schema},ensure_ascii=False).encode('utf-8')
    request=urllib.request.Request(endpoint,data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=60) as response:
            result=json.load(response)
        plan=simplify_tree(extract_json(result['choices'][0]['message']['content']))
        queries=[]
        for query in plan.get('queries',[]):
            if isinstance(query,str) and query.strip() and query.strip() not in queries:
                queries.append(query.strip())
        main_topic=plan.get('main_topic')
        if not isinstance(main_topic,str) or not main_topic.strip() or len(queries)<2:
            raise GenerationError('搜索关键词规划结果不完整')
        return {'main_topic':main_topic.strip(),'queries':queries[:4],'method':'qwen4-max'}
    except (OSError,KeyError,IndexError,TypeError,ValueError) as exc:
        raise GenerationError('大模型搜索词规划失败') from exc

def generate_storyboard(topic, sources, api_key=None, model=None, previous=None, revision=None):
    # 这是创作 prompt 的唯一入口：要求主题化风格和讲述口吻，但不固定幕数或叙事模板。
    # 把主题和检索资料交给百炼；创意结构由模型按主题决定，JSON 只约束字段。
    key = read_api_key() if api_key is None else api_key
    if not key:
        raise GenerationError('请先设置 DASHSCOPE_API_KEY 环境变量')
    topic=to_simplified(topic)
    if not topic or not topic.strip():
        raise GenerationError('请输入知识主题')
    if not sources:
        raise GenerationError('未找到资料来源，请重试检索')
    model = model or os.getenv('BAILIAN_MODEL', 'qwen4-max')
    endpoint = os.getenv('BAILIAN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1').rstrip('/') + '/chat/completions'
    source_text = '\n'.join(f"{s['title']} {s['url']} {s.get('snippet','')}" for s in sources)
    prompt = ('你是知识短片导演、视觉设计师和严谨的科普作者。制作无旁白简体中文知识动画，观众为普通大众，依据资料讲清主题。'
              '所有面向观众的title、text、caption以及叙事说明必须使用简体中文；检索资料即使是繁体，也要先转换为简体再表达。'
              '不要套用预设的幕数、镜头顺序、叙事弧线、画面布局、色板或示例模板。先理解这个主题，再自行决定需要讲几个信息点、如何推进、哪里停顿或转折、每幕时长、构图、视觉隐喻和整体风格。'
              '成片总时长目标约一分钟，按内容自然分段，镜头数量和各幕时长可变，不要求等长。'
              '讲解要有层次，不要停留在定义、口号或剧情简介：选择值得解释的核心问题，说明背景、机制、矛盾或人物处境如何联系，给出资料支持的具体例子，并指出结论成立的条件或适用边界。'
              '以讲述者身份直接讲知识，不写成检索报告或转述摘要。面向观众的title、text、caption和narrative_arc中禁止出现“我查到”“查阅资料”“资料显示”“据某网站/资料”“根据搜索结果”“来源提到”等检索过程措辞；把已经核实的信息自然讲出来。来源链接只保留在独立的sources清单，不念来源。'
              '每幕推进新信息，避免重复摘要；有限时长里讲透一个核心问题，不罗列浅层知识点。'
              '只输出JSON对象，包含字段：title（标题）；narrative_arc（本主题实际采用的叙事推进说明）；art_direction（本主题专属的风格描述、视觉隐喻、自由描述构图composition、背景色background、强调色accent、辅助色secondary、纹理motif）；scenes（按本主题需要决定数量的分镜数组）。'
              '每个scene包含text（语义完整、尽量精炼的观众主文字，复杂内容可自然换行）、caption（可有层次地补充背景、因果或边界，最多约90个中文字）、visual_description（具体构图、元素、运动和转场意图）、duration_seconds（本幕时长）及data（只有图形确实需要的数据才填写）。不要留下半句话或未完成的列表项。'
              '不要在输出中照抄字段说明或使用占位文字。风格由主题决定：文学作品可以考虑人物视角、留白、纸本文学或心理意象；科学概念可考虑空间、尺度或过程，但这些只是可能性，不是规定。请为当前主题重新判断，不要沿用其他主题的配色和叙事。'
              '渲染器会依据visual_description与data把分镜转成可用的图形画面；描述应具体可画。图形数据必须来自资料或明确标为示意，不得伪造数字、引用或因果。'
              '没有资料支持的细节要收窄结论，并在caption说明不确定性。'
              '\n用户主题：'+topic+'\n检索资料与来源：\n'+source_text)
    if previous is not None and revision:
        prompt += '\n这是现有分镜，请依据修改意见修改，保留无关内容：\n' + json.dumps(simplify_tree(previous), ensure_ascii=False) + '\n修改意见：' + to_simplified(revision)
    # JSON Schema 保证每幕字段齐全，但不指定幕数、顺序、颜色或故事模板。
    # JSON schema 只固定程序接口字段，不预设每幕内容、颜色或布局。
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
        storyboard=complete_visual_descriptions(simplify_tree(extract_json(content)))
        return validate_storyboard(storyboard)
    except StoryboardError as exc:
        raise GenerationError(f'分镜校验失败：{exc}') from exc
    except (OSError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise GenerationError('百炼调用失败或响应格式不正确，请检查网络、模型和额度') from exc
