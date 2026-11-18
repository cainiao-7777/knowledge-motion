"""Local-only web interface for the work-in-progress video generator."""
import json
import re
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from src.projects import list_projects, load_project, save_project, project_dir, delete_project, ProjectError
from src.pipeline import create_video_project, revise_video_project

# 以 app.py 所在目录作为项目根目录，工作目录变化也不会影响资源定位。
ROOT=Path(__file__).resolve().parent
# 所有作品、视频、来源和修改历史都保存在这个本机目录。
OUTPUT=ROOT/'outputs'/'projects'
# Web 服务只绑定本机地址，8765 是浏览器访问端口。
PORT=8765
# 记录正在修改的作品编号，防止同一作品并发重渲染。
active_revisions=set()
revision_lock=threading.Lock()
# 新作品渲染很耗时，暂时一次只允许一个新生成任务。
generation_lock=threading.Lock()
OPERATION_TIMEOUT_SECONDS=5*60

def run_with_timeout(cancel_event, operation, *args):
    # The event lets pipeline stages stop cooperatively at the five-minute limit.
    timer=threading.Timer(OPERATION_TIMEOUT_SECONDS,cancel_event.set)
    timer.daemon=True
    timer.start()
    try:
        operation(*args,cancel_event=cancel_event)
    finally:
        timer.cancel()

def generation_worker(topic, cancel_event):
    # 在线程里运行生成流程，HTTP 请求可先返回，不必等视频渲染结束。
    try:
        run_with_timeout(cancel_event,create_video_project,OUTPUT,topic)
    finally:
        generation_lock.release()

def revise_worker(project_id, instruction, cancel_event):
    # 无论修改成功还是失败，都要解除“正在修改”标记。
    try:
        run_with_timeout(cancel_event,revise_video_project,OUTPUT,project_id,instruction)
    finally:
        with revision_lock:
            active_revisions.discard(project_id)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def respond(self, status, body, mime='application/json; charset=utf-8'):
        # HTTP 正文必须是字节；统一 UTF-8，避免中文在浏览器显示乱码。
        if not isinstance(body, bytes): body=body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(body)

    def reply_json(self,status,data):
        self.respond(status,json.dumps(data,ensure_ascii=False))

    def respond_video(self,file):
        # 浏览器拖动视频进度条时会请求某一段字节，不能每次强制重传整部 MP4。
        size=file.stat().st_size
        header=self.headers.get('Range','')
        if not header:
            # 普通播放请求：完整返回文件，同时声明服务器支持按字节范围读取。
            self.send_response(200)
            self.send_header('Content-Type','video/mp4')
            self.send_header('Content-Length',str(size))
            self.send_header('Accept-Ranges','bytes')
            self.send_header('Cache-Control','no-store')
            self.end_headers()
            with file.open('rb') as stream:
                shutil.copyfileobj(stream,self.wfile)
            return
        # 只接受一个合法的 bytes 范围；其他格式按HTTP 416拒绝。
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',header.strip())
        if not match or (not match.group(1) and not match.group(2)):
            self.send_response(416)
            self.send_header('Content-Range',f'bytes */{size}')
            self.end_headers()
            return
        if match.group(1):
            # 处理 bytes=起点-终点，或 bytes=起点-（一直到文件尾）。
            start=int(match.group(1)); end=int(match.group(2)) if match.group(2) else size-1
        else:
            # 处理 bytes=-N：读取文件末尾N个字节，浏览器常用它探测MP4索引。
            suffix=int(match.group(2)); start=max(0,size-suffix); end=size-1
        if start>=size or end<start:
            self.send_response(416)
            self.send_header('Content-Range',f'bytes */{size}')
            self.end_headers()
            return
        end=min(end,size-1)
        length=end-start+1
        # 返回部分内容206及Content-Range，浏览器才能随机跳播。
        self.send_response(206)
        self.send_header('Content-Type','video/mp4')
        self.send_header('Content-Length',str(length))
        self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        with file.open('rb') as stream:
            stream.seek(start)
            self.wfile.write(stream.read(length))

    def do_GET(self):
        # GET 只读：提供页面资源、作品列表、作品元数据和本地文件。
        if self.headers.get('Host') != f'127.0.0.1:{PORT}':
            return self.reply_json(403,{'error':'无效请求来源'})
        path=urlsplit(self.path).path
        if path=='/':
            return self.respond(200,(ROOT/'web'/'index.html').read_bytes(),'text/html; charset=utf-8')
        assets={'/assets/style.css':('style.css','text/css; charset=utf-8'),
                '/assets/app.js':('app.js','text/javascript; charset=utf-8')}
        if path in assets:
            # 静态文件只允许访问上述白名单，避免拼接任意文件路径。
            name,mime=assets[path]
            return self.respond(200,(ROOT/'web'/name).read_bytes(),mime)
        if path=='/api/projects':
            # 列表接口返回本地所有作品，前端负责搜索和分页。
            return self.reply_json(200,list_projects(OUTPUT))
        parts=path.strip('/').split('/')
        if len(parts)==3 and parts[:2]==['api','projects']:
            # 返回单条作品元数据；UUID无效或项目不存在时返回404。
            try: return self.reply_json(200,load_project(OUTPUT,parts[2]))
            except (ProjectError,ValueError): return self.reply_json(404,{'error':'作品不存在'})
        if len(parts)==3 and parts[0]=='files' and parts[2] in ('video.mp4','sources.md'):
            # 文件名也设白名单；作品目录通过project_dir再次校验UUID。
            try:
                file=project_dir(OUTPUT,parts[1])/parts[2]
                if parts[2]=='video.mp4':
                    return self.respond_video(file)
                mime='video/mp4' if parts[2].endswith('mp4') else 'text/markdown; charset=utf-8'
                return self.respond(200,file.read_bytes(),mime)
            except (ProjectError,OSError): return self.reply_json(404,{'error':'文件不存在'})
        return self.reply_json(404,{'error':'页面不存在'})

    def do_POST(self):
        # POST 接收新主题或自然语言修改意见，并检查同源与输入长度。
        if self.headers.get('Host') != f'127.0.0.1:{PORT}' or self.headers.get('Origin') != f'http://127.0.0.1:{PORT}':
            return self.reply_json(403,{'error':'无效请求来源'})
        path=urlsplit(self.path).path
        if path != '/api/generate' and not path.startswith('/api/revise/'):
            return self.reply_json(404,{'error':'页面不存在'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            # 限制请求体大小，主题/修改意见的字符长度在解析后再检查。
            if length <= 0 or length > 4096: raise ValueError()
            payload=json.loads(self.rfile.read(length))
            if path.startswith('/api/revise/'):
                # 修改只允许针对已完成作品；锁内检查可以避免和删除操作竞态。
                instruction=payload.get('instruction','').strip()
                project_id=path.removeprefix('/api/revise/')
                if not instruction or len(instruction)>500: raise ValueError()
                # 在锁内检查状态并登记任务，避免同一作品同时修改和删除。
                with revision_lock:
                    if project_id in active_revisions:
                        return self.reply_json(409,{'error':'作品正在修改'})
                    project=load_project(OUTPUT,project_id)
                    if project['status'] != 'complete':
                        return self.reply_json(409,{'error':'作品尚未完成或正在修改'})
                    active_revisions.add(project_id)
                cancel_event=threading.Event()
                threading.Thread(target=revise_worker,args=(project_id,instruction,cancel_event),daemon=True).start()
                return self.reply_json(202,{'message':'正在修改，原视频会保留'})
            topic=payload.get('topic','').strip()
            if not topic or len(topic)>150: raise ValueError()
        except (ValueError,AttributeError,json.JSONDecodeError,ProjectError):
            return self.reply_json(400,{'error':'输入无效，请检查主题或修改意见'})
        if not generation_lock.acquire(blocking=False):
            # 有生成任务时直接返回409，不让第二个任务静默排队。
            return self.reply_json(409,{'error':'已有视频正在生成，请等待完成'})
        try:
            cancel_event=threading.Event()
            threading.Thread(target=generation_worker,args=(topic,cancel_event),daemon=True).start()
        except Exception:
            generation_lock.release()
            raise
        return self.reply_json(202,{'message':'开始生成，请在作品列表查看进度'})

    def do_DELETE(self):
        # 删除是破坏性操作；前端先二次确认，服务端再拒绝删除运行中的作品。
        if self.headers.get('Host') != f'127.0.0.1:{PORT}' or self.headers.get('Origin') != f'http://127.0.0.1:{PORT}':
            return self.reply_json(403,{'error':'无效请求来源'})
        path=urlsplit(self.path).path
        parts=path.strip('/').split('/')
        if len(parts)!=3 or parts[:2]!=['api','projects']:
            return self.reply_json(404,{'error':'页面不存在'})
        try:
            # 只有完成或失败的作品可删除；锁防止和修改线程竞争。
            with revision_lock:
                project=load_project(OUTPUT,parts[2])
                if parts[2] in active_revisions or project.get('status') in ('new','planning_search','researching','writing','classifying','rendering','revising'):
                    return self.reply_json(409,{'error':'作品正在生成或修改，暂时不能删除'})
                delete_project(OUTPUT,parts[2])
        except ProjectError as exc:
            return self.reply_json(404,{'error':str(exc)})
        except OSError:
            return self.reply_json(500,{'error':'删除失败，请确认项目文件未被其他程序占用'})
        return self.reply_json(200,{'message':'作品及其本地文件已删除'})

def recover_interrupted_projects():
    # Restarted servers cannot resume Python worker threads; close stale statuses safely.
    for project in list_projects(OUTPUT):
        if project.get('status') not in ('new','planning_search','researching','writing','classifying','rendering','revising'):
            continue
        folder=project_dir(OUTPUT,project['id'])
        for partial in folder.glob('candidate-*.mp4'):
            partial.unlink(missing_ok=True)
        video=folder/'video.mp4'
        if project.get('status')=='revising' and video.is_file():
            project['status']='complete'
            project['revision_notice']='服务重启时，本次修改已中断，原视频已保留。'
        elif project.get('status')=='rendering' and video.is_file() and video.stat().st_size>0:
            project['status']='complete'
            project['error']=''
        else:
            project['status']='cancelled'
            project['error']='服务重启时，生成任务已中断。'
        save_project(OUTPUT,project)

if __name__=='__main__':
    # 直接运行 python app.py 时启动本机开发服务器。
    # 上次进程中断后，线程无法恢复；先收尾遗留的活动状态。
    recover_interrupted_projects()
    print(f'知识动画工作台：http://127.0.0.1:{PORT}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
