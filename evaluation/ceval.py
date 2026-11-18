"""Pilot C-Eval knowledge questions: these do not evaluate video quality."""
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path
from src.generator import read_api_key,extract_json
from src.classifier import DEFAULT_MODEL
from src.evaluation import score_answers

def post_json(url, body, headers=None, timeout=120):
    # 云端和本地模型的请求都返回 JSON，因此共用这一层 HTTP 包装。
    request=urllib.request.Request(url,data=json.dumps(body,ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json',**(headers or {})})
    with urllib.request.urlopen(request,timeout=timeout) as response: return json.load(response)

def run():
    # 读取公开验证题，让两个模型使用同一题目集合进行小样本对照。
    rows=json.loads(Path('data/ceval_computer_network_val.json').read_text(encoding='utf-8'))
    items=rows[:10]
    questions=[{k:row[k] for k in ('question','A','B','C','D')} for row in items]
    prompt='请回答每个中文单项选择题，只返回 JSON 对象 {"answers":["A","B"]}，每题一个大写选项，保持原顺序：'+json.dumps(questions,ensure_ascii=False)
    key=read_api_key()
    if not key: raise RuntimeError('请先配置 DASHSCOPE_API_KEY')
    endpoint=os.environ.get('BAILIAN_BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1').rstrip('/')+'/chat/completions'
    cloud=post_json(endpoint,{'model':os.environ.get('BAILIAN_MODEL','qwen4-max'),'messages':[{'role':'user','content':prompt}],'max_tokens':2500}, {'Authorization':'Bearer '+key})
    cloud_answers=extract_json(cloud['choices'][0]['message']['content'])['answers']
    schema={'type':'object','properties':{'answers':{'type':'array','items':{'type':'string','enum':['A','B','C','D']},'minItems':len(items),'maxItems':len(items)}},'required':['answers']}
    local=post_json('http://127.0.0.1:11434/api/generate',{'model':os.environ.get('SMALL_MODEL',DEFAULT_MODEL),'prompt':prompt,'stream':False,'think':False,'format':schema,'options':{'num_predict':200,'num_ctx':4096,'temperature':0}})
    local_answers=json.loads(local['response'])['answers']
    report={'dataset':'C-Eval computer_network validation first 10 items','source':'https://huggingface.co/datasets/ceval/ceval-exam','license':'CC BY-NC-SA 4.0','date':datetime.now().isoformat(timespec='seconds'),'scope':'Tiny convenience sample; measures multiple-choice knowledge, not video generation or broad performance.','cloud':score_answers(items,cloud_answers),'small':score_answers(items,local_answers),'cloud_usage':cloud.get('usage',{})}
    dest=Path('outputs/evaluation/ceval.json');dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('cloud:',report['cloud']['correct'],'/',report['cloud']['total'])
    print('small:',report['small']['correct'],'/',report['small']['total'])
    print('output:',dest)

if __name__=='__main__': run()
