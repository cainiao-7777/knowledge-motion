"""Local-only web interface for the work-in-progress video generator."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from src.projects import list_projects, load_project, project_dir, ProjectError
from src.pipeline import create_video_project, revise_video_project

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'outputs'/'projects'
PORT=8765
active_revisions=set()
revision_lock=threading.Lock()
generation_lock=threading.Lock()

def generation_worker(topic):
    try:
        create_video_project(OUTPUT,topic)
    finally:
        generation_lock.release()

def revise_worker(project_id, instruction):
    try:
        revise_video_project(OUTPUT,project_id,instruction)
    finally:
        with revision_lock:
            active_revisions.discard(project_id)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def respond(self, status, body, mime='application/json; charset=utf-8'):
        if not isinstance(body, bytes): body=body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(body)

    def reply_json(self,status,data):
        self.respond(status,json.dumps(data,ensure_ascii=False))

    def do_GET(self):
        if self.headers.get('Host') != f'127.0.0.1:{PORT}':
            return self.reply_json(403,{'error':'无效请求来源'})
        path=urlsplit(self.path).path
        if path=='/':
            return self.respond(200,(ROOT/'web'/'index.html').read_bytes(),'text/html; charset=utf-8')
        if path=='/api/projects':
            return self.reply_json(200,list_projects(OUTPUT))
        parts=path.strip('/').split('/')
        if len(parts)==3 and parts[:2]==['api','projects']:
            try: return self.reply_json(200,load_project(OUTPUT,parts[2]))
            except (ProjectError,ValueError): return self.reply_json(404,{'error':'作品不存在'})
        if len(parts)==3 and parts[0]=='files' and parts[2] in ('video.mp4','sources.md'):
            try:
                file=project_dir(OUTPUT,parts[1])/parts[2]
                mime='video/mp4' if parts[2].endswith('mp4') else 'text/markdown; charset=utf-8'
                return self.respond(200,file.read_bytes(),mime)
            except (ProjectError,OSError): return self.reply_json(404,{'error':'文件不存在'})
        return self.reply_json(404,{'error':'页面不存在'})

    def do_POST(self):
        if self.headers.get('Host') != f'127.0.0.1:{PORT}' or self.headers.get('Origin') != f'http://127.0.0.1:{PORT}':
            return self.reply_json(403,{'error':'无效请求来源'})
        path=urlsplit(self.path).path
        if path != '/api/generate' and not path.startswith('/api/revise/'):
            return self.reply_json(404,{'error':'页面不存在'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length <= 0 or length > 4096: raise ValueError()
            payload=json.loads(self.rfile.read(length))
            if path.startswith('/api/revise/'):
                instruction=payload.get('instruction','').strip()
                project_id=path.removeprefix('/api/revise/')
                if not instruction or len(instruction)>500: raise ValueError()
                project=load_project(OUTPUT,project_id)
                if project['status'] != 'complete':
                    return self.reply_json(409,{'error':'作品尚未完成或正在修改'})
                with revision_lock:
                    if project_id in active_revisions:
                        return self.reply_json(409,{'error':'作品正在修改'})
                    active_revisions.add(project_id)
                threading.Thread(target=revise_worker,args=(project_id,instruction),daemon=True).start()
                return self.reply_json(202,{'message':'正在修改，原视频会保留'})
            topic=payload.get('topic','').strip()
            if not topic or len(topic)>150: raise ValueError()
        except (ValueError,AttributeError,json.JSONDecodeError,ProjectError):
            return self.reply_json(400,{'error':'输入无效，请检查主题或修改意见'})
        if not generation_lock.acquire(blocking=False):
            return self.reply_json(409,{'error':'已有视频正在生成，请等待完成'})
        try:
            threading.Thread(target=generation_worker,args=(topic,),daemon=True).start()
        except Exception:
            generation_lock.release()
            raise
        return self.reply_json(202,{'message':'开始生成，请在作品列表查看进度'})

if __name__=='__main__':
    print(f'知识动画工作台：http://127.0.0.1:{PORT}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
