/* «زمینِ رفسنجان پایین می‌رود» (kerman_fa): window.renderAt(t) draws the frame of time t (seconds) from
   /build/film.json, which src/kerman.py writes (every string, every number, the clock, the cues, the camera).
   Nothing is typed here: this file only decides how the film looks. The plain is one stage on a lon/lat grid
   (src/kerman_landsat/s13_stage.py: Landsat 1987 and 2025, the green canopy of each) with the sinking ground of the
   radar over it; the photographs move with their depth (src/cycles_depth.py). Every frame is a pure function of t. */
import * as THREE from "/vendor/three.module.min.js";
const L = 96, R = 924, W = 828, MID = (L + R) / 2;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const easeOut = p => 1 - Math.pow(1 - p, 3);
const easeInOut = p => p * p * (3 - 2 * p);
const bump = p => Math.sin(Math.PI * clamp(p));
const lerp = (a, b, p) => a + (b - a) * p;
const fa = s => String(s).replace(/\d/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]).replace(".", "٫");
const SVGNS = "http://www.w3.org/2000/svg";
function el(tag, cls, parent, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; if (parent) parent.appendChild(e); return e; }
function svg(tag, attrs, parent) { const e = document.createElementNS(SVGNS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function css(e, o) { for (const k in o) e.style[k] = typeof o[k] === "number" ? o[k] + "px" : o[k]; return e; }
function marked(parent, s) {
  s.split(/(\{[^}]*\})/).forEach(part => { if (!part) return; if (part[0] === "{") el("span", "key", parent, part.slice(1, -1)); else parent.appendChild(document.createTextNode(part)); });
}
function fit(nodes, limit, floor) {
  if (!nodes.length) return;
  let size = parseFloat(getComputedStyle(nodes[0]).fontSize);
  const wide = () => Math.max(...nodes.map(n => n.scrollWidth));
  while (wide() > limit && size > floor) { size -= 1; nodes.forEach(n => css(n, { fontSize: size + "px", lineHeight: Math.round(size * (n.classList.contains("line") ? 1.36 : 1.4)) + "px" })); }
}
const show = (e, p) => { e.style.opacity = clamp(p).toFixed(3); };
const full = () => ({ width: 1080, height: 1920, viewBox: "0 0 1080 1920" });
function keyed(keys, t) {                            // keyframes [t, ...values]: eased between neighbours
  if (t <= keys[0][0]) return keys[0].slice(1);
  for (let i = 0; i + 1 < keys.length; i++) {
    const a = keys[i], b = keys[i + 1];
    if (t <= b[0]) { const p = easeInOut(seg(t, a[0], b[0])); return a.slice(1).map((v, k) => lerp(v, b[k + 1], p)); }
  }
  return keys[keys.length - 1].slice(1);
}
function pathOf(pts) { return pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join(""); }
const COL = { red: "#FF4E3C", redf: "#D7362A", green: "#A6DB55", blue: "#5AAEFF", bluef: "#1F68D2", gold: "#F2B544", ink: "#F7EFE4", dim: "#C9B8A4", soil: "#5A3A22", soil2: "#3B2414" };
const SCRIM = "12,8,6";
const KEY = { sink: "red", qanat: "red", wells: "green", warm: "red", city: "red" };   // the headline's highlight: what the scene is about
const BEFORE = { qanat: "blue" };                    // and of a scene's first headline, where it has two

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const END = F.end, Wd = F.words, Q = F.cues, PENDING = [];

  // ── the night behind everything: two slow warm lights by the clock ──
  const sky = el("canvas", "abs", stage); sky.width = 1080; sky.height = 1920; css(sky, { left: 0, top: 0 });
  const sk = sky.getContext("2d");
  function drawSky(T) {
    sk.clearRect(0, 0, 1080, 1920);
    const lamp = (x, y, r, c) => { const g = sk.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, `rgba(${c},0.20)`); g.addColorStop(1, `rgba(${c},0)`); sk.fillStyle = g; sk.fillRect(x - r, y - r, 2 * r, 2 * r); };
    lamp(230 + 120 * Math.sin(2 * Math.PI * T / 37), 560 + 90 * Math.cos(2 * Math.PI * T / 29), 760, "196,110,52");
    lamp(860 + 110 * Math.cos(2 * Math.PI * T / 41), 1330 + 100 * Math.sin(2 * Math.PI * T / 33), 720, "120,60,40");
  }

  async function image(file) { const im = new Image(); im.src = "/build/" + file; await im.decode(); return im; }
  function texture(im) {
    const t = new THREE.Texture(im); t.flipY = false; t.generateMipmaps = false; t.colorSpace = THREE.NoColorSpace;
    t.minFilter = t.magFilter = THREE.LinearFilter; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping; t.needsUpdate = true; return t;
  }
  const SHOT = {};
  for (const [k, v] of Object.entries(F.photos)) {
    const im = await image(v.file);
    const dp = await image(v.file.replace("photo_", "depth_").replace(".jpg", ".png")).catch(() => null);
    SHOT[k] = { im, dp };
  }
  // a still that moves like a shot: the near things (white in the depth) slide against the far ones as the camera drifts
  const DEPTH_FS = `
    precision highp float;
    uniform sampler2D tImg, tDepth;
    uniform vec2 uShift;
    uniform float uZoom;
    out vec4 colour;
    void main() {
      vec2 uv = vec2(gl_FragCoord.x / 1080.0, 1.0 - gl_FragCoord.y / 1920.0), c = vec2(0.5, 0.44);
      vec2 p = (uv - c) / uZoom + c;
      float d = texture(tDepth, p).r;
      vec2 q = p + uShift * (d - 0.45);
      d = texture(tDepth, q).r; q = p + uShift * (d - 0.45);
      colour = vec4(texture(tImg, clamp(q, 0.002, 0.998)).rgb, 1.0);
    }`;
  function photo(b, key) {                           // a photograph to the edges of the frame; the camera moves in slowly
    const P = F.photos[key], T = SHOT[key];
    let im, cam = null;
    if (T.dp) {
      const ren = new THREE.WebGLRenderer({ antialias: false, alpha: false, preserveDrawingBuffer: true });
      ren.setPixelRatio(1); ren.setSize(1080, 1920); ren.outputColorSpace = THREE.LinearSRGBColorSpace;
      const mat = new THREE.ShaderMaterial({ glslVersion: THREE.GLSL3, depthTest: false, fragmentShader: DEPTH_FS,
        vertexShader: "void main() { gl_Position = vec4(position.xy, 0.0, 1.0); }",
        uniforms: { tImg: { value: texture(T.im) }, tDepth: { value: texture(T.dp) }, uShift: { value: new THREE.Vector2() }, uZoom: { value: 1 } } });
      const scene = new THREE.Scene(), eye = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat));
      im = ren.domElement; im.className = "abs"; b.appendChild(im);
      cam = (z, u) => { mat.uniforms.uZoom.value = z + 0.035; mat.uniforms.uShift.value.set(0.030 * (2 * u - 1), -0.010 * (2 * u - 1)); ren.render(scene, eye); };
    } else { im = el("img", "abs", b); im.src = "/build/" + P.file; PENDING.push(im.decode().catch(() => {})); }
    css(im, { left: 0, top: 0, width: 1080, height: 1920, objectFit: "cover", transformOrigin: "50% 44%", opacity: "0", filter: P.tone || "brightness(.97) contrast(1.06)" });
    return { credit: P.credit, what: P.what || "", el: im,
             show(alpha, u) { const z = lerp(P.zoom[0], P.zoom[1], clamp(u)); im.style.opacity = clamp(alpha).toFixed(3);
               if (cam) { if (alpha > 0) cam(z, clamp(u)); } else im.style.transform = `scale(${z.toFixed(4)})`; } };
  }
  function motes(b) {                                // dust in the light: a few soft specks that drift by the clock
    const cv = el("canvas", "abs", b); cv.width = 1080; cv.height = 1920; css(cv, { left: 0, top: 0 });
    const c2 = cv.getContext("2d");
    let sd = 4711; const rn = () => (sd = (Math.imul(sd, 1664525) + 1013904223) >>> 0) / 4294967296;
    const M = Array.from({ length: 64 }, () => ({ x: rn() * 1080, y: 420 + rn() * 800, r: 1.2 + 3.2 * Math.pow(rn(), 2.2), a: 0.05 + 0.2 * rn(), vx: 6 + 16 * rn(), vy: -(3 + 9 * rn()), ph: rn(), per: 3 + 5 * rn() }));
    return t => { c2.clearRect(0, 0, 1080, 1920);
      for (const m of M) { const x = (m.x + m.vx * t) % 1080, y = 420 + ((m.y - 420 + m.vy * t) % 800 + 800) % 800;
        c2.globalAlpha = m.a * (0.55 + 0.45 * Math.sin(2 * Math.PI * (t / m.per + m.ph))); c2.fillStyle = "#FFE3C0";
        c2.beginPath(); c2.arc(x, y, m.r, 0, 6.2832); c2.fill(); } };
  }
  function scrims(b, top, bottom) {                  // the fades the type stands on
    const a = top ? css(el("div", "abs", b), { left: 0, top: 0, width: 1080, height: top, background: `linear-gradient(180deg, rgba(${SCRIM},.92) 0, rgba(${SCRIM},.70) 58%, rgba(${SCRIM},0) 100%)` }) : null;
    const c = bottom ? css(el("div", "abs", b), { left: 0, top: bottom, width: 1080, height: 1920 - bottom, background: `linear-gradient(180deg, rgba(${SCRIM},0) 0, rgba(${SCRIM},.80) ${Math.round(100 * 240 / (1920 - bottom))}%, rgba(${SCRIM},.95) 100%)` }) : null;
    return [a, c];
  }

  // ── the plain: one stage the camera moves over ──
  const ST = F.stage, SF = ST.files;
  const toStage = (lat, lon) => [(lon - ST.west) / ST.dlon, (ST.north - lat) / ST.dlat];
  function plain(b, layers) {                        // layers: a list of [name, file]; returns the camera and the layers
    const wrap = css(el("div", "abs", b), { left: 0, top: 0, width: ST.width, height: ST.height, transformOrigin: "0 0" });
    const fade = "linear-gradient(180deg, transparent 0, #000 140px)";     // the data's north edge melts into the night
    css(wrap, { maskImage: fade, webkitMaskImage: fade });
    const L = {};
    for (const [name, file] of layers) { const im = css(el("img", "abs", wrap), { left: 0, top: 0, width: ST.width, height: ST.height }); im.src = "/build/" + file; PENDING.push(im.decode().catch(() => {})); L[name] = im; }
    let V = [0, 0, 1, 0, 0];
    return { L, wrap,
      view(v) { V = v; const [x, y] = toStage(v[1], v[0]); wrap.style.transform = `translate(${(v[3] - v[2] * x).toFixed(2)}px, ${(v[4] - v[2] * y).toFixed(2)}px) scale(${v[2].toFixed(5)})`; },
      at(lat, lon) { const [x, y] = toStage(lat, lon), [x0, y0] = toStage(V[1], V[0]); return { x: V[3] + V[2] * (x - x0), y: V[4] + V[2] * (y - y0) }; },
      stageX(sx) { const [x0] = toStage(V[1], V[0]); return x0 + (sx - V[3]) / V[2]; } };
  }
  function dotted(b, s, colour, cls) {               // a chip beside a place, with its dot
    const c = css(el("div", "chip " + (cls || ""), b, s), {});
    c.dot = css(el("div", "abs", b), { width: 22, height: 22, borderRadius: "50%", background: colour, boxShadow: `0 0 0 4px #fff, 0 0 24px 8px ${colour}` });
    return c;
  }
  function place(c, p, dx, dy, a) { css(c.dot, { left: p.x - 11, top: p.y - 11, opacity: a.toFixed(3) }); css(c, { left: p.x + dx(c), top: p.y + dy, opacity: a.toFixed(3) }); }
  const ring = (d, t) => { d.style.scale = (1 + 0.18 * Math.sin(2 * Math.PI * t / 1.2)).toFixed(3); };

  function headOf(root, title, small, side) {
    const head = el("div", "head k-" + side, root);
    const lines = title.split(" // ").map(s => { const ln = el("span", "line", head); marked(ln, s); return ln; });
    const smalls = small ? small.split(" // ").map(s => el("span", "small" + (/[؟?]$/.test(s) ? " ask" : ""), head, s)) : [];
    return { head, lines, smalls };
  }
  function frame(sc) {
    const root = el("div", "scene", stage), heads = [];
    if (sc.before) heads.push(headOf(root, sc.before, sc.before_small || "", BEFORE[sc.key] || "blue"));
    heads.push(headOf(root, sc.title, sc.small, KEY[sc.key]));
    const body = css(el("div", "abs", root), { inset: "0" });
    const src = el("div", "sources", root, sc.source);
    return { root, heads, body, src };
  }

  // ── 1: the ground that sinks, glowing on the plain; a pole against a person ──
  function sink(sc) {
    const f = frame(sc), b = f.body, q = Q.sink, K = Wd.sink;
    const map = plain(b, [["sat", SF.now], ["glow", SF.sink]]);
    scrims(b, 760, 1180);
    const fast = dotted(b, K.bahreman, COL.red, "red"), city = dotted(b, K.rafsanjan, COL.gold);
    // the legend: the glow's colours, cm a year
    const lg = css(el("div", "abs", b), { left: 620, top: 1336, width: 300, height: 16, borderRadius: "8px",
      background: "linear-gradient(90deg, rgb(255,196,92), rgb(255,92,52), rgb(232,36,50), rgb(255,214,222))", boxShadow: "0 0 0 1.5px rgba(255,255,255,.25)" });
    const lgT = css(el("div", "label", b, K.legend), { top: 1282 });
    const lgK = F.legend.map(([v, s]) => css(el("div", "tick", b, s), { top: 1356 }));
    // the pole: a well casing anchored deep; the ground falls along it with a person standing on it
    const PX = 90, drop = F.numbers.sink.drop_m * PX, man = F.person_m * PX;
    const X0 = 110, X1 = 496, G0 = 1120, BOT = 1470, POLE = 232;
    const card = css(el("div", "abs", b), { left: X0 - 14, top: 960, width: X1 - X0 + 28, height: BOT - 960, borderRadius: "26px", background: "rgba(14,9,6,.80)", boxShadow: "0 0 0 1.5px rgba(255,238,214,.16), 0 18px 40px rgba(0,0,0,.6)" });
    const sv = svg("svg", full(), b), id = "pc" + Math.round(Math.random() * 1e9);
    const clip = svg("clipPath", { id }, svg("defs", {}, sv)); svg("rect", { x: X0 - 14, y: 960, width: X1 - X0 + 28, height: BOT - 960, rx: 26 }, clip);
    const g = svg("g", { "clip-path": `url(#${id})` }, sv);
    const soil = svg("rect", { x: X0 - 14, width: X1 - X0 + 28, fill: COL.soil, opacity: 0.95 }, g);
    const soilLine = svg("line", { x1: X0 - 14, x2: X1 + 14, stroke: "#C9935E", "stroke-width": 4 }, g);
    const old = svg("line", { x1: X0, x2: X1, y1: G0, y2: G0, stroke: COL.ink, "stroke-width": 3, "stroke-dasharray": "12 10", opacity: 0.9 }, g);
    svg("rect", { x: POLE - 9, y: G0 - 70, width: 18, height: BOT - G0 + 70, rx: 4, fill: "#D9DDE2", stroke: "#8E959C", "stroke-width": 2 }, g);   // the casing stays where it is
    const person = svg("g", { fill: COL.ink, opacity: 0.95 }, g);              // a person, feet at 0, head at -man
    const u = man / 1.75;
    svg("circle", { cx: 0, cy: -man + 0.12 * u, r: 0.12 * u }, person);
    svg("path", { d: `M${-0.2 * u},${-man + 0.27 * u} h${0.4 * u} l${0.06 * u},${0.62 * u} h${-0.1 * u} l${-0.02 * u},${-0.5 * u} h${-0.04 * u} v${0.5 * u} l0,${0.73 * u} h${-0.13 * u} l${-0.02 * u},${-0.62 * u} l${-0.02 * u},${0.62 * u} h${-0.13 * u} v${-0.73 * u} v${-0.5 * u} h${-0.04 * u} l${-0.02 * u},${0.5 * u} h${-0.1 * u} z` }, person);
    const bracket = svg("path", { d: "", fill: "none", stroke: COL.red, "stroke-width": 5, "stroke-linecap": "round" }, g);
    const tOld = css(el("div", "label", b, K.then), { left: X0 + 150, top: G0 - 50 });
    const year = css(el("div", "label", b, ""), { left: X0 + 150 });
    const tag = css(el("div", "tag", b, K.tag), {});
    const pers = css(el("div", "label num", b, K.person), { color: COL.dim });
    f.prep = () => { const w = 300; F.legend.forEach(([v], k) => css(lgK[k], { left: 620 + w * (v - 2) / 26 - lgK[k].offsetWidth / 2 })); css(lgT, { left: 920 - lgT.offsetWidth }); };
    const Y = ["۱۳۹۳", "۱۳۹۴", "۱۳۹۵", "۱۳۹۶", "۱۳۹۷", "۱۳۹۸", "۱۳۹۹", "۱۴۰۰", "۱۴۰۱"];
    return { ...f, update(t) {
      map.view(keyed(F.view.sink, t));
      const gl = easeOut(seg(t, q.glow[0], q.glow[1]));
      map.L.glow.style.opacity = ((0.45 + 0.55 * gl) * (t > q.glow[1] ? 0.88 + 0.12 * Math.sin(2 * Math.PI * (t - q.glow[1]) / 1.6) : 1)).toFixed(3);
      const pf = map.at(F.places.fastest[0], F.places.fastest[1]), pc = map.at(F.places.rafsanjan[0], F.places.rafsanjan[1]);
      place(fast, pf, c => 26, -74, easeOut(seg(t, q.chips[0], q.chips[0] + 0.4))); ring(fast.dot, t);
      place(city, pc, c => -c.offsetWidth - 26, -30, easeOut(seg(t, q.chips[1], q.chips[1] + 0.4))); ring(city.dot, t + 0.5);
      const lgA = easeOut(seg(t, q.legend, q.legend + 0.4)); [lg, lgT, ...lgK].forEach(e => show(e, lgA));
      // the pole
      const pa = easeOut(seg(t, q.pole[0] - 0.4, q.pole[0])), p = easeInOut(seg(t, q.pole[0], q.pole[1]));
      [card, sv, tOld].forEach(e => show(e, pa));
      const gy = G0 + drop * p;
      soil.setAttribute("y", gy); soil.setAttribute("height", BOT - gy + 10); soilLine.setAttribute("y1", gy); soilLine.setAttribute("y2", gy);
      person.setAttribute("transform", `translate(${X0 + 70},${gy})`);
      year.textContent = Y[Math.min(Y.length - 1, Math.floor(p * (Y.length - 1) + 1e-6))]; css(year, { top: gy + 8, opacity: (pa * (p > 0.04 ? 1 : 0)).toFixed(3) });
      bracket.setAttribute("d", p > 0.02 ? `M${POLE + 30},${G0} h16 V${gy} h-16` : "");
      const ta = easeOut(seg(t, q.tag, q.tag + 0.45)), br = t > q.tag + 0.6 ? 0.03 * Math.sin(2 * Math.PI * (t - q.tag) / 1.3) : 0;
      css(tag, { left: POLE + 46, top: (G0 + gy) / 2 - 37, opacity: ta.toFixed(3), scale: (0.85 + 0.15 * ta + 0.07 * bump(seg(t, q.tag, q.tag + 0.6)) + br).toFixed(3) });
      css(pers, { left: X0 + 4, top: gy - man - 46, opacity: (pa * seg(t, q.pole[0] + 0.6, q.pole[0] + 1.0)).toFixed(3) });
      void old;
    } };
  }

  // ── 2: the qanat that brought the water, then the dry one ──
  function qanat(sc) {
    const f = frame(sc), b = f.body, q = Q.qanat, A = photo(b, "flow"), B = photo(b, "dry"), dust = motes(b);
    scrims(b, 820, 1240);
    const what = el("div", "abs what", b, ""), credit = el("div", "abs credit", b, "");
    return { ...f, update(t) {
      const sw = easeInOut(seg(t, q.swap[0], q.swap[1]));
      A.show(1 - sw, seg(t, 0, q.swap[1])); B.show(sw, seg(t, q.swap[0], sc.length)); dust(t);
      const cur = sw < 0.5 ? A : B; what.textContent = cur.what; credit.textContent = cur.credit;
      const a = sw < 0.5 ? 1 - 2 * sw : 2 * sw - 1; show(what, 0.82 * a); show(credit, 0.62 * a);
    } };
  }

  // ── 3: the plain in 1987 wiped to 2025, the green canopy tinted ──
  function wells(sc) {
    const f = frame(sc), b = f.body, q = Q.wells, K = Wd.wells;
    const map = plain(b, [["now", SF.now], ["gnow", SF.green_now], ["then", SF.then], ["gthen", SF.green_then]]);
    scrims(b, 860, 1240);
    const line = css(el("div", "abs", b), { top: 560, width: 6, height: 980, background: "linear-gradient(180deg, rgba(242,181,68,0), #F2B544 12%, #FFE7AE 50%, #F2B544 88%, rgba(242,181,68,0))", borderRadius: "3px", boxShadow: "0 0 26px 4px rgba(242,181,68,.75)" });
    const then = css(el("div", "chip", b, K.then), { top: 900 }), now = css(el("div", "chip gold", b, K.now), { top: 900 });
    const city = dotted(b, K.rafsanjan, COL.gold);
    return { ...f, update(t) {
      map.view(keyed(F.view.wells, t));
      const p = easeInOut(seg(t, q.wipe[0], q.wipe[1])), wx = lerp(1040, 40, p);         // left of wx: 1987; right of it: 2025
      const sx = map.stageX(wx);
      [map.L.then, map.L.gthen].forEach(e => { e.style.clipPath = `inset(0 ${Math.max(0, ST.width - sx).toFixed(1)}px 0 0)`; });
      const gA = 0.72 + 0.28 * easeOut(seg(t, q.green[0], q.green[1])) * (0.85 + 0.15 * Math.sin(2 * Math.PI * Math.max(0, t - q.green[0]) / 1.8));
      [map.L.gnow, map.L.gthen].forEach(e => { e.style.opacity = gA.toFixed(3); });
      const moving = p > 0 && p < 1;
      css(line, { left: clamp(wx, 20, 1060) - 3, opacity: moving ? "1" : "0" });
      css(then, { left: p < 1 ? clamp(wx - 30, 120, 1000) - then.offsetWidth : 60, opacity: (p < 0.97 ? 1 : 0).toString() });
      css(now, { left: p > 0 ? clamp(wx + 30, 80, 940 - now.offsetWidth) : 1200, opacity: (p > 0.02 ? 1 : 0).toString() });
      place(city, map.at(F.places.rafsanjan[0], F.places.rafsanjan[1]), c => -c.offsetWidth - 26, -30, 1); ring(city.dot, t);
    } };
  }

  // ── 4: the plain's air, warmer, over Iranian pistachios ──
  function warm(sc) {
    const f = frame(sc), b = f.body, q = Q.warm, K = Wd.warm, pc = photo(b, "nuts"), dust = motes(b);
    scrims(b, 900, 860);
    const what = el("div", "abs what", b, pc.what), credit = el("div", "abs credit", b, pc.credit);
    const A = F.air, X0 = L + 20, X1 = 900, Y0 = 1300, Y1 = 1010, V0 = 14.6, V1 = 18.6;   // its year labels stay clear of the picture's lines (1412)
    const xs = y => X0 + (y - 1951) / 74 * (X1 - X0), ys = v => Y0 - (v - V0) / (V1 - V0) * (Y0 - Y1);
    const sv = svg("svg", full(), b);
    svg("line", { x1: X0, x2: X1, y1: Y0 + 20, y2: Y0 + 20, stroke: "rgba(255,255,255,.45)", "stroke-width": 3 }, sv);
    const m1 = svg("line", { x1: xs(1951), x2: xs(1980), y1: ys(A.first), y2: ys(A.first), stroke: COL.blue, "stroke-width": 5, "stroke-dasharray": "14 10", opacity: 0 }, sv);
    const m2 = svg("line", { x1: xs(1996), x2: xs(2025), y1: ys(A.last), y2: ys(A.last), stroke: COL.red, "stroke-width": 5, "stroke-dasharray": "14 10", opacity: 0 }, sv);
    const thin = svg("path", { d: "", fill: "none", stroke: "rgba(255,255,255,.34)", "stroke-width": 2.5 }, sv);
    const under = svg("path", { d: "", fill: "none", stroke: COL.red, "stroke-width": 22, opacity: 0.35, "stroke-linecap": "round", "stroke-linejoin": "round" }, sv); under.style.filter = "blur(12px)";
    const bold = svg("path", { d: "", fill: "none", stroke: COL.red, "stroke-width": 9, "stroke-linecap": "round", "stroke-linejoin": "round" }, sv);
    const tip = svg("circle", { r: 13, fill: COL.red, stroke: "#fff", "stroke-width": 4, opacity: 0 }, sv); tip.style.filter = `drop-shadow(0 0 14px ${COL.red})`;
    const br = svg("path", { d: `M${xs(2025) + 22},${ys(A.first)} h16 V${ys(A.last)} h-16`, fill: "none", stroke: COL.ink, "stroke-width": 4, opacity: 0 }, sv);
    const gap = css(el("div", "tag", b, K.gap), { top: (ys(A.first) + ys(A.last)) / 2 - 37 });
    const first = css(el("div", "tick", b, K.first), { top: Y0 + 28 }), last = css(el("div", "tick", b, K.last), { top: Y0 + 28 });
    const unit = css(el("div", "label", b, K.unit), { top: Y1 - 70 });
    const pts = A.series.map(p => [xs(p[0]), ys(p[1])]), sm = A.smooth.map(p => [xs(p[0]), ys(p[1])]);
    f.prep = () => { css(first, { left: xs(1951) - first.offsetWidth / 2 }); css(last, { left: xs(2025) - last.offsetWidth / 2 }); css(unit, { left: X1 - unit.offsetWidth + 40 }); css(gap, { left: xs(2025) - gap.offsetWidth - 40 }); };
    return { ...f, update(t) {
      pc.show(seg(t, 0, 0.6), seg(t, 0, sc.length)); dust(t + 20);
      const d = easeInOut(seg(t, q.draw[0], q.draw[1])), n = Math.max(2, Math.round(d * pts.length));
      thin.setAttribute("d", pathOf(pts.slice(0, n))); const s2 = sm.slice(0, Math.max(2, Math.round(d * sm.length)));
      bold.setAttribute("d", pathOf(s2)); under.setAttribute("d", pathOf(s2));
      const e = s2[s2.length - 1]; tip.setAttribute("cx", e[0]); tip.setAttribute("cy", e[1]); tip.setAttribute("opacity", d > 0.02 ? "1" : "0");
      tip.setAttribute("r", (13 * (1 + 0.16 * Math.sin(2 * Math.PI * t / 1.1))).toFixed(2));
      show(m1, seg(t, q.draw[0] + 0.6, q.draw[0] + 1.0)); show(m2, seg(t, q.draw[1] - 0.3, q.draw[1]));
      const g = easeOut(seg(t, q.gap, q.gap + 0.45)); br.setAttribute("opacity", g.toFixed(3));
      css(gap, { opacity: g.toFixed(3), scale: (0.85 + 0.15 * g + 0.07 * bump(seg(t, q.gap, q.gap + 0.6)) + (t > q.gap + 0.6 ? 0.03 * Math.sin(2 * Math.PI * (t - q.gap) / 1.3) : 0)).toFixed(3) });
      show(what, 0.82 * seg(t, 0.4, 0.8)); show(credit, 0.62 * seg(t, 0.4, 0.8));
    } };
  }

  // ── 5: Kerman: the ground settled and the water main broke; a crack runs through the picture ──
  function city(sc) {
    const f = frame(sc), b = f.body, q = Q.city, pc = photo(b, "city"), dust = motes(b);
    scrims(b, 900, 1160);
    const what = el("div", "abs what", b, pc.what), credit = el("div", "abs credit", b, pc.credit);
    const sv = svg("svg", full(), b);
    let sd = 1405; const rn = () => (sd = (Math.imul(sd, 1664525) + 1013904223) >>> 0) / 4294967296;
    const mid = [[1100, 1240, 16]]; for (let x = 1100; x > -30; ) { x -= 18 + 30 * rn(); mid.push([x, 1240 + (rn() - 0.5) * 46 + 14 * Math.sin(x / 110), 4 + 16 * Math.pow(rn(), 1.5) * (0.4 + 0.6 * x / 1100)]); }
    const poly = [...mid.map(p => [p[0], p[1] - p[2] / 2]), ...mid.slice().reverse().map(p => [p[0], p[1] + p[2] / 2])];
    const id = "ck" + Math.round(rn() * 1e9), cl = svg("clipPath", { id }, svg("defs", {}, sv)), open = svg("rect", { x: 1080, y: 1100, width: 0, height: 300 }, cl);
    const gC = svg("g", { "clip-path": `url(#${id})` }, sv);
    const glowC = svg("path", { d: pathOf(poly) + "Z", fill: COL.red, opacity: 0 }, gC); glowC.style.filter = "blur(10px)";
    svg("path", { d: pathOf(poly) + "Z", fill: "#0E0603" }, gC);
    svg("path", { d: pathOf(mid.map(p => [p[0], p[1] - p[2] / 2 - 1.5])), fill: "none", stroke: "#F1D2A8", "stroke-width": 2, opacity: 0.55 }, gC);
    return { ...f, update(t) {
      pc.show(seg(t, 0, 0.6), seg(t, 0, sc.length)); dust(t + 40);
      const c = easeOut(seg(t, q.small[0] - 0.6, q.small[0] + 0.9));
      open.setAttribute("x", (1100 - 1140 * c).toFixed(1)); open.setAttribute("width", (1140 * c + 20).toFixed(1));
      glowC.setAttribute("opacity", (0.45 * c * (0.7 + 0.3 * Math.sin(2 * Math.PI * t / 1.4))).toFixed(3));
      show(what, 0.82 * seg(t, 0.4, 0.8)); show(credit, 0.62 * seg(t, 0.4, 0.8));
    } };
  }

  const builders = { sink, qanat, wells, warm, city };
  const scenes = F.scenes.map(sc => Object.assign(builders[sc.key](sc), { sc }));
  await document.fonts.ready;
  await Promise.all(PENDING);
  scenes.forEach(s => {
    s.root.style.display = "block";
    s.heads.forEach(h => { fit(h.lines, W, 54); fit(h.smalls, W, 34); });
    fit([s.src], W, 22);
    if (s.src.scrollWidth > W + 1) throw new Error("sources wider than 828 px: " + s.sc.key);
    if (s.prep) s.prep();
    s.root.style.display = "none";
  });
  window.renderAt = function (t) {
    t = clamp(t, 0, END - 1e-6);
    let i = 0;
    while (i + 1 < F.scenes.length && t >= F.scenes[i + 1].start) i += 1;
    const sc = F.scenes[i], dt = t - sc.start, s = scenes[i];
    scenes.forEach((x, k) => { x.root.style.display = k === i ? "block" : "none"; });
    drawSky(t);
    s.update(dt, t);
    const enter = i === 0 ? 1 : easeOut(seg(dt, 0, 0.35));
    css(s.body, { opacity: (0.25 + 0.75 * enter).toFixed(3), transform: `translateY(${(14 * (1 - enter)).toFixed(2)}px)` });
    const turn = s.heads.length > 1 ? sc.turn : null, ph = turn !== null && dt >= turn ? 1 : 0;
    const lt = ph ? dt - turn : dt;
    s.heads.forEach((h, k) => { h.head.style.display = k === ph ? "block" : "none"; });
    if (!ph && turn !== null) s.heads[0].head.style.opacity = (1 - seg(dt, turn - 0.35, turn)).toFixed(3);
    const late = ph === s.heads.length - 1 && sc.small_at !== undefined ? sc.small_at : null;   // small lines with their own moments
    s.heads[ph].smalls.forEach((ln, k) => { if (late === null) return; const at = Array.isArray(late) ? late[Math.min(k, late.length - 1)] : late + 0.12 * k, p = easeOut(seg(dt, at, at + 0.4)); css(ln, { opacity: p.toFixed(3), transform: `translateY(${(18 * (1 - p)).toFixed(2)}px)` }); });
    [...s.heads[ph].lines, ...(late === null ? s.heads[ph].smalls : [])].forEach((ln, k) => {   // the headline arrives line by line (the first scene stands from frame 0)
      const p = i === 0 && !ph ? 1 : easeOut(seg(lt, 0.08 * k, 0.30 + 0.08 * k));
      css(ln, { opacity: (0.15 + 0.85 * p).toFixed(3), transform: `translateY(${(22 * (1 - p)).toFixed(2)}px)` });
    });
    return i;
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
