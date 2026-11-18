"""Use a local small Ollama model to classify storyboard scene layouts.

This is prompt-based adaptation, not a trained classifier.
"""
import json
import os
import re
import urllib.request
from src.cancellation import check_cancelled

class ClassificationError(RuntimeError): pass

LABELS={'concept','comparison','summary','flow'}
# 默认小模型来自本机 Ollama；SMALL_MODEL 环境变量可切换本地模型。
DEFAULT_MODEL='modelscope.cn/unsloth/Qwen3.5-0.8B-GGUF:latest'

# 先看这幕在讲什么，再根据已有图形数据推荐程序能绘制的布局。
LAYOUT_GUIDANCE = """为单幕中文知识短片选布局。用主文字和补充字幕判断讲解目的，画面的排列与出场顺序只影响动画。
summary：回顾前文，归纳多个已讲过的例子，或收束观点。
concept：引出问题，解释概念、术语或单个现象。
flow：讲真实步骤或先后变化，且图形数据里的 nodes 能表达这些步骤。
comparison：在同一维度对照两项，且图形数据里提供 left 和 right。
如果图形数据明确为空，只在 concept 和 summary 中选。如果旧分镜未提供图形数据，根据文字及画面描述已有的讲解意图分类。只返回含 label 的 JSON 对象。"""

def parse_labels(text, count):
    # 严格确认本地小模型返回了指定数量且在允许集合内的类别。
    text=re.sub(r'^\s*```(?:json)?\s*|\s*```\s*$','',text,flags=re.I)
    try: labels=json.loads(text)
    except (ValueError,TypeError) as exc: raise ClassificationError('小模型返回格式无效') from exc
    if isinstance(labels,dict): labels=labels.get('labels')
    if not isinstance(labels,list) or len(labels)!=count or any(x not in LABELS for x in labels if isinstance(x,str)) or any(not isinstance(x,str) for x in labels):
        raise ClassificationError('小模型返回的类别无效或数量不匹配')
    return labels

def apply_scene_labels(scenes, labels):
    # 保留大模型明确设计且数据完整的画面；小模型补充布局建议。
    if len(scenes) != len(labels):
        raise ClassificationError('小模型类别数量与分镜不匹配')
    report=[]
    for scene, label in zip(scenes,labels):
        if label not in LABELS:
            raise ClassificationError('小模型返回的分镜类别无效')
        data=scene.get('data') if isinstance(scene.get('data'),dict) else {}
        # 大模型若已选布局且数据齐全就保留，否则用小模型建议作补充。
        requested=scene.get('type')
        # Keep a complete layout deliberately selected by the large model;
        # otherwise let the small model suggest a data-supported layout.
        candidate=requested if requested in ('comparison','flow','matrix','summary') else label
        chosen=candidate
        if chosen == 'matrix':
            cells=data.get('cells')
            if not isinstance(cells,list) or len(cells)!=4 or any(not isinstance(x,str) or not x.strip() for x in cells):
                chosen='concept'
        elif chosen == 'flow':
            nodes=data.get('nodes')
            if not isinstance(nodes,list) or len([x for x in nodes if isinstance(x,str) and x.strip()]) < 2:
                chosen=label if label in ('concept','summary') else 'concept'
        elif chosen == 'comparison':
            if not all(isinstance(data.get(x),str) and data[x].strip() for x in ('left','right')):
                chosen=label if label in ('concept','summary') else 'concept'
        scene['type']=chosen
        report.append({'predicted':label,'requested':requested,'chosen':chosen})
    return report

def classify_scenes(scenes,cancel_event=None):
    # 每幕单独请求 Ollama，避免小模型批量输出时重复同一个标签。
    labels=[]
    for scene in scenes:
        check_cancelled(cancel_event)
        # 只传与布局有关的数据，避免大段素材挤占小模型的上下文。
        data = scene.get('data')
        allowed_labels = LABELS
        if isinstance(data, dict):
            graph = {key: data[key] for key in ('left', 'right', 'nodes') if data.get(key)}
            description = {
                '主文字': scene['text'],
                '补充字幕': scene.get('caption', ''),
                '画面描述': scene['visual_description'],
                '图形数据': graph,
            }
            # 已知没有可用图形数据时，输出格式也限定在可以绘制的两种布局。
            if not graph:
                allowed_labels = {'concept', 'summary'}
            prompt = LAYOUT_GUIDANCE + '\n\n当前分镜：' + json.dumps(description, ensure_ascii=False)
        else:
            # 旧分镜没有 data 字段，继续按它的主文字和画面描述分类。
            description = {'text': scene['text'], 'description': scene['visual_description']}
            prompt = ('Choose exactly one label: concept=definition; comparison=compare alternatives; '
                      'flow=sequence of steps; summary=conclusion. Scene: '
                      + json.dumps(description, ensure_ascii=False))
        schema={'type':'object','properties':{'label':{'type':'string','enum':sorted(allowed_labels)}},'required':['label']}
        payload={'model':os.environ.get('SMALL_MODEL',DEFAULT_MODEL),'prompt':prompt,'stream':False,'think':False,'format':schema,'options':{'num_predict':80,'num_ctx':4096,'temperature':0}}
        req=urllib.request.Request('http://127.0.0.1:11434/api/generate',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=120) as response: result=json.load(response)
            check_cancelled(cancel_event)
            label=json.loads(result.get('response','')).get('label')
            if label not in allowed_labels: raise ClassificationError('小模型返回的分镜类别无效')
            labels.append(label)
        except (OSError,ValueError,AttributeError) as exc:
            raise ClassificationError('本地小模型调用失败，请检查 Ollama 和模型') from exc
    return labels
