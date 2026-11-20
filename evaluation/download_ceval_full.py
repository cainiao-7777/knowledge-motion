import json, urllib.request, urllib.parse
from pathlib import Path
base='https://datasets-server.huggingface.co/rows?'
params={'dataset':'ceval/ceval-exam','config':'computer_network','split':'val','offset':0,'length':100}
with urllib.request.urlopen(urllib.request.Request(base+urllib.parse.urlencode(params),headers={'User-Agent':'KnowledgeMotion/1.0'}),timeout=40) as r:
 data=json.load(r)
rows=[x['row'] for x in data['rows']]
if len(rows)!=data['num_rows_total'] or len(rows)!=19: raise ValueError('验证集返回不完整')
for x in rows:
 if not all(k in x for k in ('id','question','A','B','C','D','answer')):raise ValueError('缺少必要字段')
p=Path('data/ceval_computer_network_val_full.json')
p.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
print('验证题数',len(rows),'文件',p)

