"""Evaluate all computer-network validation items and retain each answer."""
import json,os,sys,time,urllib.request
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path.cwd()))
from src.generator import read_api_key,extract_json
from src.classifier import DEFAULT_MODEL
from src.evaluation import score_answers
rows=json.loads(Path('data/ceval_computer_network_val_full.json').read_text(encoding='utf8'))
out=Path('outputs/evaluation/ceval_computer_network_val_full.json')
data={'dataset':'C-Eval computer_network val','source':'https://huggingface.co/datasets/ceval/ceval-exam','date':datetime.now().isoformat(timespec='seconds'),'sample_count':len(rows),'models':{},'scope':'计算机网络单科验证集全部19题；不代表全科、测试集或视频质量'}
def post(url,body,headers=None):
 req=urllib.request.Request(url,json.dumps(body,ensure_ascii=False).encode('utf8'),{'Content-Type':'application/json',**(headers or {})})
 with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
def persist():out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
def run(kind):
 model=DEFAULT_MODEL if kind=='small' else os.getenv('BAILIAN_MODEL','qwen4-max')
 key=read_api_key()
 entry={'model':model,'answers':[],'batches':[],'status':'running'}
 data['models'][kind]=entry;persist()
 for start in range(0,len(rows),5):
  chunk=rows[start:start+5]
  qs=[{k:x[k] for k in ('question','A','B','C','D')} for x in chunk]
  prompt='回答下面中文单选题。每题仅选择一个正确选项。只返回 JSON，格式为 {"answers":["A","B"]}，答案顺序与题目一致。题目：'+json.dumps(qs,ensure_ascii=False)
  try:
   if kind=='small':
    schema={'type':'object','properties':{'answers':{'type':'array','items':{'type':'string','enum':['A','B','C','D']},'minItems':len(chunk),'maxItems':len(chunk)}},'required':['answers']}
    res=post('http://127.0.0.1:11434/api/generate',{'model':model,'prompt':prompt,'stream':False,'think':False,'format':schema,'options':{'num_predict':150,'num_ctx':4096,'temperature':0}})
    answer=json.loads(res['response'])['answers'];usage={'prompt_eval_count':res.get('prompt_eval_count'),'eval_count':res.get('eval_count')}
   else:
    if not key:raise RuntimeError('未配置百炼密钥')
    url=os.getenv('BAILIAN_BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1').rstrip('/')+'/chat/completions'
    res=post(url,{'model':model,'messages':[{'role':'user','content':prompt}],'max_tokens':300,'temperature':0,'enable_thinking':False,'response_format':{'type':'json_object'}},{'Authorization':'Bearer '+key})
    answer=extract_json(res['choices'][0]['message']['content'])['answers'];usage=res.get('usage',{})
   if len(answer)!=len(chunk) or any(x not in 'ABCD' or len(x)!=1 for x in answer):raise ValueError('答案格式或数量无效')
   entry['answers']+=answer
   entry['batches'].append({'start':start,'count':len(chunk),'usage':usage})
   persist()
   print(kind,'完成',len(entry['answers']),'/',len(rows),flush=True)
  except Exception as e:
   entry['status']='failed';entry['error']=type(e).__name__+': '+str(e);persist();print(kind,'失败',entry['error'],flush=True);return
 entry['score']=score_answers(rows,entry['answers'])
 entry['status']='complete';persist()
 print(kind,'结果',entry['score'],flush=True)
run('small')
run('cloud')

