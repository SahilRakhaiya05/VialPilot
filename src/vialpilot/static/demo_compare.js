/** VialPilot — 3-way LLM speed race for demo video */
const DemoRace = {
  racing: false,
  timers: {},
  animFrame: null,
  maxMs: 25000,

  cards: {
    'cerebras-gemma4': { timer: 'timer-cerebras', bar: 'bar-cerebras', status: 'status-cerebras', summary: 'summary-cerebras', el: '.demo-cerebras' },
    'openai-gpt52': { timer: 'timer-openai', bar: 'bar-openai', status: 'status-openai', summary: 'summary-openai', el: '.demo-openai' },
    'gemini-20': { timer: 'timer-gemini', bar: 'bar-gemini', status: 'status-gemini', summary: 'summary-gemini', el: '.demo-gemini' },
  },

  async start() {
    if (this.racing) return;
    this.racing = true;
    const btn = document.getElementById('btn-race');
    if (btn) { btn.disabled = true; btn.textContent = 'Racing…'; }

    document.getElementById('demo-winner').hidden = true;
    Object.keys(this.cards).forEach((id) => {
      const c = this.cards[id];
      const card = document.querySelector(c.el);
      card?.classList.remove('winner', 'loser');
      card?.classList.add('racing');
      this._set(c.status, 'Running vision inference…');
      this._set(c.timer, '0 ms');
      this._set(c.summary, '');
      const bar = document.getElementById(c.bar);
      if (bar) bar.style.width = '0%';
      this.timers[id] = { start: performance.now(), done: false, ms: 0 };
    });

    this._animate();

    try {
      const res = await fetch('/api/demo/race', { method: 'POST' });
      const data = await res.json();
      this._finish(data);
    } catch (e) {
      this._set('status-cerebras', 'Race failed — check server');
      this.racing = false;
      if (btn) { btn.disabled = false; btn.textContent = '▶ Start Speed Race'; }
    }
  },

  _animate() {
    const tick = () => {
      if (!this.racing) return;
      const now = performance.now();
      Object.keys(this.timers).forEach((id) => {
        const t = this.timers[id];
        if (t.done) return;
        const elapsed = now - t.start;
        const c = this.cards[id];
        this._set(c.timer, `${Math.round(elapsed)} ms`);
        const bar = document.getElementById(c.bar);
        if (bar) bar.style.width = `${Math.min(100, (elapsed / this.maxMs) * 100)}%`;
      });
      this.animFrame = requestAnimationFrame(tick);
    };
    this.animFrame = requestAnimationFrame(tick);
  },

  _finish(data) {
    cancelAnimationFrame(this.animFrame);
    this.racing = false;
    const btn = document.getElementById('btn-race');
    if (btn) { btn.disabled = false; btn.textContent = '▶ Run Again'; }

    (data.results || []).forEach((r) => {
      const c = this.cards[r.id];
      if (!c) return;
      const card = document.querySelector(c.el);
      card?.classList.remove('racing');
      if (r.winner) card?.classList.add('winner');
      else card?.classList.add('loser');

      this.timers[r.id] = { ...this.timers[r.id], done: true, ms: r.latency_ms };
      this._set(c.timer, `${Math.round(r.latency_ms)} ms`);
      this._set(c.status, r.live ? '✓ Live inference complete' : (r.simulated ? '✓ Simulated GPU complete' : 'Unavailable'));
      this._set(c.summary, r.summary || '');
      const bar = document.getElementById(c.bar);
      if (bar) bar.style.width = `${Math.min(100, (r.latency_ms / this.maxMs) * 100)}%`;
    });

    const w = document.getElementById('demo-winner');
    const h = document.getElementById('winner-headline');
    const n = document.getElementById('winner-note');
    if (w && h) {
      h.textContent = data.headline || 'Race complete';
      if (n) n.textContent = data.note || '';
      w.hidden = false;
    }
  },

  _set(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  },
};