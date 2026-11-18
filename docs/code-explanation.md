# 知识动画项目代码逐块解释

这份说明按程序的实际运行顺序解释代码。主语言是 Python；网页使用 HTML、CSS 和 JavaScript；FFmpeg 负责视频编码。大模型使用百炼 qwen4-max，小模型固定使用本机 Ollama 的 Qwen3.5 0.8B。

## 1. 一句话到视频：总体调用链

```text
web/index.html 表单
  → web/app.js 发送 POST /api/generate
  → app.py 检查请求并启动后台线程
  → src/pipeline.py 安排资料搜索、分镜生成、小模型分类、音乐分析和渲染
  → outputs/projects/<UUID>/ 保存作品、来源和视频
  → app.py 的 GET 接口把状态、MP4 和来源返回网页
```

修改作品时，浏览器 POST `/api/revise/<UUID>`，服务调用同一套分镜、分类、节奏和渲染流程；成功后备份旧视频再替换。

## 2. 网页层：web/index.html、web/style.css、web/app.js

### web/index.html

页面提供标题、主题输入框、生成按钮、作品搜索框、分页按钮和作品列表容器。`<label for="topic">` 把标签和输入框关联；`aria-live` 区域让辅助技术可以读取状态变化；CSS 和 JS 分开加载，便于分别维护。

### web/style.css

定义页面颜色、卡片、按钮、焦点和窄屏布局。`.seekbar` 是视频下方可拖动的时间滑杆；`.status-timeout` 标记取消中的超时任务；`.delete-project` 突出删除操作。

### web/app.js

- `postJson(url, body)`：把对象编码成 JSON 并发送到本机服务。
- 表单 `submit`：读取主题、暂时禁用按钮、提交生成任务并更新反馈。
- `makeRevisionForm(id)`：收集自然语言修改意见并提交。
- `makeProjectCard(project)`：建立作品卡片，用 `textContent` 显示模型文字，避免把内容误当 HTML 执行。
- 播放器滑杆：`input` 事件把滑杆位置换算为 `video.currentTime`；`timeupdate` 把播放位置同步回滑杆。服务器必须支持 HTTP Range，浏览器才能读取 MP4 的任意片段进行跳播。
- 删除按钮：先弹出确认框，说明会移除视频、来源和历史版本；用户确认后才发 DELETE 请求。
- `searchableProjectText()`：组合主题、分镜标题/文字/说明和资料来源，供搜索匹配。
- `renderProjects()`：按关键词筛选，再按每页6条分页，更新结果数和上一页/下一页按钮。
- `refresh()`：每5秒读取项目状态；数据没变化时只更新超时提示，不重建正在播放的 video 元素。
- `updateTimeoutLabels()`：任务超过5分钟仍在活动时显示软超时提醒，但不会终止任务。

## 3. 本地 HTTP 服务：app.py

- `ROOT`、`OUTPUT`、`PORT`：定位项目、作品目录和本机 8765 端口。
- `generation_lock`：避免同时启动多个新视频生成；`active_revisions` 和 `revision_lock` 避免同一作品重复修改或在运行时删除。
- `generation_worker()`、`revise_worker()`：在后台运行耗时流程，结束后释放锁和活动标记。
- `respond()`、`reply_json()`：统一返回 HTTP 状态码、内容类型和 UTF-8 数据；`Cache-Control: no-store` 避免浏览器继续用旧脚本。
- `respond_video(file)`：普通请求返回完整 MP4；带 `Range: bytes=...` 时返回 206 分段内容和 `Content-Range`，让播放器跳到视频中间。
- `do_GET()`：按路径白名单提供网页、静态文件、作品信息、MP4 和来源清单；项目编号先做 UUID 校验。
- `do_POST()`：检查 Host/Origin、请求体大小和主题/修改意见长度，再启动后台任务。
- `do_DELETE()`：只允许同源请求；检查作品是否正在生成或修改，然后删除一个 UUID 对应的本地作品目录。

## 4. 生成编排：src/pipeline.py

`create_video_project(root, topic)` 是总流程：

1. 把主题转成简体，创建作品编号和文件夹。
2. 保存 `planning_search` 状态，调用 `plan_search_queries()` 让 qwen4-max 从一句话提炼核心主题和2–4个搜索词，并把规划存入项目记录。
3. 保存 `researching` 状态，把规划词传给 `search_sources()` 搜网页并合并来源，再写入 `sources.md`。
4. 保存 `writing` 状态，调用百炼生成分镜。
5. 保存 `classifying` 状态，本地小模型逐幕分类，`apply_scene_labels()` 再检查图形数据是否完整。
6. 保存 `rendering` 状态，分析配乐、调整总时长并把镜头边界靠近估计拍点。
7. 调用 `render_video()` 导出 MP4，完成后保存 `complete`；异常会保存 `error` 和错误信息。

`revise_video_project()` 读取旧分镜，把用户修改意见交给大模型，重新分类并渲染到候选文件。候选成功后才备份旧视频并替换，因此失败时原视频保留。

## 5. 网页搜索、模糊候选与简体：src/research.py、src/language.py

- `extract_search_query()` 优先提取《书名》，否则移除“为什么/怎么解释”等指令外壳。
- `spelling_suggestions()` 用 Google 公共自动补全扩展关键词；`expand_name_candidates()` 处理汉字后接拼音、以及少量常见同音字。补全词只用于搜索，不当作资料来源。
- `browser_search()` 解析 DuckDuckGo 网页结果；Wikipedia 提供百科条目，Open Library 提供书目资料。
- `rank_sources()` 按标题和摘要的词语匹配排序；模糊人名找到精确候选条目时优先给该人名结果，普通主题融合百科和网页结果。
- `fetch_json()` 对外网请求有限重试；搜索失败会提示网络或关键词问题，不伪造来源。
- `src/language.py` 用 OpenCC 的 `t2s` 把主题、资料标题/摘要和模型输出转成简体，保留来源 URL。

## 6. 大模型和故事板：src/generator.py、src/storyboard.py

- `read_api_key()` 从 `DASHSCOPE_API_KEY` 读取密钥，不把密钥写进代码。
- `plan_search_queries()` 先把用户一句话拆成核心主题和2–4个查询词。调用失败会记录回退并用本地规则继续。`generate_storyboard()` 再把主题和检索资料发给 qwen4-max。prompt 不规定固定幕数、镜头顺序、色板或叙事弧线；模型按主题返回 `narrative_arc`、`art_direction` 和场景列表。
- prompt 要求讲述者直接解释知识，不写“资料显示/据网站”等检索过程用语；来源链接放在单独清单。
- `response_schema` 只约束 JSON 必需字段，不规定创作内容；`enable_thinking=False` 避免思考内容占满回答预算。
- `extract_json()` 能从夹带说明或代码围栏的回答中找到 JSON 对象。
- `complete_visual_descriptions()` 遇到单幕缺画面描述时，根据已有主文字和 art direction 补充非事实性的绘图说明，并记录 warning；知识文字、标题或时长等关键字段仍校验失败。
- `validate_storyboard()` 检查标题、场景、文字和时长；收益矩阵必须有四个数据格。

## 7. 小模型和主题视觉：src/classifier.py、src/style.py

- `classify_scenes()` 逐幕请求本机 Ollama Qwen3.5 0.8B。新版提示词结合主文字、补充字幕、画面描述和已有图形数据判断布局。比如，依次淡入属于画面动效，内容有真实先后才适合流程图。分镜明确没有图形数据时，模型从概念与总结中选。旧分镜若缺少 `data` 字段，会沿用原来的判定方式。模型仍通过提示词完成分类，上下文设置为 4096。
- `apply_scene_labels()` 使用小模型建议，同时保留大模型明确设计且数据完整的布局；缺少流程节点或左右标签时回退到概念画面。
- `choose_palette()` 从自由 art direction 中提取颜色并检查文字对比度。
- `resolve_motif()`、`resolve_layout()` 将自由的视觉隐喻和构图描述映射到当前程序能画的原语，如网格、轨道、裂纹、门、中心构图和非对称构图。模型可以自由设计，但实际效果受这些绘图能力限制。

## 8. 音乐、排版、音效和视频：src/beats.py、src/timeline.py、src/audio.py、src/render.py

- `analyze_music()` 用 FFmpeg 读取音乐，计算低频起音变化并估计拍格；这是启发式节拍估计，不等于专业打拍。
- `normalize_durations()` 在总时长偏离目标区间时按原比例调整；`align_scenes()` 尝试把镜头边界贴近估计拍点。
- `create_effects_track()` 生成短低频重击和瞬态点击，落在转场位置。
- `font()` 加载系统中文字体；`wrapped()` 按像素宽度切行。
- `draw_background_motif()`、`draw_theme_metaphor()` 把模型的主题纹理/隐喻变成当前支持的程序图形。
- `draw_scene()` 按 art direction 选背景、构图和场景图形；主文字太长时逐级缩小字号并换行，不再因超过固定五行直接失败；节拍到来时轻微放大画面并偏移几像素。
- `apply_rhythm_motion()` 实现确定性的节拍推近和轻微抖动。
- `render_video()` 每秒24帧绘制，做半秒交叠转场，再混合音乐和音效，结尾淡出，最后把临时文件移动为 MP4。

## 9. 作品存储和评估：src/projects.py、src/evaluation.py、evaluation/

- `create_project()` 建立 UUID 文件夹；`save_project()` 用临时 JSON 和 `os.replace()` 原子保存；`load_project()` 按编号读取；`list_projects()` 按创建时间排序；`delete_project()` 删除单个本地作品。
- `evaluation/classification.py` 用自编的小样查看小模型分类；`evaluation/ceval.py` 比较少量中文选择题表现。这些样本量有限，不能代表模型全部能力或视频质量。

## 10. 运行方式

在项目目录运行 `python app.py`，浏览器打开 `http://127.0.0.1:8765/`。依赖见 `requirements.txt`。作品视频和修改历史保存在 `outputs/projects/`；代码在私有 GitHub 的 `feat/knowledge-video` 分支。


## 11. 本地作品搜索、分页和删除

### 搜索

作品列表拿到项目 JSON 后，`searchableProjectText(project)` 把主题、故事板标题、叙事说明、各幕文字/说明和来源标题/摘要拼成一个字符串。`renderProjects()` 将搜索框内容统一转小写并做包含匹配，因此可以用主题、分镜词或来源词查找。输入变化时页码回到第1页。

### 分页

`pageSize=6` 表示每页最多显示6条。程序先得到过滤结果 `filtered`，再用 `(currentPage-1)*pageSize` 算切片起点。过滤后页数会重新计算；如果当前页超出新范围，就收回到最后一页。空结果会显示“没有匹配的作品”。上一页/下一页按钮在首末页禁用。

### 删除

作品卡片只对已完成或失败的项目显示“删除作品”。点击后 `window.confirm()` 明确列出将删除视频、来源和历史；用户取消时不发请求。确认后发送 `DELETE /api/projects/<UUID>`。

`app.py` 的 `do_DELETE()` 再验证 Host、Origin 和 UUID 对应项目状态；正在生成/修改的项目返回409，避免删除活跃任务。`src/projects.py` 的 `delete_project()` 只删除该 UUID 的项目目录。这个操作会释放本地磁盘空间，但会永久移除该作品的视频、`project.json`、来源清单和历史版本，无法从工作台恢复。

## 12. 等待超时后取消：app.py、src/cancellation.py、src/pipeline.py

生成或修改任务启动时，`app.py` 同时创建 `threading.Event` 取消信号和 5 分钟计时器。到时后计时器设置该信号；网页用同一个 5 分钟门槛显示“等待超时，正在取消…”，不再误报“仍在运行”。

`src/cancellation.py` 提供 `check_cancelled()`。资料搜索、逐幕分类、音乐分析和渲染在每个可控步骤开始或结束时检查信号；信号已设置时抛出 `OperationCancelled`，管线随即停止后续工作。正在执行的 FFmpeg 视频渲染和配乐分析进程会被终止，临时渲染目录会自动清理。

外部模型或网页请求由同步 HTTP 调用完成。取消信号在请求等待期间会先记录下来，请求返回或自身网络超时后立刻被检查，之后不再启动下一步。新生成任务会保存为“已取消（超时）”；修改任务恢复“已完成”状态，并提示本次修改取消、原视频保留。这样旧视频不会因为修改超时被替换或丢失。

取消期间仍被活动任务集合跟踪，因此删除接口继续返回409；任务完成收尾后，取消作品可以像其他已结束作品一样删除。状态页每5秒读取后台结果，最终以 `project.json` 中的状态为准。

如果 Python 服务意外关闭，后台线程无法续跑。下次启动时 `app.py` 的 `recover_interrupted_projects()` 会把遗留的运行状态收尾：修改中的作品恢复为已完成并保留原视频；生成阶段中断的作品标记为已取消；已写好的视频会保留。未完成的候选视频会清理掉，避免继续占用空间。


## 源码旁注

关键函数、流程边界和容易误解的逻辑已直接用中文注释放在源码旁。Python 使用 `#`，JavaScript 使用 `//`，CSS/HTML 使用各自的注释格式。这些注释解释代码“为什么这样写”和数据如何流动；函数名称与参数仍应结合本说明阅读。JSON 示例保持合法 JSON，因此不在数据文件内插注释。
