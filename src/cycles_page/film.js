/* «زمین همیشه گرم و سرد شده؟» (cycles_fa): window.renderAt(t) draws the frame of time t (seconds) from
   /build/film.json, which src/cycles.py writes (every string, every number, the series, the clock and the cues).
   Nothing is typed here: this file only decides how the film looks. The globe is NASA's Blue Marble with the ice-age
   map of src/cycles.py laid on it pixel by pixel: a cell of today's sea is dry land at an age older than its flood age
   (red channel, hundreds of years), a cell is under ice at an age older than its melt age (green), shaded by the
   relief of 21,000 years ago (blue). Every frame is a pure function of t (several workers render the frames out of
   order): the stars, the glows and the camera drift are all functions of the clock. */
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
  while (wide() > limit && size > floor) { size -= 1; nodes.forEach(n => css(n, { fontSize: size + "px", lineHeight: Math.round(size * (CUT === "d" && n.classList.contains("line") ? 1.36 : 1.4)) + "px" })); }
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

// ── the look. Two of them, chosen by film.html?theme=: "light" (the default: the account's cream paper and ink) and
//    "night" (light on a dark sky). Blue = natural, red = human in both; each has a tone for lines and one for fills that
//    carry white type. The film's own colours (film.json) keep their names; only their values are set here. ──
const THEME = new URLSearchParams(location.search).get("theme") === "night" ? "night" : "light";
document.documentElement.dataset.theme = THEME;
const CUT = new URLSearchParams(location.search).get("cut") === "d" ? "d" : "a";     // a: the eight scenes; d: the documentary cut
document.documentElement.dataset.cut = CUT;
const LOOK = {
  light: { paper: "#FFFFFF", ink: "#2E2118", dim: "#5E4E42", axis: "rgba(46,33,24,.80)", grid: "rgba(46,33,24,.34)",
           mark: "#B5332A", markf: "#A03129", nat: "#2468B4", natf: "#2468B4", gold: "#A8700F", ice: "#EEF3F8", shelf: "#CDB48A",
           iran: "#2F7D4F", usa: "#8E1B16", china: "#C8372D", eu: "#E8705F", russia: "#F2A999", rest: "#BDB3A4", bar: "#DC977F",
           glowK: 0.42, off: "rgba(46,33,24,.07)", offInk: "rgba(46,33,24,.45)", stars: 0, add: 0.0, dark: 0.46,
           card: "rgba(255,253,248,.95)", cardShadow: "0 0 0 1.5px rgba(46,33,24,.08), 0 18px 40px rgba(46,33,24,.30)", tube: "rgba(46,33,24,.10)", glass: "rgba(46,33,24,.78)",
           lamps: [[255, 255, 255, 0.34], [226, 208, 180, 0.16]], area: 0.17, floor: "", shadow: 0.26, hemi: [0xfff8ee, 0xd8cdbb, 1.3], sun: 2.2, rim: 0.4 },
  night: { paper: "#FFFFFF", ink: "#F4EFE6", dim: "#A9B6CC", axis: "rgba(255,255,255,.46)", grid: "rgba(255,255,255,.17)",
           mark: "#FF5A4E", markf: "#D8352B", nat: "#5AB0FF", natf: "#1F6FD6", gold: "#F2B33D", ice: "#EEF4FA", shelf: "#C9AE82",
           iran: "#35D58A", usa: "#E3241B", china: "#FF5E4A", eu: "#FF937F", russia: "#FFC9BD", rest: "#737884", bar: "#FF8E83",
           glowK: 1.0, off: "rgba(255,255,255,.07)", offInk: "rgba(244,239,230,.42)", stars: 1, add: 1.0, dark: 0.16,
           card: "rgba(8,14,30,.80)", cardShadow: "0 0 0 1.5px rgba(255,255,255,.20), 0 22px 44px rgba(0,0,0,.55)", tube: "rgba(255,255,255,.10)", glass: "rgba(255,255,255,.62)",
           lamps: [[52, 110, 214, 0.16], [216, 72, 60, 0.10]], area: 0.30, floor: "radial-gradient(closest-side, rgba(70,110,190,.26), rgba(70,110,190,0))", shadow: 0.55, hemi: [0xe6ecff, 0x232a3c, 1.0], sun: 2.3, rim: 1.0 },
}[THEME];
let UID = 0;
function grad(sv, colour, y1, y2, a1, a2) {          // a vertical fade of one colour, in stage pixels
  const id = "g" + (UID++), d = sv.querySelector("defs") || svg("defs", {}, sv);
  const g = svg("linearGradient", { id, gradientUnits: "userSpaceOnUse", x1: 0, x2: 0, y1, y2 }, d);
  svg("stop", { offset: 0, "stop-color": colour, "stop-opacity": a1 }, g); svg("stop", { offset: 1, "stop-color": colour, "stop-opacity": a2 }, g);
  return `url(#${id})`;
}
function glow(sv, attrs, blur = 10, strength = 0.62) {   // a stroke with its own soft light under it
  strength *= LOOK.glowK;
  const under = svg("path", { ...attrs, "stroke-width": 2.3 * attrs["stroke-width"], opacity: strength }, sv);
  under.style.filter = `blur(${blur}px)`;
  const top = svg("path", attrs, sv);
  return { setAttribute(k, v) { top.setAttribute(k, v); if (k === "d") under.setAttribute(k, v); if (k === "opacity") under.setAttribute(k, (strength * v).toFixed(3)); } };
}

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const C = F.cuts[CUT], col = Object.assign({}, F.colours, LOOK), END = C.end, Wd = F.words, S = F.series;

  // ── the sky: two slow soft lights by the clock and, at night, a few hundred stars that drift and twinkle ──
  const sky = el("canvas", null, stage); sky.id = "sky"; sky.width = 1080; sky.height = 1920;
  const sk = sky.getContext("2d");
  let seed = 20261123; const rnd = () => (seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 4294967296;
  const STARS = Array.from({ length: 460 }, () => ({ x: rnd() * 1080, y: rnd() * 1920, r: 0.55 + 2.0 * Math.pow(rnd(), 3.2), a: 0.22 + 0.78 * rnd(), ph: rnd(), per: 2.4 + 4.2 * rnd(), tint: rnd() }));
  function drawSky(T, k) {
    sk.clearRect(0, 0, 1080, 1920);
    const lamp = (x, y, r, c) => { const g = sk.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, `rgba(${c[0]},${c[1]},${c[2]},${c[3]})`); g.addColorStop(1, `rgba(${c[0]},${c[1]},${c[2]},0)`); sk.globalAlpha = 1; sk.fillStyle = g; sk.fillRect(x - r, y - r, 2 * r, 2 * r); };
    lamp(210 + 120 * Math.sin(2 * Math.PI * T / 37), 520 + 90 * Math.cos(2 * Math.PI * T / 29), 760, LOOK.lamps[0]);
    lamp(880 + 110 * Math.cos(2 * Math.PI * T / 41), 1330 + 100 * Math.sin(2 * Math.PI * T / 33), 720, LOOK.lamps[1]);
    if (LOOK.stars) for (const s of STARS) {
      const x = (s.x + T * 2.4 * (0.35 + s.r / 2.6)) % 1080;
      sk.globalAlpha = k * s.a * (0.6 + 0.4 * Math.sin(2 * Math.PI * (T / s.per + s.ph)));
      sk.fillStyle = s.tint > 0.86 ? "#FFE2B4" : s.tint < 0.16 ? "#BBD8FF" : "#FFFFFF";
      sk.beginPath(); sk.arc(x, s.y, s.r, 0, 6.2832); sk.fill();
    }
    sk.globalAlpha = 1;
  }

  const progress = el("div", null, stage); progress.id = "progress";
  const segs = C.scenes.map(() => el("i", null, el("div", "seg", progress)));
  const pill = css(el("div", "pill", stage), { padding: "0", display: "flex", overflow: "hidden" });
  const half = k => css(el("span", null, pill, Wd.pill[k]), { padding: "2px 26px 7px", display: "block", fontSize: "44px", lineHeight: "60px", fontWeight: "800" });
  const pNat = half("nat"), pHum = half("hum");
  function lit(key, dt) {                            // which half the scene is about: "nat", "hum" or "both"
    let st = F.pill[key]; if (Array.isArray(st)) st = dt < st[1] ? st[0] : st[2];
    const on = (e, c, yes) => css(e, { background: yes ? c : LOOK.off, color: yes ? "#fff" : LOOK.offInk });
    on(pNat, col.natf, st !== "hum"); on(pHum, col.markf, st !== "nat");
    return st;
  }
  const KEY = { hook: "hum", melt: "nat", speed: "hum", sun: "nat", co2: "nat", who: "hum", accel: "hum", call: "hum",
                gulf: "hum", thaw: "nat", life: "nat", exit: "hum", send: "hum" };   // the headline's highlight wears its scene's side
  const BEFORE = { speed: "nat", gulf: "hum" };      // and the side of a scene's first headline, where it has two
  const STARRY = { hook: 1, melt: 1, call: 1, gulf: 1, thaw: 1 };      // full stars behind the globe, fainter behind the charts

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
    uniform float uTop, uH, uPx, uLat1, uAgeL, uAgeR, uWx, uRelief, uAdd, uDark;
    uniform vec3 uIce, uShelf;
    out vec4 colour;
    const vec3 Lgt = normalize(vec3(-0.52, 0.50, 0.70));
    const vec3 Air = vec3(0.38, 0.64, 1.0);
    float height(vec2 uv, float ice) {          // metres: today's land, plus the ice of the ice age where it still lies
      vec4 r = texture(tRelief, uv / uTex);
      return 6000.0 * r.r * r.r + ice * 4500.0 * r.g * r.g;
    }
    void main() {
      float X = gl_FragCoord.x, Y = uTop + (uH - gl_FragCoord.y);
      float Rs = uView.w * uView.z, nx = (X - uC.x) / Rs, ny = (uC.y - Y) / Rs, r2 = nx * nx + ny * ny;
      if (r2 >= 1.0) {                           // the air against space: a halo, brighter on the sunlit side
        float r = sqrt(r2) - 1.0, g = 0.20;
        if (r >= g) discard;
        float side = 0.55 + 0.45 * clamp(dot(normalize(vec2(nx, ny)), normalize(Lgt.xy)), -1.0, 1.0);
        float a = (0.60 * exp(-r / 0.030) + 0.20 * pow(1.0 - r / g, 2.0)) * (0.35 + 0.65 * side);
        colour = vec4(mix(vec3(0.30, 0.56, 0.94), Air, uAdd) * a, a * mix(1.0, 0.55, uAdd)); return;   // on paper the air tints, on the night sky it shines
      }
      float nz = sqrt(1.0 - r2), p0 = radians(uView.x), s0 = sin(p0), c0 = cos(p0);
      float la = asin(clamp(ny * c0 + nz * s0, -1.0, 1.0)), d = atan(nx, nz * c0 - ny * s0);
      float lat = degrees(la), lon = mod(uView.y + degrees(d) + 180.0, 360.0) - 180.0;
      vec2 uv = vec2((lon + 180.0) * uPx, (uLat1 - lat) * uPx);
      vec3 c = texture(tWorld, uv / uTex).rgb * 255.0;
      c = mix(c, vec3(15.0, 40.0, 84.0), smoothstep(77.0, 83.5, lat) * texture(tRelief, uv / uTex).b);   // the open sea by the pole, where the picture's rows run into streaks
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
      float cl = max(cos(la), 0.05);
      float he = (height(uv + vec2(1.0, 0.0), ice) - height(uv - vec2(1.0, 0.0), ice)) / (2.0 * 11100.0 / uPx * 10.0 * cl);
      float hn = (height(uv - vec2(0.0, 1.0), ice) - height(uv + vec2(0.0, 1.0), ice)) / (2.0 * 11100.0 / uPx * 10.0);
      vec3 N = vec3(nx, ny, nz), E = vec3(cos(d), s0 * sin(d), -c0 * sin(d));
      vec3 Nn = vec3(-sin(la) * sin(d), c0 * cos(la) + s0 * sin(la) * cos(d), s0 * cos(la) - c0 * sin(la) * cos(d));
      vec3 n = normalize(N - uRelief * (he * E + hn * Nn));
      float water = texture(tRelief, uv / uTex).b * (1.0 - land) * (1.0 - ice);
      float zoomed = smoothstep(1.4, 2.6, uView.z);                 // close on the Gulf the whole view is in daylight
      float day = mix(smoothstep(-0.42, 0.42, dot(N, Lgt)), 1.0, zoomed);   // a soft terminator on the far side from the sun
      float light = 1.16 * clamp(0.5 + 0.58 * dot(n, Lgt), 0.0, 1.18) * mix(uDark, 1.0, day);
      float spec = pow(max(dot(N, normalize(Lgt + vec3(0.0, 0.0, 1.0))), 0.0), 70.0) * 0.6 * water * day;
      vec3 rgb = c * light + 255.0 * spec;
      rgb += ice * day * vec3(-10.0, 0.0, 12.0) * (1.0 - clamp(dot(n, Lgt), 0.0, 1.0));   // a breath of blue in the ice's shade
      float gray = dot(rgb, vec3(0.299, 0.587, 0.114)); rgb = mix(vec3(gray), rgb, 1.14);       // a little more colour
      float fres = pow(1.0 - nz, 2.8) * (1.0 - zoomed);             // the air seen edge-on, over the limb
      rgb = mix(rgb, 255.0 * Air, 0.62 * fres * (0.30 + 0.70 * day));
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
                  uWx: { value: 0 }, uRelief: { value: 22.0 }, uAdd: { value: LOOK.add }, uDark: { value: LOOK.dark }, uIce: { value: hex3(col.ice) }, uShelf: { value: hex3(col.shelf) } } });
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
  function dotted(parent, s, cls, colour) {
    const c = chipAt(parent, s, cls), k = colour || col.mark;
    c.dot = css(el("div", "abs", parent), { width: 18, height: 18, borderRadius: "50%", background: k, boxShadow: `0 0 0 4px #fff, 0 0 22px 6px ${k}` });
    return c;
  }
  const ring = (dotEl, t) => { dotEl.style.scale = (1 + 0.16 * Math.sin(2 * Math.PI * t / 1.2)).toFixed(3); };   // a place's dot breathes

  function headOf(root, title, small, side) {       // a headline: its lines, its small line, the side its highlight wears
    const head = el("div", "head k-" + side, root);
    const lines = title.split(" // ").map(s => { const ln = el("span", "line", head); marked(ln, s); return ln; });
    return { head, lines, smalls: small ? small.split(" // ").map(s => el("span", "small", head, s)) : [] };
  }
  function frame(sc) {                               // a scene with "before" has two headlines: the natural side first,
    const root = el("div", "scene", stage), heads = [];   // then its own from the cue "human" on
    if (sc.before) heads.push(headOf(root, sc.before, "", BEFORE[sc.key] || "nat"));
    heads.push(headOf(root, sc.title, sc.small, KEY[sc.key]));
    const body = css(el("div", "abs", root), { inset: "0" });
    const src = el("div", "sources", root, sc.source);
    return { root, heads, body, src, fits: [] };
  }

  // ── 1: the ice age wiped to today and back ──
  function hook(sc) {
    const f = frame(sc), b = f.body, q = F.cues.hook, H = Wd.hook, g = globe(b, 540, 930);
    const line = css(el("div", "abs", b), { top: 575, width: 6, height: 870, background: "linear-gradient(180deg, rgba(242,179,61,0), #F2B33D 12%, #FFE7AE 50%, #F2B33D 88%, rgba(242,179,61,0))", borderRadius: "3px", boxShadow: "0 0 26px 4px rgba(242,179,61,.75)" });
    const then = chipAt(b, H.then), now = chipAt(b, H.now, "gold");
    const gulf = dotted(b, H.gulf), iran = dotted(b, H.iran, "", col.iran);
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
      show(iran, 1); show(iran.dot, 1); ring(iran.dot, t); ring(gulf.dot, t + 0.6);
      if (pg.x < 0) gulf.style.display = "none";
    } };
  }

  // ── 2: the ice melts, the sea fills the Gulf, the thermometer climbs ──
  function melt(sc) {
    const f = frame(sc), b = f.body, q = F.cues.melt, M = Wd.melt, g = globe(b, 540, 930);
    const chip = chipAt(b, ""); css(chip, { top: 600, fontWeight: "800", fontSize: "50px", lineHeight: "66px" });
    const gulf = dotted(b, M.gulf);
    // the thermometer card (left): Osman et al. 2021 at the age on the chip, -8 to +1 degrees
    css(el("div", "abs", b), { left: 70, top: 770, width: 200, height: 620, borderRadius: "30px", background: LOOK.card, boxShadow: LOOK.cardShadow });
    const T0 = 1270, T1 = 820, tY = v => T0 + (v + 8) / 9 * (T1 - T0);    // stage y of a temperature (card at top 700)
    css(el("div", "abs", b), { left: 140, top: T1 - 20, width: 40, height: T0 - T1 + 40, borderRadius: "20px", background: LOOK.tube, boxShadow: "0 0 0 3px " + LOOK.glass });
    css(el("div", "abs", b), { left: 124, top: T0 + 6, width: 72, height: 72, borderRadius: "50%", background: `radial-gradient(circle at 36% 32%, #BFE0FF, ${col.nat} 46%, ${col.natf})`, boxShadow: `0 0 0 3px ${LOOK.glass}, 0 0 30px 4px rgba(90,176,255,${(0.55 * LOOK.glowK).toFixed(2)})` });
    const merc = css(el("div", "abs", b), { left: 150, width: 20, borderRadius: "10px", background: `linear-gradient(180deg, #BFE0FF, ${col.nat} 30%, ${col.natf})`, boxShadow: `0 0 18px rgba(90,176,255,${(0.7 * LOOK.glowK).toFixed(2)})` });
    const br = svg("svg", full(), b), brl = svg("path", { fill: "none", stroke: col.nat, "stroke-width": 5, "stroke-linecap": "round" }, br);
    const gap = css(el("div", "abs big", b, M.gap), { left: 196, fontSize: "44px", lineHeight: "54px", color: "#fff", background: col.natf, borderRadius: "12px", padding: "0 10px 3px", boxShadow: "0 8px 22px rgba(31,111,214,.55)" });
    const a20 = interp(S.temp, 20100), a10 = interp(S.temp, 9900);
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
      const z = easeOut(seg(t, q.zoom[1] - 0.6, q.zoom[1] + 0.2)); show(gulf, z); show(gulf.dot, z); ring(gulf.dot, t);
    } };
  }

  // ── 3: speed: 20,000 years of the curve in blue (natural, Osman et al. 2021), then 150 years in red (HadCRUT5) ──
  const CH = { x0: L + 40, x1: R - 10, y0: 1380, y1: 800, v0: -8, v1: 1.8 };
  const cx = a => CH.x1 - (a / 20000) * (CH.x1 - CH.x0), cy = v => CH.y0 + (v - CH.v0) / (CH.v1 - CH.v0) * (CH.y1 - CH.y0);
  function centreTicks(b) { b.querySelectorAll(".tick").forEach(e => { if (e.dataset.cx) e.style.left = (parseFloat(e.dataset.cx) - e.offsetWidth / 2) + "px"; }); }
  function tag(b, s, colour) { return css(el("div", "abs mk", b, s), { background: colour, fontSize: "46px", lineHeight: "62px", padding: "0 18px 5px", borderRadius: "16px" }); }
  const under = (sl, y) => pathOf(sl) + `L${sl[sl.length - 1][0].toFixed(1)},${y} L${sl[0][0].toFixed(1)},${y}Z`;   // the area between a line and its axis
  function speed(sc) {
    const f = frame(sc), b = f.body, q = F.cues.speed, K = Wd.speed, sv = svg("svg", full(), b);
    svg("line", { x1: CH.x0, x2: CH.x1, y1: CH.y0, y2: CH.y0, stroke: col.axis, "stroke-width": 3 }, sv);
    svg("line", { x1: CH.x0, x2: CH.x1, y1: cy(0), y2: cy(0), stroke: col.ink, "stroke-width": 2, "stroke-dasharray": "8 10", opacity: 0.38 }, sv);
    const calm = svg("rect", { x: cx(10000), y: CH.y1 - 30, width: cx(0) - cx(10000), height: CH.y0 - CH.y1 + 30, rx: 12, fill: col.gold, opacity: 0 }, sv);   // the calm ten thousand years
    const band = S.band.filter(p => p[0] <= 20100);
    const bandP = svg("path", { d: pathOf([...band.map(p => [cx(p[0]), cy(p[2])]), ...band.slice().reverse().map(p => [cx(p[0]), cy(p[1])])]) + "Z", fill: col.nat, opacity: 0 }, sv);
    const pts = S.temp.filter(p => p[0] <= 20100).slice().reverse().map(p => [cx(p[0]), cy(p[1])]);
    const area = svg("path", { d: "", fill: grad(sv, col.nat, CH.y1, CH.y0, LOOK.area, 0.0) }, sv);
    const line = glow(sv, { d: "", fill: "none", stroke: col.nat, "stroke-width": 9, "stroke-linejoin": "round", "stroke-linecap": "round" });
    const lead = svg("circle", { r: 11, fill: "#fff", stroke: col.nat, "stroke-width": 4, opacity: 0 }, sv); lead.style.filter = `drop-shadow(0 0 12px ${col.nat})`;
    K.ticks.forEach(([a, s]) => { const e = text(b, "tick", s, { top: CH.y0 + 10 }); e.dataset.cx = cx(a); });
    text(b, "tick", K.axis, { top: CH.y0 + 56, left: MID - 60 });
    const hc = S.hadcrut, last10 = hc.slice(-10).reduce((s, p) => s + p[1], 0) / 10, x = cx(0) + 4;
    const spike = glow(sv, { d: "", fill: "none", stroke: col.mark, "stroke-width": 14, "stroke-linecap": "round" }, 14, 0.85);
    const top = svg("circle", { cx: x, cy: cy(last10), r: 17, fill: col.mark, stroke: "#fff", "stroke-width": 5, opacity: 0 }, sv); top.style.filter = `drop-shadow(0 0 16px ${col.mark})`;
    const nat = tag(b, K.nat, col.natf), hum = tag(b, K.hum, col.markf);
    const yNat = cy(interp(S.temp, 15000));
    const pins = (K.markers || []).map((m, k, all) => {   // a dot on the curve at its age, a stem down, its name on a chip: a ladder, the
      const px = cx(m.age), py = cy(interp(S.temp, m.age)), up = k === all.length - 1;   // the youngest stands above the curve, in gold;
      const top = up ? 800 : 985 + 75 * (all.length - 2 - k);                              // the older ones below, oldest lowest: no stem crosses a chip or the curve
      const stem = svg("line", { x1: px, x2: px, y1: py, y2: up ? top + 52 : top + 6, stroke: col.gold, "stroke-width": 4, "stroke-linecap": "round", opacity: 0 }, sv);
      const dot = svg("circle", { cx: px, cy: py, r: 12, fill: col.gold, stroke: "#fff", "stroke-width": 4, opacity: 0 }, sv);
      return { px, stem, dot, chip: css(chipAt(b, m.label, up ? "gold" : ""), { top, fontWeight: "800" }) };
    });
    f.prep = () => { centreTicks(b); css(nat, { left: cx(15000) + 30, top: yNat + 40 }); css(hum, { left: x - hum.offsetWidth - 34, top: cy(last10) - 120 });
      pins.forEach(o => css(o.chip, { left: clamp(o.px - 26, L, R - o.chip.offsetWidth) })); };
    return { ...f, update(t) {
      const p = easeInOut(seg(t, q.draw[0], q.draw[1])), sl = pts.slice(0, Math.max(2, Math.round(p * pts.length))), tipP = sl[sl.length - 1];
      line.setAttribute("d", pathOf(sl)); area.setAttribute("d", under(sl, CH.y0)); bandP.setAttribute("opacity", (0.16 * p).toFixed(3));
      lead.setAttribute("cx", tipP[0]); lead.setAttribute("cy", tipP[1]); lead.setAttribute("opacity", p > 0 && p < 1 ? "1" : "0");
      const away = q.human === undefined ? 0 : seg(t, q.human - 0.1, q.human + 0.3);        // the names leave when the scene turns to the human side; the dots stay
      if (q.band !== undefined) calm.setAttribute("opacity", (0.13 * easeOut(seg(t, q.band, q.band + 0.5)) * (1 - 0.45 * away)).toFixed(3));
      pins.forEach((o, k) => {
        const a = easeOut(seg(t, q.marks[k], q.marks[k] + 0.4)), pop = 0.07 * bump(seg(t, q.marks[k], q.marks[k] + 0.6));
        o.dot.setAttribute("opacity", a.toFixed(3)); o.dot.setAttribute("r", (12 * (0.6 + 0.4 * a + pop)).toFixed(2));
        o.stem.setAttribute("opacity", (0.9 * a * (1 - away)).toFixed(3));
        css(o.chip, { opacity: (a * (1 - away)).toFixed(3), scale: (0.85 + 0.15 * a + pop).toFixed(3) });
      });
      const n = easeOut(seg(t, q.nat, q.nat + 0.45)); css(nat, { opacity: n.toFixed(3), scale: (0.85 + 0.15 * n + 0.05 * bump(seg(t, q.nat, q.nat + 0.6))).toFixed(3) });
      const s = easeOut(seg(t, q.spike[0], q.spike[1]));
      spike.setAttribute("d", s > 0 ? `M${x},${cy(0)} L${x + 0.5},${cy(last10 * s)}` : "");
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
      svg("rect", { x: X0, y: top - 10, width: X1 - X0, height: h + 10, fill: grad(sv, colour, top - 10, top + h, 0.10, 0.0) }, sv);
      svg("line", { x1: X0, x2: X1, y1: top + h, y2: top + h, stroke: col.axis, "stroke-width": 3 }, sv);
      ticks.forEach(([v, s]) => { svg("line", { x1: X0, x2: X1, y1: ys(v), y2: ys(v), stroke: col.ink, "stroke-width": 1.5, "stroke-dasharray": "4 10", opacity: 0.30 }, sv); text(b, "tick", s, { top: ys(v) - 22, left: L - 6 }); });
      css(text(b, "axis", title, { top: top - 64, right: 1080 - R }), { color: colour });
      text(b, "tick", unit, { top: top - 56, left: L });
      const thin = svg("path", { d: "", fill: "none", stroke: colour, "stroke-width": 3, opacity: 0.5 }, sv);
      const bold = glow(sv, { d: "", fill: "none", stroke: colour, "stroke-width": 9, "stroke-linecap": "round", "stroke-linejoin": "round" });
      return { thin, bold, a: ann.map(p => [xs(p[0]), ys(p[1])]), e: eleven.map(p => [xs(p[0]), ys(p[1])]) };
    };
    const pt = panel(720, 250, -0.1, 1.6, S.sun.t, S.sun.t11, col.mark, U.temp, U.unit_t, [[0, "۰"], [1, "۱"]]);
    const ps = panel(1120, 250, 1360.0, 1362.8, S.sun.s, S.sun.s11, col.nat, U.sun, U.unit_s, [[1361, "۱۳۶۱"], [1362, "۱۳۶۲"]]);
    U.years.forEach(([y, s]) => { const e = text(b, "tick", s, { top: 1384 }); e.dataset.cx = xs(y); });
    const arrow = () => svg("path", { d: "", fill: col.ink, opacity: 0 }, sv);
    const aT = arrow(), aS = arrow();
    const dT = svg("circle", { r: 11, fill: col.mark, stroke: "#fff", "stroke-width": 4, opacity: 0 }, sv), dS = svg("circle", { r: 11, fill: col.nat, stroke: "#fff", "stroke-width": 4, opacity: 0 }, sv);   // the lines' ends breathe
    dT.style.filter = `drop-shadow(0 0 14px ${col.mark})`; dS.style.filter = `drop-shadow(0 0 14px ${col.nat})`;
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
    svg("rect", { x: X0, y: ys(300), width: X1 - X0, height: ys(180) - ys(300), rx: 6, fill: col.nat, opacity: 0.10 }, sv);
    svg("line", { x1: X0, x2: X1, y1: Y0, y2: Y0, stroke: col.axis, "stroke-width": 3 }, sv);
    svg("line", { x1: X0, x2: X1 - 40, y1: Y1, y2: Y1, stroke: col.axis, "stroke-width": 3 }, sv);
    const topR = svg("line", { x1: X1 - 40, x2: X1 + 10, y1: Y1, y2: Y1, stroke: col.axis, "stroke-width": 3 }, sv);
    [[200, "۲۰۰"], [300, "۳۰۰"]].forEach(([p, s]) => { svg("line", { x1: X0, x2: X1, y1: ys(p), y2: ys(p), stroke: col.ink, "stroke-width": 1.5, "stroke-dasharray": "4 10", opacity: 0.34 }, sv); text(b, "tick", s, { top: ys(p) - 22, left: L - 4 }); });
    const nat = tag(b, K.nat, col.natf), hum = tag(b, K.hum, col.markf);
    text(b, "axis", K.unit, { top: Y1 - 64, left: L - 4 });
    K.ticks.forEach(([a, s]) => { const e = text(b, "tick", s, { top: Y0 + 10 }); e.dataset.cx = xs(a); });
    text(b, "tick", K.axis, { top: Y0 + 56, left: MID - 60 });
    const old = S.co2.filter(p => p[0] > 100), young = S.co2.filter(p => p[0] <= 100);
    const pts = old.map(p => [xs(p[0]), ys(p[1])]);
    const line = glow(sv, { d: "", fill: "none", stroke: col.nat, "stroke-width": 5, "stroke-linejoin": "round" }, 7, 0.5);
    const sp = glow(sv, { d: "", fill: "none", stroke: col.mark, "stroke-width": 11, "stroke-linecap": "round" }, 14, 0.85);
    const now = young[young.length - 1][1], xNow = X1 + 4;
    const tip = svg("circle", { cx: xNow, cy: ys(now), r: 15, fill: col.mark, stroke: "#fff", "stroke-width": 5, opacity: 0 }, sv); tip.style.filter = `drop-shadow(0 0 16px ${col.mark})`;
    const shards = [0, 1, 2, 3].map(() => svg("path", { d: "M0,0 l14,-6 l-4,14 z", fill: col.ink, opacity: 0 }, sv));
    const counter = css(text(b, "chip", "", { top: 690 }), { fontWeight: "900", fontSize: "60px", lineHeight: "80px" });
    const chip = css(text(b, "mk", K.now, { top: ys(now) - 34 }), { background: col.markf, fontWeight: "900", fontSize: "54px", lineHeight: "70px" });
    f.prep = () => { centreTicks(b); css(chip, { left: xNow - chip.offsetWidth - 34 }); css(nat, { left: MID - nat.offsetWidth / 2 - 60, top: Y1 - 96 }); css(hum, { left: xNow - hum.offsetWidth - 34, top: ys(now) + 60 }); };
    return { ...f, update(t) {
      const d = easeInOut(seg(t, q.draw[0], q.draw[1])), n = Math.max(2, Math.round(d * pts.length));
      line.setAttribute("d", pathOf(pts.slice(0, n)));
      const a = old[Math.min(n, old.length) - 1][0], ka = Math.max(0, Math.round(a / 10000) * 10000);
      const lab = F.chip_ages.co2.find(c => c[0] === ka); counter.textContent = lab && lab[0] > 0 ? lab[1] : ""; counter.style.visibility = counter.textContent ? "visible" : "hidden";
      css(counter, { left: MID - counter.offsetWidth / 2, opacity: (1 - seg(d, 0.93, 0.99)).toFixed(3) });   // gone before the line reaches the last centuries
      const s = easeOut(seg(t, q.spike[0], q.spike[1])), last = old[old.length - 1][1], v = last + (now - last) * s;
      sp.setAttribute("d", s > 0 ? `M${xNow},${ys(last)} L${xNow + 0.5},${ys(v)}` : "");
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
  function block(w, h, d, r) {                       // a cube with rounded edges (an extruded rounded square with a bevel)
    const x = w / 2 - r, z = d / 2 - r, s = new THREE.Shape();
    s.absarc(x, z, r, 0, Math.PI / 2); s.absarc(-x, z, r, Math.PI / 2, Math.PI); s.absarc(-x, -z, r, Math.PI, 1.5 * Math.PI); s.absarc(x, -z, r, 1.5 * Math.PI, 2 * Math.PI);
    const bv = 0.8 * r, g = new THREE.ExtrudeGeometry(s, { depth: h - 2 * bv, bevelEnabled: true, bevelThickness: bv, bevelSize: bv, bevelOffset: -bv, bevelSegments: 3, curveSegments: 5 });
    g.center(); g.rotateX(-Math.PI / 2); return g;
  }
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
    if (LOOK.floor) css(el("div", "abs", b), { left: 90, top: top + 250, width: 900, height: 420, borderRadius: "50%", background: LOOK.floor });   // the floor's light
    const band = css(el("div", "abs", b), { left: 0, top, width: 1080, height });
    const ren = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    ren.setPixelRatio(1); ren.setSize(1080, height); ren.shadowMap.enabled = true; ren.shadowMap.type = THREE.PCFSoftShadowMap;
    ren.outputColorSpace = THREE.SRGBColorSpace; ren.toneMapping = THREE.NeutralToneMapping; ren.toneMappingExposure = 1.0; band.appendChild(ren.domElement);
    const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(26, 1080 / height, 0.1, 100);
    scene.add(new THREE.HemisphereLight(...LOOK.hemi));
    const sun = new THREE.DirectionalLight(0xfff6ea, LOOK.sun); sun.position.set(-7, 13, 8); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -9, right: 9, top: 9, bottom: -9, near: 1, far: 40 }); sun.shadow.radius = 5; sun.shadow.bias = -0.0006;
    scene.add(sun);
    const rim = new THREE.DirectionalLight(0xbfd2ff, LOOK.rim); rim.position.set(8, 6, -9); scene.add(rim);
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ opacity: LOOK.shadow }));
    ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
    const GEO = { 1: block(0.86, 0.86, 0.86, 0.11), 0.5: block(0.41, 0.86, 0.86, 0.09) };
    const cubes = order.flatMap((k, i) => {                    // the split cube is two half cubes: Iran's half and the world's half
      const parts = k === "split" ? [["iran", 0.5, -0.22], ["rest", 0.5, 0.22]] : [[k, 1, 0]];
      return parts.map(([key, w, dx]) => {
        const c3 = new THREE.Color(col[key]);
        const m = new THREE.Mesh(GEO[w], new THREE.MeshStandardMaterial({ color: c3, roughness: key === "rest" ? 0.62 : 0.34, metalness: 0.04, emissive: c3.clone().multiplyScalar(key === "rest" ? 0.06 : 0.14) }));
        m.castShadow = true; m.receiveShadow = true; scene.add(m);
        const c = i % 10, r = Math.floor(i / 10);
        return { m, i, key, base: c3, x: 4.5 - c + dx, z: r - 4.5 };
      });
    });
    const legend = G.map((g, i) => {
      const e = el("div", "leg", b), sw = el("i", null, e); sw.style.background = col[g.key];
      e.appendChild(document.createTextNode(g.label + (g.v !== null ? " " + fa(g.v) + "٪" : "")));
      return css(e, { top: 1300 + Math.floor(i / 2) * 64, right: i % 2 ? 1080 - MID + 20 : 1080 - R });
    });
    text(b, "tick", Wd.who.unit, { top: top - 20, left: L });
    return { ...f, update(t) {
      cam.position.set(1.7 * Math.sin(2 * Math.PI * t / 17), 14.2, 15.6); cam.lookAt(0, 0.2, 0.45);     // a slow drift: the block has depth
      cubes.forEach(o => {
        const t0 = when[o.i], p = seg(t, t0, t0 + 0.55), y = 0.43 + 7.5 * (1 - easeBounce(p));
        const four = o.i < nFour ? 0.35 * bump(seg(t, q.four, q.four + 0.7)) : 0;
        const wave = t > q.iran + 0.8 && o.i < nFour ? 0.22 * Math.max(0, Math.sin(2 * Math.PI * ((t - q.iran) / 2.2 - o.i / 30))) : 0;
        const hop = o.key === "iran" && t > q.iran + 0.6 ? 0.25 * Math.abs(Math.sin(2 * Math.PI * (t - q.iran) / 1.2)) : 0;
        o.m.visible = t >= t0; o.m.position.set(o.x, y + four + wave + hop, o.z);
        o.m.rotation.y = 0.6 * (1 - easeOut(p));
        if (o.key === "iran") o.m.material.emissive.copy(o.base).multiplyScalar(t > q.iran ? 0.34 + 0.22 * Math.sin(2 * Math.PI * t / 1.2) : 0.16);
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
    svg("line", { x1: L, x2: R, y1: Y0, y2: Y0, stroke: col.axis, "stroke-width": 3 }, sv);
    css(text(b, "tick", A.unit.replace(" // ", "\n"), { top: ys(vmax) - 100, left: L }), { whiteSpace: "pre-line", lineHeight: "46px", textAlign: "right" });
    const halo = svg("rect", { x: xs(last) - 6, width: colw + 12, y: Y0, height: 0, rx: 14, fill: col.mark, opacity: 0.55 }, sv); halo.style.filter = "blur(22px)";
    const fillOld = grad(sv, col.bar, ys(1.0), Y0, 0.95, 0.42), fillNew = grad(sv, col.mark, ys(1.3), Y0, 1.0, 0.72);
    const bars = D.map((d, i) => svg("rect", { x: xs(i), width: colw, y: Y0, height: 0, rx: 12, fill: i === last ? fillNew : fillOld }, sv));
    const vals = A.values.map((s, i) => css(text(b, "tick", s, { top: 0 }), { fontWeight: "800", fontSize: i === last ? "50px" : "40px", color: i === last ? col.mark : col.ink }));
    const first = text(b, "tick", A.first, { top: Y0 + 12 }), lastL = text(b, "tick", A.last, { top: Y0 + 12 });
    const paris = svg("line", { x1: L, x2: R, y1: ys(1.5), y2: ys(1.5), stroke: col.gold, "stroke-width": 4, "stroke-dasharray": "14 12" }, sv);
    const parisL = css(text(b, "tick", A.paris, { top: ys(1.5) - 52, left: L }), { fontWeight: "800", color: col.gold });
    const dot = svg("circle", { cx: xs(last) + colw / 2, cy: ys(S.y2024), r: 16, fill: col.mark, stroke: "#fff", "stroke-width": 5, opacity: 0 }, sv); dot.style.filter = `drop-shadow(0 0 16px ${col.mark})`;
    const yr = css(text(b, "tick", A.year, { top: ys(S.y2024) - 64 }), { fontWeight: "800", color: col.mark });
    const tg = css(el("div", "abs mk", b, A.tag), { background: col.markf, fontSize: "42px", lineHeight: "58px", padding: "0 16px 5px", borderRadius: "14px" });
    const at = i => q.bars[0] + (q.bars[1] - q.bars[0]) * i / D.length;
    f.prep = () => { css(first, { left: xs(0) + colw / 2 - first.offsetWidth / 2 }); css(lastL, { left: xs(last) + colw / 2 - lastL.offsetWidth / 2 });
      css(yr, { left: xs(last) - yr.offsetWidth - 10 });
      css(tg, { left: xs(last) - tg.offsetWidth - 20, top: ys(1.5) + 16 }); };   // under the 1.5 line, clear of the columns' values
    return { ...f, update(t) {
      D.forEach((d, i) => {                          // each column rises with its value counting up on top of it
        const p = easeOut(seg(t, at(i), at(i) + 0.6)), v = d[1] * p;
        bars[i].setAttribute("y", ys(v)); bars[i].setAttribute("height", Y0 - ys(v));
        if (i === last) { halo.setAttribute("y", ys(v) - 6); halo.setAttribute("height", Y0 - ys(v) + 6); halo.setAttribute("opacity", (LOOK.glowK * p * (0.5 + 0.12 * Math.sin(2 * Math.PI * t / 1.4))).toFixed(3)); }
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
    css(icon, { left: MID - 130, top: 1080, filter: `drop-shadow(0 0 20px rgba(255,90,78,${(0.75 * LOOK.glowK).toFixed(2)}))` });
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

  // ══ the documentary cut: pictures to the edges of the frame, type on a dark fade, one curve that runs through it ══
  const SCRIM = THEME === "night" ? (CUT === "d" ? "5,9,30" : "5,9,18") : "243,236,225", PENDING = [];
  function scrims(b, top, bottom) {                  // the fades the type stands on: under the headline, under the curve
    const a = top ? css(el("div", "abs", b), { left: 0, top: 0, width: 1080, height: top, background: `linear-gradient(180deg, rgba(${SCRIM},.90) 0, rgba(${SCRIM},.66) 58%, rgba(${SCRIM},0) 100%)` }) : null;
    const c = bottom ? css(el("div", "abs", b), { left: 0, top: bottom, width: 1080, height: 1920 - bottom, background: `linear-gradient(180deg, rgba(${SCRIM},0) 0, rgba(${SCRIM},.84) ${Math.round(100 * 230 / (1920 - bottom))}%, rgba(${SCRIM},.96) 100%)` }) : null;
    return [a, c];
  }
  function photo(b, key) {                           // a photograph to the edges of the frame; the camera moves in slowly
    const P = (F.photos || {})[key];
    if (!P) return { show() {}, credit: "", what: "" };
    const im = el("img", "abs", b); im.src = "/build/" + P.file;
    css(im, { left: 0, top: -(P.lift || 0), width: 1080, height: 1920, objectFit: "cover", transformOrigin: "50% 44%", opacity: "0", filter: P.tone || (THEME === "night" ? "brightness(.97) contrast(1.06) saturate(1.02)" : "none") });
    const lift = P.lift || 0, soft = lift > 0 ? "linear-gradient(0deg, transparent 0, #000 240px)" : lift < 0 ? "linear-gradient(180deg, transparent 0, #000 260px)" : "";
    if (soft) css(im, { maskImage: soft, webkitMaskImage: soft });          // a lifted picture ends in a fade, not an edge
    const veil = css(el("div", "abs", b), { left: 0, top: 0, width: 1080, height: 1920, background: THEME === "night" ? "rgba(8,18,48,.10)" : "transparent", opacity: "0" });
    PENDING.push(im.decode().catch(() => {}));       // every photograph is in memory before the first frame is drawn
    return { credit: P.credit, what: P.what || "",
             show(alpha, u) { const z = lerp(P.zoom[0], P.zoom[1], clamp(u)); im.style.opacity = veil.style.opacity = clamp(alpha).toFixed(3); im.style.transform = `scale(${z.toFixed(4)}) translateY(${(-10 * clamp(u)).toFixed(2)}px)`; } };
  }
  function motes(b) {                                // dust in the light over a photograph: a few soft specks that drift by the clock
    const cv = el("canvas", "abs", b); cv.width = 1080; cv.height = 1920; css(cv, { left: 0, top: 0 });
    const cx2 = cv.getContext("2d");
    let sd = 7331; const rn = () => (sd = (Math.imul(sd, 1664525) + 1013904223) >>> 0) / 4294967296;
    const M = Array.from({ length: 64 }, () => ({ x: rn() * 1080, y: 420 + rn() * 700, r: 1.2 + 3.2 * Math.pow(rn(), 2.2), a: 0.05 + 0.2 * rn(), vx: 6 + 16 * rn(), vy: -(3 + 9 * rn()), ph: rn(), per: 3 + 5 * rn() }));
    return t => { cx2.clearRect(0, 0, 1080, 1920);
      for (const m of M) { const x = (m.x + m.vx * t) % 1080, y = 420 + ((m.y - 420 + m.vy * t) % 700 + 700) % 700;
        cx2.globalAlpha = m.a * (0.55 + 0.45 * Math.sin(2 * Math.PI * (t / m.per + m.ph))); cx2.fillStyle = "#FFE9C4";
        cx2.beginPath(); cx2.arc(x, y, m.r, 0, 6.2832); cx2.fill(); } };
  }
  // the strip: the 20,000-year curve under the picture. z = 0 shows all of it, z = 1 the last 11,000 years, where the
  // corridor is: the band between the coldest and the warmest 200-year mean of the last 10,000 years (film.json "corridor")
  const ST = { x0: 56, x1: 1004, y0: 1380, y1: 1010 };
  const sx = (age, z) => { const a0 = lerp(20500, 11200, z), a1 = lerp(-900, -760, z); return ST.x1 - (age - a1) / (a0 - a1) * (ST.x1 - ST.x0); };
  const sy = (v, z) => { const v0 = lerp(-8.3, -1.75, z), v1 = lerp(2.4, 1.85, z); return ST.y0 - (v - v0) / (v1 - v0) * (ST.y0 - ST.y1); };
  function battlement(x0, x1, y, up) {               // the stepped merlons of Persepolis along an edge of the corridor, from x0 to x1
    const s = up ? -1 : 1, d = [`M${x0.toFixed(1)},${y.toFixed(1)}`];
    for (let x = x0; x < x1; x += 52) d.push(`h9 v${7 * s} h6 v${7 * s} h6 v${7 * s} h10 v${-7 * s} h6 v${-7 * s} h6 v${-7 * s} h9`);
    return d.join(" ");
  }
  const TEMP = S.temp.filter(p => p[0] <= 20100).slice().reverse();          // oldest first
  const HAD = (() => { const h = S.hadcrut, out = []; for (let i = 9; i < h.length; i++) { let m = 0; for (let k = i - 9; k <= i; k++) m += h[k][1]; out.push([1950 - (h[i][0] - 4.5), m / 10]); } return out; })();   // ten-year means, as years before 1950
  function strip(b) {
    const sv = svg("svg", full(), b), K = Wd.strip, id = "c" + (UID++);
    const defs = svg("defs", {}, sv), clip = svg("clipPath", { id }, defs); svg("rect", { x: 0, y: ST.y1 - 140, width: 1080, height: ST.y0 - ST.y1 + 144 }, clip);
    const wall = svg("clipPath", { id: id + "w" }, defs), wallR = svg("rect", { x: 0, y: 0, width: 0, height: 1920 }, wall);   // the corridor is laid from its left end
    const base = svg("line", { x1: ST.x0, x2: ST.x1 + 20, y1: ST.y0, y2: ST.y0, stroke: col.axis, "stroke-width": 3 }, sv);
    const g = svg("g", { "clip-path": `url(#${id})` }, sv), gw = svg("g", { "clip-path": `url(#${id}w)` }, g);
    const band = svg("rect", { fill: grad(sv, col.gold, ST.y1, ST.y0, 0.30, 0.12), opacity: 0 }, gw);
    const edges = [0, 1].map(() => glow(gw, { d: "", fill: "none", stroke: col.gold, "stroke-width": 3.5, "stroke-linejoin": "miter" }, 8, 0.5));
    const area = svg("path", { d: "", fill: grad(sv, col.nat, ST.y1, ST.y0, LOOK.area, 0.0) }, g);
    const line = glow(g, { d: "", fill: "none", stroke: col.nat, "stroke-width": 8, "stroke-linejoin": "round", "stroke-linecap": "round" });
    const red = glow(g, { d: "", fill: "none", stroke: col.mark, "stroke-width": 10, "stroke-linejoin": "round", "stroke-linecap": "round" }, 13, 0.85);
    const lead = svg("circle", { r: 11, fill: "#fff", stroke: col.nat, "stroke-width": 4, opacity: 0 }, g); lead.style.filter = `drop-shadow(0 0 12px ${col.nat})`;
    const tip = svg("circle", { r: 15, fill: col.mark, stroke: "#fff", "stroke-width": 5, opacity: 0 }, g); tip.style.filter = `drop-shadow(0 0 16px ${col.mark})`;
    const dots = (Wd.life.markers || []).map(() => svg("circle", { r: 13, fill: col.gold, stroke: "#fff", "stroke-width": 4, opacity: 0 }, g));
    const ticks = { wide: K.wide.map(([a, t]) => ({ a, e: text(b, "tick", t, { top: ST.y0 + 10 }) })), near: K.near.map(([a, t]) => ({ a, e: text(b, "tick", t, { top: ST.y0 + 10 }) })) };
    const axis = text(b, "tick", K.axis, { top: ST.y0 + 56, left: MID - 60 });
    void axis;
    return { sv, draw(z, age, o = {}) {                // o: band 0..1, red 0..1 (the last 150 years), marks (how many dots), now (seconds, for the breathing)
      const live = TEMP.filter(q => q[0] >= age), last = [age, interp(S.temp, age)];
      const pts = [...live, last].map(q => [sx(q[0], z), sy(q[1], z)]);
      line.setAttribute("d", pathOf(pts)); area.setAttribute("d", under(pts, ST.y0));
      const tipP = pts[pts.length - 1], bb = clamp(o.band || 0);
      lead.setAttribute("cx", tipP[0]); lead.setAttribute("cy", tipP[1]); lead.setAttribute("opacity", o.lead ? "1" : "0");
      const xa = sx(10000, z), xb = 1090, yt = sy(F.corridor[1], z), yb = sy(F.corridor[0], z);   // from 10,000 years ago to the edge of the frame
      band.setAttribute("x", xa); band.setAttribute("y", yt); band.setAttribute("width", xb - xa); band.setAttribute("height", yb - yt);
      band.setAttribute("opacity", bb.toFixed(3)); wallR.setAttribute("x", xa - 4); wallR.setAttribute("width", Math.max(0, (xb - xa + 8) * bb));
      edges.forEach((e, k) => { e.setAttribute("d", battlement(xa, xb, k ? yb : yt, !k)); e.setAttribute("opacity", (0.95 * (bb > 0 ? 1 : 0)).toFixed(3)); });
      base.setAttribute("opacity", (1 - z).toFixed(3));
      const r = clamp(o.red || 0), n = Math.max(2, Math.round(r * HAD.length)), rp = HAD.slice(0, n).map(q => [sx(q[0], z), sy(q[1], z)]);
      red.setAttribute("d", r > 0 ? pathOf(rp) : ""); const top = rp[rp.length - 1];
      tip.setAttribute("cx", top[0]); tip.setAttribute("cy", top[1]); tip.setAttribute("opacity", r > 0.02 ? "1" : "0");
      tip.setAttribute("r", (15 * (1 + 0.15 * Math.sin(2 * Math.PI * (o.now || 0) / 1.1))).toFixed(2));
      dots.forEach((d, k) => { const m = Wd.life.markers[k], on = k < (o.marks || 0), act = k === (o.marks || 0) - 1 && !o.red;
        d.setAttribute("cx", sx(m.age, z)); d.setAttribute("cy", sy(interp(S.temp, m.age), z)); d.setAttribute("opacity", on ? "1" : "0");
        d.setAttribute("r", (13 * (act ? 1.15 + 0.2 * Math.sin(2 * Math.PI * (o.now || 0) / 1.1) : 1)).toFixed(2)); });
      const wide = clamp(1 - 5 * z), near = clamp(2.2 * z - 1.2);            // the far ticks are gone before the frame closes in past them
      ticks.wide.forEach(q => css(q.e, { left: sx(q.a, z) - q.e.offsetWidth / 2, opacity: wide.toFixed(3) }));
      ticks.near.forEach(q => css(q.e, { left: sx(q.a, z) - q.e.offsetWidth / 2, opacity: near.toFixed(3) }));
      return { tip: top, head: tipP, yt, yb, xb };
    } };
  }
  function counter(b, top) { return css(chipAt(b, ""), { top, fontWeight: "800", fontSize: "50px", lineHeight: "66px" }); }
  function years(chip, ka, centre) {                 // the chip of the age, in steps of 500 years
    const a = Math.round(ka * 2) / 2 * 1000, lab = F.chip_ages.melt.find(c => c[0] === a);
    chip.textContent = lab ? lab[1] : ""; css(chip, { left: centre - chip.offsetWidth / 2 });
  }

  // ── d1: the Persian Gulf, dry land 20,000 years ago, and the sea coming in ──
  function gulf(sc) {
    const f = frame(sc), b = f.body, q = F.cues.gulf, G = Wd.gulf, g = globe(b, 0, 1920);
    scrims(b, 640, 1330);
    const chip = counter(b, 700), iran = dotted(b, G.iran, "", col.iran);   // the headline names the Gulf: no label on it
    return { ...f, update(t) {
      const ka = lerp(q.age[2], q.age[3], easeInOut(seg(t, q.age[0], q.age[1])));
      g.draw(keyed(F.view.gulf, t), ka, ka, 0);
      years(chip, ka, MID); show(chip, seg(t, q.age[0] + 0.05, q.age[0] + 0.3));   // the headline has the age at frame 0; the chip comes in when it starts to count
      pin(iran, g, F.places.iran[0], F.places.iran[1], 22, -30); ring(iran.dot, t + 0.6);
    } };
  }

  // ── d2: the thaw from space, the curve drawing under it ──
  function thaw(sc) {
    const f = frame(sc), b = f.body, q = F.cues.thaw, g = globe(b, 0, 1920);
    scrims(b, 620, 880);
    const st = strip(b), chip = counter(b, 912);
    f.prep = () => st.draw(0, 20100);
    return { ...f, update(t) {
      const ka = lerp(q.age[2], q.age[3], easeInOut(seg(t, q.age[0], q.age[1])));
      g.draw(keyed(F.view.thaw, t), ka, ka, 0);
      years(chip, ka, MID);
      st.draw(0, Math.min(20100, ka * 1000), { lead: t < q.age[1] + 0.2, now: t });
    } };
  }

  // ── d3: the corridor of life: the last 11,000 years, a photograph behind each marker ──
  function title(b, s) {                             // a picture's name, large, and the line under it
    const big = css(el("div", "abs ptitle", b, s), { top: 792 }), sub = css(el("div", "abs psub", b, ""), { top: 912 });
    return { big, sub, show(a, lift) { [big, sub].forEach(e => css(e, { opacity: clamp(a).toFixed(3), transform: `translateY(${(18 * (1 - clamp(lift))).toFixed(2)}px)` })); } };
  }
  function life(sc) {
    const f = frame(sc), b = f.body, q = F.cues.life, M = Wd.life.markers, pics = M.map(m => photo(b, m.photo));
    const dust = motes(b);
    const [shade] = scrims(b, 720, 760);
    const credit = el("div", "abs credit", b, ""), what = el("div", "abs what", b, "");
    const st = strip(b), names = M.map(m => title(b, m.label));
    f.prep = () => { st.draw(1, 10000); names.forEach((n, k) => { n.sub.textContent = M[k].ago; [n.big, n.sub].forEach(e => css(e, { left: MID - e.offsetWidth / 2 })); }); };
    const start = k => k === 0 ? 0.0 : q.marks[k] - q.fade[0], full = k => k === 0 ? 0.7 : q.marks[k] - q.fade[1];
    return { ...f, update(t) {
      const z = easeInOut(seg(t, q.zoom[0], q.zoom[1])), age = keyed(q.run, t)[0];
      let shown = 0, cur = 0;
      M.forEach((m, k) => { if (t >= q.marks[k]) shown = k + 1; if (t >= start(k)) cur = k; });
      pics.forEach((pc, k) => { const end = k + 1 < M.length ? full(k + 1) : sc.length; pc.show(seg(t, start(k), full(k)), seg(t, start(k), end)); });
      credit.textContent = pics[cur].credit || ""; what.textContent = pics[cur].what || "";
      const seen = seg(t, sc.turn - 0.1, sc.turn + 0.4); show(credit, 0.62 * seen); show(what, 0.8 * seen);   // with the headline away: the picture's own lines
      names.forEach((n, k) => { const out = k + 1 < M.length ? 1 - seg(t, start(k + 1), start(k + 1) + 0.4) : 1; n.show(easeOut(seg(t, q.marks[k] - 0.25, q.marks[k] + 0.25)) * out, easeOut(seg(t, q.marks[k] - 0.25, q.marks[k] + 0.35))); });
      st.draw(z, age, { band: z, marks: shown, lead: true, now: t }); dust(t);
      const up = Math.max(1 - seg(t, sc.turn - 0.4, sc.turn + 0.2), seg(t, sc.late - 0.2, sc.late + 0.4));   // a headline is on: its fade is too
      shade.style.opacity = (0.14 + 0.86 * up).toFixed(3);
    } };
  }

  // ── d4: the last 150 years leave the corridor ──
  function exit(sc) {
    const f = frame(sc), b = f.body, q = F.cues.exit, pc = photo(b, "today"), dust = motes(b);
    scrims(b, 720, 760);
    const credit = el("div", "abs credit", b, pc.credit || ""); el("div", "abs what", b, pc.what || "");
    const st = strip(b), tg = css(tag(b, Wd.exit.tag, col.markf), { fontSize: "58px", lineHeight: "76px", fontWeight: "900" }), flash = css(el("div", "abs", b), { left: 0, top: 0, width: 1080, height: 1920, background: `radial-gradient(900px 700px at 80% 62%, rgba(255,70,50,.34), rgba(255,70,50,0) 70%)`, opacity: "0" });
    const shards = [0, 1, 2, 3, 4].map(() => svg("path", { d: "M0,0 l16,-6 l-5,15 z", fill: col.gold, opacity: 0 }, st.sv));
    f.prep = () => st.draw(1, 100);
    return { ...f, update(t) {
      pc.show(seg(t, 0, 0.6), seg(t, 0, sc.length)); dust(t + 20);
      const r = easeInOut(seg(t, q.spike[0], q.spike[1])), marks = Wd.life.markers.length;
      const at = st.draw(1, 100, { band: 1, red: r, marks, now: t, broke: r > 0.5 });
      const out = at.tip[1] < at.yt, p = seg(t, q.spike[0] + 0.5 * (q.spike[1] - q.spike[0]), q.spike[1] + 0.9);
      shards.forEach((e, k) => { e.setAttribute("opacity", out ? (1 - p).toFixed(3) : "0"); e.setAttribute("transform", `translate(${at.tip[0] - 26 + (k - 2) * 16 + (k - 2) * 62 * p},${at.yt - 4 - 110 * p + 90 * p * p * (k % 2 ? 1 : 0.45)}) rotate(${(k * 83 + 320 * p).toFixed(1)})`); });
      flash.style.opacity = (0.9 * r * (0.75 + 0.25 * Math.sin(2 * Math.PI * t / 1.6))).toFixed(3);
      const g = easeOut(seg(t, q.tag, q.tag + 0.45)), br = t > q.tag + 0.6 ? 0.03 * Math.sin(2 * Math.PI * (t - q.tag) / 1.3) : 0;
      css(tg, { left: at.tip[0] - tg.offsetWidth - 30, top: at.tip[1] - 34, opacity: g.toFixed(3), scale: (0.85 + 0.15 * g + 0.07 * bump(seg(t, q.tag, q.tag + 0.6)) + br).toFixed(3) });
    } };
  }

  // ── d6: send it on, over Persepolis ──
  function send(sc) {
    const f = frame(sc), b = f.body, q = F.cues.send, pc = photo(b, "end"), dust = motes(b);
    scrims(b, 900, 1100);
    const credit = el("div", "abs credit", b, pc.credit || ""); css(credit, { top: 1452 }); css(el("div", "abs what", b, pc.what || ""), { top: 1414 });
    const icon = svg("svg", { width: 520, height: 240, viewBox: "-130 -60 260 120" }, b);
    css(icon, { left: MID - 260, top: 1150, filter: `drop-shadow(0 0 20px rgba(255,90,78,${(0.75 * LOOK.glowK).toFixed(2)}))` });
    const plane = svg("g", { fill: "none", stroke: "#fff", "stroke-width": 8, "stroke-linecap": "round", "stroke-linejoin": "round" }, icon);
    svg("path", { d: "M-108,-34 L-28,-40 L-72,38 L-80,2 Z" }, plane); svg("path", { d: "M-80,2 L-28,-40" }, plane);
    const ic = svg("g", { fill: "none", stroke: col.mark, "stroke-width": 8, "stroke-linecap": "round", "stroke-linejoin": "round" }, icon);
    svg("path", { d: "M40,-6 v-12 a9,9 0 0 1 9,-9 h46" }, ic); svg("path", { d: "M86,-38 l11,11 l-11,11" }, ic);
    svg("path", { d: "M104,8 v12 a9,9 0 0 1 -9,9 h-46" }, ic); svg("path", { d: "M58,40 l-11,-11 l11,-11" }, ic);
    return { ...f, update(t) {
      pc.show(seg(t, 0, 0.6), seg(t, 0, sc.length)); dust(t + 40);
      const a = easeOut(seg(t, q.icon, q.icon + 0.5)), fly = 10 * Math.sin(2 * Math.PI * Math.max(0, t - q.icon) / 1.6);
      css(icon, { opacity: a.toFixed(3), scale: (0.8 + 0.2 * a).toFixed(3) });
      plane.setAttribute("transform", `translate(${(fly * 0.8).toFixed(2)},${(-fly).toFixed(2)})`);
      ic.setAttribute("transform", `rotate(${(8 * Math.sin(2 * Math.PI * Math.max(0, t - q.icon) / 2.2)).toFixed(2)} 72 1)`);
    } };
  }

  const builders = { hook, melt, speed, sun, co2, who, accel, call, gulf, thaw, life, exit, send };
  const scenes = C.scenes.map(sc => Object.assign(builders[sc.key](sc), { sc }));
  await document.fonts.ready;
  await Promise.all(PENDING);
  scenes.forEach(s => {
    s.root.style.display = "block";
    s.heads.forEach(h => { fit(h.lines, W, 54); fit(h.smalls, W, 38); });
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
    const sc = C.scenes[i], dt = t - sc.start, s = scenes[i];
    scenes.forEach((x, k) => { x.root.style.display = k === i ? "block" : "none"; });
    drawSky(t, STARRY[sc.key] ? 1 : 0.42);
    s.update(dt, t);
    lit(sc.key, dt);
    const enter = i === 0 ? 1 : easeOut(seg(dt, 0, 0.35));
    css(s.body, { opacity: (0.25 + 0.75 * enter).toFixed(3), transform: `translateY(${(14 * (1 - enter)).toFixed(2)}px)` });
    const turn = s.heads.length > 1 ? sc.turn : null, ph = turn !== null && dt >= turn ? 1 : 0;
    const from = sc.late === undefined ? turn : sc.late, lt = ph ? dt - from : dt;      // a scene may leave its picture alone between its two headlines
    s.heads.forEach((h, k) => { h.head.style.display = k === ph && !(ph && dt < from) ? "block" : "none"; });
    s.heads[0].head.style.opacity = !ph && sc.late !== undefined ? (1 - seg(dt, turn - 0.4, turn)).toFixed(3) : "1";
    const late = sc.small_at === undefined ? null : sc.small_at;           // a small line with its own moment comes in then, from nothing
    s.heads[ph].smalls.forEach((ln, k) => { if (late === null) return; const at = Array.isArray(late) ? late[Math.min(k, late.length - 1)] : late + 0.12 * k, p = easeOut(seg(dt, at, at + 0.4)); css(ln, { opacity: p.toFixed(3), transform: `translateY(${(18 * (1 - p)).toFixed(2)}px)` }); });
    [...s.heads[ph].lines, ...(late === null ? s.heads[ph].smalls : [])].forEach((ln, k) => {   // the headline arrives line by line (the first scene stands from frame 0)
      const p = i === 0 && !ph ? 1 : easeOut(seg(lt, 0.08 * k, 0.30 + 0.08 * k));
      css(ln, { opacity: (0.15 + 0.85 * p).toFixed(3), transform: `translateY(${(22 * (1 - p)).toFixed(2)}px)` });
    });
    segs.forEach((x, k) => { x.style.width = (k < i ? 100 : k > i ? 0 : 100 * dt / sc.length).toFixed(3) + "%"; });
    return i;
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
