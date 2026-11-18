// 缓存页面控件；搜索和分页状态只存在浏览器内，不改变磁盘项目数据。
const form = document.getElementById('form');
const message = document.getElementById('message');
const projects = document.getElementById('projects');
const projectSearch = document.getElementById('projectSearch');
const projectCount = document.getElementById('projectCount');
const pageInfo = document.getElementById('pageInfo');
const previousPage = document.getElementById('previousPage');
const nextPage = document.getElementById('nextPage');
let lastSnapshot = '';
let allProjects = [];
let currentPage = 1;
const pageSize = 6;

async function postJson(url, body) {
  // 新建和修改都发送 JSON，并把服务端返回的状态消息交回页面。
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return response.json();
}

form.addEventListener('submit', async (event) => {
  // 新建作品：先阻止浏览器默认刷新，再把主题交给本机 API。
  event.preventDefault();
  const button = document.getElementById('submit');
  button.disabled = true;
  message.textContent = '正在创建任务…';
  try {
    const result = await postJson('/api/generate', {
      topic: document.getElementById('topic').value
    });
    message.textContent = result.message || result.error;
    await refresh();
  } catch (error) {
    message.textContent = '无法连接本机服务，请检查程序是否运行。';
  } finally {
    button.disabled = false;
  }
});

function makeRevisionForm(projectId) {
  // 为单个作品创建自然语言修改表单，项目编号决定修改目标。
  const form = document.createElement('form');
  const label = document.createElement('label');
  label.textContent = '用一句话修改这个作品';
  const input = document.createElement('textarea');
  input.maxLength = 500;
  input.required = true;
  input.placeholder = '例如：第二幕文字更简洁';
  label.append(input);
  form.append(label);

  const button = document.createElement('button');
  button.textContent = '提交修改';
  form.append(button);
  const feedback = document.createElement('p');
  feedback.className = 'message';
  feedback.setAttribute('role', 'status');
  form.append(feedback);

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    button.disabled = true;
    try {
      const result = await postJson('/api/revise/' + projectId, {
        instruction: input.value
      });
      feedback.textContent = result.message || result.error;
      await refresh();
    } catch (error) {
      feedback.textContent = '无法连接本机服务。';
    } finally {
      button.disabled = false;
    }
  });
  return form;
}

function makeProjectCard(project) {
  // 把服务器保存的一条 project.json 记录渲染成作品卡片。
  const card = document.createElement('article');
  card.className = 'project';
  const title = document.createElement('strong');
  title.textContent = project.topic;
  card.append(title);

  const labels = {
    new: '准备中', planning_search: '正在提炼搜索词', researching: '正在查找资料', writing: '正在生成分镜',
    classifying: '正在选择动画形式', rendering: '正在渲染视频',
    complete: '已完成', revising: '正在修改', error: '生成失败'
  };
  const status = document.createElement('span');
  status.className = 'status';
  status.textContent = labels[project.status] || project.status;
  status.dataset.baseText = status.textContent;
  status.dataset.active = ['new','planning_search','researching','writing','classifying','rendering','revising'].includes(project.status) ? 'true' : 'false';
  status.dataset.startedAt = project.operation_started_at || project.created || '';
  card.append(status);

  if (project.error || project.revision_error) {
    const error = document.createElement('p');
    error.textContent = project.revision_error
      ? '修改失败，原视频已保留：' + project.revision_error : project.error;
    card.append(error);
  }
  if (Array.isArray(project.warnings) && project.warnings.length) {
    const warning = document.createElement('p');
    warning.className = 'normalization-warning';
    warning.textContent = project.warnings.join(' ');
    card.append(warning);
  }
  if (project.status === 'complete') {
    const video = document.createElement('video');
    video.controls = true;
    video.preload = 'metadata';
    video.src = '/files/' + project.id + '/video.mp4';
    // 自定义滑杆把0–1000映射到视频时长；Range请求由app.py支持。
    const seek = document.createElement('input');
    seek.type = 'range';
    seek.className = 'seekbar';
    seek.min = '0';
    seek.max = '1000';
    seek.value = '0';
    seek.disabled = true;
    seek.setAttribute('aria-label', '拖动播放进度');
    seek.title = '拖动跳转到视频位置';
    seek.addEventListener('input', () => {
      if (Number.isFinite(video.duration) && video.duration > 0) {
        video.currentTime = Number(seek.value) / 1000 * video.duration;
      }
    });
    video.addEventListener('loadedmetadata', () => { seek.disabled = false; });
    video.addEventListener('timeupdate', () => {
      if (Number.isFinite(video.duration) && video.duration > 0 && !seek.matches(':active')) {
        seek.value = String(Math.round(video.currentTime / video.duration * 1000));
      }
    });
    card.append(video, seek);
    const sources = document.createElement('a');
    sources.href = '/files/' + project.id + '/sources.md';
    sources.textContent = '查看来源清单';
    card.append(sources, makeRevisionForm(project.id));
  }
  if (!['new','researching','writing','classifying','rendering','revising'].includes(project.status)) {
    // 进行中的作品不显示删除按钮，避免删掉正在写入的目录。
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'delete-project';
    remove.textContent = '删除作品';
    remove.addEventListener('click', async () => {
      const message = '确定删除“' + project.topic + '”？这会永久删除该作品的视频、资料清单和修改历史，并释放本地磁盘空间。';
      if (!window.confirm(message)) return;
      remove.disabled = true;
      try {
        const response = await fetch('/api/projects/' + encodeURIComponent(project.id), { method: 'DELETE' });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || '删除失败');
        lastSnapshot = '';
        await refresh();
      } catch (error) {
        remove.disabled = false;
        window.alert(error.message || '删除失败，请重试。');
      }
    });
    card.append(remove);
  }
  return card;
}

function searchableProjectText(project) {
  // 把主题、分镜和来源合为可检索文本，不下载视频内容参与搜索。
  const story = project.storyboard || {};
  const scenes = Array.isArray(story.scenes) ? story.scenes : [];
  const sources = Array.isArray(project.sources) ? project.sources : [];
  return [project.topic,story.title,story.narrative_arc,
    ...scenes.flatMap(scene => [scene.text,scene.caption]),
    ...sources.flatMap(source => [source.title,source.snippet])]
    .filter(Boolean).join(' ').toLocaleLowerCase();
}

function renderProjects() {
  // 先过滤再分页；过滤条件变化时页码回到第1页。
  const query = projectSearch.value.trim().toLocaleLowerCase();
  const filtered = allProjects.filter(project => !query || searchableProjectText(project).includes(query));
  const pageCount = Math.max(1,Math.ceil(filtered.length/pageSize));
  currentPage = Math.min(currentPage,pageCount);
  const start = (currentPage-1)*pageSize;
  const visible = filtered.slice(start,start+pageSize);
  projects.replaceChildren();
  projectCount.textContent = query
    ? `找到 ${filtered.length} 个作品${filtered.length ? `，显示 ${start+1}–${start+visible.length}` : ''}`
    : `共 ${filtered.length} 个作品`;
  pageInfo.textContent = `第 ${currentPage} / ${pageCount} 页`;
  previousPage.disabled = currentPage<=1;
  nextPage.disabled = currentPage>=pageCount;
  if (!visible.length) {
    projects.textContent = query ? '没有匹配的作品。' : '还没有作品。';
    return;
  }
  for (const project of visible) projects.append(makeProjectCard(project));
}

projectSearch.addEventListener('input',() => { currentPage=1; renderProjects(); });
previousPage.addEventListener('click',() => { currentPage=Math.max(1,currentPage-1); renderProjects(); });
nextPage.addEventListener('click',() => { currentPage+=1; renderProjects(); });

async function refresh() {
  // 周期性同步状态；数据未变时不重建播放器，避免重置播放位置。
  try {
    const response = await fetch('/api/projects');
    const items = await response.json();
    const snapshot = JSON.stringify(items);
    if (snapshot === lastSnapshot) {
      updateTimeoutLabels();
      return;
    }
    lastSnapshot = snapshot;
    allProjects = items;
    renderProjects();
  } catch (error) {
    projects.textContent = '无法读取本地作品列表。';
  }
}

function updateTimeoutLabels() {
  // 仅给长时间活动的任务加提示，不在前端终止后台任务。
  const timeoutMs = 5 * 60 * 1000;
  for (const status of document.querySelectorAll('.status[data-active="true"]')) {
    const elapsed = Date.now() - Date.parse(status.dataset.startedAt);
    if (Number.isFinite(elapsed) && elapsed >= timeoutMs) {
      status.textContent = '等待超时（已 ' + Math.floor(elapsed / 60000) + ' 分钟，仍在运行）';
      status.classList.add('status-timeout');
    } else {
      status.textContent = status.dataset.baseText;
      status.classList.remove('status-timeout');
    }
  }
}

refresh();
setInterval(refresh, 5000);
