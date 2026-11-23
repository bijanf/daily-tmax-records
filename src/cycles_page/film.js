/* «زمین همیشه گرم و سرد شده؟» (cycles_fa): window.renderAt(t) draws the frame of time t (seconds) from
   /build/film.json, which src/cycles.py writes (every string, every number, the series, the clock and the cues).
   Nothing is typed here. The globe is NASA's Blue Marble with the ice-age map of src/cycles.py laid on it pixel by
   pixel: a cell of today's sea is dry land at an age older than its flood age (red channel, hundreds of years), a cell
   is under ice at an age older than its melt age (green), shaded by the relief of 21,000 years ago (blue). Every frame
   is a pure function of t (several workers render the frames out of order). */
"use strict";
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
  el("div", "pill", stage, Wd.pill);

  // ── the pictures: the Blue Marble and the ice-age map, on one grid ──
  async function pixels(file) {
    const im = new Image(); im.src = "/build/" + file; await im.decode();
    const c = document.createElement("canvas"); c.width = im.naturalWidth; c.height = im.naturalHeight;
    const x = c.getContext("2d", { willReadFrequently: true }); x.drawImage(im, 0, 0);
    return { w: c.width, h: c.height, d: x.getImageData(0, 0, c.width, c.height).data };
  }
  const tex = await pixels(F.maps.world), age = await pixels(F.maps.age), PX = F.maps.pxd, LAT1 = F.maps.lat1;
  const ICE = [238, 243, 248], SHELF = hex(col.shelf);
  function hex(h) { return [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)); }

  // the globe in a band of the stage: centre latitude and longitude, zoom, disc centre (x, y) and radius (px)
  function globe(parent, top, height) {
    const band = css(el("div", "band", parent), { top, height });
    const cv = css(el("canvas", null, band), { position: "absolute", left: 0, top: 0, width: 1080, height }); cv.width = 1080; cv.height = height;
    const ctx = cv.getContext("2d"), img = ctx.createImageData(1080, height), out = img.data;
    let V = null;
    function project(lat, lon) {                     // stage x, y of a place; visible or not
      const [la0, lo0, z, cx, cy, Rg] = V, Rs = Rg * z, p = lat * Math.PI / 180, l = (lon - lo0) * Math.PI / 180, p0 = la0 * Math.PI / 180;
      const x = Math.cos(p) * Math.sin(l), y = Math.cos(p0) * Math.sin(p) - Math.sin(p0) * Math.cos(p) * Math.cos(l), zz = Math.sin(p0) * Math.sin(p) + Math.cos(p0) * Math.cos(p) * Math.cos(l);
      return { x: cx + Rs * x, y: cy - Rs * y, on: zz > 0.05 };
    }
    function draw(view, ageAt) {                     // ageAt(x) = the age (thousands of years) shown at stage column x
      V = view;
      const [la0, lo0, z, cx, cy, Rg] = view, Rs = Rg * z, p0 = la0 * Math.PI / 180, s0 = Math.sin(p0), c0 = Math.cos(p0);
      const tw = tex.w, th = tex.h, td = tex.d, ad = age.d, glow = 0.07;
      out.fill(0);
      const ages = new Float32Array(1080); for (let x = 0; x < 1080; x++) ages[x] = 10 * ageAt(x);
      for (let y = 0; y < height; y++) {
        const ny = (cy - (top + y + 0.5)) / Rs;
        for (let x = 0; x < 1080; x++) {
          const nx = (x + 0.5 - cx) / Rs, r2 = nx * nx + ny * ny, o = (y * 1080 + x) * 4;
          if (r2 >= 1) {                             // the air around the Earth: a soft blue glow
            const r = Math.sqrt(r2) - 1; if (r < glow) { const a = Math.pow(1 - r / glow, 2); out[o] = 110; out[o + 1] = 160; out[o + 2] = 235; out[o + 3] = Math.round(150 * a); }
            continue;
          }
          const nz = Math.sqrt(1 - r2), lat = Math.asin(clamp(ny * c0 + nz * s0, -1, 1)) * 180 / Math.PI;
          let lon = lo0 + Math.atan2(nx, nz * c0 - ny * s0) * 180 / Math.PI; lon = ((lon + 180) % 360 + 360) % 360 - 180;
          const u = (lon + 180) * PX - 0.5, v = clamp((LAT1 - lat) * PX - 0.5, 0, th - 1.001);
          const u0 = Math.floor(u), v0 = Math.floor(v), fu = u - u0, fv = v - v0, ua = (u0 + tw) % tw, ub = (u0 + 1) % tw;
          const q = [(v0 * tw + ua) * 4, (v0 * tw + ub) * 4, ((v0 + 1) * tw + ua) * 4, ((v0 + 1) * tw + ub) * 4];
          const wq = [(1 - fu) * (1 - fv), fu * (1 - fv), (1 - fu) * fv, fu * fv];
          let r = 0, g = 0, b = 0, land = 0, ice = 0, sh = 0; const A = ages[x];
          for (let k = 0; k < 4; k++) {
            const i = q[k], w = wq[k];
            r += td[i] * w; g += td[i + 1] * w; b += td[i + 2] * w; sh += ad[i + 2] * w;
            if (ad[i] > 0 && ad[i] < A) land += w;
            if (ad[i + 1] > 0 && ad[i + 1] < A) ice += w;
          }
          const s = sh / 255;
          if (land > 0) { const f = 0.86 + 0.5 * (s - 0.62); r = lerp(r, SHELF[0] * f, land); g = lerp(g, SHELF[1] * f, land); b = lerp(b, SHELF[2] * f, land); }
          if (ice > 0) { const f = 0.9 + 0.55 * (s - 0.62); r = lerp(r, ICE[0] * f, ice); g = lerp(g, ICE[1] * f, ice); b = lerp(b, ICE[2] * f, ice); }
          const light = 1.1 * clamp(0.62 + 0.38 * (-0.45 * nx + 0.5 * ny + 0.74 * nz), 0, 1.1) * (0.74 + 0.26 * Math.sqrt(nz));
          const edge = clamp((1 - Math.sqrt(r2)) * Rs, 0, 1);
          out[o] = r * light; out[o + 1] = g * light; out[o + 2] = b * light; out[o + 3] = Math.round(255 * edge);
        }
      }
      ctx.putImageData(img, 0, 0);
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
      g.draw(view, x => (x < wx ? 21 : 0));
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
    const card = css(el("div", "abs", b), { left: 70, top: 700, width: 200, height: 690, borderRadius: "26px", background: "rgba(251,247,240,.93)", boxShadow: "0 14px 30px rgba(46,33,24,.25)" });
    css(el("div", null, card, M.thermo), { position: "absolute", left: 10, right: 10, top: 12, textAlign: "center", fontWeight: "800", fontSize: "32px", lineHeight: "40px", whiteSpace: "normal" });
    const T0 = 1270, T1 = 820, tY = v => T0 + (v + 8) / 9 * (T1 - T0);    // stage y of a temperature (card at top 700)
    const tube = css(el("div", "abs", b), { left: 140, top: T1 - 20, width: 40, height: T0 - T1 + 40, borderRadius: "20px", background: col.land, boxShadow: "0 0 0 4px " + col.ink });
    const bulb = css(el("div", "abs", b), { left: 124, top: T0 + 6, width: 72, height: 72, borderRadius: "50%", background: col.mark, boxShadow: "0 0 0 4px " + col.ink });
    const merc = css(el("div", "abs", b), { left: 150, width: 20, borderRadius: "10px", background: col.mark });
    const br = svg("svg", full(), b), brl = svg("path", { fill: "none", stroke: col.ink, "stroke-width": 5, "stroke-linecap": "round" }, br);
    const gap = css(el("div", "abs big", b, M.gap), { left: 196, fontSize: "44px", lineHeight: "54px", color: col.mark, background: "var(--card)", borderRadius: "12px", padding: "0 10px 3px" });
    const a20 = interp(S.temp, 20100), a10 = interp(S.temp, 9900);
    void bulb; void tube;
    return { ...f, update(t) {
      const ka = lerp(q.age[2], q.age[3], easeInOut(seg(t, q.age[0], q.age[1])));
      const view = keyed(F.view.melt, t);
      g.draw(view, () => ka);
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

  // ── 3 and 4: the curve of 20,000 years (Osman et al. 2021), then the last 150 years (HadCRUT5) ──
  const CH = { x0: L + 40, x1: R - 10, y0: 1360, y1: 760, v0: -8, v1: 1.8 };
  const cx = a => CH.x1 - (a / 20000) * (CH.x1 - CH.x0), cy = v => CH.y0 + (v - CH.v0) / (CH.v1 - CH.v0) * (CH.y1 - CH.y0);
  function curve(f, b, opts = {}) {
    const C3 = Wd.calm, o = {};
    const sv = svg("svg", full(), b);
    svg("line", { x1: CH.x0, x2: CH.x1, y1: CH.y0, y2: CH.y0, stroke: col.ink, "stroke-width": 4 }, sv);
    svg("line", { x1: CH.x0, x2: CH.x1, y1: cy(0), y2: cy(0), stroke: col.ink, "stroke-width": 2, "stroke-dasharray": "8 10", opacity: 0.55 }, sv);
    o.holo = svg("rect", { x: cx(10000), y: CH.y1 - 10, width: cx(0) - cx(10000), height: CH.y0 - CH.y1 + 10, fill: col.gold, opacity: 0 }, sv);
    const band = S.band.filter(p => p[0] <= 20100);
    o.band = svg("path", { d: pathOf([...band.map(p => [cx(p[0]), cy(p[2])]), ...band.slice().reverse().map(p => [cx(p[0]), cy(p[1])])]) + "Z", fill: col.mark, opacity: 0.14 }, sv);
    o.pts = S.temp.filter(p => p[0] <= 20100).slice().reverse().map(p => [cx(p[0]), cy(p[1])]);   // old to young
    o.line = svg("path", { d: "", fill: "none", stroke: col.mark, "stroke-width": 8, "stroke-linejoin": "round", "stroke-linecap": "round" }, sv);
    C3.ticks.forEach(([a, s]) => { const e = text(b, "tick", s, { top: CH.y0 + 10 }); e.style.left = (cx(a) - 0) + "px"; e.dataset.cx = cx(a); });
    text(b, "tick", C3.axis, { top: CH.y0 + 56, left: MID - 60 });
    C3.yticks.forEach(([v, s]) => {                 // 0 below its line on the left (the curve is low there), -6 on the right (the curve is high there)
      if (v < 0 && opts.noCold) return;
      if (v < 0) svg("line", { x1: CH.x0, x2: CH.x1, y1: cy(v), y2: cy(v), stroke: col.ink, "stroke-width": 1.5, "stroke-dasharray": "4 10", opacity: 0.4 }, sv);
      text(b, "tick", s, v < 0 ? { top: cy(v) - 50, right: 1080 - CH.x1 } : { top: cy(v) + 4, left: CH.x0 + 6 });
    });
    text(b, "axis", C3.y, { top: CH.y1 - 120, left: CH.x0 });
    o.sv = sv;
    return o;
  }
  function centreTicks(b) { b.querySelectorAll(".tick").forEach(e => { if (e.dataset.cx) e.style.left = (parseFloat(e.dataset.cx) - e.offsetWidth / 2) + "px"; }); }
  function calm(sc) {
    const f = frame(sc), b = f.body, q = F.cues.calm, o = curve(f, b);
    const marks = Wd.calm.markers.map((m, i) => {
      const x = cx(m.age), y = cy(interp(S.temp, m.age));
      const dot = svg("circle", { cx: x, cy: y, r: 13, fill: col.gold, stroke: "#fff", "stroke-width": 4 }, o.sv);
      const stem = svg("line", { x1: x, x2: x, y1: y - 16, y2: y - 70 - 62 * i, stroke: col.ink, "stroke-width": 3 }, o.sv);
      const lab = text(b, "mk", m.label, { top: y - 128 - 62 * i });
      return { dot, stem, lab, x };
    });
    const last = o.pts[o.pts.length - 1], now = svg("circle", { cx: last[0], cy: last[1], r: 14, fill: col.mark, stroke: "#fff", "stroke-width": 5, opacity: 0 }, o.sv);
    f.prep = () => { centreTicks(b); marks.forEach(m => { css(m.lab, { left: clamp(m.x - m.lab.offsetWidth / 2, L, R - m.lab.offsetWidth) }); }); };
    return { ...f, update(t) {
      now.setAttribute("opacity", t > q.draw[1] ? "1" : "0"); now.setAttribute("r", (14 * (1 + 0.16 * Math.sin(2 * Math.PI * t / 1.2))).toFixed(2));
      marks.forEach((m, i) => m.dot.setAttribute("r", (13 * (1 + 0.1 * Math.sin(2 * Math.PI * (t / 1.5 - i / 3)))).toFixed(2)));
      const p = easeInOut(seg(t, q.draw[0], q.draw[1])), n = Math.max(2, Math.round(p * o.pts.length));
      o.line.setAttribute("d", pathOf(o.pts.slice(0, n))); o.band.style.opacity = (0.14 * p).toFixed(3);
      o.holo.setAttribute("opacity", (0.16 * easeOut(seg(t, q.band, q.band + 0.6))).toFixed(3));
      marks.forEach((m, i) => { const s = easeOut(seg(t, q.markers[i], q.markers[i] + 0.45)); [m.dot, m.stem].forEach(e => e.setAttribute("opacity", s.toFixed(3))); css(m.lab, { opacity: s.toFixed(3), scale: (0.8 + 0.2 * s + 0.06 * bump(seg(t, q.markers[i], q.markers[i] + 0.5))).toFixed(3) }); });
    } };
  }
  function jump(sc) {
    const f = frame(sc), b = f.body, q = F.cues.jump, J = Wd.jump, o = curve(f, b, { noCold: true });
    o.line.setAttribute("d", pathOf(o.pts)); o.holo.setAttribute("opacity", "0.16");
    const hc = S.hadcrut, last10 = hc.slice(-10).reduce((s, p) => s + p[1], 0) / 10;
    const x = cx(0) + 4, spike = svg("path", { d: "", fill: "none", stroke: col.mark, "stroke-width": 12, "stroke-linecap": "round" }, o.sv);
    const top = svg("circle", { cx: x, cy: cy(last10), r: 16, fill: col.mark, stroke: "#fff", "stroke-width": 5, opacity: 0 }, o.sv);
    const chip = text(b, "chip gold", J.chip, { top: cy(last10) - 30 });
    // the inset: every year 1850-2025 (HadCRUT5) on its own scale
    const I = { x0: 590, x1: 870, y0: 1270, y1: 1080 }, iy = v => I.y0 + (v + 0.4) / 2.0 * (I.y1 - I.y0), ix = yr => I.x0 + (yr - 1850) / 175 * (I.x1 - I.x0);
    const inset = css(el("div", "abs", b), { left: I.x0 - 30, top: I.y1 - 70, width: I.x1 - I.x0 + 60, height: I.y0 - I.y1 + 130, borderRadius: "22px", background: "rgba(251,247,240,.96)", boxShadow: "0 14px 30px rgba(46,33,24,.25)" });
    const isv = svg("svg", full(), b), ipts = hc.map(p => [ix(p[0]), iy(p[1])]);
    const iline = svg("path", { d: "", fill: "none", stroke: col.mark, "stroke-width": 5, "stroke-linejoin": "round" }, isv);
    svg("line", { x1: I.x0, x2: I.x1, y1: iy(0), y2: iy(0), stroke: col.ink, "stroke-width": 2, "stroke-dasharray": "6 8", opacity: 0.5 }, isv);
    const ilab = text(b, "tick", J.inset, { top: I.y1 - 62 });
    const link = svg("path", { d: `M${x - 10},${cy(last10)} C ${x - 200},${cy(last10) + 60} ${I.x1 + 160},${I.y1 - 40} ${I.x1 + 30},${I.y1 + 20}`, fill: "none", stroke: col.ink, "stroke-width": 3, "stroke-dasharray": "8 8", opacity: 0 }, o.sv);
    f.prep = () => { centreTicks(b); css(chip, { left: x - chip.offsetWidth - 30 }); css(ilab, { left: (I.x0 + I.x1) / 2 - ilab.offsetWidth / 2 }); };
    return { ...f, update(t) {
      const p = easeOut(seg(t, q.spike[0], q.spike[1])), v = last10 * p;
      spike.setAttribute("d", `M${x},${cy(0)} L${x},${cy(v)}`);
      top.setAttribute("opacity", (p > 0.98 ? 1 : 0).toString());
      const c = easeOut(seg(t, q.chip, q.chip + 0.4)); css(chip, { opacity: c.toFixed(3), scale: (0.85 + 0.15 * c + 0.06 * bump(seg(t, q.chip, q.chip + 0.6))).toFixed(3) });
      const ip = easeOut(seg(t, q.inset[0], q.inset[0] + 0.4)), d = seg(t, q.inset[0] + 0.2, q.inset[1]);
      [inset, isv, ilab].forEach(e => show(e, ip)); link.setAttribute("opacity", (0.6 * ip).toFixed(3));
      iline.setAttribute("d", pathOf(ipts.slice(0, Math.max(2, Math.round(d * ipts.length)))));
      const pulse = t > q.spike[1] ? 1 + 0.16 * Math.sin(2 * Math.PI * (t - q.spike[1]) / 1.2) : 1;
      css(chip, { translate: `0 ${(5 * Math.sin(2 * Math.PI * t / 1.6)).toFixed(2)}px` });
      top.setAttribute("r", (16 * pulse).toFixed(2));
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
    const ps = panel(1120, 250, 1360.0, 1362.8, S.sun.s, S.sun.s11, col.gold, U.sun, U.unit_s, [[1361, "۱۳۶۱"], [1362, "۱۳۶۲"]]);
    U.years.forEach(([y, s]) => { const e = text(b, "tick", s, { top: 1384 }); e.dataset.cx = xs(y); });
    const mean = text(b, "tick", U.mean, { top: 1430, left: X0 });
    const arrow = (p, dy) => svg("path", { d: "", fill: col.ink, opacity: 0 }, sv);
    const aT = arrow(pt), aS = arrow(ps);
    f.prep = () => centreTicks(b);
    void mean;
    return { ...f, update(t) {
      [[pt, q.temp], [ps, q.sun]].forEach(([p, w]) => { const d = easeInOut(seg(t, w[0], w[1])); p.thin.setAttribute("d", pathOf(p.a.slice(0, Math.max(2, Math.round(d * p.a.length))))); p.bold.setAttribute("d", pathOf(p.e.slice(0, Math.max(2, Math.round(d * p.e.length))))); });
      const v = easeOut(seg(t, q.verdict, q.verdict + 0.4));
      const tipT = pt.e[pt.e.length - 1], tipS = ps.e[ps.e.length - 1];
      const bob = 7 * Math.sin(2 * Math.PI * t / 1.2);
      aT.setAttribute("d", `M${tipT[0] + 4},${tipT[1] - 46 - bob} l-22,34 h44 z`); aT.setAttribute("fill", col.mark); aT.setAttribute("opacity", v.toFixed(3));
      aS.setAttribute("d", `M${tipS[0] + 44 + bob},${tipS[1]} l-34,-22 v44 z`); aS.setAttribute("fill", col.gold); aS.setAttribute("opacity", v.toFixed(3));
    } };
  }

  // ── 6: carbon dioxide over 800,000 years; today breaks through the top of the chart ──
  function co2(sc) {
    const f = frame(sc), b = f.body, q = F.cues.co2, K = Wd.co2, sv = svg("svg", full(), b);
    const X0 = L + 120, X1 = R - 30, Y0 = 1400, Y1 = 940, P0 = 150, P1 = 320;
    const xs = a => X1 - Math.max(a, 0) / 805000 * (X1 - X0), ys = p => Y0 - (p - P0) / (P1 - P0) * (Y0 - Y1);
    svg("rect", { x: X0, y: ys(300), width: X1 - X0, height: ys(180) - ys(300), fill: col.gold, opacity: 0.13 }, sv);
    svg("line", { x1: X0, x2: X1, y1: Y0, y2: Y0, stroke: col.ink, "stroke-width": 4 }, sv);
    const topL = svg("line", { x1: X0, x2: X1 - 40, y1: Y1, y2: Y1, stroke: col.ink, "stroke-width": 4 }, sv);
    const topR = svg("line", { x1: X1 - 40, x2: X1 + 10, y1: Y1, y2: Y1, stroke: col.ink, "stroke-width": 4 }, sv);
    [[200, "۲۰۰"], [300, "۳۰۰"]].forEach(([p, s]) => { svg("line", { x1: X0, x2: X1, y1: ys(p), y2: ys(p), stroke: col.ink, "stroke-width": 1.5, "stroke-dasharray": "4 10", opacity: 0.45 }, sv); text(b, "tick", s, { top: ys(p) - 22, left: L - 4 }); });
    text(b, "tick", K.band, { top: ys(300) + 6, left: X0 + 12 });
    text(b, "axis", K.unit, { top: Y1 - 76, right: 1080 - R });
    K.ticks.forEach(([a, s]) => { const e = text(b, "tick", s, { top: Y0 + 10 }); e.dataset.cx = xs(a); });
    text(b, "tick", K.axis, { top: Y0 + 56, left: MID - 60 });
    const old = S.co2.filter(p => p[0] > 100), young = S.co2.filter(p => p[0] <= 100);
    const pts = old.map(p => [xs(p[0]), ys(p[1])]);
    const line = svg("path", { d: "", fill: "none", stroke: col.ink, "stroke-width": 4.5, "stroke-linejoin": "round" }, sv);
    const sp = svg("path", { d: "", fill: "none", stroke: col.mark, "stroke-width": 11, "stroke-linecap": "round" }, sv);
    const now = young[young.length - 1][1], xNow = X1 + 4;
    const tip = svg("circle", { cx: xNow, cy: ys(now), r: 15, fill: col.mark, stroke: "#fff", "stroke-width": 5, opacity: 0 }, sv);
    const shards = [0, 1, 2, 3].map(k => svg("path", { d: "M0,0 l14,-6 l-4,14 z", fill: col.ink, opacity: 0 }, sv));
    const counter = css(text(b, "chip", "", { top: 690 }), { fontWeight: "900", fontSize: "60px", lineHeight: "78px" });
    const chip = css(text(b, "chip", K.now, { top: ys(now) - 34 }), { background: col.mark, color: col.paper, fontWeight: "900", fontSize: "54px", lineHeight: "70px" });
    f.prep = () => { centreTicks(b); css(chip, { left: xNow - chip.offsetWidth - 34 }); };
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
      f.head.querySelector(".small").style.opacity = easeOut(seg(t, q.small, q.small + 0.5)).toFixed(3);
    } };
  }

  // ── 7: whose fuel: 100 squares, each 1 % of the warming from fossil fuels so far ──
  function who(sc) {
    const f = frame(sc), b = f.body, q = F.cues.who, G = Wd.who.groups, size = 56, gapq = 8, X1 = R - 40, Y0 = 640;
    const order = []; G.forEach(gr => { if (gr.key !== "rest" && gr.key !== "iran") for (let i = 0; i < gr.v; i++) order.push(gr.key); });
    const nFour = order.length;
    const restN = 100 - nFour - 1.5;                // 39.5 squares: the last full square of the rest is split with Iran
    for (let i = 0; i < Math.floor(restN); i++) order.push("rest");
    order.push("split"); order.push("iran");
    const pos = i => ({ x: X1 - (i % 10) * (size + gapq) - size, y: Y0 + Math.floor(i / 10) * (size + gapq) });   // right to left, top to bottom
    const sq = order.map((k, i) => {
      const e = css(el("div", "sq", b), { width: size, height: size });
      if (k === "split") e.style.background = `linear-gradient(90deg, ${col.iran} 50%, ${col.rest} 50%)`; else e.style.background = col[k];
      return e;
    });
    const ring = css(el("div", "abs", b), { width: 2 * size + gapq + 24, height: size + 24, borderRadius: "16px", boxShadow: "0 0 0 6px " + col.iran });
    const legend = G.map((g, i) => {
      const e = el("div", "leg", b), sw = el("i", null, e); sw.style.background = col[g.key];
      e.appendChild(document.createTextNode(g.label + (g.v !== null ? " " + fa(g.v) + "٪" : "")));
      return css(e, { top: 1290 + Math.floor(i / 2) * 62, right: i % 2 ? 1080 - MID + 20 : 1080 - R });
    });
    const unit = text(b, "tick", Wd.who.unit, { top: Y0 - 60, left: L });
    void unit;
    return { ...f, update(t) {
      sq.forEach((e, i) => {
        const t0 = q.fill[0] + (q.fill[1] - q.fill[0]) * i / sq.length, p = easeOut(seg(t, t0, t0 + 0.35)), P = pos(i);
        const four = order[i] !== "rest" && order[i] !== "iran" && order[i] !== "split" ? 0.08 * bump(seg(t, q.four, q.four + 0.6)) : 0;
        const wave = t > q.fill[1] + 0.4 ? 0.06 * Math.max(0, Math.sin(2 * Math.PI * ((t - q.fill[1]) / 2.0 - i / 40))) : 0;
        css(e, { left: P.x, top: P.y - 120 * (1 - p), opacity: p.toFixed(3), scale: (0.4 + 0.6 * p + four + wave).toFixed(3) });
      });
      const P = pos(98), ip = easeOut(seg(t, q.iran, q.iran + 0.5));
      css(ring, { left: P.x - size - gapq - 12, top: P.y - 12, opacity: ip.toFixed(3), scale: (1 + 0.06 * Math.sin(2 * Math.PI * Math.max(0, t - q.iran) / 1.2)).toFixed(3) });
      legend.forEach((e, i) => {
        const g = G[i], first = order.findIndex(k => k === g.key), done = q.fill[0] + (q.fill[1] - q.fill[0]) * Math.max(0, first) / sq.length;
        const at = g.key === "iran" ? q.iran : done;
        show(e, easeOut(seg(t, at, at + 0.4)));
      });
    } };
  }

  // ── 8: the call ──
  function call(sc) {
    const f = frame(sc), b = f.body, q = F.cues.call, g = globe(b, 480, 560);
    const icon = svg("svg", { width: 220, height: 220, viewBox: "-60 -60 120 120" }, b);
    css(icon, { left: MID - 110, top: 1000 });
    const ic = svg("g", { fill: "none", stroke: col.mark, "stroke-width": 9, "stroke-linecap": "round", "stroke-linejoin": "round" }, icon);
    svg("path", { d: "M-34,-8 v-14 a10,10 0 0 1 10,-10 h52" }, ic); svg("path", { d: "M18,-44 l12,12 l-12,12" }, ic);
    svg("path", { d: "M34,8 v14 a10,10 0 0 1 -10,10 h-52" }, ic); svg("path", { d: "M-18,44 l-12,-12 l12,-12" }, ic);
    const follow = css(el("div", "abs", b), { left: L, top: 1250, width: W, textAlign: "center", fontWeight: "800", fontSize: "46px", lineHeight: "62px", whiteSpace: "nowrap" });
    const w = Wd.call.follow.split(" "), cut = w.indexOf("که");
    const fl = [el("span", null, follow, w.slice(0, cut).join(" ")), el("span", null, follow, w.slice(cut).join(" "))];
    fl.forEach(x => { x.style.display = "block"; });
    f.follow = fl;
    return { ...f, update(t, T) {
      g.draw(keyed(F.view.call, t), () => 0);
      const p = easeOut(seg(t, q.icon, q.icon + 0.5)), spin = t > q.icon ? (t - q.icon) * 60 : 0;
      css(icon, { opacity: p.toFixed(3), scale: (0.7 + 0.3 * p + 0.05 * Math.sin(2 * Math.PI * Math.max(0, t - q.icon) / 1.3)).toFixed(3) });
      ic.setAttribute("transform", `rotate(${(spin % 360).toFixed(1)})`);
      show(follow, easeOut(seg(t, q.follow, q.follow + 0.6)));
    } };
  }

  const builders = { hook, melt, calm, jump, sun, co2, who, call };
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
    const enter = i === 0 ? 1 : easeOut(seg(dt, 0, 0.35));
    css(scenes[i].body, { opacity: (0.25 + 0.75 * enter).toFixed(3), transform: `translateY(${(14 * (1 - enter)).toFixed(2)}px)` });
    segs.forEach((s, k) => { s.style.width = (k < i ? 100 : k > i ? 0 : 100 * dt / sc.length).toFixed(3) + "%"; });
    return i;
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
