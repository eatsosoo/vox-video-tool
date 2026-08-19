const form = document.querySelector('#form');
const result = document.querySelector('#result');
const projects = document.querySelector('#projects');
const config = document.querySelector('#config');

const statusLabels = {
  queued: 'Đang chờ',
  planning: 'Đang lập kịch bản',
  planned: 'Đã lập kịch bản',
  generating_voice: 'Đang tạo giọng đọc',
  rendering_visuals: 'Đang tạo hình ảnh',
  composing: 'Đang ghép video',
  finalizing: 'Đang hoàn thiện',
  completed: 'Hoàn thành',
  failed: 'Thất bại',
};

const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[character]));

const formatCreatedAt = value => value
  ? new Intl.DateTimeFormat('vi-VN', {dateStyle: 'short', timeStyle: 'medium'}).format(new Date(value))
  : 'Chưa xác định';

const statusText = project => `${statusLabels[project.status] || project.status} · ${project.progress}%`;

async function loadConfig() {
  const value = await fetch('/api/config').then(response => response.json());
  const providers = `Director ${value.openai_model} · Voice ${value.tts_provider} · Visual ${value.visual_provider}`;
  const errors = value.errors.length ? `<small>${value.errors.map(esc).join(' · ')}</small>` : '';
  config.className = `config ${value.ready ? 'ready' : 'warning'}`;
  config.innerHTML = `<strong>${esc(value.app_mode.toUpperCase())}</strong><span>${esc(providers)}</span>${errors}`;
}

async function load() {
  const rows = await fetch('/api/projects').then(response => response.json());
  projects.innerHTML = rows.map(project => `
    <div class="project">
      <span><strong>${esc(project.request.topic)}</strong><small>Tạo lúc ${esc(formatCreatedAt(project.created_at))}</small></span>
      <span class="status">${esc(statusText(project))}</span>
    </div>`).join('') || '<p>Chưa có dự án.</p>';
}

async function watch(id) {
  const project = await fetch(`/api/projects/${id}`).then(response => response.json());
  result.classList.remove('hidden');
  result.innerHTML = `
    <h2>${esc(project.request.topic)}</h2>
    <p>Tạo lúc: ${esc(formatCreatedAt(project.created_at))}</p>
    <p>Trạng thái: <span class="status">${esc(statusText(project))}</span></p>
    ${project.error ? `<p class="error">${esc(project.error)}</p>` : ''}
    ${project.output_url ? `<video controls src="${project.output_url}"></video><p><a href="${project.output_url}" download>Tải MP4</a></p>` : ''}`;
  await load();
  if (!['completed', 'failed'].includes(project.status)) setTimeout(() => watch(id), 1500);
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button');
  button.disabled = true;
  button.textContent = 'Đang khởi tạo...';
  try {
    const project = await fetch('/api/projects', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        topic: topic.value,
        script: script.value,
        target_seconds: +duration.value,
        aspect_ratio: ratio.value,
        language: 'vi',
      }),
    }).then(response => response.json());
    watch(project.id);
  } finally {
    button.disabled = false;
    button.textContent = 'Tạo video';
  }
});

loadConfig();
load();
