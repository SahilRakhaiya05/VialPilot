/**
 * VialPilot — 3D robotics simulator
 * Wooden bench, checker floor, gantry arm, smooth sweep pick/place
 */
(function (global) {
  const BLOCK_COLORS = {
    red: 0xd94a4a, blue: 0x3d7dd6, green: 0x3db86a,
    orange: 0xe8942a, purple: 0x9b59d4, gray: 0x8890a0,
  };
  const ZONE_FILL = { source: 0x5a6470, destination: 0xfad4e4, hazard: 0x8a4040 };
  const ZONE_EDGE = { source: 0x6a7588, destination: 0xf07898, hazard: 0xc05050 };
  const ARM_ORIGIN = { x: 0, y: 0.31, z: 0 };
  const HOME = { x: 0, z: 0.02 };
  const TABLE_Y = 0.31;
  const BLOCK_TOP_Y = TABLE_Y + 0.056;
  const H = { travel: 0.64, approach: 0.52, hover: 0.44, grasp: BLOCK_TOP_Y, lift: 0.56 };
  const LERP = 0.045;
  const GRIP_LERP = 0.1;

  function benchToWorld(x, y, bench) {
    const bw = bench?.width || 10, bh = bench?.height || 6;
    return { x: (x / bw - 0.5) * 1.0, z: -(y / bh - 0.5) * 0.65 };
  }

  function lerp(a, b, t) { return a + (b - a) * t; }
  function lerpAngle(c, t, f) {
    let d = t - c;
    while (d > Math.PI) d -= Math.PI * 2;
    while (d < -Math.PI) d += Math.PI * 2;
    return c + d * f;
  }

  const JLIMIT = {
    j1y: [0.04, 0.44], j1: [-1.85, 1.85], j2: [-1.55, -0.04], j3: [-0.25, 1.05],
  };

  function clampV(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function clampTy(ty) { return clampV(ty, BLOCK_TOP_Y - 0.004, 0.72); }

  function createWoodTexture(THREE) {
    const c = document.createElement('canvas');
    c.width = 256; c.height = 256;
    const g = c.getContext('2d');
    g.fillStyle = '#c9a96e';
    g.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 14; i++) {
      const y = i * 18 + (i % 3) * 2;
      g.strokeStyle = i % 2 ? '#b08d55' : '#a07d48';
      g.lineWidth = 1.5;
      g.beginPath(); g.moveTo(0, y); g.lineTo(256, y + 4); g.stroke();
    }
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(3, 2);
    return tex;
  }

  function createCheckerTexture(THREE) {
    const c = document.createElement('canvas');
    c.width = 128; c.height = 128;
    const g = c.getContext('2d');
    const sz = 16;
    for (let y = 0; y < 8; y++) {
      for (let x = 0; x < 8; x++) {
        g.fillStyle = (x + y) % 2 ? '#fafafa' : '#ececec';
        g.fillRect(x * sz, y * sz, sz, sz);
      }
    }
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(12, 12);
    return tex;
  }

  class Lab3D {
    constructor(containerId, options = {}) {
      this.container = document.getElementById(containerId);
      if (!this.container || !global.THREE) return;
      this.opts = {
        pollMs: options.pollMs !== undefined ? options.pollMs : 800,
        sceneUrl: options.sceneUrl || '/simulator/scene',
        compact: !!options.compact,
        labStyle: options.labStyle !== false,
      };
      this.vials = new Map();
      this._sceneHash = '';
      this._joint = { j1y: 0.38, j1: 0, j2: -0.5, j3: 0.2 };
      this._jointTarget = { j1y: 0.38, j1: 0, j2: -0.5, j3: 0.2 };
      this._gripperOpen = 1;
      this._gripperTarget = 1;
      this._motionQueue = [];
      this._motionBusy = false;
      this._lastArm = {};
      this._pendingScene = null;
      this.motionSpeed = 1;
      this._tick = 0;
      this._init();
      if (this.opts.pollMs > 0 && !this.opts.compact) this._poll();
    }

    _init() {
      const THREE = global.THREE;
      const w = this.container.clientWidth || 640;
      const h = this.container.clientHeight || (
        this.opts.compact ? 280 : Math.max(480, window.innerHeight - 140)
      );

      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(this.opts.labStyle ? 0xdce4ee : 0x0a0e18);
      if (this.opts.labStyle) this.scene.fog = new THREE.Fog(0xdce4ee, 2.8, 7.5);

      this.camera = new THREE.PerspectiveCamera(42, w / h, 0.1, 50);
      this.camera.position.set(0, 0.92, 1.28);
      this.camera.lookAt(0, 0.32, 0.02);

      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
      this.renderer.setSize(w, h);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      this.renderer.shadowMap.enabled = true;
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.05;
      this.container.innerHTML = '';
      this.container.appendChild(this.renderer.domElement);

      const amb = new THREE.AmbientLight(0xffffff, this.opts.labStyle ? 0.72 : 0.5);
      this.scene.add(amb);
      const sun = new THREE.DirectionalLight(0xfff8f0, 1.05);
      sun.position.set(1.5, 3.5, 2);
      sun.castShadow = true;
      sun.shadow.mapSize.set(2048, 2048);
      sun.shadow.camera.near = 0.5;
      sun.shadow.camera.far = 8;
      sun.shadow.camera.left = -2;
      sun.shadow.camera.right = 2;
      sun.shadow.camera.top = 2;
      sun.shadow.camera.bottom = -2;
      this.scene.add(sun);
      const fill = new THREE.DirectionalLight(0xc8d8f0, 0.35);
      fill.position.set(-2, 2, -1);
      this.scene.add(fill);
      const hemi = new THREE.HemisphereLight(0xf0f4ff, 0x8a9098, 0.42);
      this.scene.add(hemi);

      const checker = createCheckerTexture(THREE);
      const floor = new THREE.Mesh(
        new THREE.PlaneGeometry(8, 8),
        new THREE.MeshStandardMaterial({ map: checker, roughness: 0.9 })
      );
      floor.rotation.x = -Math.PI / 2;
      floor.position.y = 0;
      floor.receiveShadow = true;
      this.scene.add(floor);

      const wood = createWoodTexture(THREE);
      this.table = new THREE.Mesh(
        new THREE.BoxGeometry(1.05, 0.07, 0.72),
        new THREE.MeshStandardMaterial({ map: wood, roughness: 0.75, metalness: 0.05 })
      );
      this.table.position.set(0, 0.275, 0);
      this.table.castShadow = true;
      this.table.receiveShadow = true;
      this.scene.add(this.table);
      this._buildTableGrid(THREE);

      const skirt = new THREE.Mesh(
        new THREE.BoxGeometry(1.08, 0.11, 0.75),
        new THREE.MeshStandardMaterial({ color: 0x8a7048, roughness: 0.85 })
      );
      skirt.position.set(0, 0.225, 0);
      skirt.castShadow = true;
      this.scene.add(skirt);

      this._buildInputRack(THREE);
      this._buildBackdrop(THREE);

      this.zoneGroup = new THREE.Group();
      this.scene.add(this.zoneGroup);
      this.vialGroup = new THREE.Group();
      this.scene.add(this.vialGroup);

      this._buildGantry();
      this._setupControls();
      this._animate();
      window.addEventListener('resize', () => this._resize());
      this.loadScene();
    }

    _setupControls() {
      const OrbitControls = global.THREE?.OrbitControls;
      if (!OrbitControls || this.opts.compact) return;
      this.controls = new OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.07;
      this.controls.target.set(0, 0.32, 0.02);
      this.controls.minDistance = 0.7;
      this.controls.maxDistance = 3.5;
      this.controls.maxPolarAngle = Math.PI / 2.1;
      this.controls.minPolarAngle = 0.35;
    }

    _buildTableGrid(THREE) {
      const g = new THREE.Group();
      const mat = new THREE.LineBasicMaterial({ color: 0x8a7048, transparent: true, opacity: 0.35 });
      for (let i = -5; i <= 5; i++) {
        const t = i / 5;
        const geoH = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(-0.5, 0.31, t * 0.34),
          new THREE.Vector3(0.5, 0.31, t * 0.34),
        ]);
        g.add(new THREE.Line(geoH, mat));
        const geoV = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(t * 0.5, 0.31, -0.34),
          new THREE.Vector3(t * 0.5, 0.31, 0.34),
        ]);
        g.add(new THREE.Line(geoV, mat));
      }
      this.scene.add(g);
    }

    _buildBackdrop(THREE) {
      const checker = createCheckerTexture(THREE);
      const wall = new THREE.Mesh(
        new THREE.PlaneGeometry(6, 2.5),
        new THREE.MeshStandardMaterial({ map: checker, roughness: 0.92 })
      );
      wall.position.set(0, 1.15, -1.75);
      wall.receiveShadow = true;
      this.scene.add(wall);
      const sideL = wall.clone();
      sideL.rotation.y = Math.PI / 2;
      sideL.position.set(-2.8, 1.1, -0.4);
      this.scene.add(sideL);
      const sideR = wall.clone();
      sideR.rotation.y = -Math.PI / 2;
      sideR.position.set(2.8, 1.1, -0.4);
      this.scene.add(sideR);
    }

    setCameraPreset(preset) {
      const presets = {
        iso: { pos: [0, 0.92, 1.28], target: [0, 0.32, 0.02] },
        top: { pos: [0, 2.1, 0.15], target: [0, 0.31, 0] },
        side: { pos: [1.55, 0.78, 0.12], target: [0, 0.34, 0] },
      };
      const p = presets[preset] || presets.iso;
      this.camera.position.set(...p.pos);
      if (this.controls) {
        this.controls.target.set(...p.target);
        this.controls.update();
      } else {
        this.camera.lookAt(...p.target);
      }
    }

    _buildInputRack(THREE) {
      const rack = new THREE.Group();
      const mat = new THREE.MeshStandardMaterial({ color: 0x6a7585, metalness: 0.55, roughness: 0.35 });
      const left = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.14, 0.5), mat);
      left.position.set(-0.42, 0.34, 0.02);
      const right = left.clone();
      right.position.x = 0.42;
      const back = new THREE.Mesh(new THREE.BoxGeometry(0.86, 0.14, 0.02), mat);
      back.position.set(0, 0.34, 0.26);
      rack.add(left, right, back);
      this.scene.add(rack);
    }

    _zoneLabel(THREE, text) {
      const c = document.createElement('canvas');
      c.width = 256; c.height = 64;
      const g = c.getContext('2d');
      g.fillStyle = 'rgba(255,255,255,0.92)';
      if (g.roundRect) g.roundRect(4, 8, 248, 44, 8);
      else g.rect(4, 8, 248, 44);
      g.fill();
      g.fillStyle = '#3a342c';
      g.font = 'bold 22px DM Sans, sans-serif';
      g.fillText(String(text).slice(0, 18), 14, 38);
      const tex = new THREE.CanvasTexture(c);
      const mat = new THREE.SpriteMaterial({ map: tex, transparent: true });
      const spr = new THREE.Sprite(mat);
      spr.scale.set(0.22, 0.055, 1);
      spr.position.y = 0.06;
      return spr;
    }

    _buildGantry() {
      const THREE = global.THREE;
      const steel = new THREE.MeshStandardMaterial({ color: 0xa8b0bc, metalness: 0.55, roughness: 0.32 });
      const blue = new THREE.MeshStandardMaterial({ color: 0x2d6fd4, metalness: 0.4, roughness: 0.38 });
      const dark = new THREE.MeshStandardMaterial({ color: 0x3d4654, metalness: 0.55, roughness: 0.3 });

      this.arm = new THREE.Group();
      this.arm.position.set(ARM_ORIGIN.x, ARM_ORIGIN.y, ARM_ORIGIN.z);

      const base = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.12, 0.06, 28), blue);
      base.position.y = 0.03;
      base.castShadow = true;
      this.arm.add(base);

      const column = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.34, 0.1), steel);
      column.position.y = 0.23;
      column.castShadow = true;
      this.arm.add(column);
      const stripe = new THREE.Mesh(
        new THREE.BoxGeometry(0.102, 0.06, 0.102),
        new THREE.MeshStandardMaterial({ color: 0x2d6fd4, roughness: 0.38, metalness: 0.35 })
      );
      stripe.position.y = 0.12;
      this.arm.add(stripe);
      const jmat = new THREE.MeshStandardMaterial({ color: 0x2d3748, metalness: 0.7, roughness: 0.25 });

      this.j1 = new THREE.Group();
      this.j1.position.y = 0.4;
      this.arm.add(this.j1);

      const shoulder = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.08, 0.12), dark);
      shoulder.castShadow = true;
      this.j1.add(shoulder);
      const j1s = new THREE.Mesh(new THREE.SphereGeometry(0.04, 16, 16), jmat);
      j1s.castShadow = true;
      this.j1.add(j1s);

      this.j2 = new THREE.Group();
      this.j2.position.y = 0;
      const link = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.07, 0.28), steel);
      link.position.set(0, 0, -0.14);
      link.castShadow = true;
      this.j2.add(link);
      const j2s = new THREE.Mesh(new THREE.SphereGeometry(0.035, 14, 14), jmat);
      j2s.position.set(0, 0, -0.14);
      this.j2.add(j2s);
      this.j1.add(this.j2);

      this.j3 = new THREE.Group();
      this.j3.position.set(0, 0, -0.28);
      const fore = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, 0.12), steel);
      fore.position.set(0, 0, -0.06);
      fore.castShadow = true;
      this.j3.add(fore);
      this.j2.add(this.j3);

      this.gripper = new THREE.Group();
      this.gripper.position.set(0, -0.01, -0.14);

      const flange = new THREE.Mesh(new THREE.CylinderGeometry(0.036, 0.04, 0.018, 24), steel);
      flange.rotation.x = Math.PI / 2;
      flange.position.set(0, -0.008, 0.01);
      flange.castShadow = true;
      this.gripper.add(flange);

      const wrist = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.034, 0.05, 22), blue);
      wrist.rotation.x = Math.PI / 2;
      wrist.position.set(0, -0.022, 0.008);
      wrist.castShadow = true;
      this.gripper.add(wrist);

      const palm = new THREE.Mesh(new THREE.BoxGeometry(0.092, 0.042, 0.056), dark);
      palm.position.set(0, -0.048, -0.006);
      palm.castShadow = true;
      this.gripper.add(palm);

      const rail = new THREE.Mesh(new THREE.BoxGeometry(0.096, 0.01, 0.044), steel);
      rail.position.set(0, -0.068, 0.004);
      this.gripper.add(rail);

      const fingerMat = new THREE.MeshStandardMaterial({ color: 0x6a7588, metalness: 0.72, roughness: 0.18 });
      const padMat = new THREE.MeshStandardMaterial({ color: 0x1a1e24, roughness: 0.96, metalness: 0.04 });
      const mkFinger = (side) => {
        const root = new THREE.Group();
        const sign = side === 'L' ? -1 : 1;
        const mount = new THREE.Mesh(new THREE.BoxGeometry(0.018, 0.026, 0.042), dark);
        mount.position.set(sign * 0.038, -0.066, 0);
        mount.castShadow = true;
        const joint = new THREE.Group();
        joint.position.set(sign * 0.038, -0.074, 0);
        const prox = new THREE.Mesh(new THREE.BoxGeometry(0.014, 0.028, 0.038), fingerMat);
        prox.position.set(0, -0.014, 0);
        prox.castShadow = true;
        const mid = new THREE.Mesh(new THREE.BoxGeometry(0.013, 0.032, 0.036), fingerMat);
        mid.position.set(0, -0.042, 0);
        mid.castShadow = true;
        const pad = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.018, 0.034), padMat);
        pad.position.set(0, -0.062, 0);
        joint.add(prox, mid, pad);
        root.add(mount, joint);
        root.userData.joint = joint;
        return root;
      };
      this._fingerL = mkFinger('L');
      this._fingerR = mkFinger('R');
      const thumb = new THREE.Mesh(new THREE.BoxGeometry(0.028, 0.046, 0.032), fingerMat);
      thumb.position.set(0, -0.064, 0.028);
      thumb.castShadow = true;
      this.gripper.add(thumb);

      this.heldSlot = new THREE.Group();
      this.heldSlot.position.set(0, -0.098, 0.006);
      this.gripper.add(this.heldSlot);
      this._tcpMarker = new THREE.Object3D();
      this._tcpMarker.position.set(0, 0.036, 0);
      this.heldSlot.add(this._tcpMarker);

      const cradle = new THREE.Mesh(
        new THREE.BoxGeometry(0.062, 0.008, 0.052),
        new THREE.MeshStandardMaterial({ color: 0x4a5568, roughness: 0.45, metalness: 0.5 })
      );
      cradle.position.set(0, -0.01, 0);
      this.heldSlot.add(cradle);

      this.gripper.add(this._fingerL, this._fingerR);
      this.j3.add(this.gripper);
      this._setGripperOpen(1);

      this.heldVial = null;
      this.scene.add(this.arm);
    }

    _makeBlock(colorName, id) {
      const THREE = global.THREE;
      const g = new THREE.Group();
      const c = BLOCK_COLORS[colorName] || BLOCK_COLORS.gray;
      const shadow = new THREE.Mesh(
        new THREE.CircleGeometry(0.038, 24),
        new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.18 })
      );
      shadow.rotation.x = -Math.PI / 2;
      shadow.position.y = 0.002;
      g.add(shadow);
      const body = new THREE.Mesh(
        new THREE.BoxGeometry(0.052, 0.052, 0.052),
        new THREE.MeshStandardMaterial({ color: c, roughness: 0.28, metalness: 0.12 })
      );
      body.position.y = 0.028;
      body.castShadow = true;
      const cap = new THREE.Mesh(
        new THREE.BoxGeometry(0.04, 0.008, 0.04),
        new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.2, metalness: 0.05, transparent: true, opacity: 0.35 })
      );
      cap.position.y = 0.056;
      g.add(body, cap);
      g.userData.id = id;
      g.userData.color = colorName;
      return g;
    }

    _zoneBorder(THREE, w, d, color) {
      const pts = [
        new THREE.Vector3(-w / 2, 0, -d / 2),
        new THREE.Vector3(w / 2, 0, -d / 2),
        new THREE.Vector3(w / 2, 0, d / 2),
        new THREE.Vector3(-w / 2, 0, d / 2),
        new THREE.Vector3(-w / 2, 0, -d / 2),
      ];
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      const mat = new THREE.LineDashedMaterial({ color, dashSize: 0.035, gapSize: 0.022, linewidth: 2 });
      const line = new THREE.Line(geo, mat);
      line.computeLineDistances();
      return line;
    }

    resetSession() {
      this._motionQueue = [];
      this._motionBusy = false;
      this._sceneHash = '';
      this._lastArm = {};
      this._pickPos = null;
      if (this.heldVial) {
        this.heldSlot?.remove(this.heldVial);
        this.gripper?.remove(this.heldVial);
        this.vialGroup.remove(this.heldVial);
        this.heldVial = null;
      }
      this.vials.forEach(v => this.vialGroup.remove(v));
      this.vials.clear();
      this._ikSolve(HOME.x, H.travel, HOME.z);
      this._gripperOpen = this._gripperTarget = 1;
      this._setGripperOpen(1);
    }

    _blockTarget(obj, bench) {
      const p = benchToWorld(obj.x, obj.y, bench);
      return { x: p.x, y: BLOCK_TOP_Y, z: p.z };
    }

    _zoneTarget(zone, bench) {
      const p = benchToWorld(zone.x + zone.w / 2, zone.y + zone.h / 2, bench);
      return { x: p.x, y: BLOCK_TOP_Y, z: p.z };
    }

    _tcpXZ() {
      const t = this._tcpWorld();
      return { x: t.x, z: t.z };
    }

    _applyJointsFromState() {
      if (!this.j1) return;
      const j = this._joint;
      this.j1.position.y = j.j1y ?? 0.25;
      this.j1.rotation.y = j.j1 ?? 0;
      this.j2.rotation.z = j.j2 ?? -0.7;
      this.j3.rotation.z = j.j3 ?? 0.4;
      if (this.arm) this.arm.updateMatrixWorld(true);
    }

    _tcpWorld() {
      const THREE = global.THREE;
      const v = new THREE.Vector3();
      const m = this._tcpMarker || this.heldSlot;
      if (!m) return v;
      m.getWorldPosition(v);
      return v;
    }

    _swingAngle(tx, tz) {
      return Math.atan2(tx - ARM_ORIGIN.x, tz - ARM_ORIGIN.z);
    }

    _ikIterate(target, seed, toward) {
      let { j1y, j1, j2, j3 } = seed;
      let best = { j1y, j1, j2, j3, err: Infinity };
      for (let iter = 0; iter < 72; iter++) {
        j1y = clampV(j1y, JLIMIT.j1y[0], JLIMIT.j1y[1]);
        j1 = clampV(j1, JLIMIT.j1[0], JLIMIT.j1[1]);
        j2 = clampV(j2, JLIMIT.j2[0], JLIMIT.j2[1]);
        j3 = clampV(j3, JLIMIT.j3[0], JLIMIT.j3[1]);
        this._joint = { j1y, j1, j2, j3 };
        this._applyJointsFromState();
        const err = this._tcpWorld().distanceTo(target);
        if (err < best.err) best = { j1y, j1, j2, j3, err };
        if (err < 0.002) break;

        const eps = 0.011;
        const vals = { j1y, j1, j2, j3 };
        const grads = {};
        for (const p of ['j1y', 'j1', 'j2', 'j3']) {
          const trial = { ...vals };
          trial[p] = clampV(vals[p] + eps, JLIMIT[p][0], JLIMIT[p][1]);
          this._joint = trial;
          this._applyJointsFromState();
          grads[p] = (this._tcpWorld().distanceTo(target) - err) / eps;
        }
        j1y = clampV(j1y - grads.j1y * 0.2, JLIMIT.j1y[0], JLIMIT.j1y[1]);
        j1 = clampV(j1 - grads.j1 * 0.34, JLIMIT.j1[0], JLIMIT.j1[1]);
        j2 = clampV(j2 - grads.j2 * 0.38, JLIMIT.j2[0], JLIMIT.j2[1]);
        j3 = clampV(j3 - grads.j3 * 0.38, JLIMIT.j3[0], JLIMIT.j3[1]);
        j1 = lerpAngle(j1, toward, 0.18);
      }
      return best;
    }

    /** Multi-seed IK — always swings from center (home) side, never wrong hemisphere. */
    _ikSolve(tx, ty, tz) {
      const THREE = global.THREE;
      const target = new THREE.Vector3(tx, clampTy(ty), tz);
      const toward = this._swingAngle(tx, tz);
      const seeds = [
        { j1y: 0.3, j1: toward, j2: -0.95, j3: 0.7 },
        { j1y: 0.2, j1: toward, j2: -1.2, j3: 0.88 },
        { j1y: 0.36, j1: toward, j2: -0.72, j3: 0.48 },
        { j1y: this._joint.j1y ?? 0.28, j1: toward, j2: this._joint.j2 ?? -0.9, j3: this._joint.j3 ?? 0.6 },
      ];
      let best = null;
      for (const s of seeds) {
        const r = this._ikIterate(target, s, toward);
        if (!best || r.err < best.err) best = r;
      }
      this._joint = this._jointTarget = {
        j1y: best.j1y, j1: best.j1, j2: best.j2, j3: best.j3,
        tx, ty: target.y, tz,
      };
      this._applyJointsFromState();
      return best.err;
    }

    loadScene() {
      fetch(this.opts.sceneUrl)
        .then(r => r.json())
        .then(data => this.applyState(data))
        .catch(() => {});
    }

    _sceneFingerprint(data) {
      const scene = data.scene || data;
      const arm = data.arm || {};
      return JSON.stringify({
        objects: scene.objects,
        zones: scene.zones,
        holding: arm.holding,
        gripper: arm.gripper_open,
        target: arm.target,
      });
    }

    /** Waypoint between home and block — always approach from center line. */
    _pathPoint(tx, tz, t) {
      return { x: lerp(HOME.x, tx, t), z: lerp(HOME.z, tz, t) };
    }

    _sweepArc(ax, az, bx, bz, count) {
      const pts = [];
      const n = count || 6;
      const dx = bx - ax;
      const dz = bz - az;
      const len = Math.hypot(dx, dz) || 1;
      let nx = -dz / len;
      let nz = dx / len;
      if (nz < 0) { nx = -nx; nz = -nz; }
      const bulge = 0.1;
      for (let i = 1; i <= n; i++) {
        const t = i / n;
        const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
        const x = lerp(ax, bx, ease);
        const z = lerp(az, bz, ease);
        const b = Math.sin(t * Math.PI) * bulge;
        const arcY = H.lift + Math.sin(t * Math.PI) * 0.1;
        pts.push({ x: x + nx * b, z: z + nz * b, y: arcY });
      }
      return pts;
    }

    _enqueueMotion(steps) {
      this._motionQueue.push(...steps);
      if (!this._motionBusy) this._runMotionQueue();
    }

    _waitMotion() {
      return new Promise(resolve => {
        const check = () => {
          if (this._motionBusy || this._motionQueue.length) requestAnimationFrame(check);
          else resolve();
        };
        check();
      });
    }

    _runMotionSequence(steps) {
      this._motionQueue = [...steps];
      this._motionBusy = false;
      this._runMotionQueue();
      return this._waitMotion();
    }

    /** Smooth slide block into gripper — no teleport into hand. */
    _animateBlockIntoGrip(id, scene, bench) {
      return new Promise(resolve => {
        const obj = (scene.objects || []).find(o => o.id === id);
        if (!obj) { resolve(); return; }
        const bt = this._blockTarget(obj, bench);
        this._ikSolve(bt.x, bt.y, bt.z);
        let hv = this.vials.get(id);
        if (!hv || this.heldVial) { resolve(); return; }
        const sx = hv.position.x;
        const sy = hv.position.y;
        const sz = hv.position.z;
        const t0 = performance.now();
        const dur = 360;
        const tick = () => {
          const t = Math.min(1, (performance.now() - t0) / dur);
          const e = this._easeInOutCubic(t);
          const tcp = this._tcpWorld();
          hv.position.set(
            lerp(sx, tcp.x, e),
            lerp(sy, lerp(TABLE_Y, tcp.y - 0.04, 0.55), e),
            lerp(sz, tcp.z, e)
          );
          if (t < 1) requestAnimationFrame(tick);
          else {
            this._attachHeld(id, scene);
            resolve();
          }
        };
        tick();
      });
    }

    async _tryGripAttach(id, scene, bench) {
      const obj = (scene.objects || []).find(o => o.id === id);
      if (!obj) return;
      const bt = this._blockTarget(obj, bench);
      this._ikSolve(bt.x, bt.y, bt.z);
      const tcp = this._tcpWorld();
      const dx = tcp.x - bt.x;
      const dz = tcp.z - bt.z;
      const dy = tcp.y - bt.y;
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
      if (dist > 0.055) this._ikSolve(bt.x, bt.y, bt.z);
      await this._animateBlockIntoGrip(id, scene, bench);
    }

    /** Full sweep — center approach, align XYZ, descend, grip, smooth lift. */
    async animateSweepPick(sceneData, objectId) {
      const scene = sceneData.scene || sceneData;
      const bench = scene.bench_size || { width: 10, height: 6 };
      const obj = (scene.objects || []).find(o => o.id === objectId);
      if (!obj) return;
      this._motionScene = scene;
      this._motionBench = bench;
      const bt = this._blockTarget(obj, bench);
      const w20 = this._pathPoint(bt.x, bt.z, 0.2);
      const w45 = this._pathPoint(bt.x, bt.z, 0.45);
      const w70 = this._pathPoint(bt.x, bt.z, 0.7);
      const approach = [
        { x: HOME.x, z: HOME.z, y: H.travel, grip: 1, ms: 600 },
        { x: w20.x, z: w20.z, y: H.travel, grip: 1, ms: 950 },
        { x: w45.x, z: w45.z, y: H.approach, grip: 1, ms: 1050 },
        { x: w70.x, z: w70.z, y: H.hover, grip: 1, ms: 950 },
        { x: bt.x, z: bt.z, y: H.hover, grip: 1, ms: 900 },
        { x: bt.x, z: bt.z, y: 0.48, grip: 1, ms: 880 },
        { x: bt.x, z: bt.z, y: 0.42, grip: 1, ms: 850 },
        { x: bt.x, z: bt.z, y: bt.y, grip: 1, ms: 820 },
        { x: bt.x, z: bt.z, y: bt.y, grip: 0.35, ms: 380 },
        { x: bt.x, z: bt.z, y: bt.y, grip: 0.08, ms: 320, holdMs: 280 },
        { x: bt.x, z: bt.z, y: bt.y, grip: 0, ms: 280, attach: objectId, holdMs: 180 },
        { x: bt.x, z: bt.z, y: H.lift, grip: 0, ms: 900 },
        { x: bt.x, z: bt.z, y: H.travel, grip: 0, ms: 1000 },
      ];
      await this._runMotionSequence(approach);
      this._pickPos = { x: bt.x, z: bt.z };
      this._motionScene = null;
      this._motionBench = null;
    }

    /** Full XYZ place — sweep arc, descend, release, rise, return home. */
    async animateSweepPlace(sceneData, objectId, zoneId) {
      const scene = sceneData.scene || sceneData;
      const bench = scene.bench_size || { width: 10, height: 6 };
      const zone = (scene.zones || []).find(z => z.id === zoneId);
      if (!zone) return;

      if (!this.heldVial && objectId) {
        this._attachHeld(objectId, scene);
      }

      const zt = this._zoneTarget(zone, bench);
      this._applyJointsFromState();
      const cur = this._tcpWorld();
      const from = { x: cur.x, z: cur.z };
      const arc = this._sweepArc(from.x, from.z, zt.x, zt.z, 8);
      const midHome = this._pathPoint(zt.x, zt.z, 0.5);

      const steps = [
        { x: from.x, z: from.z, y: H.travel, grip: 0, ms: 700 },
      ];
      arc.forEach((pt, i) => {
        steps.push({ x: pt.x, z: pt.z, y: pt.y, grip: 0, ms: 780 + i * 55 });
      });
      steps.push(
        { x: zt.x, z: zt.z, y: H.hover, grip: 0, ms: 900 },
        { x: zt.x, z: zt.z, y: 0.44, grip: 0, ms: 850 },
        { x: zt.x, z: zt.z, y: 0.40, grip: 0, ms: 820 },
        { x: zt.x, z: zt.z, y: zt.y, grip: 0, ms: 880 },
        { x: zt.x, z: zt.z, y: zt.y, grip: 0.25, ms: 380 },
        { x: zt.x, z: zt.z, y: zt.y, grip: 1, ms: 520, holdMs: 200,
          onMid: () => this._detachHeldSmoothAt(zt.x, zt.z) },
        { x: zt.x, z: zt.z, y: H.lift, grip: 1, ms: 850 },
        { x: midHome.x, z: midHome.z, y: H.travel, grip: 1, ms: 950 },
        { x: HOME.x, z: HOME.z, y: H.travel, grip: 1, ms: 1100 },
      );
      await this._runMotionSequence(steps);
      this._pickPos = { x: zt.x, z: zt.z };
    }

    _runMotionQueue() {
      if (!this._motionQueue.length) {
        this._motionBusy = false;
        if (this._pendingScene) {
          const p = this._pendingScene;
          this._pendingScene = null;
          this._applySceneObjects(p);
        }
        return;
      }
      this._motionBusy = true;
      const step = this._motionQueue.shift();
      this._animateTo(step, () => this._runMotionQueue());
    }

    _setGripperOpen(amount) {
      if (!this._fingerL || !this._fingerR) return;
      const spread = 0.022 + amount * 0.032;
      this._fingerL.position.x = -spread;
      this._fingerR.position.x = spread;
      const curl = amount * 0.32;
      const lj = this._fingerL.userData.joint;
      const rj = this._fingerR.userData.joint;
      if (lj) { lj.rotation.z = curl; lj.rotation.x = curl * 0.15; }
      if (rj) { rj.rotation.z = -curl; rj.rotation.x = -curl * 0.15; }
    }

    _easeInOutCubic(t) {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    _animateTo(step, onDone) {
      this._applyJointsFromState();
      const startTcp = this._tcpWorld();
      const endY = clampTy(step.y !== undefined ? step.y : H.hover);
      const endTcp = { x: step.x, y: endY, z: step.z };
      const startGrip = this._gripperOpen;
      const endGrip = step.grip !== undefined ? step.grip : this._gripperTarget;
      const dur = (step.ms || 520) / (this.motionSpeed || 1);
      const t0 = performance.now();

      const tick = () => {
        const t = Math.min(1, (performance.now() - t0) / dur);
        const e = this._easeInOutCubic(t);
        const cx = lerp(startTcp.x, endTcp.x, e);
        const cy = lerp(startTcp.y, endTcp.y, e);
        const cz = lerp(startTcp.z, endTcp.z, e);
        this._ikSolve(cx, cy, cz);
        this._gripperOpen = this._gripperTarget = lerp(startGrip, endGrip, e);
        this._setGripperOpen(this._gripperOpen);
        if (t < 1) requestAnimationFrame(tick);
        else {
          this._ikSolve(endTcp.x, endTcp.y, endTcp.z);
          const afterStep = async () => {
            if (step.attach && this._motionScene) {
              await this._tryGripAttach(step.attach, this._motionScene, this._motionBench);
            }
            if (step.onMid) step.onMid();
            onDone();
          };
          if (step.holdMs) setTimeout(() => { afterStep(); }, step.holdMs);
          else afterStep();
        }
      };
      tick();
    }

    _buildPickPlaceMotion(arm, scene, bench) {
      const target = arm.target || {};
      const tx = target.x ?? 0;
      const tz = target.z ?? 0;
      const holding = arm.holding;
      const gripClosed = arm.gripper_open === false;
      const steps = [];

      if (holding && gripClosed) {
        steps.push({ x: tx, z: tz, y: H.hover, grip: 0, ms: 480 });
        steps.push({ x: tx, z: tz, y: H.grasp, grip: 0, ms: 420 });
        steps.push({ x: tx, z: tz, y: H.grasp, grip: 0, ms: 180, holdMs: 120, onMid: () => this._attachHeld(holding, scene) });
        steps.push({ x: tx, z: tz, y: H.lift, grip: 0, ms: 450 });
      } else if (!holding && !gripClosed && this._lastArm.holding) {
        steps.push({ x: tx, z: tz, y: H.hover, grip: 0, ms: 560 });
        steps.push({ x: tx, z: tz, y: H.grasp, grip: 0, ms: 400 });
        steps.push({ x: tx, z: tz, y: H.grasp, grip: 1, ms: 200, holdMs: 100, onMid: () => this._detachHeld() });
        steps.push({ x: tx, z: tz, y: H.travel, grip: 1, ms: 420 });
      } else {
        steps.push({ x: tx, z: tz, y: gripClosed ? H.grasp : H.hover, grip: gripClosed ? 0 : 1, ms: 600 });
      }
      return steps;
    }

    _attachHeld(id, scene) {
      let hv = this.vials.get(id);
      if (!hv) {
        const o = (scene.objects || []).find(x => x.id === id);
        if (o) { hv = this._makeBlock(o.color, o.id); this.vials.set(id, hv); }
      }
      if (!hv || !this.heldSlot) return;
      if (this.heldVial && this.heldVial !== hv) {
        this.heldSlot.remove(this.heldVial);
        this.gripper.remove(this.heldVial);
      }
      this.heldVial = hv;
      this.vialGroup.remove(hv);
      if (hv.parent !== this.heldSlot) {
        this.heldSlot.add(hv);
      }
      hv.position.set(0, 0.038, 0);
      hv.rotation.set(0, 0, 0);
      hv.scale.set(1, 1, 1);
      hv.traverse(ch => {
        if (ch.isMesh) {
          ch.renderOrder = 10;
          if (ch.material) ch.material.depthTest = true;
        }
      });
      const shadow = hv.children[0];
      if (shadow?.isMesh) shadow.visible = false;
    }

    _detachHeld() {
      const t = this._tcpWorld();
      this._detachHeldAt(t.x, t.z);
    }

    _detachHeldAt(wx, wz) {
      if (!this.heldVial) return;
      const v = this.heldVial;
      if (this.heldSlot) this.heldSlot.remove(v);
      this.gripper.remove(v);
      this.vialGroup.add(v);
      v.position.set(wx, TABLE_Y, wz);
      v.rotation.set(0, 0, 0);
      const shadow = v.children[0];
      if (shadow?.isMesh) shadow.visible = true;
      v.traverse(ch => { if (ch.isMesh) ch.renderOrder = 0; });
      this.heldVial = null;
    }

    _detachHeldSmoothAt(wx, wz) {
      if (!this.heldVial) return;
      const v = this.heldVial;
      const tcp = this._tcpWorld();
      if (this.heldSlot) this.heldSlot.remove(v);
      this.gripper.remove(v);
      this.vialGroup.add(v);
      const sx = tcp.x;
      const sy = TABLE_Y + 0.06;
      const sz = tcp.z;
      const t0 = performance.now();
      const tick = () => {
        const t = Math.min(1, (performance.now() - t0) / 340);
        const e = this._easeInOutCubic(t);
        v.position.set(lerp(sx, wx, e), lerp(sy, TABLE_Y, e), lerp(sz, wz, e));
        if (t < 1) requestAnimationFrame(tick);
        else {
          v.position.set(wx, TABLE_Y, wz);
          const shadow = v.children[0];
          if (shadow?.isMesh) shadow.visible = true;
          v.traverse(ch => { if (ch.isMesh) ch.renderOrder = 0; });
          this.heldVial = null;
        }
      };
      tick();
    }

    _applySceneObjects(data) {
      const scene = data.scene || data;
      const bench = scene.bench_size || { width: 10, height: 6 };
      const arm = data.arm || {};
      const THREE = global.THREE;

      while (this.zoneGroup.children.length) this.zoneGroup.remove(this.zoneGroup.children[0]);
      (scene.zones || []).forEach(z => {
        const p = benchToWorld(z.x + z.w / 2, z.y + z.h / 2, bench);
        const gw = (z.w / bench.width) * 0.98;
        const gd = (z.h / bench.height) * 0.68;
        const kind = z.kind || 'destination';
        const fill = new THREE.Mesh(
          new THREE.BoxGeometry(gw, 0.006, gd),
          new THREE.MeshStandardMaterial({
            color: ZONE_FILL[kind] || ZONE_FILL.destination,
            transparent: true, opacity: kind === 'destination' ? 0.55 : 0.45, roughness: 0.85,
          })
        );
        fill.position.set(p.x, 0.312, p.z);
        this.zoneGroup.add(fill);
        const border = this._zoneBorder(THREE, gw * 0.92, gd * 0.92, ZONE_EDGE[kind] || 0xe87898);
        border.position.set(p.x, 0.316, p.z);
        this.zoneGroup.add(border);
        if (kind === 'destination') {
          const glow = new THREE.Mesh(
            new THREE.RingGeometry(0.02, Math.min(gw, gd) * 0.42, 32),
            new THREE.MeshBasicMaterial({ color: 0xf0a8c8, transparent: true, opacity: 0.45, side: THREE.DoubleSide })
          );
          glow.rotation.x = -Math.PI / 2;
          glow.position.set(p.x, 0.314, p.z);
          this.zoneGroup.add(glow);
        }
        if (!this.opts.compact && z.label) {
          const lbl = this._zoneLabel(THREE, z.label);
          lbl.position.set(p.x, 0.34, p.z);
          this.zoneGroup.add(lbl);
        }
      });

      const seen = new Set();
      (scene.objects || []).forEach(obj => {
        if (arm.holding === obj.id) return;
        if (this.heldVial && this.heldVial.userData.id === obj.id) return;
        seen.add(obj.id);
        const p = benchToWorld(obj.x, obj.y, bench);
        let v = this.vials.get(obj.id);
        if (!v) {
          v = this._makeBlock(obj.color, obj.id);
          this.vialGroup.add(v);
          this.vials.set(obj.id, v);
        }
        v.position.set(p.x, 0.31, p.z);
      });
      this.vials.forEach((v, id) => {
        if (this.heldVial && this.heldVial.userData.id === id) return;
        if (!seen.has(id) && arm.holding !== id) {
          this.vialGroup.remove(v);
          this.vials.delete(id);
        }
      });

      if (arm.holding && arm.gripper_open === false) {
        this._attachHeld(arm.holding, scene);
      } else if (!arm.holding && !this._motionBusy && !this.heldVial) {
        this._detachHeld();
      }

      const prompt = data.task_prompt || scene.description;
      const bar = document.getElementById('lab-task-text');
      if (bar && prompt) bar.textContent = '— ' + prompt.replace(/^Sort all[^.]*/, '').trim() || prompt;
    }

    applyState(data, opts = {}) {
      if (!data || !this.scene) return;
      const instant = opts.instant || this.opts.compact;
      const hash = this._sceneFingerprint(data);
      if (hash === this._sceneHash && !opts.force) return;
      this._sceneHash = hash;

      const scene = data.scene || data;
      const bench = scene.bench_size || { width: 10, height: 6 };
      const arm = data.arm || {};

      if (instant) {
        this._applySceneObjects(data);
        if (!opts.skipArm && arm.target) {
          const ty = arm.target.y || (arm.gripper_open === false ? H.grasp : H.hover);
          this._ikSolve(arm.target.x, ty, arm.target.z);
        }
        if (!opts.skipArm) this._gripperTarget = arm.gripper_open === false ? 0 : 1;
        this._lastArm = { holding: arm.holding, gripper: arm.gripper_open, target: arm.target };
        return;
      }

      const armChanged = JSON.stringify(arm) !== JSON.stringify(this._lastArm);
      if (armChanged && arm.target) {
        if (this._motionBusy) this._pendingScene = data;
        else {
          this._applySceneObjects(data);
          const steps = this._buildPickPlaceMotion(arm, scene, bench);
          this._enqueueMotion(steps);
        }
      } else {
        this._applySceneObjects(data);
      }
      this._lastArm = { holding: arm.holding, gripper: arm.gripper_open, target: arm.target };
    }

    /** Play full sweep animation after a simulator step (demo / manual control). */
    async playStep(sceneData) {
      this._sceneHash = '';
      return new Promise(resolve => {
        const done = () => setTimeout(resolve, 80);
        this.applyState(sceneData, { force: true });
        const check = () => {
          if (this._motionBusy || this._motionQueue.length) requestAnimationFrame(check);
          else done();
        };
        setTimeout(check, 100);
      });
    }

    _animateArm() {
      if (!this.arm || !this.j1) return;
      if (!this._motionBusy) {
        const jt = this._jointTarget;
        this._joint.j1y = lerp(this._joint.j1y ?? 0.25, jt.j1y ?? 0.25, LERP);
        this._joint.j1 = lerpAngle(this._joint.j1, jt.j1, LERP);
        this._joint.j2 = lerp(this._joint.j2, jt.j2, LERP);
        this._joint.j3 = lerp(this._joint.j3, jt.j3, LERP);
        this._gripperOpen += (this._gripperTarget - this._gripperOpen) * GRIP_LERP;
        this._applyJointsFromState();
        this._setGripperOpen(this._gripperOpen);
      }
    }

    _animate() {
      requestAnimationFrame(() => this._animate());
      this._tick += 0.016;

      this._animateArm();
      if (this.controls) this.controls.update();
      if (this.renderer && this.scene && this.camera) this.renderer.render(this.scene, this.camera);
    }

    _resize() {
      if (!this.container || !this.renderer) return;
      const w = this.container.clientWidth;
      const h = this.container.clientHeight;
      if (w < 10 || h < 10) return;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    }

    _poll() {
      setInterval(() => {
        if (!this._motionBusy) this.loadScene();
      }, this.opts.pollMs);
    }
  }

  global.Lab3D = Lab3D;
})(typeof window !== 'undefined' ? window : global);