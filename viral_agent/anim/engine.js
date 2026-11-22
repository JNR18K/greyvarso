// Moteur d'animation 3D (three.js) pour vidéos POV cartoon.
// Rendu image par image (déterministe) : window.setupShot(shot) puis window.renderFrame(t, mouths).
import * as THREE from './three.module.js';

const W = 720, H = 1280;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(W, H);
renderer.setPixelRatio(1);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
document.body.appendChild(renderer.domElement);

// ------------------------------------------------------------ utilitaires
const gradient = (() => {
  const d = new Uint8Array([90, 170, 255]);
  const t = new THREE.DataTexture(d, 3, 1, THREE.RedFormat);
  t.minFilter = t.magFilter = THREE.NearestFilter; t.needsUpdate = true; return t;
})();
const toon = (color, extra = {}) => new THREE.MeshToonMaterial({ color, gradientMap: gradient, ...extra });
const basic = (color, extra = {}) => new THREE.MeshBasicMaterial({ color, ...extra });
const ease = (x) => x < 0.5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
const lerp = (a, b, x) => a + (b - a) * x;
const lerpV = (a, b, x) => new THREE.Vector3(lerp(a[0], b[0], x), lerp(a[1], b[1], x), lerp(a[2], b[2], x));
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d'); draw(g, w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}
function mesh(geo, mat, x = 0, y = 0, z = 0, parent) {
  const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); if (parent) parent.add(m); return m;
}
function outline(m, s = 1.06) {  // contour noir façon dessin animé
  const o = new THREE.Mesh(m.geometry, basic(0x1a1410, { side: THREE.BackSide }));
  o.scale.setScalar(s); m.add(o); return m;
}
function blobShadow(parent, r = 0.35, x = 0, z = 0) {
  const t = canvasTex(64, 64, (g) => { const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(0,0,0,0.45)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, 64, 64); });
  const m = mesh(new THREE.PlaneGeometry(r * 2, r * 2), new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false }), x, 0.005, z, parent);
  m.rotation.x = -Math.PI / 2; return m;
}

// ------------------------------------------------------------ personnage jouet (design original)
const SKIN = 0xf2c9a0, WOOD = 0xe7c39a;
function makeCharacter(o = {}) {
  const c = {
    skin: SKIN, shirt: 0xd8312a, pants: 0x1f2a5a, shoes: 0x2b2b2b, hair: 0x3a2516, hairStyle: 'short',
    chubby: false, robe: false, dress: null, beard: false, aviators: false, glasses: false, chain: false, scale: 1, ...o };
  const root = new THREE.Group(); root.scale.setScalar(c.scale);
  const body = new THREE.Group(); root.add(body);
  const wide = c.chubby ? 1.35 : 1;
  // jambes en bois
  const legGeo = new THREE.CylinderGeometry(0.045, 0.04, 0.55, 10); legGeo.translate(0, -0.275, 0);
  const legs = [-1, 1].map((s) => {
    const hip = new THREE.Group(); hip.position.set(0.09 * s * wide, 0.95, 0); body.add(hip);
    outline(mesh(legGeo, toon(WOOD), 0, 0, 0, hip));
    const shoe = outline(mesh(new THREE.SphereGeometry(0.075, 12, 8), toon(c.shoes), 0, -0.56, 0.03, hip)); shoe.scale.set(0.9, 0.55, 1.4);
    return hip;
  });
  // short / pantalon / robe
  if (c.dress) {
    outline(mesh(new THREE.ConeGeometry(0.3 * wide, 0.5, 18, 1, true), toon(c.dress, { side: THREE.DoubleSide }), 0, 0.88, 0, body));
  } else {
    const p = outline(mesh(new THREE.CylinderGeometry(0.17 * wide, 0.19 * wide, 0.22, 16), toon(c.pants), 0, 0.98, 0, body));
    if (c.robe) p.visible = false;
  }
  // torse
  const torsoMat = toon(c.robe ? 0xf4f4f0 : c.shirt);
  const torso = outline(mesh(new THREE.CapsuleGeometry(0.16, 0.26, 6, 16), torsoMat, 0, 1.25, 0, body));
  torso.scale.set(1.05 * wide, 1, 0.85 * wide);
  if (c.robe) {  // peignoir
    const lower = outline(mesh(new THREE.CylinderGeometry(0.2 * wide, 0.26 * wide, 0.5, 16), torsoMat, 0, 0.88, 0, body));
    const belt = mesh(new THREE.TorusGeometry(0.19 * wide, 0.02, 6, 20), toon(0xdedcd5), 0, 1.08, 0, body); belt.rotation.x = Math.PI / 2;
    const lap = mesh(new THREE.BoxGeometry(0.06, 0.32, 0.02), toon(0xe9e7e0), 0, 1.3, 0.15 * wide, body); lap.rotation.z = 0.25;
  }
  if (c.chain) { const ch = mesh(new THREE.TorusGeometry(0.11, 0.012, 6, 24), toon(0xf3c63f, { emissive: 0x3a2a00 }), 0, 1.4, 0.06, body); ch.rotation.x = 1.25; }
  // bras + manches bouffantes
  const armGeo = new THREE.CylinderGeometry(0.035, 0.03, 0.46, 10); armGeo.translate(0, -0.23, 0);
  const arms = [-1, 1].map((s) => {
    const sh = new THREE.Group(); sh.position.set(0.22 * s * wide, 1.42, 0); body.add(sh);
    const sleeve = outline(mesh(new THREE.SphereGeometry(0.085, 14, 10), torsoMat, 0, -0.04, 0, sh)); sleeve.scale.set(1, 1.1, 1);
    if (c.robe) { const ls = outline(mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.3, 10), torsoMat, 0, -0.18, 0, sh)); }
    outline(mesh(armGeo, toon(WOOD), 0, 0, 0, sh));
    const hand = outline(mesh(new THREE.SphereGeometry(0.05, 12, 8), toon(c.skin), 0, -0.48, 0, sh)); hand.scale.set(1, 1.15, 0.8);
    sh.rotation.z = 0.12 * s;
    return sh;
  });
  // tête
  const neck = mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.1, 8), toon(WOOD), 0, 1.53, 0, body);
  const head = new THREE.Group(); head.position.set(0, 1.74, 0); body.add(head);
  const skull = outline(mesh(new THREE.SphereGeometry(0.2, 24, 18), toon(c.skin), 0, 0, 0, head)); skull.scale.set(c.chubby ? 1.12 : 1, 1.05, 1);
  const eyes = [-1, 1].map((s) => {
    const e = new THREE.Group(); e.position.set(0.075 * s, 0.03, 0.17); head.add(e);
    const white = outline(mesh(new THREE.SphereGeometry(0.055, 16, 12), basic(0xffffff), 0, 0, 0, e), 1.12);
    const pupil = mesh(new THREE.SphereGeometry(0.026, 12, 8), basic(0x111111), 0, 0, 0.042, e);
    const shine = mesh(new THREE.SphereGeometry(0.008, 6, 6), basic(0xffffff), 0.01, 0.012, 0.064, e);
    return { e, pupil };
  });
  const brows = [-1, 1].map((s) => { const b = mesh(new THREE.BoxGeometry(0.07, 0.014, 0.02), basic(0x2a1a10), 0.075 * s, 0.11, 0.19, head); return b; });
  const nose = outline(mesh(new THREE.SphereGeometry(0.03, 10, 8), toon(0xe0a982), 0, -0.035, 0.2, head));
  const mouth = mesh(new THREE.SphereGeometry(0.045, 14, 10), basic(0x3a0d0d), 0, -0.1, 0.17, head); mouth.scale.set(1, 0.15, 0.4);
  // cheveux
  const hairMat = toon(c.hair);
  if (c.hairStyle === 'short' || c.hairStyle === 'long') {
    const cap = outline(mesh(new THREE.SphereGeometry(0.212, 24, 12, 0, Math.PI * 2, 0, Math.PI * 0.42), hairMat, 0, 0.015, -0.01, head));
    cap.rotation.x = -0.25;
  }
  if (c.hairStyle === 'long') {
    const back = outline(mesh(new THREE.CapsuleGeometry(0.17, 0.32, 4, 12), hairMat, 0, -0.14, -0.09, head)); back.scale.set(1.25, 1, 0.6);
    [-1, 1].forEach((s) => { const side = outline(mesh(new THREE.CapsuleGeometry(0.05, 0.3, 4, 8), hairMat, 0.19 * s, -0.1, 0.02, head)); });
  }
  if (c.hairStyle === 'curly') {
    const r = rng(7);
    for (let i = 0; i < 26; i++) {
      const th = r() * Math.PI * 2, ph = r() * 1.1;
      const p = new THREE.Vector3(Math.sin(ph) * Math.cos(th), Math.cos(ph), Math.sin(ph) * Math.sin(th)).multiplyScalar(0.2);
      if (p.z > 0.12 && p.y < 0.12) continue;
      outline(mesh(new THREE.SphereGeometry(0.055 + r() * 0.02, 10, 8), hairMat, p.x, p.y + 0.03, p.z - 0.02, head));
    }
  }
  if (c.hairStyle === 'bald') {
    const ring = mesh(new THREE.TorusGeometry(0.19, 0.035, 8, 24, Math.PI * 1.3), hairMat, 0, 0.0, -0.02, head);
    ring.rotation.set(Math.PI / 2, 0, Math.PI * 0.85);
  }
  if (c.beard) {
    const b = mesh(new THREE.SphereGeometry(0.2, 20, 12, 0, Math.PI * 2, Math.PI * 0.55, Math.PI * 0.45), toon(c.hair), 0, -0.01, 0.01, head);
    b.scale.set(1.03, 1.05, 1.05);
    mouth.position.z = 0.205;
  }
  if (c.aviators || c.glasses) {
    const frame = toon(c.aviators ? 0xd9a520 : 0x222222);
    [-1, 1].forEach((s) => {
      const ring = mesh(new THREE.TorusGeometry(0.058, 0.009, 6, 18), frame, 0.075 * s, 0.03, 0.225, head);
      if (c.aviators) { const lens = mesh(new THREE.CircleGeometry(0.056, 18), basic(0x1b2430, { transparent: true, opacity: 0.88 }), 0.075 * s, 0.03, 0.226, head); lens.scale.y = 0.85; }
    });
    mesh(new THREE.BoxGeometry(0.04, 0.008, 0.008), frame, 0, 0.05, 0.225, head);
    if (c.aviators) eyes.forEach((e) => (e.e.visible = false));
  }
  blobShadow(root, 0.32 * wide);
  return { root, body, head, legs, arms, eyes, brows, mouth, cfg: c, mood: 'neutral' };
}

// pose du personnage à l'instant t
function animateCharacter(ch, t, mouthOpen = 0, act = {}) {
  const a = act.action || 'idle';
  const breath = Math.sin(t * 2.2 + (act.phase || 0)) * 0.012;
  ch.body.position.y = breath; ch.body.rotation.set(0, 0, 0);
  ch.legs.forEach((l) => (l.rotation.x = 0));
  ch.arms[0].rotation.set(0, 0, -0.12 - Math.sin(t * 2) * 0.02);
  ch.arms[1].rotation.set(0, 0, 0.12 + Math.sin(t * 2) * 0.02);
  if (a === 'walk') {
    const w = Math.sin(t * 7);
    ch.legs[0].rotation.x = w * 0.55; ch.legs[1].rotation.x = -w * 0.55;
    ch.arms[0].rotation.x = -w * 0.45; ch.arms[1].rotation.x = w * 0.45;
    ch.body.position.y = Math.abs(Math.cos(t * 7)) * 0.04;
  }
  if (a === 'sit') {
    ch.legs.forEach((l) => (l.rotation.x = -1.45)); ch.body.position.y = -0.42;
  }
  if (a === 'point') {  // pointe le doigt vers la caméra, agacé
    ch.arms[1].rotation.set(-1.35 + Math.sin(t * 9) * 0.08, 0, 0.25);
  }
  if (a === 'toss') {  // lance des pièces
    const k = Math.min(1, ((t - (act.at || 0.4)) * 3));
    ch.arms[1].rotation.set(k > 0 ? -0.9 - Math.sin(Math.min(k, 1) * Math.PI) * 0.6 : 0, 0, 0.2);
  }
  if (a === 'hips') { ch.arms[0].rotation.set(0, 0, -0.9); ch.arms[1].rotation.set(0, 0, 0.9); }
  if (a === 'hug_self') { ch.arms[0].rotation.set(-1.2, 0, 0.5); ch.arms[1].rotation.set(-1.2, 0, -0.5); }
  if (a === 'wave') { ch.arms[1].rotation.set(0, 0, 2.6 + Math.sin(t * 8) * 0.3); }
  // tête : parle = petits hochements
  ch.head.rotation.set(mouthOpen * 0.08 * Math.sin(t * 13) + (act.headTilt || 0), Math.sin(t * 0.7) * 0.06 + (act.headTurn || 0), Math.sin(t * 1.3) * 0.03);
  ch.mouth.scale.set(1 - mouthOpen * 0.25, 0.15 + mouthOpen * 0.85, 0.4);
  // clignement des yeux
  const blink = ((t + (act.phase || 0)) % 3.7) < 0.12 ? 0.1 : 1;
  ch.eyes.forEach((e) => (e.e.scale.y = blink));
  const mood = act.mood || 'neutral';
  const tilt = { angry: 0.45, sad: -0.4, surprised: 0, happy: -0.1, neutral: 0 }[mood] ?? 0;
  const lift = { surprised: 0.03, sad: 0.0, angry: -0.01 }[mood] ?? 0;
  ch.brows.forEach((b, i) => { b.rotation.z = (i === 0 ? -tilt : tilt); b.position.y = 0.11 + lift; });
  ch.eyes.forEach((e) => (e.pupil.position.set((act.lookX || 0) * 0.012, (act.lookY || 0) * 0.012, 0.042)));
}

// ------------------------------------------------------------ mains POV (attachées à la caméra)
function makePovHands(sleeve = 0x3d7bd9) {
  const g = new THREE.Group();
  const mk = (s) => {
    const arm = new THREE.Group(); g.add(arm);
    mesh(new THREE.CylinderGeometry(0.055, 0.065, 0.5, 12), toon(sleeve), 0, -0.25, 0, arm).rotation.x = 0;
    const palm = outline(mesh(new THREE.BoxGeometry(0.11, 0.12, 0.045), toon(SKIN), 0, 0.04, 0, arm), 1.08);
    const fingers = [];
    for (let i = 0; i < 4; i++) {
      const f = new THREE.Group(); f.position.set(-0.04 + i * 0.027, 0.1, 0); arm.add(f);
      outline(mesh(new THREE.CapsuleGeometry(0.012, 0.05, 3, 6), toon(SKIN), 0, 0.03, 0, f), 1.15);
      fingers.push(f);
    }
    const th = new THREE.Group(); th.position.set(0.06 * -s, 0.03, 0.01); arm.add(th);
    outline(mesh(new THREE.CapsuleGeometry(0.014, 0.045, 3, 6), toon(SKIN), 0, 0.025, 0, th), 1.15); th.rotation.z = 0.9 * s;
    return { arm, fingers, th };
  };
  return { group: g, L: mk(-1), R: mk(1) };
}
const HAND_POSES = {  // position (repère caméra) et rotation de chaque main
  idle:  { L: [[-0.36, -0.52, -0.75], [0.5, 0.2, 0.5]], R: [[0.36, -0.52, -0.75], [0.5, -0.2, -0.5]] },
  low:   { L: [[-0.42, -0.66, -0.8], [0.6, 0.2, 0.6]], R: [[0.42, -0.66, -0.8], [0.6, -0.2, -0.6]] },
  up:    { L: [[-0.3, -0.25, -0.75], [0.1, 0.3, 0.35]], R: [[0.3, -0.25, -0.75], [0.1, -0.3, -0.35]] },
  palms: { L: [[-0.17, -0.33, -0.65], [-0.9, 0.3, 0.2]], R: [[0.17, -0.33, -0.65], [-0.9, -0.3, -0.2]] },
  phone: { L: [[-0.42, -0.66, -0.8], [0.6, 0.2, 0.6]], R: [[0.06, -0.3, -0.6], [0.2, 0, 0]] },
  hold:  { L: [[-0.22, -0.38, -0.7], [0.2, 0.5, 0.9]], R: [[0.22, -0.38, -0.7], [0.2, -0.5, -0.9]] },
  table: { L: [[-0.25, -0.5, -0.7], [-1.2, 0.2, 0.3]], R: [[0.25, -0.5, -0.7], [-1.2, -0.2, -0.3]] },
};
function poseHands(h, pose, t, intensity = 1, shake = 0) {
  const p = HAND_POSES[pose] || HAND_POSES.idle;
  [['L', h.L], ['R', h.R]].forEach(([k, hand], i) => {
    const [pos, rot] = p[k];
    const bob = Math.sin(t * 2.4 + i) * 0.008 * intensity;
    const sh = shake ? (Math.sin(t * 47 + i * 3) * 0.006 + Math.sin(t * 31) * 0.004) * shake : 0;
    hand.arm.position.set(pos[0] + sh, pos[1] + bob + sh, pos[2]);
    hand.arm.rotation.set(rot[0], rot[1], rot[2]);
    const curl = pose === 'phone' && k === 'R' ? 1.2 : pose === 'hold' ? 0.9 : pose === 'table' ? 0.3 : 0.25;
    hand.fingers.forEach((f, j) => (f.rotation.x = curl + Math.sin(t * 3 + j) * 0.03));
  });
}

// ------------------------------------------------------------ textures
function textTex(lines, o = {}) {
  const { w = 512, h = 256, bg = '#4b5320', fg = '#e8dfa0', font = 'bold 52px Arial', align = 'center', border } = o;
  return canvasTex(w, h, (g) => {
    g.fillStyle = bg; g.fillRect(0, 0, w, h);
    if (o.noise) { const r = rng(3); for (let i = 0; i < 1600; i++) { g.fillStyle = `rgba(0,0,0,${r() * 0.12})`; g.fillRect(r() * w, r() * h, 2 + r() * 4, 2 + r() * 4); } }
    if (border) { g.strokeStyle = border; g.lineWidth = 10; g.strokeRect(8, 8, w - 16, h - 16); }
    g.fillStyle = fg; g.textAlign = align; g.textBaseline = 'middle';
    lines.forEach((l, i) => { g.font = l.font || font; g.fillStyle = l.color || fg; g.fillText(l.t ?? l, align === 'center' ? w / 2 : 30, (h / (lines.length + 1)) * (i + 1)); });
  });
}
const CRATE_SIDE = () => textTex([{ t: '7,62×39 mm', font: 'bold 64px Arial Black, Arial' }, '1440 CTGS', { t: 'LOT 71-1978', font: 'bold 40px Arial' }], { noise: true, border: '#2f3514' });
const CRATE_END = () => textTex([{ t: '▲▲', font: 'bold 70px Arial' }, 'AMMO'], { w: 256, h: 256, noise: true, border: '#2f3514' });
const CRATE_TOP = () => textTex([' '], { noise: true, border: '#2f3514' });

// caisse de munitions militaire (olive, pochoirs, poignées de corde, fermoirs métalliques)
function makeCrate(open = false) {
  const g = new THREE.Group();
  const side = CRATE_SIDE(), end = CRATE_END(), top = CRATE_TOP();
  const mats = [toon(0xffffff, { map: end }), toon(0xffffff, { map: end }), toon(0xffffff, { map: top }), toon(0x3d4419), toon(0xffffff, { map: side }), toon(0xffffff, { map: side })];
  const W_ = 0.8, H_ = 0.36, D_ = 0.42;
  if (!open) { mesh(new THREE.BoxGeometry(W_, H_, D_), mats, 0, H_ / 2, 0, g); }
  else {
    const wall = (w, h, d, x, y, z, m) => mesh(new THREE.BoxGeometry(w, h, d), m, x, y, z, g);
    wall(W_, 0.03, D_, 0, 0.015, 0, toon(0x3d4419));
    wall(W_, H_, 0.03, 0, H_ / 2, D_ / 2, mats[4]); wall(W_, H_, 0.03, 0, H_ / 2, -D_ / 2, mats[5]);
    wall(0.03, H_, D_, W_ / 2, H_ / 2, 0, mats[0]); wall(0.03, H_, D_, -W_ / 2, H_ / 2, 0, mats[1]);
    // cartouches debout : douille laiton + ogive cuivre
    const nx = 18, nz = 9, n = nx * nz;
    const caseGeo = new THREE.CylinderGeometry(0.011, 0.012, 0.07, 10);
    const tipGeo = new THREE.ConeGeometry(0.0105, 0.04, 10);
    const cases = new THREE.InstancedMesh(caseGeo, toon(0xd4a63a, { emissive: 0x2a1c00 }), n);
    const tips = new THREE.InstancedMesh(tipGeo, toon(0xb5653a), n);
    const m4 = new THREE.Matrix4(); let k = 0; const r = rng(11);
    for (let i = 0; i < nx; i++) for (let j = 0; j < nz; j++) {
      const x = -W_ / 2 + 0.05 + i * ((W_ - 0.1) / (nx - 1)), z = -D_ / 2 + 0.05 + j * ((D_ - 0.1) / (nz - 1));
      const y = H_ - 0.09 + (r() - 0.5) * 0.006;
      m4.makeTranslation(x, y, z); cases.setMatrixAt(k, m4);
      m4.makeTranslation(x, y + 0.055, z); tips.setMatrixAt(k, m4); k++;
    }
    g.add(cases, tips);
    const lid = mesh(new THREE.BoxGeometry(W_, 0.04, D_), [toon(0x4b5320), toon(0x4b5320), toon(0xffffff, { map: top }), toon(0x3d4419), toon(0x4b5320), toon(0x4b5320)], 0, 0.32, -D_ / 2 - 0.06, g);
    lid.rotation.x = -0.3;
  }
  // poignées de corde + fermoirs
  [-1, 1].forEach((s) => {
    const rope = mesh(new THREE.TorusGeometry(0.05, 0.01, 6, 14, Math.PI), toon(0xc8b48a), (W_ / 2 + 0.012) * s, H_ * 0.55, 0, g); rope.rotation.y = Math.PI / 2; rope.rotation.z = Math.PI;
    mesh(new THREE.BoxGeometry(0.06, 0.06, 0.02), toon(0x55585a), 0.22 * s, H_ - 0.04, D_ / 2 + 0.012, g);
  });
  return g;
}

function skyTex(top, mid, bottom) {
  return canvasTex(16, 512, (g) => { const gr = g.createLinearGradient(0, 0, 0, 512); gr.addColorStop(0, top); gr.addColorStop(0.6, mid); gr.addColorStop(1, bottom); g.fillStyle = gr; g.fillRect(0, 0, 16, 512); });
}
function addSky(scene, top, mid, bottom) {
  const s = new THREE.Mesh(new THREE.SphereGeometry(400, 32, 16), new THREE.MeshBasicMaterial({ map: skyTex(top, mid, bottom), side: THREE.BackSide, fog: false }));
  scene.add(s); return s;
}
function addClouds(scene, n = 8, seed = 2, tint = 0xffffff) {
  const r = rng(seed), mat = toon(tint, { emissive: 0x404040 });
  for (let i = 0; i < n; i++) {
    const c = new THREE.Group(); c.position.set((r() - 0.5) * 160, 25 + r() * 25, -60 - r() * 100); scene.add(c);
    for (let j = 0; j < 6; j++) mesh(new THREE.SphereGeometry(4 + r() * 4, 12, 10), mat, (j - 3) * 4 + r() * 2, r() * 3, r() * 2, c);
    c.userData.speed = 0.3 + r() * 0.5;
  }
}
function palm(parent, x, z, h = 6, seed = 1) {
  const g = new THREE.Group(); g.position.set(x, 0, z); parent.add(g);
  const r = rng(seed); const bend = (r() - 0.5) * 0.5;
  let y = 0;
  for (let i = 0; i < 6; i++) { const seg = outline(mesh(new THREE.CylinderGeometry(0.16 - i * 0.012, 0.19 - i * 0.012, h / 6, 8), toon(0x9b7650), bend * i * 0.15, y + h / 12, 0, g), 1.04); y += h / 6; }
  const crown = new THREE.Group(); crown.position.set(bend * 0.9, h, 0); g.add(crown);
  for (let i = 0; i < 9; i++) {
    const leaf = new THREE.Mesh(new THREE.ConeGeometry(0.35, 2.8, 4, 1), toon(0x2f9e44)); leaf.scale.set(1, 1, 0.15);
    leaf.position.set(0, 0, 0); leaf.geometry.translate(0, 1.4, 0);
    leaf.rotation.set(1.1 + r() * 0.3, (i / 9) * Math.PI * 2, 0, 'YXZ'); crown.add(leaf);
  }
  return g;
}
function building(parent, x, z, w, h, d, color, seed) {
  const r = rng(seed);
  const tex = canvasTex(256, 512, (g) => {
    g.fillStyle = color; g.fillRect(0, 0, 256, 512);
    g.fillStyle = 'rgba(255,255,255,0.35)'; for (let y = 60; y < 512; y += 120) g.fillRect(0, y, 256, 10);
    for (let y = 30; y < 500; y += 60) for (let xx = 20; xx < 240; xx += 55) { g.fillStyle = r() > 0.2 ? '#7fc8e8' : '#ffe8a0'; g.fillRect(xx, y, 34, 34); g.strokeStyle = '#ffffff'; g.lineWidth = 4; g.strokeRect(xx, y, 34, 34); }
  });
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(Math.max(1, w / 6), Math.max(1, h / 10));
  const b = mesh(new THREE.BoxGeometry(w, h, d), toon(0xffffff, { map: tex }), x, h / 2, z, parent);
  mesh(new THREE.BoxGeometry(w + 0.3, 0.4, d + 0.3), toon(0xffffff), x, h + 0.2, z, parent);
  return b;
}
function room(scene, o) {  // pièce intérieure : sol, murs, plafond
  const { w = 8, d = 8, h = 3.2, wall = 0xbfe3d8, floor = 0xb98a5a, ceiling = 0xf5f1e8 } = o;
  const g = new THREE.Group(); scene.add(g);
  const fl = mesh(new THREE.PlaneGeometry(w, d), toon(floor), 0, 0, 0, g); fl.rotation.x = -Math.PI / 2;
  const ce = mesh(new THREE.PlaneGeometry(w, d), toon(ceiling), 0, h, 0, g); ce.rotation.x = Math.PI / 2;
  [[0, h / 2, -d / 2, 0], [0, h / 2, d / 2, Math.PI], [-w / 2, h / 2, 0, Math.PI / 2], [w / 2, h / 2, 0, -Math.PI / 2]].forEach(([x, y, z, ry]) => {
    const m = mesh(new THREE.PlaneGeometry(w, h), toon(wall), x, y, z, g); m.rotation.y = ry;
  });
  return g;
}
function poster(parent, lines, x, y, z, w, h, o = {}) {
  const m = mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: textTex(lines, { w: 512, h: Math.round(512 * h / w), ...o }) }), x, y, z, parent);
  if (o.ry) m.rotation.y = o.ry; if (o.rx) m.rotation.x = o.rx; return m;
}
function phoneMesh(screenLines, o = {}) {
  const g = new THREE.Group();
  outline(mesh(new THREE.BoxGeometry(0.075, 0.15, 0.012), toon(0x1c1c22), 0, 0, 0, g), 1.05);
  const scr = textTex(screenLines, { w: 256, h: 512, bg: o.bg || '#0f1f3a', fg: '#ffffff', font: 'bold 34px Arial' });
  mesh(new THREE.PlaneGeometry(0.065, 0.13), new THREE.MeshBasicMaterial({ map: scr }), 0, 0, 0.0065, g);
  return g;
}

// ------------------------------------------------------------ décors
const SETS = {};
SETS.warehouse = (S) => {
  S.scene.background = new THREE.Color(0x14110d); S.scene.fog = new THREE.Fog(0x14110d, 6, 26);
  const fl = mesh(new THREE.PlaneGeometry(40, 60), toon(0x4a4642), 0, 0, -10, S.scene); fl.rotation.x = -Math.PI / 2;
  const crate = makeCrate(false);
  // rangées de caisses empilées des deux côtés de l'allée
  for (const side of [-1, 1]) for (let row = 0; row < 10; row++) for (let col = 0; col < 2; col++) for (let lvl = 0; lvl < 7; lvl++) {
    if (lvl > 4 + ((row * 7 + col * 3) % 3)) continue;
    const c = crate.clone(); c.position.set(side * (1.3 + col * 0.85), lvl * 0.37, 1 - row * 1.8 + (lvl % 2) * 0.05); c.rotation.y = Math.PI / 2 * (lvl % 2 ? 1 : 1) + (side > 0 ? Math.PI : 0); S.scene.add(c);
  }
  // lampes suspendues
  for (let i = 0; i < 4; i++) {
    const z = -1 - i * 5;
    mesh(new THREE.CylinderGeometry(0.005, 0.005, 3), basic(0x111111), 0, 5.5, z, S.scene);
    const shade = mesh(new THREE.ConeGeometry(0.35, 0.3, 16, 1, true), toon(0x2d3a2d, { side: THREE.DoubleSide }), 0, 4, z, S.scene);
    mesh(new THREE.SphereGeometry(0.09, 10, 8), basic(0xfff1b0), 0, 3.85, z, S.scene);
    const l = new THREE.SpotLight(0xffd99a, 90, 14, 1.0, 0.6, 1.2); l.position.set(0, 3.9, z); l.target.position.set(0, 0, z); S.scene.add(l, l.target);
  }
  S.scene.add(new THREE.AmbientLight(0x8090c0, 0.9)); S.scene.add(new THREE.HemisphereLight(0xffe2b0, 0x302820, 0.6));
  // poussière en suspension
  const r = rng(5), n = 400, pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { pos[i * 3] = (r() - 0.5) * 4; pos[i * 3 + 1] = r() * 4; pos[i * 3 + 2] = 2 - r() * 18; }
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const dust = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xffe6b0, size: 0.02, transparent: true, opacity: 0.6 }));
  S.scene.add(dust); S.updates.push((t) => { dust.position.y = Math.sin(t * 0.3) * 0.1; dust.rotation.y = t * 0.01; });
};
SETS.crate_open = (S) => {
  SETS.warehouse(S);
  const c = makeCrate(true); c.position.set(0, 0.0, -1.2); S.scene.add(c);
  const c2 = makeCrate(false); c2.position.set(0.95, 0, -1.3); c2.rotation.y = 0.2; S.scene.add(c2);
  const c3 = makeCrate(false); c3.position.set(-0.95, 0, -1.25); c3.rotation.y = -0.15; S.scene.add(c3);
  const c4 = makeCrate(false); c4.position.set(0.9, 0.37, -1.3); c4.rotation.y = 0.25; S.scene.add(c4);
  const l = new THREE.SpotLight(0xffe2a8, 25, 6, 0.6, 0.5, 1.2); l.position.set(0.3, 2.4, -0.4); l.target.position.set(0, 0, -1.2); S.scene.add(l, l.target);
};
SETS.miami = (S) => {
  addSky(S.scene, '#2f7fe0', '#8cc8f5', '#ffd9e6'); addClouds(S.scene, 12, 4, 0xfff0f4);
  S.scene.fog = new THREE.Fog(0xcfe6f7, 30, 140);
  const road = mesh(new THREE.PlaneGeometry(10, 400), toon(0x4a4d55), 0, 0, -150, S.scene); road.rotation.x = -Math.PI / 2;
  for (let i = 0; i < 60; i++) { const d = mesh(new THREE.PlaneGeometry(0.2, 2), basic(0xf5f5f5), 0, 0.01, 5 - i * 6, S.scene); d.rotation.x = -Math.PI / 2; }
  [-1, 1].forEach((s) => { const sw = mesh(new THREE.BoxGeometry(5, 0.2, 400), toon(0xe8dcc8), s * 7.5, 0.1, -150, S.scene); });
  const colors = ['#f7a8c4', '#9fe3d8', '#ffe39a', '#c9b6f2', '#ffc9a0', '#a8d8ff'];
  for (let i = 0; i < 18; i++) for (const s of [-1, 1]) {
    const h = 8 + ((i * 7 + (s > 0 ? 3 : 0)) % 5) * 3;
    building(S.scene, s * 15, 2 - i * 14, 10, h, 12, colors[(i + (s > 0 ? 2 : 0)) % colors.length], i * 10 + (s > 0 ? 1 : 2));
  }
  for (let i = 0; i < 22; i++) for (const s of [-1, 1]) palm(S.scene, s * 6.3, -2 - i * 9 + (s > 0 ? 4 : 0), 6 + (i % 3), i * 2 + (s > 0 ? 1 : 0));
  // voitures garées
  const carCol = [0xe63946, 0x2a9d8f, 0xf4a261, 0xffffff];
  for (let i = 0; i < 10; i++) { const car = new THREE.Group(); car.position.set(i % 2 ? 3.4 : -3.4, 0, -8 - i * 13); S.scene.add(car);
    outline(mesh(new THREE.BoxGeometry(1.8, 0.6, 4), toon(carCol[i % 4]), 0, 0.55, 0, car), 1.02); outline(mesh(new THREE.BoxGeometry(1.6, 0.5, 2), toon(0x9fd3f0), 0, 1.05, -0.2, car), 1.02);
    [-1, 1].forEach((a) => [-1, 1].forEach((b) => { const w = mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.2, 14), toon(0x111111), a * 0.9, 0.32, b * 1.3, car); w.rotation.z = Math.PI / 2; })); }
  // passants
  const shirts = [0xffd23f, 0x3bceac, 0xee4266, 0x540d6e, 0x0ead69];
  for (let i = 0; i < 8; i++) { const p = makeCharacter({ shirt: shirts[i % 5], hairStyle: i % 3 ? 'short' : 'long', hair: i % 2 ? 0x3a2516 : 0xe0b050, pants: 0x2b3a67 });
    p.root.position.set(i % 2 ? 7.2 : -7.2, 0.2, -10 - i * 9); p.root.rotation.y = i % 2 ? Math.PI : 0; S.scene.add(p.root); S.extras.push({ ch: p, act: { action: 'walk', phase: i } }); }
  S.scene.add(new THREE.HemisphereLight(0xcfe8ff, 0xf0d0b0, 1.2));
  const sun = new THREE.DirectionalLight(0xfff2d6, 2.2); sun.position.set(-20, 30, 10); S.scene.add(sun);
};
SETS.spa = (S) => {
  S.scene.background = new THREE.Color(0xbfe3d8);
  room(S.scene, { w: 6, d: 6, wall: 0xbfe3d8, floor: 0xc49a6c });
  const table = new THREE.Group(); table.position.set(0, 0, -1.6); S.scene.add(table);
  outline(mesh(new THREE.BoxGeometry(0.8, 0.12, 1.9), toon(0xffffff), 0, 0.78, 0, table), 1.02);
  outline(mesh(new THREE.BoxGeometry(0.82, 0.06, 1.92), toon(0x7ac7b8), 0, 0.7, 0, table), 1.02);
  [-1, 1].forEach((a) => [-1, 1].forEach((b) => mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.7), toon(0x8a6a4a), a * 0.33, 0.35, b * 0.8, table)));
  // étagère + flacons d'huile
  const shelf = mesh(new THREE.BoxGeometry(1.6, 0.05, 0.3), toon(0x8a6a4a), 1.6, 1.4, -2.85, S.scene);
  const bc = [0xe9c46a, 0x9bd17a, 0xf4a261, 0xb5838d];
  for (let i = 0; i < 6; i++) { outline(mesh(new THREE.CylinderGeometry(0.05, 0.06, 0.22, 10), toon(bc[i % 4], { transparent: true, opacity: 0.9 }), 1.0 + i * 0.22, 1.54, -2.85, S.scene), 1.06); }
  // pile de serviettes
  for (let i = 0; i < 4; i++) outline(mesh(new THREE.BoxGeometry(0.5, 0.09, 0.35), toon(i % 2 ? 0xffffff : 0xf0ece0), -1.7, 0.75 + i * 0.09, -2.6, S.scene), 1.03);
  mesh(new THREE.BoxGeometry(0.6, 0.7, 0.4), toon(0x8a6a4a), -1.7, 0.35, -2.6, S.scene);
  // plante
  outline(mesh(new THREE.CylinderGeometry(0.18, 0.14, 0.35, 12), toon(0xd17a4a), 2.3, 0.17, -2.3, S.scene));
  for (let i = 0; i < 7; i++) { const l = mesh(new THREE.SphereGeometry(0.2, 8, 6), toon(0x3a9a4a), 2.3 + Math.cos(i) * 0.15, 0.55 + (i % 3) * 0.15, -2.3 + Math.sin(i) * 0.15, S.scene); l.scale.set(0.6, 1.4, 0.3); l.rotation.z = Math.cos(i) * 0.6; }
  poster(S.scene, [{ t: 'MASSAGE', font: 'bold 80px Arial' }, { t: '60 min · 75 $', font: 'bold 64px Arial' }], -0.9, 2.0, -2.97, 1.3, 0.75, { bg: '#fdf6e3', fg: '#2a6f63', border: '#2a6f63' });
  S.scene.add(new THREE.HemisphereLight(0xffffff, 0xd9c0a0, 1.3));
  const l = new THREE.DirectionalLight(0xfff0dc, 1.4); l.position.set(2, 4, 3); S.scene.add(l);
};
SETS.apartment_night = (S) => {
  S.scene.background = new THREE.Color(0x10142a);
  room(S.scene, { w: 6, d: 6, wall: 0x2e3a66, floor: 0x5a4632, ceiling: 0x1c2240 });
  // fenêtre sur la ville la nuit
  const city = canvasTex(512, 384, (g) => { g.fillStyle = '#0b1030'; g.fillRect(0, 0, 512, 384); const r = rng(9);
    for (let i = 0; i < 18; i++) { const x = i * 30, h = 80 + r() * 220; g.fillStyle = '#151a3a'; g.fillRect(x, 384 - h, 28, h);
      for (let y = 384 - h + 8; y < 380; y += 16) for (let xx = x + 4; xx < x + 26; xx += 9) if (r() > 0.55) { g.fillStyle = '#ffd77a'; g.fillRect(xx, y, 5, 7); } } });
  mesh(new THREE.PlaneGeometry(2.2, 1.6), new THREE.MeshBasicMaterial({ map: city }), 0.8, 1.8, -2.98, S.scene);
  outline(mesh(new THREE.BoxGeometry(2.3, 0.08, 0.1), toon(0xeeeeee), 0.8, 1.0, -2.95, S.scene));
  // table + factures
  const table = outline(mesh(new THREE.BoxGeometry(1.6, 0.06, 1.0), toon(0x8a5a3a), 0, 0.78, -1.0, S.scene), 1.02);
  [-1, 1].forEach((a) => [-1, 1].forEach((b) => mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.78), toon(0x5a3a22), a * 0.7, 0.39, -1 + b * 0.4, S.scene)));
  const bills = [['FACTURE', 'ÉLECTRICITÉ', { t: 'IMPAYÉ', color: '#d62828', font: 'bold 70px Arial' }], ['LOYER', 'Novembre', { t: 'EN RETARD', color: '#d62828', font: 'bold 64px Arial' }], ['GARAGE', 'Réparation', { t: '1 240 $', color: '#d62828', font: 'bold 70px Arial' }], ['BANQUE', 'Solde', { t: '-312 $', color: '#d62828', font: 'bold 76px Arial' }]];
  bills.forEach((b, i) => { const p = mesh(new THREE.PlaneGeometry(0.3, 0.4), new THREE.MeshBasicMaterial({ map: textTex(b, { w: 300, h: 400, bg: '#fbfbf5', fg: '#222', font: 'bold 40px Arial' }) }), -0.45 + i * 0.3, 0.815, -0.9 + (i % 2) * 0.12, S.scene);
    p.rotation.x = -Math.PI / 2; p.rotation.z = (i - 1.5) * 0.15; });
  // lampe de bureau
  outline(mesh(new THREE.ConeGeometry(0.15, 0.2, 14, 1, true), toon(0xe9c46a, { side: THREE.DoubleSide }), 0.6, 1.25, -1.25, S.scene));
  mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.45), toon(0x333333), 0.6, 1.02, -1.25, S.scene);
  const lamp = new THREE.PointLight(0xffc870, 6, 4, 1.5); lamp.position.set(0.6, 1.2, -1.2); S.scene.add(lamp);
  S.scene.add(new THREE.AmbientLight(0x4050a0, 0.5));
};
SETS.memory = (S) => {  // cadre photo d'enfance sur une commode
  SETS.apartment_night(S);
  const frame = new THREE.Group(); frame.position.set(-0.2, 0.84, -1.05); frame.rotation.x = -0.15; S.scene.add(frame);
  outline(mesh(new THREE.BoxGeometry(0.42, 0.52, 0.03), toon(0xc9a227), 0, 0.26, 0, frame), 1.03);
  const kid = canvasTex(320, 400, (g) => { g.fillStyle = '#9ad1f5'; g.fillRect(0, 0, 320, 400); g.fillStyle = '#7bc96f'; g.fillRect(0, 300, 320, 100);
    g.fillStyle = '#f2c9a0'; g.beginPath(); g.arc(160, 170, 70, 0, 7); g.fill(); g.fillStyle = '#3a2516'; g.beginPath(); g.arc(160, 140, 72, Math.PI, 0); g.fill();
    g.fillStyle = '#fff'; [130, 190].forEach((x) => { g.beginPath(); g.arc(x, 170, 16, 0, 7); g.fill(); }); g.fillStyle = '#111'; [130, 190].forEach((x) => { g.beginPath(); g.arc(x, 172, 7, 0, 7); g.fill(); });
    g.strokeStyle = '#7a1d1d'; g.lineWidth = 6; g.beginPath(); g.arc(160, 200, 26, 0.2, Math.PI - 0.2); g.stroke();
    g.fillStyle = '#ffd23f'; g.beginPath(); g.moveTo(100, 95); g.lineTo(120, 45); g.lineTo(145, 85); g.lineTo(160, 35); g.lineTo(175, 85); g.lineTo(200, 45); g.lineTo(220, 95); g.closePath(); g.fill();
    g.fillStyle = '#d62828'; g.fillRect(105, 250, 110, 60); g.fillStyle = '#fff'; g.font = 'bold 34px Arial'; g.textAlign = 'center'; g.fillText('$$$', 160, 292);
    g.fillStyle = '#111'; g.font = 'bold 28px Arial'; g.fillText('FUTUR MILLIONNAIRE', 160, 370); });
  mesh(new THREE.PlaneGeometry(0.36, 0.45), new THREE.MeshBasicMaterial({ map: kid }), 0, 0.26, 0.017, frame);
};
SETS.living = (S) => {
  S.scene.background = new THREE.Color(0xf3d9b1);
  room(S.scene, { w: 7, d: 7, wall: 0xf6d7a7, floor: 0xa9744f, ceiling: 0xfff6e6 });
  const sofa = new THREE.Group(); sofa.position.set(0, 0, -2.3); S.scene.add(sofa);
  outline(mesh(new THREE.BoxGeometry(2.4, 0.45, 0.9), toon(0x5c7cfa), 0, 0.3, 0, sofa), 1.02);
  outline(mesh(new THREE.BoxGeometry(2.4, 0.7, 0.25), toon(0x4c6ef5), 0, 0.75, -0.35, sofa), 1.02);
  [-1, 1].forEach((s) => outline(mesh(new THREE.BoxGeometry(0.25, 0.65, 0.9), toon(0x4c6ef5), s * 1.25, 0.5, 0, sofa), 1.02));
  [-0.6, 0.6].forEach((x, i) => { const c = outline(mesh(new THREE.BoxGeometry(0.45, 0.4, 0.12), toon(i ? 0xffd43b : 0xff8787), x, 0.72, -0.15, sofa), 1.04); c.rotation.z = i ? 0.15 : -0.15; });
  const lamp = new THREE.PointLight(0xffd7a0, 8, 6, 1.4); lamp.position.set(-1.8, 1.8, -1.6); S.scene.add(lamp);
  outline(mesh(new THREE.ConeGeometry(0.3, 0.35, 16, 1, true), toon(0xfff3bf, { side: THREE.DoubleSide, emissive: 0x806020 }), -1.8, 1.65, -2.4, S.scene));
  mesh(new THREE.CylinderGeometry(0.02, 0.02, 1.5), toon(0x333333), -1.8, 0.75, -2.4, S.scene);
  poster(S.scene, [{ t: '♥', font: 'bold 160px Arial', color: '#e64980' }], 1.4, 1.9, -3.48, 0.7, 0.7, { bg: '#fff0f6', border: '#c2255c' });
  S.scene.add(new THREE.HemisphereLight(0xfff4e0, 0xb08060, 1.1));
};
SETS.balcony = (S) => {
  addSky(S.scene, '#3b2a6e', '#ff7b54', '#ffd27a');
  const sun = mesh(new THREE.SphereGeometry(8, 24, 16), basic(0xffe08a, { fog: false }), 20, 14, -150, S.scene);
  for (let i = 0; i < 40; i++) { const h = 10 + ((i * 37) % 30); mesh(new THREE.BoxGeometry(6, h, 6), basic(0x2a1e45), -120 + i * 6.5, h / 2 - 5, -90 - (i % 3) * 10, S.scene); }
  const fl = mesh(new THREE.BoxGeometry(5, 0.2, 3), toon(0xc8b8a8), 0, -0.1, -0.8, S.scene);
  for (let i = 0; i < 17; i++) outline(mesh(new THREE.CylinderGeometry(0.02, 0.02, 1.0), toon(0xf1f1f1), -2.4 + i * 0.3, 0.5, -2.2, S.scene), 1.1);
  outline(mesh(new THREE.BoxGeometry(5, 0.06, 0.1), toon(0xffffff), 0, 1.0, -2.2, S.scene), 1.05);
  S.scene.add(new THREE.HemisphereLight(0xffb38a, 0x553366, 1.2));
  const l = new THREE.DirectionalLight(0xffa060, 1.6); l.position.set(10, 6, -10); S.scene.add(l);
};
SETS.laptop = (S) => {
  S.scene.background = new THREE.Color(0x07080f);
  room(S.scene, { w: 5, d: 5, wall: 0x141a33, floor: 0x2a2018, ceiling: 0x0c0f1f });
  outline(mesh(new THREE.BoxGeometry(1.6, 0.06, 0.9), toon(0x4a3626), 0, 0.78, -0.9, S.scene), 1.02);
  const lap = new THREE.Group(); lap.position.set(0, 0.81, -0.95); S.scene.add(lap);
  outline(mesh(new THREE.BoxGeometry(0.6, 0.025, 0.4), toon(0xb8bcc4), 0, 0, 0, lap), 1.03);
  const scrG = new THREE.Group(); scrG.position.set(0, 0.01, -0.2); scrG.rotation.x = -0.25; lap.add(scrG);
  outline(mesh(new THREE.BoxGeometry(0.6, 0.4, 0.02), toon(0xb8bcc4), 0, 0.2, 0, scrG), 1.03);
  const ad = canvasTex(600, 400, (g) => { g.fillStyle = '#ffffff'; g.fillRect(0, 0, 600, 400); g.fillStyle = '#1c7ed6'; g.fillRect(0, 0, 600, 70);
    g.fillStyle = '#fff'; g.font = 'bold 34px Arial'; g.textAlign = 'center'; g.fillText('BONNE AFFAIRE !', 300, 48);
    g.fillStyle = '#e9ecef'; g.fillRect(40, 95, 230, 200); g.fillStyle = '#ffffff'; g.fillRect(55, 160, 200, 110); g.fillStyle = '#d0ebff'; g.fillRect(55, 120, 200, 50);
    g.fillStyle = '#111'; g.font = 'bold 30px Arial'; g.textAlign = 'left'; g.fillText('Draps en coton', 300, 140); g.fillText('égyptien', 300, 180);
    g.fillStyle = '#e03131'; g.font = 'bold 52px Arial'; g.fillText('-70 %', 300, 250); g.fillStyle = '#f59f00'; g.font = 'bold 34px Arial'; g.fillText('★★★★★', 300, 295);
    g.fillStyle = '#2b8a3e'; g.fillRect(40, 320, 520, 60); g.fillStyle = '#fff'; g.font = 'bold 28px Arial'; g.textAlign = 'center'; g.fillText('Revendez-les aux maisons de retraite', 300, 360); });
  mesh(new THREE.PlaneGeometry(0.56, 0.36), new THREE.MeshBasicMaterial({ map: ad }), 0, 0.2, 0.011, scrG);
  const glow = new THREE.PointLight(0x9ccfff, 5, 3, 1.5); glow.position.set(0, 1.0, -0.6); S.scene.add(glow);
  S.scene.add(new THREE.AmbientLight(0x303a70, 0.6));
};

// ------------------------------------------------------------ plan (shot)
const CAST = {};  // personnages réutilisables par nom
let S = null;
window.setupShot = (shot) => {
  const scene = new THREE.Scene();
  S = { scene, updates: [], extras: [], actors: {}, shot, props: {} };
  SETS[shot.set](S);
  for (const a of shot.actors || []) {
    const ch = makeCharacter(a.look || {});
    ch.root.position.set(...(a.pos || [0, 0, -2])); ch.root.rotation.y = a.rotY || 0;
    scene.add(ch.root); S.actors[a.id] = { ch, a };
  }
  const cam = new THREE.PerspectiveCamera(shot.fov || 55, W / H, 0.05, 600);
  scene.add(cam); S.cam = cam;
  if (shot.hands !== false) { S.hands = makePovHands(shot.sleeve || 0x3d7bd9); cam.add(S.hands.group); }
  if (shot.phone) { S.phone = phoneMesh(shot.phone, { bg: shot.phoneBg }); S.hands && S.hands.R.arm.add(S.phone); S.phone.position.set(0, 0.13, 0.03); }
  if (shot.coins) {  // pièces qui tombent sur la table
    S.coins = [0, 1].map((i) => { const c = outline(mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.008, 18), toon(0xd8d8d8, { emissive: 0x202020 }), 0, 2, 0, scene), 1.1); return c; });
  }
  return true;
};
window.renderFrame = (t, mouths = {}) => {
  const sh = S.shot, D = sh.duration || 3, x = ease(Math.min(1, t / D));
  // caméra : trajectoire + balancement de marche / tremblement
  const c = sh.camera || {};
  const p = lerpV(c.from || [0, 1.6, 2], c.to || c.from || [0, 1.6, 2], x);
  const look = lerpV(c.lookFrom || c.look || [0, 1.4, -3], c.lookTo || c.look || c.lookFrom || [0, 1.4, -3], x);
  if (c.walk) { p.y += Math.abs(Math.sin(t * 6.5)) * 0.05; p.x += Math.sin(t * 3.25) * 0.03; }
  if (c.shake) { p.x += Math.sin(t * 41) * 0.012 * c.shake; p.y += Math.sin(t * 37 + 1) * 0.01 * c.shake; }
  S.cam.position.copy(p); S.cam.lookAt(look);
  if (c.roll) S.cam.rotation.z += Math.sin(t * 3.25) * c.roll;
  if (S.hands) poseHands(S.hands, sh.handPose || 'idle', t, c.walk ? 3 : 1, sh.handShake || 0);
  for (const id in S.actors) { const { ch, a } = S.actors[id]; animateCharacter(ch, t, mouths[id] || 0, a.act || {});
    if (a.walkTo) { const k = Math.min(1, t / D); ch.root.position.set(...lerpV(a.pos, a.walkTo, k).toArray()); } }
  for (const e of S.extras) { animateCharacter(e.ch, t, 0, e.act); e.ch.root.position.z += (e.ch.root.rotation.y ? 1 : -1) * 0.012; }
  if (S.coins) S.coins.forEach((coin, i) => { const t0 = (sh.coinsAt || 0.6) + i * 0.15, k = Math.max(0, t - t0);
    const base = sh.coinsPos || [0, 0.86, -1.3]; const y = Math.max(base[1], base[1] + 0.9 - 4.9 * k * k);
    coin.position.set(base[0] + i * 0.08, k > 0 ? y : 3, base[2] + i * 0.05); coin.rotation.set(k * 14 * (y > base[1] ? 1 : 0), 0, i); });
  S.updates.forEach((u) => u(t));
  renderer.render(S.scene, S.cam);
  return renderer.domElement.toDataURL('image/jpeg', 0.9);
};
window.ENGINE_READY = true;
