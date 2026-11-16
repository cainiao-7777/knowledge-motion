"""Use a local small Ollama model to classify storyboard scene layouts.

This is prompt-based adaptation, not a trained classifier.
"""
import json
import os
import re
import urllib.request

class ClassificationError(RuntimeError): pass

LABELS={'concept','comparison','summary'}
DEFAULT_MODEL='modelscope.cn/unsloth/Qwen3.5-0.8B-GGUF:latest'

def parse_labels(text, count):
    text=re.sub(r'^\s*```(?:json)?\s*|\s*```\s*$','',text,flags=re.I)
    try: labels=json.loads(text)
    except (ValueError,TypeError) as exc: raise ClassificationError('小模型返回格式无效') from exc
    if isinstance(labels,dict): labels=labels.get('labels')
    if not isinstance(labels,list) or len(labels)!=count or any(x not in LABELS for x in labels if isinstance(x,str)) or any(not isinstance(x,str) for x in labels):
        raise ClassificationError('小模型返回的类别无效或数量不匹配')
    return labels

def classify_scenes(scenes):
    descriptions=[{'text':x['text'],'description':x['visual_description']} for x in scenes]
    prompt=('Classify each scene as concept, comparison or summary. Return ONLY a JSON array of labels, one per scene, same order. '
            'concept=explain idea; comparison=compare alternatives; summary=conclusion.\nScenes: '
            + json.dumps(descriptions,ensure_ascii=False))
    schema={'type':'object','properties':{'labels':{'type':'array','items':{'type':'string','enum':sorted(LABELS)},'minItems':len(scenes),'maxItems':len(scenes)}},'required':['labels']}
    payload={'model':os.environ.get('SMALL_MODEL',DEFAULT_MODEL),'prompt':prompt,'stream':False,'think':False,'format':schema,'options':{'num_predict':180,'num_ctx':4096,'temperature':0}}
    req=urllib.request.Request('http://127.0.0.1:11434/api/generate',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=120) as response: result=json.load(response)
        return parse_labels(result.get('response',''),len(scenes))
    except (OSError,ValueError) as exc:
        raise ClassificationError('本地小模型调用失败，请检查 Ollama 和模型') from exc
