/** VialPilot Run Dashboard — loads live data from API, no inline mock JSON */
const API_BASE = '/api';

function vp() {
  return window.VialPilot || {
    API: API_BASE,
    llmLabel: () => 'AI',
    runProgress: () => 0,
    renderStepper: () => {},
    renderAgentCards: () => {},
    renderSafetyCards: () => {},
    renderCommandList: () => {},
    renderTimeline: () => {},
    renderLatencyChart: () => {},
    mediaUrl: (p) => '/media?path=' + encodeURIComponent(String(p || '').replace(/\\/g, '/')),
    drawAnnotations: () => {},
  };
}

const RunPage = {
  runId: null,
  lab3d: null,
  lab3dFull: null,
  pollTimer: null,

  async init(runId) {
    this.runId = runId;
    this._bindTabs();
    document.getElementById('run-id-short').textContent = runId.slice(0, 8);

    this._mount3d();

    await this.refresh();
    document.getElementById('run-loading').hidden = true;
    document.getElementById('run-body').hidden = false;

    const live = new URLSearchParams(location.search).get('live') === '1';
    const run = await this._fetchRun();
    if (live || ['running', 'created', 'uploaded'].includes(run?.status)) {
      this._startPoll();
    }
  },

  _mount3d() {
    if (this.lab3d || !window.Lab3D) return;
    if (window.SimLab) this.lab3d = SimLab.mountMini('run-lab3d');
    this.lab3dFull = new Lab3D('run-lab3d-full', { compact: true, pollMs: 700 });
    if (this.lab3d) this.lab3d.opts.pollMs = 700;
  },

  _bindTabs() {
    document.querySelectorAll('.run-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.run-tab').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.run-tab-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        if (btn.dataset.tab === 'robot' && this.lab3dFull) this.lab3dFull._resize();
      });
    });
  },

  async _fetchRun() {
    const r = await fetch(`${vp().API}/runs/${this.runId}`);
    if (!r.ok) return null;
    return r.json();
  },

  async _fetchEvents() {
    const r = await fetch(`${vp().API}/runs/${this.runId}/events`);
    return r.ok ? r.json() : [];
  },

  async refresh() {
    const [run, events] = await Promise.all([this._fetchRun(), this._fetchEvents()]);
    if (!run) {
      document.getElementById('run-error').textContent = 'Run not found.';
      document.getElementById('run-error').hidden = false;
      return;
    }
    this._render(run, events);
  },

  _render(run, events) {
    document.getElementById('run-instruction').textContent = run.instruction || '—';
    const badge = document.getElementById('run-status-badge');
    badge.textContent = run.status;
    badge.className = 'badge badge-' + run.status;

    const cab = document.getElementById('current-agent-badge');
    if (run.current_agent) {
      cab.textContent = run.current_agent;
      cab.hidden = false;
    } else {
      cab.hidden = true;
    }

    const m = run.latency_metrics || {};
    document.getElementById('stat-agents').textContent = (run.agent_outputs || []).length;
    document.getElementById('stat-llm-calls').textContent = m.real_llm_calls || 0;
    document.getElementById('stat-latency').textContent = Math.round(m.total_latency_ms || 0);
    document.getElementById('stat-llm').textContent = m.model || m.llm_provider || '—';

    const real = (m.real_llm_calls || 0) > 0;
    const llmBadge = document.getElementById('run-llm-badge');
    if (llmBadge) {
      llmBadge.textContent = vp().llmLabel(m);
      llmBadge.classList.toggle('live', real);
    }
    const hint = document.getElementById('ai-mode-hint');
    if (hint) {
      hint.textContent = real ? '— live Gemma 4 on Cerebras' : '— add CEREBRAS_API_KEY in Settings';
    }

    const progress = vp().runProgress(run);
    document.getElementById('run-progress').style.width = progress + '%';
    document.getElementById('run-progress-label').textContent =
      run.status === 'running' ? `${progress}% · ${run.current_agent || 'working…'}` : run.status;

    if (run.error_message) {
      const err = document.getElementById('run-error');
      err.textContent = run.error_message;
      err.hidden = false;
    }

    document.getElementById('confirm-banner').hidden = run.status !== 'blocked';

    const V = vp();
    V.renderStepper(run.current_agent, run.agent_outputs);
    V.renderAgentCards(run.agent_outputs, 'agent-cards');
    V.renderSafetyCards(run.safety_decisions, 'safety-cards');
    V.renderCommandList(run.commands, 'command-list');
    V.renderTimeline(events, 'event-timeline');
    V.renderLatencyChart(run.latency_metrics);
    if (V.renderSpeedPanel) V.renderSpeedPanel(run.latency_metrics);

    this._renderVision(run);
    this._render3d(run);
  },

  _renderVision(run) {
    const img = document.getElementById('bench-image');
    const canvas = document.getElementById('annotation-canvas');
    const empty = document.getElementById('vision-empty');
    const summary = document.getElementById('vision-summary');
    const sourceBadge = document.getElementById('vision-source-badge');
    const objCount = document.getElementById('vision-obj-count');
    const chips = document.getElementById('vision-object-chips');
    if (!img) return;

    let src = '/simulator/frame.png';
    let source = 'Simulator camera';
    const paths = run.upload_paths || [];
    const frames = run.frame_paths || [];
    for (const p of paths) {
      if (!p.toLowerCase().endsWith('.mp4')) {
        src = vp().mediaUrl(p);
        source = 'Uploaded image';
        break;
      }
    }
    if (src === '/simulator/frame.png' && frames.length) {
      src = vp().mediaUrl(frames[0]);
      source = frames.length > 1 ? `Video · ${frames.length} frames` : 'Video frame';
    }

    const vision = run.visual_observations || {};
    const objects = vision.objects || [];
    const hazards = vision.hazards || [];

    if (sourceBadge) {
      sourceBadge.textContent = source;
      sourceBadge.classList.add('live');
    }
    if (objCount) {
      const n = objects.length;
      objCount.textContent = `${n} object${n === 1 ? '' : 's'}`;
      objCount.hidden = !n;
    }
    if (summary) {
      summary.textContent = vision.visual_summary
        || (objects.length
          ? `Detected ${objects.length} object(s)${hazards.length ? ` and ${hazards.length} hazard(s)` : ''}.`
          : (run.status === 'running' ? 'Vision agent analyzing frame…' : 'No vision analysis yet — re-run or add an image on the dashboard.'));
    }
    if (chips) {
      const esc = (s) => (vp().escapeHtml ? vp().escapeHtml(s) : String(s));
      chips.innerHTML = [
        ...objects.map(o => {
          const conf = o.confidence != null ? Math.round(o.confidence * 100) : null;
          const cls = conf != null && conf < 70 ? 'warn' : 'ok';
          const label = (o.label || o.id || 'object') + (conf != null ? ` ${conf}%` : '');
          return `<span class="vision-obj-chip ${cls}">${esc(label)}</span>`;
        }),
        ...hazards.map(h => `<span class="vision-obj-chip warn">⚠ ${esc(h.label || h.id || 'hazard')}</span>`),
      ].join('');
    }

    const bust = (src.includes('?') ? '&' : '?') + 't=' + Date.now();
    const draw = () => {
      if (empty) empty.hidden = true;
      img.hidden = false;
      if (objects.length) {
        vp().drawAnnotations('annotation-canvas', 'bench-image', objects);
      } else if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    };

    img.onload = draw;
    img.onerror = () => {
      if (empty) {
        empty.hidden = false;
        empty.textContent = 'Vision frame unavailable — simulator may be offline.';
      }
      img.hidden = true;
    };
    img.src = src + bust;
    if (img.complete && img.naturalWidth) draw();
  },

  _render3d(run) {
    const live = ['running', 'created', 'uploaded'].includes(run.status);
    const viewers = [this.lab3d, this.lab3dFull].filter(Boolean);
    if (!viewers.length) return;

    if (live) {
      viewers.forEach(v => {
        v.opts.sceneUrl = '/simulator/scene';
        v._sceneHash = '';
        v.loadScene();
      });
      return;
    }

    const state = run.bench_state;
    if (state?.objects) {
      const scene = {
        objects: state.objects,
        zones: state.zones || [],
        bench_size: state.bench_size || { width: 10, height: 6 },
        name: state.name,
      };
      const payload = { scene, arm: state.arm || {} };
      viewers.forEach(v => {
        v.opts.sceneUrl = '/simulator/scene';
        v._sceneHash = '';
        v.applyState(payload);
      });
    } else {
      viewers.forEach(v => v.loadScene());
    }
  },

  _startPoll() {
    if (this.pollTimer) clearInterval(this.pollTimer);
    const tick = async () => {
      await this.refresh();
      const run = await this._fetchRun();
      if (run && !['running', 'created', 'uploaded'].includes(run.status)) {
        clearInterval(this.pollTimer);
        const u = new URL(location.href);
        u.searchParams.delete('live');
        history.replaceState({}, '', u);
      }
    };
    tick();
    this.pollTimer = setInterval(tick, 1000);
  },

  async rerun() {
    const btn = document.getElementById('btn-rerun');
    btn.disabled = true;
    btn.textContent = 'Starting…';
    await fetch(`${vp().API}/runs/${this.runId}/rerun`, { method: 'POST' });
    const u = new URL(location.href);
    u.searchParams.set('live', '1');
    location.href = u.toString();
  },
};

window.RunPage = RunPage;