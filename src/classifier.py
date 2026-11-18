"""Use a local small Ollama model to classify storyboard scene layouts.

This is prompt-based adaptation, not a trained classifier.
"""
import json
import os
import re
import urllib.request

class ClassificationError(RuntimeError): pass

LABELS={'concept','comparison','summary','flow'}
# 默认小模型来自本机 Ollama；SMALL_MODEL 环境变量可切换本地模型。
DEFAULT_MODEL='modelscope.cn/unsloth/Qwen3.5-0.8B-GGUF:latest'

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

def classify_scenes(scenes):
    # 每幕单独请求 Ollama，避免小模型批量输出时重复同一个标签。
    labels=[]
    schema={'type':'object','properties':{'label':{'type':'string','enum':sorted(LABELS)}},'required':['label']}
    for scene in scenes:
        description={'text':scene['text'],'description':scene['visual_description']}
        prompt=('Choose exactly one label: concept=definition; comparison=compare alternatives; '
                'flow=sequence of steps; summary=conclusion. Scene: '+json.dumps(description,ensure_ascii=False))
        payload={'model':os.environ.get('SMALL_MODEL',DEFAULT_MODEL),'prompt':prompt,'stream':False,'think':False,'format':schema,'options':{'num_predict':80,'num_ctx':4096,'temperature':0}}
        req=urllib.request.Request('http://127.0.0.1:11434/api/generate',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=120) as response: result=json.load(response)
            label=json.loads(result.get('response','')).get('label')
            if label not in LABELS: raise ClassificationError('小模型返回的分镜类别无效')
            labels.append(label)
        except (OSError,ValueError,AttributeError) as exc:
            raise ClassificationError('本地小模型调用失败，请检查 Ollama 和模型') from exc
    return labels
