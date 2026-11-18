"""Keep user projects in separate local folders with atomic metadata writes."""
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

class ProjectError(ValueError): pass

def project_dir(root, project_id):
    # 项目编号必须是 UUID；避免 URL 中的路径穿越到作品目录之外。
    try:
        if str(uuid.UUID(project_id)) != project_id: raise ValueError()
    except (ValueError, TypeError, AttributeError) as exc:
        raise ProjectError('作品编号无效') from exc
    return Path(root) / project_id

def create_project(root, topic):
    # 每个主题创建独立 UUID 文件夹，后续元数据和视频不会互相覆盖。
    if not isinstance(topic,str) or not topic.strip(): raise ProjectError('请输入知识主题')
    item={'id':str(uuid.uuid4()),'topic':topic.strip(),'created':datetime.now().isoformat(timespec='seconds'),'notes':[],'sources':[],'storyboard':None,'status':'new'}
    project_dir(root,item['id']).mkdir(parents=True,exist_ok=False)
    save_project(root,item)
    return item

def save_project(root, item):
    # 先写临时 JSON 再原子替换，避免程序中断时留下半截项目记录。
    folder=project_dir(root,item.get('id'))
    if not folder.is_dir(): raise ProjectError('作品不存在')
    temporary=folder/'project.json.tmp'
    temporary.write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(temporary,folder/'project.json')

def load_project(root, project_id):
    # 按 UUID 读取项目状态；找不到时转为清晰的业务错误。
    try: return json.loads((project_dir(root,project_id)/'project.json').read_text(encoding='utf-8'))
    except FileNotFoundError as exc: raise ProjectError('作品不存在') from exc

def list_projects(root):
    # 只读每个子目录的 project.json，并按创建时间从新到旧排列。
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
    # 只删除经过 UUID 校验的单个作品目录，其中含视频、来源和历史版本。
    folder=project_dir(root,project_id)
    if not folder.is_dir():
        raise ProjectError('作品不存在')
    shutil.rmtree(folder)
