/* «زمین همیشه گرم و سرد شده؟» (cycles_fa): window.renderAt(t) draws the frame of time t (seconds) from
   /build/film.json, which src/cycles.py writes (every string, every number, the series, the clock and the cues).
   Nothing is typed here. The globe is NASA's Blue Marble with the ice-age map of src/cycles.py laid on it pixel by
   pixel: a cell of today's sea is dry land at an age older than its flood age (red channel, hundreds of years), a cell
   is under ice at an age older than its melt age (green), shaded by the relief of 21,000 years ago (blue). Every frame
   is a pure function of t (several workers render the frames out of order). */
import * as THREE from "/page/vendor/three.module.min.js";
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
function text(parent, cls, s, o) { return css(el("div", "abs " + cls, parent, s), o); }
function marked(parent, s) {
  s.split(/(\{[^}]*\})/).forEach(part => { if (!part) return; if (part[0] === "{") el("span", "key", parent, part.slice(1, -1)); else parent.appendChild(document.createTextNode(part)); });
}
function fit(nodes, limit, floor) {
  if (!nodes.length) return;
  let size = parseFloat(getComputedStyle(nodes[0]).fontSize);
  const wide = () => Math.max(...nodes.map(n => n.scrollWidth));
  while (wide() > limit && size > floor) { size -= 1; nodes.forEach(n => css(n, { fontSize: size + "px", lineHeight: Math.round(size * 1.4) + "px" })); }
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
function interp(series, x) {                         // series [[x, y], ...] sorted by x (either direction)
  const up = series[0][0] < series[series.length - 1][0];
  for (let i = 0; i + 1 < series.length; i++) {
    const a = series[i], b = series[i + 1];
    if (up ? (x >= a[0] && x <= b[0]) : (x <= a[0] && x >= b[0])) return lerp(a[1], b[1], (x - a[0]) / (b[0] - a[0] || 1));
  }
  return (up ? x < series[0][0] : x > series[0][0]) ? series[0][1] : series[series.length - 1][1];
}
function pathOf(pts) { return pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join(""); }

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const C = F.cuts.a, col = F.colours, END = C.end, Wd = F.words, S = F.series;
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const progress = el("div", null, stage); progress.id = "progress";
  const segs = C.scenes.map(() => el("i", null, el("div", "seg", progress)));
  const pill = css(el("div", "pill", stage), { padding: "0", display: "flex", overflow: "hidden", background: "transparent" });
  const half = k => css(el("span", null, pill, Wd.pill[k]), { padding: "2px 26px 7px", display: "block", fontSize: "44px", lineHeight: "60px", fontWeight: "800" });
  const pNat = half("nat"), pHum = half("hum");
  function lit(key, dt) {                            // which half the scene is about: "nat", "hum" or "both"
    let st = F.pill[key]; if (Array.isArray(st)) st = dt < st[1] ? st[0] : st[2];
    const on = (e, c, yes) => css(e, { background: yes ? c : col.land, color: yes ? col.paper : col.ink, opacity: yes ? "1" : "0.55" });
    on(pNat, col.nat, st !== "hum"); on(pHum, col.mark, st !== "nat");
    return st;
  }

  // ── the pictures: the Blue Marble, the ice-age map and the relief, as textures for the GPU (three.js, WebGL 2) ──
  async function image(file) { const im = new Image(); im.src = "/build/" + file; await im.decode(); return im; }
  const [imWorld, imAge, imRelief] = await Promise.all([F.maps.world, F.maps.age, F.maps.relief].map(image));
  const PX = F.maps.pxd, LAT1 = F.maps.lat1;
  function texture(im, nearest) {
    const t = new THREE.Texture(im); t.flipY = false; t.generateMipmaps = false; t.colorSpace = THREE.NoColorSpace;
    t.minFilter = t.magFilter = nearest ? THREE.NearestFilter : THREE.LinearFilter; t.wrapS = THREE.RepeatWrapping; t.needsUpdate = true;
    return t;
  }
  const TEX = { world: texture(imWorld), age: texture(imAge, true), relief: texture(imRelief) };
  const hex3 = h => new THREE.Vector3(...[1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)));
  const GLOBE_FS = `
    precision highp float;
    uniform sampler2D tWorld, tAge, tRelief;
    uniform vec4 uView;        // centre latitude, longitude, zoom, disc radius (px)
    uniform vec2 uC, uTex;     // disc centre (stage px); texture size (px)
    uniform float uTop, uH, uPx, uLat1, uAgeL, uAgeR, uWx, uRelief;
    uniform vec3 uIce, uShelf;
    out vec4 colour;
    const vec3 Lgt = normalize(vec3(-0.45, 0.5, 0.74));
    float height(vec2 uv, float ice) {          // metres: today's land, plus the ice of the ice age where it still lies
      vec4 r = texture(tRelief, uv / uTex);
      return 6000.0 * r.r * r.r + ice * 4500.0 * r.g * r.g;
    }
    void main() {
      float X = gl_FragCoord.x, Y = uTop + (uH - gl_FragCoord.y);
      float Rs = uView.w * uView.z, nx = (X - uC.x) / Rs, ny = (uC.y - Y) / Rs, r2 = nx * nx + ny * ny;
      if (r2 >= 1.0) {                           // the air: a soft blue rim
        float r = sqrt(r2) - 1.0, g = 0.075;
        if (r >= g) discard;
        float a = 0.62 * pow(1.0 - r / g, 2.2);
        colour = vec4(vec3(0.45, 0.66, 0.95) * a, a); return;
      }
      float nz = sqrt(1.0 - r2), p0 = radians(uView.x), s0 = sin(p0), c0 = cos(p0);
      float la = asin(clamp(ny * c0 + nz * s0, -1.0, 1.0)), d = atan(nx, nz * c0 - ny * s0);
      float lat = degrees(la), lon = mod(uView.y + degrees(d) + 180.0, 360.0) - 180.0;
      vec2 uv = vec2((lon + 180.0) * uPx, (uLat1 - lat) * uPx);
      vec3 c = texture(tWorld, uv / uTex).rgb * 255.0;
      vec2 f = uv - 0.5; ivec2 i0 = ivec2(floor(f)); vec2 fr = fract(f);
      float A = (X < uWx) ? uAgeL : uAgeR, land = 0.0, ice = 0.0, sh = 0.0;
      ivec2 sz = ivec2(uTex);
      for (int k = 0; k < 4; k++) {               // the same four-texel blend as the drawing on the canvas
        ivec2 o = ivec2(k % 2, k / 2), ij = i0 + o; ij.x = (ij.x + sz.x) % sz.x; ij.y = clamp(ij.y, 0, sz.y - 1);
        vec4 a = texelFetch(tAge, ij, 0) * 255.0;
        float w = (o.x == 0 ? 1.0 - fr.x : fr.x) * (o.y == 0 ? 1.0 - fr.y : fr.y);
        if (a.r > 0.5 && a.r < A) land += w;
        if (a.g > 0.5 && a.g < A) ice += w;
        sh += a.b * w;
      }
      float s = sh / 255.0;
      if (land > 0.0) c = mix(c, uShelf * (0.9 + 0.4 * (s - 0.62)), land);
      if (ice > 0.0) c = mix(c, uIce, ice);
      // relief: the surface normal tilted by the slope of the land and the ice (heights exaggerated to be seen)
      float cl = max(cos(la), 0.05), h0 = height(uv, ice);
      float he = (height(uv + vec2(1.0, 0.0), ice) - height(uv - vec2(1.0, 0.0), ice)) / (2.0 * 11100.0 / uPx * 10.0 * cl);
      float hn = (height(uv - vec2(0.0, 1.0), ice) - height(uv + vec2(0.0, 1.0), ice)) / (2.0 * 11100.0 / uPx * 10.0);
      vec3 N = vec3(nx, ny, nz), E = vec3(cos(d), s0 * sin(d), -c0 * sin(d));
      vec3 Nn = vec3(-sin(la) * sin(d), c0 * cos(la) + s0 * sin(la) * cos(d), s0 * cos(la) - c0 * sin(la) * cos(d));
      vec3 n = normalize(N - uRelief * (he * E + hn * Nn));
      float water = texture(tRelief, uv / uTex).b * (1.0 - land) * (1.0 - ice);
      float light = 1.12 * clamp(0.5 + 0.56 * dot(n, Lgt), 0.0, 1.15) * (0.74 + 0.26 * sqrt(nz));
      float spec = pow(max(dot(N, normalize(Lgt + vec3(0.0, 0.0, 1.0))), 0.0), 70.0) * 0.55 * water;
      vec3 rgb = c * light + 255.0 * spec;
      float gray = dot(rgb, vec3(0.299, 0.587, 0.114)); rgb = mix(vec3(gray), rgb, 1.12);       // a little more colour
      float alpha = clamp((1.0 - sqrt(r2)) * Rs, 0.0, 1.0);
      colour = vec4(clamp(rgb / 255.0, 0.0, 1.0) * alpha, alpha);
    }`;

  // the globe in a band of the stage: centre latitude and longitude, zoom, disc centre (x, y) and radius (px)
  function globe(parent, top, height) {
    const band = css(el("div", "band", parent), { top, height });
    const ren = new THREE.WebGLRenderer({ antialias: false, alpha: true, premultipliedAlpha: true, preserveDrawingBuffer: true });
    ren.setPixelRatio(1); ren.setSize(1080, height); ren.outputColorSpace = THREE.LinearSRGBColorSpace;
    css(ren.domElement, { position: "absolute", left: 0, top: 0 }); band.appendChild(ren.domElement);
    const mat = new THREE.ShaderMaterial({
      glslVersion: THREE.GLSL3, transparent: true, depthTest: false,
      vertexShader: "void main() { gl_Position = vec4(position.xy, 0.0, 1.0); }", fragmentShader: GLOBE_FS,
      uniforms: { tWorld: { value: TEX.world }, tAge: { value: TEX.age }, tRelief: { value: TEX.relief }, uView: { value: new THREE.Vector4() },
                  uC: { value: new THREE.Vector2() }, uTex: { value: new THREE.Vector2(imWorld.naturalWidth, imWorld.naturalHeight) },
                  uTop: { value: top }, uH: { value: height }, uPx: { value: PX }, uLat1: { value: LAT1 }, uAgeL: { value: 0 }, uAgeR: { value: 0 },
                  uWx: { value: 0 }, uRelief: { value: 22.0 }, uIce: { value: hex3(col.ice) }, uShelf: { value: hex3(col.shelf) } } });
    const scene = new THREE.Scene(), cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat));
    let V = null;
    function project(lat, lon) {                     // stage x, y of a place; visible or not
      const [la0, lo0, z, cx, cy, Rg] = V, Rs = Rg * z, p = lat * Math.PI / 180, l = (lon - lo0) * Math.PI / 180, p0 = la0 * Math.PI / 180;
      const x = Math.cos(p) * Math.sin(l), y = Math.cos(p0) * Math.sin(p) - Math.sin(p0) * Math.cos(p) * Math.cos(l), zz = Math.sin(p0) * Math.sin(p) + Math.cos(p0) * Math.cos(p) * Math.cos(l);
      return { x: cx + Rs * x, y: cy - Rs * y, on: zz > 0.05 };
    }
    function draw(view, ageL, ageR, wx) {            // columns left of wx show ageL, the rest ageR (thousands of years)
      V = view;
      const [la0, lo0, z, cx, cy, Rg] = view, u = mat.uniforms;
      u.uView.value.set(la0, lo0, z, Rg); u.uC.value.set(cx, cy); u.uAgeL.value = 10 * ageL; u.uAgeR.value = 10 * ageR; u.uWx.value = wx;
      ren.render(scene, cam);
    }
    return { band, draw, project, top };
  }
  function chipAt(parent, s, cls) { return css(el("div", "chip " + (cls || ""), parent, s), {}); }
  function pin(chip, g, lat, lon, dx, dy) {          // a chip beside a place on the globe, with its dot
    const p = g.project(lat, lon);
    css(chip.dot, { left: p.x - 9, top: p.y - 9, display: p.on ? "block" : "none" });
    css(chip, { left: p.x + dx, top: p.y + dy, display: p.on ? "block" : "none" });
    return p;
  }
  function dotted(parent, s, cls) { const c = chipAt(parent, s, cls); c.dot = css(el("div", "abs", parent), { width: 18, height: 18, borderRadius: "50%", background: col.mark, boxShadow: "0 0 0 4px #fff" }); return c; }

  function frame(sc) {
    const root = el("div", "scene", stage);
    const head = el("div", "head", root);
    const lines = sc.title.split(" // ").map(s => { const ln = el("span", "line", head); marked(ln, s); return ln; });
    if (sc.small) el("span", "small", head, sc.small);
    const body = css(el("div", "abs", root), { inset: "0" });
    const src = el("div", "sources", root, sc.source);
    return { root, head, lines, body, src, fits: [] };
  }

  // ── 1: the ice age wiped to today and back ──
  function hook(sc) {
    const f = frame(sc), b = f.body, q = F.cues.hook, H = Wd.hook, g = globe(b, 540, 930);
    const line = css(el("div", "abs", b), { top: 575, width: 6, height: 870, background: col.gold, borderRadius: "3px", boxShadow: "0 0 12px rgba(200,144,46,.6)" });
    const then = chipAt(b, H.then), now = chipAt(b, H.now, "gold");
    const gulf = dotted(b, H.gulf), iran = dotted(b, H.iran);
    css(iran.dot, { background: col.iran });
    return { ...f, update(t) {
      const view = keyed(F.view.hook, t);
      let wx = 2000;                                 // columns left of wx show the ice age, right of it today
      if (t >= q.wipe[0] && t < q.back[0]) wx = lerp(1000, 80, easeInOut(seg(t, q.wipe[0], q.wipe[1])));
      if (t >= q.back[0]) wx = lerp(80, 1000, easeInOut(seg(t, q.back[0], q.back[1])));
      if (t >= q.back[1]) wx = 2000;
      g.draw(view, 21, 0, wx);
      const moving = t >= q.wipe[0] && t < q.back[1] && wx < 1000 && wx > 80;
      css(line, { left: clamp(wx, 80, 1000) - 3, opacity: moving || (t >= q.wipe[1] && t < q.back[0]) ? "1" : "0" });
      const showNow = t >= q.wipe[0] && t < q.back[1];
      css(then, { left: showNow ? clamp(wx - 30, 120, 1000) - then.offsetWidth : MID - then.offsetWidth / 2, top: 610, opacity: (showNow && wx < 300) ? "0" : "1" });
      css(now, { left: clamp(wx + 30, 80, 960 - now.offsetWidth), top: 610, opacity: showNow && wx < 960 ? "1" : "0" });
      const pg = pin(gulf, g, F.places.gulf[0], F.places.gulf[1], -gulf.offsetWidth - 26, 18);
      const gp = easeOut(seg(t, q.gulf, q.gulf + 0.5));
      css(gulf, { opacity: gp.toFixed(3), scale: (0.85 + 0.15 * gp).toFixed(3) }); css(gulf.dot, { opacity: gp.toFixed(3) });
      pin(iran, g, F.places.iran[0], F.places.iran[1], 20, -30);
      show(iran, 1); show(iran.dot, 1);
      if (pg.x < 0) gulf.style.display = "none";
    } };
  }

  // ── 2: the ice melts, the sea fills the Gulf, the thermometer climbs ──
  function melt(sc) {
    const f = frame(sc), b = f.body, q = F.cues.melt, M = Wd.melt, g = globe(b, 540, 930);
    const chip = chipAt(b, ""); css(chip, { top: 600, fontWeight: "800", fontSize: "50px", lineHeight: "66px" });
    const gulf = dotted(b, M.gulf);
    // the thermometer card (left): Osman et al. 2021 at the age on the chip, -8 to +1 degrees
    const card = css(el("div", "abs", b), { left: 70, top: 770, width: 200, height: 620, borderRadius: "26px", background: "rgba(251,247,240,.93)", boxShadow: "0 14px 30px rgba(46,33,24,.25)" });
    const T0 = 1270, T1 = 820, tY = v => T0 + (v + 8) / 9 * (T1 - T0);    // stage y of a temperature (card at top 700)
    const tube = css(el("div", "abs", b), { left: 140, top: T1 - 20, width: 40, height: T0 - T1 + 40, borderRadius: "20px", background: col.land, boxShadow: "0 0 0 4px " + col.ink });
    const bulb = css(el("div", "abs", b), { left: 124, top: T0 + 6, width: 72, height: 72, borderRadius: "50%", background: col.nat, boxShadow: "0 0 0 4px " + col.ink });
    const merc = css(el("div", "abs", b), { left: 150, width: 20, borderRadius: "10px", background: col.nat });
    const br = svg("svg", full(), b), brl = svg("path", { fill: "none", stroke: col.nat, "stroke-width": 5, "stroke-linecap": "round" }, br);
    const gap = css(el("div", "abs big", b, M.gap), { left: 196, fontSize: "44px", lineHeight: "54px", color: col.paper, background: col.nat, borderRadius: "12px", padding: "0 10px 3px" });
    const a20 = interp(S.temp, 20100), a10 = interp(S.temp, 9900);
    void bulb; void tube;
    return { ...f, update(t) {
      const ka = lerp(q.age[2], q.age[3], easeInOut(seg(t, q.age[0], q.age[1])));
      const view = keyed(F.view.melt, t);
      g.draw(view, ka, ka, 0);
      const a = Math.round(ka * 2) / 2 * 1000;     // the chip in steps of 500 years
      const lab = F.chip_ages.melt.find(c => c[0] === a); chip.textContent = lab ? lab[1] : "";
      css(chip, { left: MID + 60 - chip.offsetWidth / 2 });
      const v = interp(S.temp, ka * 1000);
      css(merc, { top: tY(v), height: T0 + 30 - tY(v) });
      const gp = easeOut(seg(t, q.gap, q.gap + 0.5)), y20 = tY(a20), y10 = tY(a10);
      brl.setAttribute("d", `M186,${y20.toFixed(1)} h18 V${y10.toFixed(1)} h-18`); br.style.opacity = gp.toFixed(3);
      css(gap, { top: (y20 + y10) / 2 - 27, opacity: gp.toFixed(3) });
      pin(gulf, g, F.places.gulf[0], F.places.gulf[1], 26, -30);
      const z = easeOut(seg(t, q.zoom[1] - 0.6, q.zoom[1] + 0.2)); show(gulf, z); show(gulf.dot, z);
    } };
  }

  // ── 3: speed: 20,000 years of the curve in blue (natural, Osman et al. 2021), then 150 years in red (HadCRUT5) ──
  const CH = { x0: L + 40, x1: R - 10, y0: 1380, y1: 800, v0: -8, v1: 1.8 };
  const cx = a => CH.x1 - (a / 20000) * (CH.x1 - CH.x0), cy = v => CH.y0 + (v - CH.v0) / (CH.v1 - CH.v0) * (CH.y1 - CH.y0);
  function centreTicks(b) { b.querySelectorAll(".tick").forEach(e => { if (e.dataset.cx) e.style.left = (parseFloat(e.dataset.cx) - e.offsetWidth / 2) + "px"; }); }
  function tag(b, s, colour) { return css(el("div", "abs mk", b, s), { background: colour, color: col.paper, fontSize: "46px", lineHeight: "62px", padding: "0 18px 5px", borderRadius: "16px" }); }
  function speed(sc) {
    const f = frame(sc), b = f.body, q = F.cues.speed, K = Wd.speed, sv = svg("svg", full(), b);
    svg("line", { x1: CH.x0, x2: CH.x1, y1: CH.y0, y2: CH.y0, stroke: col.ink, "stroke-width": 4 }, sv);
    svg("line", { x1: CH.x0, x2: CH.x1, y1: cy(0), y2: cy(0), stroke: col.ink, "stroke-width": 2, "stroke-dasharray": "8 10", opacity: 0.45 }, sv);
    const band = S.band.filter(p => p[0] <= 20100);
    const bandP = svg("path", { d: pathOf([...band.map(p => [cx(p[0]), cy(p[2])]), ...band.slice().reverse().map(p => [cx(p[0]), cy(p[1])])]) + "Z", fill: col.nat, opacity: 0 }, sv);
    const pts = S.temp.filter(p => p[0] <= 20100).slice().reverse().map(p => [cx(p[0]), cy(p[1])]);
    const line = svg("path", { d: "", fill: "none", stroke: col.nat, "stroke-width": 9, "stroke-linejoin": "round", "stroke-linecap": "round" }, sv);
    K.ticks.forEach(([a, s]) => { const e = text(b, "tick", s, { top: CH.y0 + 10 }); e.dataset.cx = cx(a); });
    text(b, "tick", K.axis, { top: CH.y0 + 56, left: MID - 60 });
    const hc = S.hadcrut, last10 = hc.slice(-10).reduce((s, p) => s + p[1], 0) / 10, x = cx(0) + 4;
    const spike = svg("path", { d: "", fill: "none", stroke: col.mark, "stroke-width": 14, "stroke-linecap": "round" }, sv);
    const top = svg("circle", { cx: x, cy: cy(last10), r: 17, fill: col.mark, stroke: "#fff", "stroke-width": 5, opacity: 0 }, sv);
    const nat = tag(b, K.nat, col.nat), hum = tag(b, K.hum, col.mark);
    const yNat = cy(interp(S.temp, 15000));
    f.prep = () => { centreTicks(b); css(nat, { left: cx(15000) + 30, top: yNat + 40 }); css(hum, { left: x - hum.offsetWidth - 34, top: cy(last10) - 120 }); };
    return { ...f, update(t) {
      const p = easeInOut(seg(t, q.draw[0], q.draw[1]));
      line.setAttribute("d", pathOf(pts.slice(0, Math.max(2, Math.round(p * pts.length))))); bandP.setAttribute("opacity", (0.12 * p).toFixed(3));
      const n = easeOut(seg(t, q.nat, q.nat + 0.45)); css(nat, { opacity: n.toFixed(3), scale: (0.85 + 0.15 * n + 0.05 * bump(seg(t, q.nat, q.nat + 0.6))).toFixed(3) });
      const s = easeOut(seg(t, q.spike[0], q.spike[1]));
      spike.setAttribute("d", `M${x},${cy(0)} L${x},${cy(last10 * s)}`);
      top.setAttribute("opacity", s > 0.98 ? "1" : "0"); top.setAttribute("r", (17 * (1 + 0.16 * Math.sin(2 * Math.PI * t / 1.2))).toFixed(2));
      const h = easeOut(seg(t, q.hum, q.hum + 0.45)), br = t > q.hum + 0.6 ? 0.03 * Math.sin(2 * Math.PI * (t - q.hum) / 1.3) : 0;
      css(hum, { opacity: h.toFixed(3), scale: (0.85 + 0.15 * h + 0.07 * bump(seg(t, q.hum, q.hum + 0.6)) + br).toFixed(3) });
      nat.style.translate = `0 ${(4 * Math.sin(2 * Math.PI * t / 1.7)).toFixed(2)}px`;
    } };
  }

  // ── 5: the sun: two panels since 1960, each on its own honest scale ──
  function sun(sc) {
    const f = frame(sc), b = f.body, q = F.cues.sun, U = Wd.sun, sv = svg("svg", full(), b);
    const X0 = L + 150, X1 = R - 20, xs = y => X0 + (y - 1960) / 65 * (X1 - X0);
    const panel = (top, h, lo, hi, ann, eleven, colour, title, unit, ticks) => {
      const ys = v => top + h - (v - lo) / (hi - lo) * h;
      svg("line", { x1: X0, x2: X1, y1: top + h, y2: top + h, stroke: col.ink, "stroke-width": 3 }, sv);
      ticks.forEach(([v, s]) => { svg("line", { x1: X0, x2: X1, y1: ys(v), y2: ys(v), stroke: col.ink, "stroke-width": 1.5, "stroke-dasharray": "4 10", opacity: 0.4 }, sv); text(b, "tick", s, { top: ys(v) - 22, left: L - 6 }); });
      css(text(b, "axis", title, { top: top - 64, right: 1080 - R }), { color: colour });
      text(b, "tick", unit, { top: top - 56, left: L });
      const thin = svg("path", { d: "", fill: "none", stroke: colour, "stroke-width": 3, opacity: 0.45 }, sv);
      const bold = svg("path", { d: "", fill: "none", stroke: colour, "stroke-width": 9, "stroke-linecap": "round", "stroke-linejoin": "round" }, sv);
      return { thin, bold, a: ann.map(p => [xs(p[0]), ys(p[1])]), e: eleven.map(p => [xs(p[0]), ys(p[1])]) };
    };
    const pt = panel(720, 250, -0.1, 1.6, S.sun.t, S.sun.t11, col.mark, U.temp, U.unit_t, [[0, "۰"], [1, "۱"]]);
    const ps = panel(1120, 250, 1360.0, 1362.8, S.sun.s, S.sun.s11, col.nat, U.sun, U.unit_s, [[1361, "۱۳۶۱"], [1362, "۱۳۶۲"]]);
    U.years.forEach(([y, s]) => { const e = text(b, "tick", s, { top: 1384 }); e.dataset.cx = xs(y); });
    const arrow = (p, dy) => svg("path", { d: "", fill: col.ink, opacity: 0 }, sv);
    const aT = arrow(pt), aS = arrow(ps);
    const dT = svg("circle", { r: 11, fill: col.mark, stroke: "#fff", "stroke-width": 4, opacity: 0 }, sv), dS = svg("circle", { r: 11, fill: col.nat, stroke: "#fff", "stroke-width": 4, opacity: 0 }, sv);   // the lines' ends breathe
    f.prep = () => centreTicks(b);
    return { ...f, update(t) {
      [[pt, q.temp], [ps, q.sun]].forEach(([p, w]) => { const d = easeInOut(seg(t, w[0], w[1])); p.thin.setAttribute("d", pathOf(p.a.slice(0, Math.max(2, Math.round(d * p.a.length))))); p.bold.setAttribute("d", pathOf(p.e.slice(0, Math.max(2, Math.round(d * p.e.length))))); });
      const v = easeOut(seg(t, q.verdict, q.verdict + 0.4));
      const tipT = pt.e[pt.e.length - 1], tipS = ps.e[ps.e.length - 1];
      const bob = 7 * Math.sin(2 * Math.PI * t / 1.2);
      aT.setAttribute("d", `M${tipT[0] + 4},${tipT[1] - 46 - bob} l-22,34 h44 z`); aT.setAttribute("fill", col.mark); aT.setAttribute("opacity", v.toFixed(3));
      aS.setAttribute("d", `M${tipS[0] + 44 + bob},${tipS[1]} l-34,-22 v44 z`);
      [[dT, tipT], [dS, tipS]].forEach(([c, tip]) => { c.setAttribute("cx", tip[0]); c.setAttribute("cy", tip[1]); c.setAttribute("opacity", v.toFixed(3)); c.setAttribute("r", (11 * (1 + 0.2 * Math.sin(2 * Math.PI * t / 1.1))).toFixed(2)); }); aS.setAttribute("fill", col.nat); aS.setAttribute("opacity", v.toFixed(3));
    } };
  }

  // ── 6: carbon dioxide over 800,000 years; today breaks through the top of the chart ──
  function co2(sc) {
    const f = frame(sc), b = f.body, q = F.cues.co2, K = Wd.co2, sv = svg("svg", full(), b);
    const X0 = L + 120, X1 = R - 30, Y0 = 1400, Y1 = 940, P0 = 150, P1 = 320;
    const xs = a => X1 - Math.max(a, 0) / 805000 * (X1 - X0), ys = p => Y0 - (p - P0) / (P1 - P0) * (Y0 - Y1);
    svg("rect", { x: X0, y: ys(300), width: X1 - X0, height: ys(180) - ys(300), fill: col.nat, opacity: 0.08 }, sv);
    svg("line", { x1: X0, x2: X1, y1: Y0, y2: Y0, stroke: col.ink, "stroke-width": 4 }, sv);
    const topL = svg("line", { x1: X0, x2: X1 - 40, y1: Y1, y2: Y1, stroke: col.ink, "stroke-width": 4 }, sv);
    const topR = svg("line", { x1: X1 - 40, x2: X1 + 10, y1: Y1, y2: Y1, stroke: col.ink, "stroke-width": 4 }, sv);
    [[200, "۲۰۰"], [300, "۳۰۰"]].forEach(([p, s]) => { svg("line", { x1: X0, x2: X1, y1: ys(p), y2: ys(p), stroke: col.ink, "stroke-width": 1.5, "stroke-dasharray": "4 10", opacity: 0.45 }, sv); text(b, "tick", s, { top: ys(p) - 22, left: L - 4 }); });
    const nat = tag(b, K.nat, col.nat), hum = tag(b, K.hum, col.mark);
    text(b, "axis", K.unit, { top: Y1 - 64, left: L - 4 });
    K.ticks.forEach(([a, s]) => { const e = text(b, "tick", s, { top: Y0 + 10 }); e.dataset.cx = xs(a); });
    text(b, "tick", K.axis, { top: Y0 + 56, left: MID - 60 });
    const old = S.co2.filter(p => p[0] > 100), young = S.co2.filter(p => p[0] <= 100);
    const pts = old.map(p => [xs(p[0]), ys(p[1])]);
    const line = svg("path", { d: "", fill: "none", stroke: col.nat, "stroke-width": 5, "stroke-linejoin": "round" }, sv);
    const sp = svg("path", { d: "", fill: "none", stroke: col.mark, "stroke-width": 11, "stroke-linecap": "round" }, sv);
    const now = young[young.length - 1][1], xNow = X1 + 4;
    const tip = svg("circle", { cx: xNow, cy: ys(now), r: 15, fill: col.mark, stroke: "#fff", "stroke-width": 5, opacity: 0 }, sv);
    const shards = [0, 1, 2, 3].map(k => svg("path", { d: "M0,0 l14,-6 l-4,14 z", fill: col.ink, opacity: 0 }, sv));
    const counter = css(text(b, "chip", "", { top: 690 }), { fontWeight: "900", fontSize: "60px", lineHeight: "78px" });
    const chip = css(text(b, "chip", K.now, { top: ys(now) - 34 }), { background: col.mark, color: col.paper, fontWeight: "900", fontSize: "54px", lineHeight: "70px" });
    f.prep = () => { centreTicks(b); css(chip, { left: xNow - chip.offsetWidth - 34 }); css(nat, { left: MID - nat.offsetWidth / 2 - 60, top: Y1 - 96 }); css(hum, { left: xNow - hum.offsetWidth - 34, top: ys(now) + 60 }); };
    return { ...f, update(t) {
      const d = easeInOut(seg(t, q.draw[0], q.draw[1])), n = Math.max(2, Math.round(d * pts.length));
      line.setAttribute("d", pathOf(pts.slice(0, n)));
      const a = old[Math.min(n, old.length) - 1][0], ka = Math.max(0, Math.round(a / 10000) * 10000);
      const lab = F.chip_ages.co2.find(c => c[0] === ka); counter.textContent = lab && lab[0] > 0 ? lab[1] : ""; counter.style.visibility = counter.textContent ? "visible" : "hidden";
      css(counter, { left: MID - counter.offsetWidth / 2, opacity: (1 - seg(d, 0.93, 0.99)).toFixed(3) });   // gone before the line reaches the last centuries
      const s = easeOut(seg(t, q.spike[0], q.spike[1])), last = old[old.length - 1][1], v = last + (now - last) * s;
      sp.setAttribute("d", s > 0 ? `M${xNow},${ys(last)} L${xNow},${ys(v)}` : "");
      const broke = v > P1;                           // the top of the chart cracks where the line goes through
      topR.setAttribute("opacity", broke ? "0" : "1");
      shards.forEach((e, k) => { const p = seg(t, q.spike[0] + 0.35, q.spike[0] + 1.3); e.setAttribute("opacity", broke ? (1 - p).toFixed(3) : "0"); e.setAttribute("transform", `translate(${xNow - 20 + (k - 1.5) * 18 + (k - 1.5) * 60 * p},${Y1 - 4 - 90 * p + 70 * p * p * (k % 2 ? 1 : 0.4)}) rotate(${(k * 97 + 300 * p).toFixed(1)})`); });
      const c = easeOut(seg(t, q.chip, q.chip + 0.4)), br = t > q.chip + 0.6 ? 0.035 * Math.sin(2 * Math.PI * (t - q.chip - 0.6) / 1.3) : 0;
      css(chip, { opacity: c.toFixed(3), scale: (0.8 + 0.2 * c + 0.08 * bump(seg(t, q.chip, q.chip + 0.6)) + br).toFixed(3) });
      tip.setAttribute("opacity", s > 0.98 ? "1" : "0"); tip.setAttribute("r", (15 * (1 + 0.15 * Math.sin(2 * Math.PI * t / 1.1))).toFixed(2));
      const nt = easeOut(seg(t, q.nat, q.nat + 0.45)); css(nat, { opacity: nt.toFixed(3), scale: (0.85 + 0.15 * nt).toFixed(3), translate: `0 ${(4 * Math.sin(2 * Math.PI * t / 1.7)).toFixed(2)}px` });
      const h = easeOut(seg(t, q.hum, q.hum + 0.45)); css(hum, { opacity: h.toFixed(3), scale: (0.85 + 0.15 * h + 0.07 * bump(seg(t, q.hum, q.hum + 0.6))).toFixed(3) });
    } };
  }

  // ── 6: whose fuel: 100 cubes, each 1 % of the warming from fossil fuels so far, dropping in one country at a time ──
  const easeBounce = p => { const n = 7.5625, d = 2.75; if (p < 1 / d) return n * p * p; if (p < 2 / d) return n * (p -= 1.5 / d) * p + 0.75; if (p < 2.5 / d) return n * (p -= 2.25 / d) * p + 0.9375; return n * (p -= 2.625 / d) * p + 0.984375; };
  function who(sc) {
    const f = frame(sc), b = f.body, q = F.cues.who, G = Wd.who.groups, top = 600, height = 680;
    const order = []; ["usa", "china", "eu", "russia"].forEach(k => { for (let i = 0; i < G.find(g => g.key === k).v; i++) order.push(k); });
    const nFour = order.length, restN = 100 - nFour - 1.5;
    for (let i = 0; i < Math.floor(restN); i++) order.push("rest");
    order.push("split"); order.push("iran");
    const when = order.map((k, i) => {
      if (k === "split" || k === "iran") return q.iran + (k === "iran" ? 0.15 : 0);
      const w = q.groups[k], first = order.indexOf(k), n = order.filter(x => x === k).length;
      return w[0] + (w[1] - w[0]) * (i - first) / n;
    });
    const band = css(el("div", "abs", b), { left: 0, top, width: 1080, height });
    const ren = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    ren.setPixelRatio(1); ren.setSize(1080, height); ren.shadowMap.enabled = true; ren.shadowMap.type = THREE.PCFSoftShadowMap;
    ren.outputColorSpace = THREE.SRGBColorSpace; band.appendChild(ren.domElement);
    const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(30, 1080 / height, 0.1, 100);
    cam.position.set(0, 19.5, 10.5); cam.lookAt(0, 0, 0.6);
    scene.add(new THREE.HemisphereLight(0xfff8ee, 0xd8cdbb, 1.6));
    const sun = new THREE.DirectionalLight(0xffffff, 2.4); sun.position.set(-6, 14, 7); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -9, right: 9, top: 9, bottom: -9, near: 1, far: 40 }); sun.shadow.radius = 4;
    scene.add(sun);
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ opacity: 0.2 }));
    ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
    const cubes = order.flatMap((k, i) => {                    // the split cube is two half cubes: Iran's half and the world's half
      const parts = k === "split" ? [["iran", 0.5, -0.22], ["rest", 0.5, 0.22]] : [[k, 1, 0]];
      return parts.map(([key, w, dx]) => {
        const m = new THREE.Mesh(new THREE.BoxGeometry(0.86 * w - (w < 1 ? 0.02 : 0), 0.86, 0.86),
                                 new THREE.MeshStandardMaterial({ color: new THREE.Color(col[key]).convertSRGBToLinear(), roughness: 0.55, metalness: 0.0 }));
        m.castShadow = true; m.receiveShadow = true; scene.add(m);
        const c = i % 10, r = Math.floor(i / 10);
        return { m, i, key, x: 4.5 - c + dx, z: r - 4.5 };
      });
    });
    const legend = G.map((g, i) => {
      const e = el("div", "leg", b), sw = el("i", null, e); sw.style.background = col[g.key];
      e.appendChild(document.createTextNode(g.label + (g.v !== null ? " " + fa(g.v) + "٪" : "")));
      return css(e, { top: 1300 + Math.floor(i / 2) * 64, right: i % 2 ? 1080 - MID + 20 : 1080 - R });
    });
    text(b, "tick", Wd.who.unit, { top: top - 20, left: L });
    return { ...f, update(t) {
      cubes.forEach(o => {
        const t0 = when[o.i], p = seg(t, t0, t0 + 0.55), y = 0.43 + 7.5 * (1 - easeBounce(p));
        const four = o.i < nFour ? 0.35 * bump(seg(t, q.four, q.four + 0.7)) : 0;
        const wave = t > q.iran + 0.8 && o.i < nFour ? 0.22 * Math.max(0, Math.sin(2 * Math.PI * ((t - q.iran) / 2.2 - o.i / 30))) : 0;
        const hop = o.key === "iran" && t > q.iran + 0.6 ? 0.25 * Math.abs(Math.sin(2 * Math.PI * (t - q.iran) / 1.2)) : 0;
        o.m.visible = t >= t0; o.m.position.set(o.x, y + four + wave + hop, o.z);
        o.m.rotation.y = 0.6 * (1 - easeOut(p));
        if (o.key === "iran") o.m.material.emissive = new THREE.Color(col.iran).multiplyScalar(t > q.iran ? 0.25 + 0.2 * Math.sin(2 * Math.PI * t / 1.2) : 0);
      });
      ren.render(scene, cam);
      legend.forEach((e, i) => {
        const g = G[i], at = g.key === "iran" ? q.iran : q.groups[g.key][0];
        const s = easeOut(seg(t, at, at + 0.4)), now = g.key !== "iran" && g.key !== "rest" && t >= q.groups[g.key][0] && t < q.groups[g.key][1] + 0.3;
        css(e, { opacity: s.toFixed(3), scale: (0.85 + 0.15 * s + (now ? 0.08 : 0)).toFixed(3) });
      });
    } };
  }

  // ── 7: faster and faster: each decade's warmth above 1850-1900 (HadCRUT5), the 1.5-degree line of Paris, 2024 above it ──
  function accel(sc) {
    const f = frame(sc), b = f.body, q = F.cues.accel, A = Wd.accel, D = S.decades, sv = svg("svg", full(), b);
    const Y0 = 1360, Hh = 600, vmax = 1.75, colw = 104, gapc = 36, X0 = MID - (D.length * colw + (D.length - 1) * gapc) / 2;
    const ys = v => Y0 - v / vmax * Hh, xs = i => X0 + i * (colw + gapc), last = D.length - 1;
    svg("line", { x1: L, x2: R, y1: Y0, y2: Y0, stroke: col.ink, "stroke-width": 4 }, sv);
    css(text(b, "tick", A.unit.replace(" // ", "\n"), { top: ys(vmax) - 100, left: L }), { whiteSpace: "pre-line", lineHeight: "46px", textAlign: "right" });
    const bars = D.map((d, i) => svg("rect", { x: xs(i), width: colw, y: Y0, height: 0, rx: 10, fill: i === last ? col.mark : col.russia }, sv));
    const vals = A.values.map((s, i) => css(text(b, "tick", s, { top: 0 }), { fontWeight: "800", fontSize: i === last ? "50px" : "40px", color: i === last ? col.mark : col.ink }));
    const first = text(b, "tick", A.first, { top: Y0 + 12 }), lastL = text(b, "tick", A.last, { top: Y0 + 12 });
    const paris = svg("line", { x1: L, x2: R, y1: ys(1.5), y2: ys(1.5), stroke: col.mark, "stroke-width": 4, "stroke-dasharray": "14 12" }, sv);
    const parisL = css(text(b, "tick", A.paris, { top: ys(1.5) - 52, left: L }), { fontWeight: "800", color: col.mark });
    const dot = svg("circle", { cx: xs(last) + colw / 2, cy: ys(S.y2024), r: 16, fill: col.mark, stroke: "#fff", "stroke-width": 5, opacity: 0 }, sv);
    const yr = css(text(b, "tick", A.year, { top: ys(S.y2024) - 64 }), { fontWeight: "800", color: col.mark });
    const tg = css(el("div", "abs mk", b, A.tag), { background: col.mark, color: col.paper, fontSize: "42px", lineHeight: "58px", padding: "0 16px 5px", borderRadius: "14px" });
    const at = i => q.bars[0] + (q.bars[1] - q.bars[0]) * i / D.length;
    f.prep = () => { css(first, { left: xs(0) + colw / 2 - first.offsetWidth / 2 }); css(lastL, { left: xs(last) + colw / 2 - lastL.offsetWidth / 2 });
      css(yr, { left: xs(last) - yr.offsetWidth - 10 });
      css(tg, { left: xs(last) - tg.offsetWidth - 20, top: ys(1.5) + 16 }); };   // under the 1.5 line, clear of the columns' values
    return { ...f, update(t) {
      D.forEach((d, i) => {                          // each column rises with its value counting up on top of it
        const p = easeOut(seg(t, at(i), at(i) + 0.6)), v = d[1] * p;
        bars[i].setAttribute("y", ys(v)); bars[i].setAttribute("height", Y0 - ys(v));
        vals[i].textContent = fa(v.toFixed(2)); css(vals[i], { left: xs(i) + colw / 2 - vals[i].offsetWidth / 2, top: ys(v) - (i === last ? 64 : 54), opacity: (p > 0.02 ? 1 : 0).toString() });
        if (p >= 1) vals[i].textContent = A.values[i];
      });
      const pl = easeOut(seg(t, q.paris, q.paris + 0.6));
      paris.setAttribute("x2", (L + (R - L) * pl).toFixed(1)); show(parisL, pl);
      const dp = easeOut(seg(t, q.year, q.year + 0.4));
      dot.setAttribute("opacity", dp.toFixed(3)); dot.setAttribute("r", (16 * (0.6 + 0.4 * dp) * (1 + 0.15 * Math.sin(2 * Math.PI * Math.max(0, t - q.year) / 1.2))).toFixed(2)); show(yr, dp);
      const g = easeOut(seg(t, q.tag, q.tag + 0.45)), br = t > q.tag + 0.6 ? 0.03 * Math.sin(2 * Math.PI * (t - q.tag) / 1.3) : 0;
      css(tg, { opacity: g.toFixed(3), scale: (0.85 + 0.15 * g + 0.07 * bump(seg(t, q.tag, q.tag + 0.6)) + br).toFixed(3) });
    } };
  }

  // ── 8: the call ──
  function call(sc) {
    const f = frame(sc), b = f.body, q = F.cues.call, g = globe(b, 480, 560);
    const icon = svg("svg", { width: 260, height: 260, viewBox: "-60 -60 120 120" }, b);
    css(icon, { left: MID - 130, top: 1080 });
    const ic = svg("g", { fill: "none", stroke: col.mark, "stroke-width": 9, "stroke-linecap": "round", "stroke-linejoin": "round" }, icon);
    svg("path", { d: "M-34,-8 v-14 a10,10 0 0 1 10,-10 h52" }, ic); svg("path", { d: "M18,-44 l12,12 l-12,12" }, ic);
    svg("path", { d: "M34,8 v14 a10,10 0 0 1 -10,10 h-52" }, ic); svg("path", { d: "M-18,44 l-12,-12 l12,-12" }, ic);
    return { ...f, update(t) {
      g.draw(keyed(F.view.call, t), 0, 0, 0);
      const p = easeOut(seg(t, q.icon, q.icon + 0.5)), spin = t > q.icon ? (t - q.icon) * 60 : 0;
      css(icon, { opacity: p.toFixed(3), scale: (0.7 + 0.3 * p + 0.05 * Math.sin(2 * Math.PI * Math.max(0, t - q.icon) / 1.3)).toFixed(3) });
      ic.setAttribute("transform", `rotate(${(spin % 360).toFixed(1)})`);
    } };
  }

  const builders = { hook, melt, speed, sun, co2, who, accel, call };
  const scenes = C.scenes.map(sc => Object.assign(builders[sc.key](sc), { sc }));
  await document.fonts.ready;
  scenes.forEach(s => {
    s.root.style.display = "block";
    fit(s.lines, W, 54);
    fit([...s.head.querySelectorAll(".small")], W, 38);
    (s.fits || []).forEach(n => fit([n], W, 34));
    if (s.follow) fit(s.follow, W, 36);
    fit([s.src], W, 26);
    if (s.src.scrollWidth > W + 1) throw new Error("sources wider than 828 px: " + s.sc.key);
    if (s.prep) s.prep();
    s.root.style.display = "none";
  });
  window.renderAt = function (t) {
    t = clamp(t, 0, END - 1e-6);
    let i = 0;
    while (i + 1 < C.scenes.length && t >= C.scenes[i + 1].start) i += 1;
    const sc = C.scenes[i], dt = t - sc.start;
    scenes.forEach((s, k) => { s.root.style.display = k === i ? "block" : "none"; });
    scenes[i].update(dt, t);
    lit(sc.key, dt);
    const enter = i === 0 ? 1 : easeOut(seg(dt, 0, 0.35));
    css(scenes[i].body, { opacity: (0.25 + 0.75 * enter).toFixed(3), transform: `translateY(${(14 * (1 - enter)).toFixed(2)}px)` });
    segs.forEach((s, k) => { s.style.width = (k < i ? 100 : k > i ? 0 : 100 * dt / sc.length).toFixed(3) + "%"; });
    return i;
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
