/** VialPilot 3D simulator — full sweep animation */
const SimLab = {
  viewer: null,
  _heldId: null,
  _speed: 0.45,
  _busy: false,

  mount(containerId) {
    if (!window.Lab3D || !window.THREE) {
      const el = document.getElementById(containerId);
      if (el) el.innerHTML = '<p class="hint" style="padding:24px">Load Three.js to enable 3D lab.</p>';
      return;
    }
    this.viewer = new Lab3D(containerId, { pollMs: 0, compact: false, labStyle: true });
    this.viewer.motionSpeed = this._speed;
  },

  mountMini(containerId) {
    if (!window.Lab3D) return null;
    return new Lab3D(containerId, { compact: true, pollMs: 1200, labStyle: true });
  },

  setSpeed(v) {
    this._speed = v;
    if (this.viewer) this.viewer.motionSpeed = v;
  },

  setCamera(preset) {
    if (this.viewer?.setCameraPreset) this.viewer.setCameraPreset(preset);
  },

  resetCamera() {
    this.setCamera('iso');
  },

  _setPipeline(phase) {
    const order = ['idle', 'approach', 'grip', 'sweep', 'place', 'home'];
    const idx = order.indexOf(phase);
    document.querySelectorAll('.lab-pipe-step').forEach(el => {
      const i = order.indexOf(el.dataset.phase);
      el.classList.toggle('active', el.dataset.phase === phase);
      el.classList.toggle('done', i >= 0 && idx >= 0 && i < idx);
    });
  },

  async _setStatus(msg, phase) {
    const el = document.getElementById('sim-action-status');
    if (el) el.textContent = msg;
    const phaseEl = document.getElementById('sim-phase');
    if (phaseEl && msg) phaseEl.textContent = msg.replace(/[✓…]/g, '').trim().slice(0, 28);
    if (phase) this._setPipeline(phase);
  },

  _updateHud(sceneData) {
    const arm = sceneData?.arm || {};
    const grip = document.getElementById('sim-gripper');
    const hold = document.getElementById('sim-holding');
    if (grip) {
      grip.textContent = arm.gripper_open === false ? 'Closed' : 'Open';
      grip.className = arm.gripper_open === false ? 'lab-gripper-closed' : 'lab-gripper-open';
    }
    if (hold) {
      hold.textContent = arm.holding
        ? arm.holding.replace('_vial', '')
        : (this._heldId ? this._heldId.replace('_vial', '') : '—');
    }
    if (arm.holding) this._heldId = arm.holding;
    const sc = document.getElementById('step-count');
    if (sc && sceneData?.step_count != null) sc.textContent = sceneData.step_count;
  },

  async _scene() {
    const r = await fetch('/simulator/scene');
    const data = await r.json();
    this._updateHud(data);
    return data;
  },

  async init() {
    const sceneId = document.getElementById('scene-select')?.value || 'safe_sorting_scene';
    await this._setStatus('Initializing lab bench…', 'idle');
    const r = await fetch('/simulator/init', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scene_id: sceneId, force_new: true }),
    });
    const data = await r.json();
    this._heldId = null;
    if (this.viewer) {
      this.viewer.resetSession();
      this.viewer.motionSpeed = this._speed;
      const scene = await this._scene();
      this.viewer.applyState(scene, { force: true, instant: true });
    }
    await this._setStatus('Ready — click Pick to see full approach & grip', 'idle');
    const chip = document.getElementById('sim-mode-chip');
    if (chip) chip.textContent = data.session_mode || 'precision-lab';
    const bar = document.getElementById('lab-task-text');
    if (bar && data.last_prompt) bar.textContent = data.last_prompt;
  },

  async _step(command) {
    const r = await fetch('/simulator/step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    });
    const st = await fetch('/simulator/status').then(x => x.json());
    const sc = document.getElementById('step-count');
    if (sc) sc.textContent = st.step_count || 0;
    return r.json();
  },

  async _sweepPick(objectId) {
    if (!this.viewer?.animateSweepPick) return;
    const scene = await this._scene();
    const obj = (scene.scene?.objects || scene.objects || []).find(o => o.id === objectId);
    if (!obj) {
      await this._setStatus(`Block ${objectId} not found — click Initialize`, 'idle');
      return;
    }
    await this._setStatus(`Approaching ${objectId.replace('_vial', '')}…`, 'approach');
    await this.viewer.animateSweepPick(scene, objectId);
    await this._setStatus(`Gripping ${objectId.replace('_vial', '')}…`, 'grip');
    await this._step({ command: 'PICK_OBJECT', object_id: objectId });
    this._heldId = objectId;
    const after = await this._scene();
    this.viewer.applyState(after, { force: true, instant: true, skipArm: true });
  },

  async _sweepPlace(objectId, zoneId) {
    if (!this.viewer?.animateSweepPlace) return;
    if (!this.viewer.heldVial && this._heldId) {
      const scene = await this._scene();
      this.viewer._attachHeld(this._heldId, scene.scene || scene);
    }
    const scene = await this._scene();
    await this._setStatus(`Lifting — sweeping XYZ to ${zoneId.replace('_', ' ')}…`, 'sweep');
    await this.viewer.animateSweepPlace(scene, objectId, zoneId);
    await this._setStatus('Fingers opening — block released…', 'place');
    await this._step({ command: 'PLACE_OBJECT', object_id: objectId, to: zoneId });
    this._heldId = null;
    const after = await this._scene();
    this.viewer.applyState(after, { force: true, instant: true, skipArm: true });
    await this._setStatus('Place complete', 'home');
  },

  async _run(fn) {
    if (this._busy) return;
    this._busy = true;
    document.querySelectorAll('.lab-pick-btn, .lab-btn').forEach(b => { b.disabled = true; });
    try {
      await fn();
    } catch (e) {
      console.error(e);
      await this._setStatus('Error — click Initialize to reset', 'idle');
    } finally {
      this._busy = false;
      document.querySelectorAll('.lab-pick-btn, .lab-btn').forEach(b => { b.disabled = false; });
    }
  },

  async pick(objectId) {
    if (!this.viewer) return;
    await this._run(async () => {
      if (this._heldId && this._heldId !== objectId) {
        await this._setStatus('Place the held block before picking another', 'grip');
        return;
      }
      if (this._heldId === objectId) {
        await this._setStatus(`Already holding ${objectId.replace('_vial', '')}`, 'grip');
        return;
      }
      await this._sweepPick(objectId);
      await this._setStatus(`Holding ${objectId.replace('_vial', '')} — visible in gripper`, 'grip');
    });
  },

  async place(zoneId) {
    if (!this.viewer) return;
    await this._run(async () => {
      const id = this._heldId;
      if (!id) {
        await this._setStatus('Pick a block first', 'idle');
        return;
      }
      await this._sweepPlace(id, zoneId);
    });
  },

  async demo() {
    if (!this.viewer) return;
    await this._run(async () => {
      const plan = [
        { pick: 'red_vial', place: 'safe_tray', label: 'red' },
        { pick: 'blue_vial', place: 'cold_tray', label: 'blue' },
        { pick: 'green_vial', place: 'waste_tray', label: 'green' },
      ];
      this.viewer.resetSession();
      this._heldId = null;
      await this.init();
      for (const s of plan) {
        await this._sweepPick(s.pick);
        await this._setStatus(`Sweeping ${s.label} to tray…`, 'sweep');
        await this._sweepPlace(s.pick, s.place);
      }
      await this._setStatus('Sweep complete — all blocks sorted', 'home');
    });
  },
};

window.SimLab = SimLab;
window.SimViewer = SimLab;