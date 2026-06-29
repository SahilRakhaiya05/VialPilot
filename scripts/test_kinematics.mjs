/**
 * Headless kinematics smoke test (arm chain + swing sweep).
 * Run: node scripts/test_kinematics.mjs
 */
import { createRequire } from 'module';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const THREE = require(join(__dirname, '..', 'node_modules/three/build/three.cjs'));

const ARM_ORIGIN = { x: 0, y: 0.31, z: 0 };
const ARM_LEN = { L1: 0.28, L2: 0.16 };

function swingAngle(tx, tz) {
  const dx = tx - ARM_ORIGIN.x;
  const dz = tz - ARM_ORIGIN.z;
  return Math.atan2(-dx, -dz);
}
function lerpAngleFull(a, b, t) {
  let d = b - a;
  while (d > Math.PI) d -= Math.PI * 2;
  while (d < -Math.PI) d += Math.PI * 2;
  return a + d * t;
}

function buildArm() {
  const arm = new THREE.Group();
  arm.position.set(ARM_ORIGIN.x, ARM_ORIGIN.y, ARM_ORIGIN.z);
  const j1 = new THREE.Group();
  j1.position.y = 0.4;
  arm.add(j1);
  const j2 = new THREE.Group();
  j1.add(j2);
  const j3 = new THREE.Group();
  j3.position.set(0, 0, -ARM_LEN.L1);
  j2.add(j3);
  const gripper = new THREE.Group();
  gripper.position.set(0, -0.01, -0.14);
  j3.add(gripper);
  const heldSlot = new THREE.Group();
  heldSlot.position.set(0, -0.098, 0.006);
  gripper.add(heldSlot);
  const tcp = new THREE.Object3D();
  tcp.position.set(0, 0.036, 0);
  heldSlot.add(tcp);
  return { arm, j1, j2, j3, tcp };
}

function applyJoints(j1, j2, j3, pose) {
  j1.position.y = pose.j1y ?? 0.28;
  j1.rotation.set(0, pose.j1 ?? 0, 0);
  j2.rotation.set(pose.j2 ?? -0.7, 0, 0);
  j3.rotation.set(pose.j3 ?? 0.4, 0, 0);
  j1.parent.updateMatrixWorld(true);
}

function tcpWorld(arm, tcp) {
  const v = new THREE.Vector3();
  tcp.getWorldPosition(v);
  return v;
}

const chain = buildArm();
const { arm, j1, j2, j3, tcp } = chain;

applyJoints(j1, j2, j3, { j1y: 0.28, j1: 0, j2: -0.5, j3: 0.2 });
const home = tcpWorld(arm, tcp);
applyJoints(j1, j2, j3, { j1y: 0.28, j1: 0, j2: -1.2, j3: 0.6 });
const bent = tcpWorld(arm, tcp);

const reachDelta = Math.hypot(bent.x - home.x, bent.z - home.z);
const heightDelta = Math.abs(bent.y - home.y);

const swingLeft = swingAngle(-0.3, 0.108);
const swingRight = swingAngle(0.35, 0.217);

const homeJ = { j1y: 0.28, j1: swingAngle(0, 0.02), j2: -0.55, j3: 0.35 };
const pickJ = { j1y: 0.3, j1: swingLeft, j2: -0.95, j3: 0.65 };
const midJ1 = lerpAngleFull(homeJ.j1, pickJ.j1, 0.5);
const yawSweep = Math.abs(midJ1 - homeJ.j1);

const failures = [];
if (reachDelta < 0.04) failures.push(`j2 pitch barely changes reach (${reachDelta.toFixed(4)})`);
if (heightDelta < 0.02) failures.push(`j2 pitch barely changes height (${heightDelta.toFixed(4)})`);
if (Math.abs(swingLeft - Math.atan2(0.3, -0.108)) > 0.001) failures.push('swing left mismatch');
if (Math.abs(swingRight - Math.atan2(-0.35, -0.217)) > 0.001) failures.push('swing right mismatch');
if (yawSweep < 0.4) failures.push(`joint swing too small (${yawSweep.toFixed(3)} rad)`);

applyJoints(j1, j2, j3, pickJ);
const pickTcp = tcpWorld(arm, tcp);
applyJoints(j1, j2, j3, { j1y: 0.28, j1: swingRight, j2: -0.9, j3: 0.6 });
const trayTcp = tcpWorld(arm, tcp);
if (pickTcp.x > -0.08) failures.push(`pick pose should be left (x=${pickTcp.x.toFixed(3)})`);
if (trayTcp.x < 0.08) failures.push(`tray pose should be right (x=${trayTcp.x.toFixed(3)})`);

console.log('reach delta:', reachDelta.toFixed(4), 'height delta:', heightDelta.toFixed(4));
console.log('yaw sweep mid:', yawSweep.toFixed(3), 'rad');
console.log('pick tcp.x:', pickTcp.x.toFixed(3), 'tray tcp.x:', trayTcp.x.toFixed(3));

if (failures.length) {
  console.error('FAIL:', failures.join('; '));
  process.exit(1);
}
console.log('OK — kinematics smoke test passed');