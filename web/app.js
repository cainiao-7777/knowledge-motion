const form = document.getElementById('form');
const message = document.getElementById('message');
const projects = document.getElementById('projects');
let lastSnapshot = '';

async function postJson(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  return response.json();
}

form.addEventListener('submit', async (event) => {
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
  const card = document.createElement('article');
  card.className = 'project';
  const title = document.createElement('strong');
  title.textContent = project.topic;
  card.append(title);

  const labels = {
    new: '准备中', researching: '正在查找资料', writing: '正在生成分镜',
    classifying: '正在选择动画形式', rendering: '正在渲染视频',
    complete: '已完成', revising: '正在修改', error: '生成失败'
  };
  const status = document.createElement('span');
  status.className = 'status';
  status.textContent = labels[project.status] || project.status;
  status.dataset.baseText = status.textContent;
  status.dataset.active = ['new','researching','writing','classifying','rendering','revising'].includes(project.status) ? 'true' : 'false';
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
  return card;
}

async function refresh() {
  try {
    const response = await fetch('/api/projects');
    const items = await response.json();
    const snapshot = JSON.stringify(items);
    if (snapshot === lastSnapshot) {
      updateTimeoutLabels();
      return;
    }
    lastSnapshot = snapshot;
    projects.replaceChildren();
    if (items.length === 0) {
      projects.textContent = '还没有作品。';
      return;
    }
    for (const project of items) projects.append(makeProjectCard(project));
  } catch (error) {
    projects.textContent = '无法读取本地作品列表。';
  }
}

function updateTimeoutLabels() {
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
