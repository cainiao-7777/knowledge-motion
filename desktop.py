"""赛博图书馆 Windows 桌面入口。"""
import os
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

import app


def open_studio():
    url = f'http://127.0.0.1:{app.PORT}/'
    for location in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA'):
        edge = Path(os.environ.get(location, '')) / 'Microsoft/Edge/Application/msedge.exe'
        if edge.is_file():
            subprocess.Popen([str(edge), '--app=' + url])
            return
    webbrowser.open(url)


def main():
    window = tk.Tk()
    window.title('赛博图书馆 · 桌面控制台')
    icon = Path(__file__).with_name('library.ico')
    if icon.exists():
        window.iconbitmap(str(icon))
    window.withdraw()
    # 安装目录只放程序。作品留在用户数据目录，更新和卸载都能保留。
    app.OUTPUT = Path(os.getenv('KNOWLEDGE_PROJECTS') or
                      Path(os.environ['LOCALAPPDATA']) / 'KnowledgeMotion' / 'projects')
    try:
        # 先取得端口，再恢复中断记录，防止重复启动影响正在运行的任务。
        server = app.ThreadingHTTPServer(('127.0.0.1', app.PORT), app.Handler)
    except OSError:
        messagebox.showinfo('赛博图书馆', '本机 8765 端口正在使用。请切回已打开的工作台，或退出旧版服务后重试。', parent=window)
        window.destroy()
        return
    try:
        app.OUTPUT.mkdir(parents=True, exist_ok=True)
        app.recover_interrupted_projects()
        threading.Thread(target=server.serve_forever, daemon=True).start()
        frame = ttk.Frame(window, padding=22)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='赛博图书馆', font=('Microsoft YaHei UI', 18)).pack(anchor='w')
        ttk.Label(frame, text='关闭创作窗口后，可从这里重新打开。').pack(anchor='w', pady=(6,14))
        ttk.Button(frame, text='打开创作台', command=open_studio).pack(fill='x')
        ttk.Button(frame, text='查看本地作品文件', command=lambda: os.startfile(app.OUTPUT)).pack(fill='x', pady=6)
        def leave():
            if app.generation_lock.locked() or app.active_revisions:
                messagebox.showinfo('任务进行中', '请先在创作台结束任务，再退出应用。', parent=window)
                return
            window.destroy()
        window.protocol('WM_DELETE_WINDOW', leave)
        window.deiconify()
        open_studio()
        window.mainloop()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()

