"""Keep user projects in separate local folders with atomic metadata writes."""
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

class ProjectError(ValueError): pass

def project_dir(root, project_id):
    try:
        if str(uuid.UUID(project_id)) != project_id: raise ValueError()
    except (ValueError, TypeError, AttributeError) as exc:
        raise ProjectError('作品编号无效') from exc
    return Path(root) / project_id

def create_project(root, topic):
    if not isinstance(topic,str) or not topic.strip(): raise ProjectError('请输入知识主题')
    item={'id':str(uuid.uuid4()),'topic':topic.strip(),'created':datetime.now().isoformat(timespec='seconds'),'notes':[],'sources':[],'storyboard':None,'status':'new'}
    project_dir(root,item['id']).mkdir(parents=True,exist_ok=False)
    save_project(root,item)
    return item

def save_project(root, item):
    folder=project_dir(root,item.get('id'))
    if not folder.is_dir(): raise ProjectError('作品不存在')
    temporary=folder/'project.json.tmp'
    temporary.write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(temporary,folder/'project.json')

def load_project(root, project_id):
    try: return json.loads((project_dir(root,project_id)/'project.json').read_text(encoding='utf-8'))
    except FileNotFoundError as exc: raise ProjectError('作品不存在') from exc

def list_projects(root):
    folder=Path(root)
    if not folder.exists(): return []
    items=[]
    for path in folder.iterdir():
        if path.is_dir():
            try: items.append(load_project(root,path.name))
            except (ProjectError,ValueError,json.JSONDecodeError): continue
    return sorted(items,key=lambda x:x.get('created',''),reverse=True)

def delete_project(root, project_id):
    """Permanently remove one UUID-scoped local project directory."""
    folder=project_dir(root,project_id)
    if not folder.is_dir():
        raise ProjectError('作品不存在')
    shutil.rmtree(folder)
