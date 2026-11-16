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
  card.append(status);

  if (project.error || project.revision_error) {
    const error = document.createElement('p');
    error.textContent = project.revision_error
      ? '修改失败，原视频已保留：' + project.revision_error : project.error;
    card.append(error);
  }
  if (project.status === 'complete') {
    const video = document.createElement('video');
    video.controls = true;
    video.preload = 'none';
    video.src = '/files/' + project.id + '/video.mp4';
    card.append(video);
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
    if (snapshot === lastSnapshot) return;
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

refresh();
setInterval(refresh, 5000);
