"""Download a small C-Eval validation sample for non-commercial study."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

# 只下载10条计算机网络验证题，作为低成本的基础知识试验样本。
params={'dataset':'ceval/ceval-exam','config':'computer_network','split':'val','offset':0,'length':10}
url='https://datasets-server.huggingface.co/rows?'+urllib.parse.urlencode(params)
request=urllib.request.Request(url,headers={'User-Agent':'KnowledgeMotion/0.1 educational'})
with urllib.request.urlopen(request,timeout=40) as response:
    data=json.load(response)
rows=[record['row'] for record in data['rows']]
if len(rows)!=10 or any(not all(k in row for k in ('id','question','A','B','C','D','answer')) for row in rows):
    raise RuntimeError('数据集返回内容不完整，请检查来源')
destination=Path('data/ceval_computer_network_val.json')
destination.parent.mkdir(parents=True,exist_ok=True)
destination.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('已下载',len(rows),'条验证题到',destination)
