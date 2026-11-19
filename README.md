# 赛博图书馆 · 知识大赏

Windows x64 桌面应用，版本 **1.0.0**，已完工并可安装。输入一句中文主题，应用会提炼搜索词、检索公开资料、编排分镜，让本机小模型为每幕选择布局，再把字幕、图形和配乐合成为 MP4。完成后可以查看来源、提出修改，或在本地馆藏中检索作品。

## 安装桌面版

1. 已拿到安装包的用户，双击 `KnowledgeMotion-1.0.0-Windows-x64-Setup.exe`。它会为当前 Windows 用户安装程序，并创建开始菜单和桌面快捷方式。安装版内含 Python 及应用所需的 Python 库。
2. 只有 GitHub 源码的用户，可按下文「从源码启动」直接使用，或按「制作安装包」在本机生成同一安装程序。安装包没有上传到 GitHub Releases。
3. 配置下面的模型和配乐后，从开始菜单打开「赛博图书馆」。它会启动本机服务和独立的 Edge 创作窗口。找不到 Edge 时使用默认浏览器。关闭创作窗口后，可从桌面控制台重新打开。退出整个应用请关闭控制台。

## 首次配置

| 准备项 | 怎么做 |
| --- | --- |
| FFmpeg | 在 PowerShell 执行 `winget install --id Gyan.FFmpeg -e`，重新打开终端，执行 `ffmpeg -version` 确认可用。 |
| 本机小模型 | 安装 [Ollama for Windows](https://ollama.com/download/windows) 并启动。执行 `ollama list`。默认标签是 `modelscope.cn/unsloth/Qwen3.5-0.8B-GGUF:latest`。若标签尚未下载，执行 `ollama pull modelscope.cn/unsloth/Qwen3.5-0.8B-GGUF:latest`。已有其他可用的 Qwen 0.8B 模型时，将用户环境变量 `SMALL_MODEL` 填为 Ollama 列出的完整标签。应用通过本机 11434 端口访问 Ollama。 |
| 云端大模型 | 在百炼开通模型，并在 Windows 搜索「编辑帐户的环境变量」，新建用户变量 `DASHSCOPE_API_KEY`，值填入自己的密钥。默认模型 ID 为 `qwen4-max`。按账号权限可通过 `BAILIAN_MODEL` 覆盖。默认北京地址 `https://dashscope.aliyuncs.com/compatible-mode/v1`，其他地域可设置 `BAILIAN_BASE_URL`。生成、修改会消耗百炼额度，请先在控制台查看额度和计费设置。 |
| 本地配乐 | 准备有权使用的音乐文件。新建用户变量 `KNOWLEDGE_MUSIC`，值填入音乐的完整路径，如 `D:\Music\我的配乐.mp3`。音乐不包含在安装包中。 |
| 中文字体 | Windows 需有微软雅黑或黑体，供视频字幕渲染使用。 |

设置完变量后退出桌面控制台并重新启动。资料检索需要联网。主题和检索词会发往搜索服务，主题、检索摘要或修改意见会发往百炼。密钥、配乐、模型权重和个人作品应只保存在本机。

## 使用与作品管理

输入主题，点「开始生成」，在「作品馆藏」看进度。成片可拖动进度条，可查看资料清单。生成时的「删除任务」会停止后续操作，在线程结束后清理文件。修改时的「暂停修改」会保留修改前的成片和分镜，成功提交的新版本会成为当前成片。自动超时门槛为 5 分钟，已发送的网络请求可能要等到响应或请求自身超时才结束。请核对成片中的知识表述与实际来源。

- **桌面版作品目录**为 `%LOCALAPPDATA%\KnowledgeMotion\projects`，可用控制台的「查看本地作品文件」打开。每个作品有独立目录，包含 `project.json`、`sources.md`，成功生成后有 `video.mp4`。修改成功可能产生历史 MP4。
- **从旧网页版迁移**时，先退出旧服务。在首次启动前，将旧仓库 `outputs\projects` 中的作品子目录复制到桌面版作品目录。也可设置用户变量 `KNOWLEDGE_PROJECTS` 指向旧的 `outputs\projects` 完整路径，直接使用原来的馆藏。避免两个服务同时写同一馆藏。
- **升级**时关闭桌面控制台，备份作品目录，再运行新版安装包并选择同一安装位置。**卸载**时在 Windows「设置 → 应用 → 已安装的应用」找到「赛博图书馆」。作品单独存储，卸载后仍可备份或手动删除。工作台里的「删除作品」会永久删除该作品的视频、来源和历史。

## 从源码启动

在已装 Git 和 64 位 Python 3.13 的 Windows 上打开 PowerShell，执行以下命令，再完成上面的首次配置。

```powershell
git clone https://github.com/cainiao-7777/knowledge-motion.git
cd knowledge-motion
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe desktop.py
```

也可用同一解释器执行 `app.py`，在浏览器中打开 `http://127.0.0.1:8765/`。这一路径将作品写入仓库的 `outputs/projects/`。桌面版和网页版使用同一端口，每次启动其中一个即可。

## 制作安装包

先完成「从源码启动」中的 Python 环境安装。安装 [Inno Setup 6.7.3](https://jrsoftware.org/isinfo.php)，非商业用途可使用其免费构建器。在仓库根目录执行以下命令，并按实际安装位置修改 `ISCC.exe` 路径。

```powershell
.\.venv\Scripts\python.exe -m pip install PyInstaller==6.22.3
powershell -NoProfile -ExecutionPolicy Bypass -File .\packaging\build.ps1 -Python .\.venv\Scripts\python.exe -Iscc "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

生成物位于 `outputs/release/KnowledgeMotion-1.0.0-Windows-x64-Setup.exe`。构建脚本打包桌面入口、工作台网页、运行库、使用说明、MIT 许可证和第三方运行组件许可文本。FFmpeg、Ollama、模型与配乐由用户自行配置。安装包保存在本机，仓库没有 GitHub Release。

## 常见问题

- **提示 8765 端口被占用**：切回运行中的控制台，或在启动旧版的终端按 Ctrl+C，随后重开应用。
- **提示小模型调用失败**：确认 Ollama 已启动，`ollama list` 能看到与 `SMALL_MODEL` 完全相同的标签。
- **百炼调用失败**：核对密钥地域、模型权限和余额。修改环境变量后重新启动程序。
- **找不到音乐或 FFmpeg**：在资源管理器中打开配乐文件确认路径有效，再用新终端执行 `ffmpeg -version`。
- **安装后馆藏为空**：在控制台查看实际作品目录，并按上面的迁移步骤导入旧作品。

[代码逐块说明](docs/code-explanation.md) · [评估记录及样本限制](docs/evaluation.md) · [数据来源](data/README.md)

项目自有代码采用 [MIT 许可证](LICENSE)。第三方运行组件的许可原文随安装包置于 `THIRD_PARTY_NOTICES` 目录，摘要见 [第三方许可说明](THIRD_PARTY_NOTICES.md)。公开数据集、外部模型、音乐及检索资料适用各自的许可。
