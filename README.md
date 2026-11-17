# 知识动画工作台

将一句中文主题转换为无旁白知识视频的实习项目。当前是**开发中的原型**：已经接通公开资料检索、百炼大模型、本地小模型分镜分类、文字图形渲染、背景音乐、节奏点和合成音效；尚不能保证生成效果达到参考作品。知识内容、资料来源、音效和画面均需人工检查。

## 运行条件

- Windows、Python 3.13，安装 `requirements.txt` 中的 Python 包；FFmpeg 和 FFprobe 在 PATH 中。
- 阿里云百炼按量 API Key 在用户环境变量 `DASHSCOPE_API_KEY` 中；默认模型 `qwen4-max`，可用 `BAILIAN_MODEL` 指定。确认北京地域、模型免费额度及“免费额度用完即停”后再使用。不要把密钥写到代码或发送给他人。支持 `BAILIAN_BASE_URL` 指定同地域兼容接口的 Base URL。
- Ollama 服务运行，默认使用 `modelscope.cn/unsloth/Qwen3.5-0.8B-GGUF:latest` 做镜头类别预测；可用 `SMALL_MODEL` 覆盖。小模型目前只做提示词适配，**没有宣称微调**。
- 默认背景音乐为 `用户本地配乐文件`；在另一台电脑运行时用环境变量 `KNOWLEDGE_MUSIC` 指定本地文件。音乐版权及使用范围由使用者核实；音乐不随项目分发。
- 当前公开资料检索使用维基百科搜索接口，需要可访问该网站的网络；查不到或访问失败时会停止并提示。

## 启动

在项目文件夹打开 PowerShell：

```powershell
python -m pip install -r requirements.txt
python app.py
```

在浏览器打开 `http://127.0.0.1:8765/`。输入主题点击生成，等待状态变成“已完成”；作品和来源清单保存在 `outputs/projects/`。每次生成、修改均会调用百炼并消耗额度，具体用量以百炼控制台为准。系统会使用本机现有的用户环境变量；设置完成后若未识别，请重新打开终端。

## 主要模块

- `app.py` 和 `web/index.html`：本机网页、任务提交和作品展示。
- `src/research.py`：查找并记录来源；结果是检索摘要，不等于事实已经核实。
- `src/generator.py`：调用百炼 `qwen4-max`，把结果解析为分镜；`src/storyboard.py` 检查标题、时长与数据。
- `src/classifier.py`：本地小模型选择概念、对比、流程或总结画面，结果需用数据集测试。
- `src/beats.py`、`src/timeline.py`：粗略估计音乐中的低频强调点并调整分镜时间，不保证精确击中鼓点。
- `src/render.py`、`src/audio.py`：绘制文字图形、合成转场、音乐和短音效，导出 MP4。
- `src/projects.py` 和 `src/pipeline.py`：保存作品状态、来源和修改记录，安排生成步骤。

## 验证

```powershell
python -m unittest discover -s tests -v
python -m evaluation.classification
python -m evaluation.download_ceval
python -m evaluation.ceval
```

第二条调用本机小模型；第三条下载公开样本；第四条调用百炼并消耗额度。数据来源和试验限制见 `data/README.md`。模型输出并不保证准确；请在最终提交前自行核验事实和完整观看试听。

## 当前限制

动态效果和视觉模板仍较简单，不能达到参考片逐镜精修的质量；仅支持几类基础图形。小模型未微调，自编分镜分类试验和 C-Eval 题目样本很小，不能代表整体效果。自动画风、来源质量、音效和节拍同步还需更多主题与人工评审；报错时不会自动改用付费服务。系统仍在开发，不代表已完成实习任务。

## 本地视频和磁盘占用

生成视频保存在 `outputs/projects/<作品编号>/video.mp4`；资料清单为同目录的 `sources.md`，修改前版本以 `video-before-edit-<序号>.mp4` 保存。视频和历史版本不会提交到 GitHub，但会持续占用本机磁盘；可在文件资源管理器中查看或自行删除不需要的项目文件夹。删除项目文件夹会同时删除对应视频、来源记录和历史版本。当前演示期间 `outputs/projects` 约占用 12.3 MB，实际随视频时长和数量增加。网页播放器提供浏览器原生控制，并另有可拖动的时间滑杆。

## 超时提示

生成或修改持续超过 5 分钟时，网页会显示等待超时提示。它只提醒任务耗时较长；当前步骤不会被强行终止，完成后仍会更新为最终结果。
