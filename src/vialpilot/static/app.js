/* VialPilot — dashboard interactions */

const API = '/api';

function escapeHtml(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function mediaUrl(path) {
  if (!path) return '';
  return '/media?path=' + encodeURIComponent(path.replace(/\\/g, '/'));
}

function llmLabel(metrics) {
  if (!metrics) return 'Offline';
  const p = metrics.llm_provider || 'mock';
  const m = metrics.model || '';
  if (p.includes('cerebras')) return m ? `Cerebras · ${m}` : 'Cerebras';
  if (p === 'gemini') return m ? `Gemini · ${m}` : 'Gemini';
  return 'Offline';
}

function runProgress(run) {
  const steps = ['VisionLabAgent', 'TaskDecomposerAgent', 'LocalizerAgent', 'SafetyVetoAgent',
    'MotionPlannerAgent', 'ActorCommandAgent', 'ReflectorAgent', 'LabNotebookAgent'];
  if (!run) return 0;
  if (run.status === 'completed') return 100;
  if (run.status === 'failed' || run.status === 'blocked') return 100;
  const outputs = run.agent_outputs || [];
  const done = new Set(outputs.map(o => o.agent_name));
  let n = 0;
  steps.forEach(s => { if (done.has(s)) n++; });
  if (run.current_agent) {
    const idx = steps.indexOf(run.current_agent);
    if (idx >= 0) return Math.min(95, Math.round(((idx + 0.5) / steps.length) * 100));
  }
  return Math.round((n / steps.length) * 100);
}

function pollRun(runId, onUpdate, intervalMs = 1200) {
  const tick = async () => {
    try {
      const [runRes, eventsRes] = await Promise.all([
        fetch(`${API}/runs/${runId}`),
        fetch(`${API}/runs/${runId}/events`),
      ]);
      if (!runRes.ok) return null;
      const run = await runRes.json();
      const events = eventsRes.ok ? await eventsRes.json() : [];
      onUpdate(run, events);
      return run;
    } catch (e) { console.warn('poll error', e); return null; }
  };
  tick();
  const timer = setInterval(async () => {
    const run = await tick();
    if (run && !['running', 'created', 'uploaded'].includes(run.status)) {
      clearInterval(timer);
      onUpdate(run, await fetch(`${API}/runs/${runId}/events`).then(r => r.ok ? r.json() : []), true);
    }
  }, intervalMs);
  return timer;
}

function renderStepper(currentAgent, agentOutputs) {
  const steps = [
    'VisionLabAgent', 'TaskDecomposerAgent', 'LocalizerAgent',
    'SafetyVetoAgent', 'MotionPlannerAgent', 'ActorCommandAgent',
    'ReflectorAgent', 'LabNotebookAgent',
  ];
  const outputs = agentOutputs || [];
  const doneCount = {};
  outputs.forEach(o => { doneCount[o.agent_name] = (doneCount[o.agent_name] || 0) + 1; });
  const el = document.getElementById('agent-stepper');
  if (!el) return;
  el.innerHTML = steps.map(name => {
    let cls = 'step';
    if (currentAgent === name) cls += ' active';
    else if (doneCount[name]) cls += ' done';
    const label = name.replace('Agent', '');
    const n = doneCount[name];
    const suffix = n > 1 ? ` ×${n}` : '';
    return `<div class="${cls}"><span class="step-dot"></span><span>${label}${suffix}</span></div>`;
  }).join('');
}

function renderLatencyChart(metrics) {
  const canvas = document.getElementById('latency-chart');
  if (!canvas || !window.Chart) return;
  const per = (metrics && metrics.per_agent_latency_ms) || {};
  const labels = Object.keys(per);
  const data = Object.values(per);
  if (window._latencyChart) window._latencyChart.destroy();
  if (!labels.length) return;
  window._latencyChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Latency (ms)',
        data,
        backgroundColor: 'rgba(82, 104, 128, 0.55)',
        borderColor: '#526880',
        borderWidth: 1,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { color: '#949aa6' }, grid: { color: '#22252c' } },
        x: { ticks: { color: '#949aa6', maxRotation: 45 }, grid: { display: false } },
      },
    },
  });
}

function drawAnnotations(canvasId, imgId, objects) {
  const canvas = document.getElementById(canvasId);
  const img = document.getElementById(imgId);
  if (!canvas || !img || !objects || !objects.length) return;
  const draw = () => {
    canvas.width = img.clientWidth;
    canvas.height = img.clientHeight;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const sx = canvas.width / (img.naturalWidth || canvas.width);
    const sy = canvas.height / (img.naturalHeight || canvas.height);
    objects.forEach(obj => {
      const bbox = obj.bbox;
      let x, y, w, h;
      if (bbox && bbox.w) {
        x = bbox.x * sx; y = bbox.y * sy; w = bbox.w * sx; h = bbox.h * sy;
      } else {
        x = (obj.x || 0) * 30 * sx; y = (obj.y || 0) * 30 * sy; w = 40; h = 40;
      }
      ctx.strokeStyle = obj.confidence < 0.7 ? '#c9a227' : '#5d9a72';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);
      ctx.fillStyle = 'rgba(196, 184, 164, 0.92)';
      ctx.font = '11px sans-serif';
      ctx.fillText(obj.label || obj.id, x, Math.max(12, y - 4));
    });
  };
  if (img.complete) draw(); else img.onload = draw;
}

function modeBadge(mode, model, agentName) {
  const systemAgents = ['ActorCommandAgent', 'LabNotebookAgent'];
  if (systemAgents.includes(agentName)) {
    return '<span class="badge badge-created">Robot</span>';
  }
  const real = mode === 'real';
  const cls = real ? 'badge-success' : 'badge-blocked';
  const label = real ? (model ? `AI · ${escapeHtml(model)}` : 'AI · Live') : 'Offline';
  return `<span class="badge ${cls}">${label}</span>`;
}

function renderAgentCards(outputs, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!outputs || !outputs.length) {
    el.innerHTML = '<p class="hint empty-state">Waiting for agent outputs… Start a run or click Re-run Live AI.</p>';
    return;
  }
  el.innerHTML = outputs.map(o => {
    const model = o.data && o.data.llm_model;
    const raw = o.data && o.data.llm_raw_preview;
    return `
    <div class="agent-card-v2 status-${o.status}">
      <div class="agent-card-header">
        <strong>${escapeHtml(o.agent_name)}</strong>
        <span class="badge badge-${o.status}">${o.status}</span>
        ${modeBadge(o.mode, model, o.agent_name)}
        <span class="muted">${Math.round(o.latency_ms)}ms</span>
      </div>
      <p class="agent-summary">${escapeHtml(o.summary)}</p>
      <div class="confidence-bar"><div style="width:${Math.round(o.confidence * 100)}%"></div></div>
      ${raw ? `<details open><summary>AI response</summary><pre class="llm-raw">${escapeHtml(raw)}</pre></details>` : ''}
      <details><summary>Structured data</summary><pre>${escapeHtml(JSON.stringify(o.data, null, 2))}</pre></details>
    </div>`;
  }).join('');
}

function renderSafetyCards(decisions, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!decisions || !decisions.length) {
    el.innerHTML = '<p class="hint empty-state">No safety decisions yet.</p>';
    return;
  }
  el.innerHTML = decisions.map(s => `
    <div class="agent-card-v2 status-${s.allow ? 'success' : 'blocked'}">
      <strong>${s.allow ? '✓ Approved' : '✗ Blocked'}</strong>
      <span class="badge badge-${s.allow ? 'success' : 'blocked'}">${escapeHtml(s.risk_level || 'unknown')}</span>
      <p class="agent-summary">${escapeHtml(s.reason || '')}</p>
    </div>
  `).join('');
}

function renderCommandList(commands, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const cmds = (commands || []).filter(c => c && c.command);
  if (!cmds.length) {
    el.innerHTML = '<p class="hint empty-state">No robot commands yet.</p>';
    return;
  }
  el.innerHTML = cmds.map(cmd => `
    <div class="agent-card-v2">
      <strong>${escapeHtml(cmd.command)}</strong>
      <span class="muted">${escapeHtml(cmd.object_id || '')} → ${escapeHtml(cmd.to || cmd.destination || '')}</span>
      <p class="agent-summary">${escapeHtml(cmd.reason || cmd.message || '')}</p>
    </div>
  `).join('');
}

function renderTimeline(events, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!events || !events.length) {
    el.innerHTML = '<p class="hint empty-state">No events yet.</p>';
    return;
  }
  el.innerHTML = events.map(e => `
    <div class="event ${e.event_type}">
      <span class="event-time">${new Date(e.created_at).toLocaleTimeString()}</span>
      <strong>${escapeHtml(e.event_type)}</strong>
      ${e.agent_name ? `<span class="muted">· ${escapeHtml(e.agent_name)}</span>` : ''}
      <p>${escapeHtml(e.message || '')}</p>
    </div>
  `).join('');
}

function _setInputFile(input, file) {
  const dt = new DataTransfer();
  dt.items.add(file);
  input.files = dt.files;
}

function setupDropZone(zoneId, inputId) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  if (!zone || !input) return;
  ['dragenter', 'dragover'].forEach(ev => zone.addEventListener(ev, e => {
    e.preventDefault();
    zone.classList.add('drag-over');
  }));
  ['dragleave', 'drop'].forEach(ev => zone.addEventListener(ev, e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
  }));
  zone.addEventListener('drop', e => {
    if (e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      const label = zone.querySelector('.drop-label');
      if (label) label.textContent = e.dataTransfer.files[0].name;
    }
  });
  input.addEventListener('change', () => {
    const label = zone.querySelector('.drop-label');
    if (label && input.files[0]) label.textContent = input.files[0].name;
  });
}

function renderSpeedPanel(metrics) {
  const hero = document.getElementById('speed-hero');
  const headline = document.getElementById('speed-headline');
  const summary = document.getElementById('speed-summary');
  const metricsEl = document.getElementById('speed-metrics');
  if (!hero || !metrics) return;
  const live = (metrics.real_llm_calls || 0) > 0;
  hero.classList.toggle('live', live);
  if (headline) {
    headline.textContent = live && metrics.cerebras_advantage
      ? 'Cerebras Speed in Action'
      : 'Workflow Speed';
  }
  if (summary) {
    summary.textContent = metrics.speed_summary
      || `Total inference ${Math.round(metrics.total_latency_ms || 0)}ms across ${metrics.agent_calls || 0} agents.`;
  }
  if (metricsEl) {
    const wall = metrics.wall_clock_ms != null ? Math.round(metrics.wall_clock_ms) : '—';
    const avg = metrics.avg_llm_latency_ms != null ? Math.round(metrics.avg_llm_latency_ms) : '—';
    const replans = metrics.replan_count || 0;
    metricsEl.innerHTML = [
      `<span><strong>${wall}</strong> ms wall clock</span>`,
      `<span><strong>${avg}</strong> ms avg AI call</span>`,
      `<span><strong>${metrics.real_llm_calls || 0}</strong> live Gemma calls</span>`,
      replans ? `<span><strong>${replans}</strong> replan(s)</span>` : '',
    ].filter(Boolean).join('');
  }
}

async function runSpeedBenchmark(resultId) {
  const el = typeof resultId === 'string' ? document.getElementById(resultId) : resultId;
  if (el) {
    el.hidden = false;
    el.textContent = 'Running 3× Gemma 4 vision benchmark on Cerebras…';
  }
  try {
    const res = await fetch('/api/benchmark/speed?iterations=3', { method: 'POST' });
    const data = await res.json();
    const text = data.headline || 'Benchmark complete.';
    if (el) el.textContent = text;
    return data;
  } catch (e) {
    if (el) el.textContent = 'Benchmark failed — check API key in Settings.';
    return null;
  }
}

function setupVisionInput(rootId) {
  const root = document.getElementById(rootId);
  if (!root) return;
  const input = root.querySelector('input[name="image"], #image-input') || root.querySelector('input[type="file"]');
  const videoInput = root.querySelector('#video-input');
  const drop = root.querySelector('.vision-drop:not(.vision-drop-video)');
  const videoDrop = root.querySelector('.vision-drop-video');
  const previewWrap = root.querySelector('.vision-preview-wrap');
  const previewImg = root.querySelector('.vision-preview-wrap img');
  const sourceBadge = root.querySelector('.vision-source-badge');
  const captureBtn = root.querySelector('[data-vision-capture]');
  const clearBtn = root.querySelector('[data-vision-clear]');

  const setSource = (kind, name) => {
    if (!sourceBadge) return;
    const labels = { none: 'No image', upload: 'Uploaded', video: 'Video MP4', simulator: 'Simulator cam' };
    sourceBadge.textContent = name ? `${labels[kind] || kind} · ${name}` : (labels[kind] || kind);
    sourceBadge.classList.toggle('live', kind !== 'none');
  };

  const showPreview = (fileOrUrl) => {
    if (!previewWrap || !previewImg) return;
    if (fileOrUrl instanceof File) {
      previewImg.src = URL.createObjectURL(fileOrUrl);
    } else if (typeof fileOrUrl === 'string') {
      previewImg.src = fileOrUrl;
    }
    previewWrap.classList.add('has-image');
  };

  const clearPreview = () => {
    if (input) input.value = '';
    if (videoInput) videoInput.value = '';
    if (previewWrap) previewWrap.classList.remove('has-image');
    if (previewImg) previewImg.removeAttribute('src');
    setSource('none');
  };

  if (drop && input) {
    drop.addEventListener('click', () => input.click());
    ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => {
      e.preventDefault();
      drop.classList.add('drag-over');
    }));
    ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => {
      e.preventDefault();
      drop.classList.remove('drag-over');
    }));
    drop.addEventListener('drop', e => {
      if (!e.dataTransfer.files.length) return;
      const file = e.dataTransfer.files[0];
      _setInputFile(input, file);
      showPreview(file);
      setSource('upload', file.name);
    });
    input.addEventListener('change', () => {
      const file = input.files[0];
      if (!file) return clearPreview();
      if (videoInput) videoInput.value = '';
      showPreview(file);
      setSource('upload', file.name);
    });
  }

  if (videoDrop && videoInput) {
    videoDrop.addEventListener('click', () => videoInput.click());
    videoInput.addEventListener('change', () => {
      const file = videoInput.files[0];
      if (!file) return;
      if (input) input.value = '';
      if (previewWrap) previewWrap.classList.remove('has-image');
      if (previewImg) previewImg.removeAttribute('src');
      setSource('video', file.name);
    });
  }

  if (captureBtn) {
    captureBtn.addEventListener('click', async () => {
      captureBtn.disabled = true;
      captureBtn.textContent = 'Capturing…';
      try {
        const res = await fetch(`/simulator/frame.png?t=${Date.now()}`);
        if (!res.ok) throw new Error('Frame unavailable');
        const blob = await res.blob();
        const file = new File([blob], 'simulator_capture.png', { type: 'image/png' });
        if (input) _setInputFile(input, file);
        showPreview(file);
        setSource('simulator', 'capture.png');
      } catch (err) {
        console.warn('vision capture failed', err);
        if (sourceBadge) sourceBadge.textContent = 'Capture failed — try upload';
      } finally {
        captureBtn.disabled = false;
        captureBtn.textContent = '📷 Simulator Capture';
      }
    });
  }

  if (clearBtn) clearBtn.addEventListener('click', clearPreview);
  setSource('none');
}

async function confirmHuman(runId) {
  const note = document.getElementById('confirm-note')?.value || 'Operator approved';
  await fetch(`${API}/runs/${runId}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmed: true, note }),
  });
  window.location.href = `/runs/${runId}?live=1`;
}

window.VialPilot = {
  API, escapeHtml, pollRun, runProgress, renderStepper, renderLatencyChart, drawAnnotations,
  renderAgentCards, renderSafetyCards, renderCommandList, renderTimeline,
  setupDropZone, setupVisionInput, confirmHuman, mediaUrl, llmLabel,
  renderSpeedPanel, runSpeedBenchmark,
};