/* «۲ درجه گرم‌تر، یعنی چه؟», second cut: window.renderAt(t) draws the frame of time t (seconds) from
   /build/film.json, which src/twodeg2.py writes (every string, every number, the clock and the cues). Nothing is
   typed here; the only numbers this file writes are the counts of its own drawings (year-boxes lit, dots past the
   line) and the warming readout between the levels the report gives, in Persian digits. Every frame is a pure
   function of t (the frames are rendered out of order by several workers). */
"use strict";
const L = 96, R = 924, W = 828, MID = (L + R) / 2;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const easeOut = p => 1 - Math.pow(1 - p, 3);
const easeInOut = p => p * p * (3 - 2 * p);
const bump = p => Math.sin(Math.PI * clamp(p));
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
  let size = parseFloat(getComputedStyle(nodes[0]).fontSize);
  const wide = () => Math.max(...nodes.map(n => n.scrollWidth));
  while (wide() > limit && size > floor) { size -= 1; nodes.forEach(n => css(n, { fontSize: size + "px", lineHeight: Math.round(size * 1.4) + "px" })); }
}
const show = (e, p) => { e.style.opacity = clamp(p).toFixed(3); };
const full = () => ({ width: 1080, height: 1920, viewBox: "0 0 1080 1920" });
function smooth(pts) {                              // a smooth line through points (Catmull-Rom as cubic Béziers)
  let d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    d += ` C${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)},${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)},${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`;
  }
  return d;
}

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const C = F.cuts.a, col = F.colours, END = C.end;
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const progress = el("div", null, stage); progress.id = "progress";
  const segs = C.scenes.map(() => el("i", null, el("div", "seg", progress)));
  el("div", "pill", stage, F.pill);

  // the Earth: NASA's Blue Marble on a sphere (orthographic), natural colours, a soft light from the upper left
  const im = new Image(); im.src = "/build/" + F.map.file; await im.decode();
  const tc = document.createElement("canvas"); tc.width = im.naturalWidth; tc.height = im.naturalHeight;
  const tx = tc.getContext("2d"); tx.drawImage(im, 0, 0);
  const tex = { w: tc.width, h: tc.height, d: tx.getImageData(0, 0, tc.width, tc.height).data };
  function globe(parent, cx, cy, Rg) {
    const size = 2 * Rg;
    css(el("div", "abs", parent), { left: cx - Rg, top: cy - Rg, width: size, height: size, borderRadius: "50%", boxShadow: "0 0 44px 12px rgba(110,160,235,.55), 0 28px 46px rgba(46,33,24,.32)" });
    const cv = css(el("canvas", "abs", parent), { left: cx - Rg, top: cy - Rg, width: size, height: size }); cv.width = size; cv.height = size;
    const ctx = cv.getContext("2d"), img = ctx.createImageData(size, size), out = img.data;
    const lat0 = F.globe.lat * Math.PI / 180, s0 = Math.sin(lat0), c0 = Math.cos(lat0), M = F.map;
    const idx = [], ty = [], dl = [], sh = [], al = [];
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      const nx = (x + 0.5 - Rg) / Rg, ny = (Rg - y - 0.5) / Rg, r2 = nx * nx + ny * ny;
      if (r2 >= 1) continue;
      const nz = Math.sqrt(1 - r2), lat = Math.asin(clamp(ny * c0 + nz * s0, -1, 1)), lon = Math.atan2(nx, nz * c0 - ny * s0);
      idx.push((y * size + x) * 4);
      ty.push(clamp(Math.round((M.lat1 - lat * 180 / Math.PI) / (M.lat1 - M.lat0) * tex.h - 0.5), 0, tex.h - 1));
      dl.push(lon * 180 / Math.PI);
      sh.push(1.12 * clamp(0.62 + 0.38 * (-0.45 * nx + 0.5 * ny + 0.74 * nz), 0, 1.1) * (0.74 + 0.26 * Math.sqrt(nz)));
      al.push(Math.round(255 * clamp((1 - Math.sqrt(r2)) * Rg, 0, 1)));
    }
    return { draw(lonC) {
      const w = tex.w, d = tex.d;
      for (let i = 0; i < idx.length; i++) {
        const u = (((lonC + dl[i] - M.lon0) % 360) + 360) % 360 / 360 * w, q = (ty[i] * w + Math.min(w - 1, u | 0)) * 4, o = idx[i], s = sh[i];
        out[o] = d[q] * s; out[o + 1] = d[q + 1] * s; out[o + 2] = d[q + 2] * s; out[o + 3] = al[i];
      }
      ctx.putImageData(img, 0, 0);
    } };
  }
  const turn = T => F.globe.lon[0] + (F.globe.lon[1] - F.globe.lon[0]) * T / END;       // the slow turn over the whole reel

  function frame(sc) {
    const root = el("div", "scene", stage);
    const head = el("div", "head", root);
    const lines = sc.title.split(" // ").map(s => { const ln = el("span", "line", head); marked(ln, s); return ln; });
    el("span", "small", head, sc.small);
    const body = css(el("div", "abs", root), { inset: "0" });
    el("div", "sources", root, F.source);
    return { root, head, lines, body, fits: [] };
  }

  // ── 1: the Earth, a ring of 50 year-boxes, the warming readout; the boxes light only at the report's levels ──
  function hook(sc) {
    const f = frame(sc), b = f.body, H = F.hook, cx = MID, cy = 1010, Rg = 236, Rr = 300;   // the ring's top (y 697) clears the readout above it
    const g = globe(b, cx, cy, Rg);
    const boxes = H.order.map((_, k) => {
      const a = (-90 + k * 7.2) * Math.PI / 180;
      return css(el("div", "abs", b), { left: cx + Rr * Math.cos(a) - 13, top: cy + Rr * Math.sin(a) - 13, width: 26, height: 26, borderRadius: "8px", background: col.land, rotate: (k * 7.2) + "deg" });
    });
    const read = css(el("div", "abs big", b), { left: L, top: 606, background: col.ink, color: col.paper, borderRadius: "16px", padding: "0 18px 6px", fontSize: "44px", lineHeight: "64px", fontWeight: "800" });
    const count = css(el("div", "abs big", b), { left: MID, top: 1340, translate: "-50% 0", background: col.mark, color: col.paper, borderRadius: "18px", padding: "0 22px 6px", fontSize: "54px", lineHeight: "76px", fontWeight: "800" });
    const range = css(text(b, "unit", "", { left: MID, top: 1424 }), { translate: "-50% 0" });
    const rise = F.cues.hook.rise;
    const level = t => { let v = 0; rise.forEach(r => { if (t >= r[0]) v = r[2] + (r[3] - r[2]) * easeInOut(seg(t, r[0], r[1])); }); return v; };
    return { ...f, update(t, T) {
      g.draw(turn(T));
      const v = level(t);
      let lv = H.levels[0], since = -9;
      H.levels.forEach(x => { if (v >= x.g - 1e-9) lv = x; });
      rise.forEach(r => { if (Math.abs(r[3] - lv.g) < 1e-9 && t >= r[1]) since = t - r[1]; });
      const prev = H.levels[Math.max(0, H.levels.indexOf(lv) - 1)].n;
      let lit = 0;
      H.order.forEach((k, i) => {
        const fresh = i >= prev && i < lv.n, on = i < lv.n && (!fresh || since >= (i - prev) * 0.12), p = fresh ? seg(since, (i - prev) * 0.12, (i - prev) * 0.12 + 0.35) : 1;
        if (on) lit += 1;
        css(boxes[k], { background: on ? col.mark : col.land, scale: (on ? 1 + 0.3 * bump(p) : 1).toFixed(3), boxShadow: on ? "0 0 0 4px rgba(160,49,41,.22)" : "none" });
      });
      read.textContent = H.gauge + ": " + (v < 0.005 ? H.levels[0].read : fa(v.toFixed(1)) + " درجه");
      const cur = H.levels.filter(x => x.n === lit)[0] || lv;
      count.textContent = cur.count; range.textContent = cur.range;
      count.style.scale = (1 + 0.08 * bump(seg(since, 0.5, 1.1))).toFixed(3);
    } };
  }

  // ── 2: a mean of the whole Earth; the body's temperature (an analogy) ──
  function mean(sc) {
    const f = frame(sc), b = f.body, M = F.mean, q = F.cues.mean;
    const g = globe(b, MID, 868, 222);
    const x36 = R - 96, unit = (W - 130) / 4, gx = v => x36 - (v - 36) * unit, ty0 = 1236;
    const grp = css(el("div", "abs", b), { inset: "0" });
    css(el("div", "tag", grp, M.tag), { right: 1080 - R, top: 1132 });
    css(el("div", "abs", grp), { left: L + 10, top: ty0, width: W - 20, height: 46, borderRadius: "23px", background: col.land, boxShadow: "0 0 0 3px " + col.ink });
    const merc = css(el("div", "abs", grp), { top: ty0 + 8, height: 30, borderRadius: "15px", background: col.mark });
    css(el("div", "abs", grp), { left: R - 81, top: ty0 - 16, width: 78, height: 78, borderRadius: "50%", background: col.mark, boxShadow: "0 0 0 3px " + col.ink });
    const labs = M.marks.map((m, k) => {
      css(el("div", "abs", grp), { left: gx(m.v) - 2, top: ty0 - 12, width: 4, height: 70, background: col.ink });
      return css(text(grp, "lab", m.label, { left: gx(m.v), top: ty0 + 66 }), { translate: "-50% 0", fontWeight: k ? "800" : "500", color: k ? col.mark : col.ink });
    });
    return { ...f, update(t, T) {
      g.draw(turn(T) + q.spin[2] * easeInOut(seg(t, q.spin[0], q.spin[1])));
      show(grp, easeOut(seg(t, q.body, q.body + 0.6)));
      const v = 37 + 2 * easeInOut(seg(t, q.mercury[0], q.mercury[1]));
      css(merc, { left: gx(v), width: R - 60 - gx(v) });
      show(labs[1], seg(t, q.mercury[1] - 0.3, q.mercury[1] + 0.1));
      labs[1].style.scale = (1 + 0.14 * bump(seg(t, q.mercury[1], q.mercury[1] + 0.7))).toFixed(3);
    } };
  }

  // ── 3: the distribution of 100 summer days, with its axes; the pile moves, the very hot days are counted ──
  function pile(sc) {
    const f = frame(sc), b = f.body, P = F.pile, q = F.cues.pile;
    const s = css(svg("svg", full(), b), { left: "0", top: "0" });
    const x0 = 196, pitch = 45, r = 13, dy = 30, base = 1318, axisX = 150, lineX = x0 + P.line * pitch - pitch / 2;
    P.yticks.forEach(tk => {
      const y = base - tk.v * dy;
      svg("line", { x1: axisX, x2: R, y1: y, y2: y, stroke: col.ink, "stroke-opacity": 0.13, "stroke-width": 2 }, s);
      css(text(b, "unit ltr", tk.label, { left: axisX - 12, top: y - 26 }), { translate: "-100% 0" });
    });
    svg("line", { x1: axisX, x2: axisX, y1: base - 16 * dy, y2: base, stroke: col.ink, "stroke-width": 4, "stroke-linecap": "round" }, s);
    svg("line", { x1: axisX, x2: R, y1: base, y2: base, stroke: col.ink, "stroke-width": 4, "stroke-linecap": "round" }, s);
    css(text(b, "unit", P.yaxis, { left: L, top: base - 16 * dy - 62 }), { fontWeight: "700" });
    css(text(b, "unit", P.xaxis, { left: (axisX + R) / 2, top: base + 12 }), { translate: "-50% 0", fontWeight: "700" });
    text(b, "unit", P.cold, { left: axisX + 6, top: base + 12 }); text(b, "unit", P.hot, { right: 1080 - R, top: base + 12 });
    const tops = sh => [[x0 + (sh - 1) * pitch, base]].concat(P.cols.map((n, c) => [x0 + (c + sh) * pitch, base - n * dy - 6]), [[x0 + (P.cols.length + sh) * pitch, base]]);
    const before = svg("path", { d: smooth(tops(0)), fill: "none", stroke: col.ink, "stroke-opacity": 0.45, "stroke-width": 4, "stroke-dasharray": "10 9" }, s);
    const curve = svg("path", { fill: "none", stroke: col.ink, "stroke-width": 5, "stroke-linecap": "round" }, s);
    const dots = [];
    P.cols.forEach((n, c) => { for (let k = 0; k < n; k++) dots.push({ c, k, e: svg("circle", { cy: base - k * dy - r - 3, r }, s), at: 0.2 + c * 0.13 + k * 0.035 }); });
    svg("line", { x1: lineX, x2: lineX, y1: base - 16 * dy + 30, y2: base + 2, stroke: col.mark, "stroke-width": 5, "stroke-dasharray": "14 10" }, s);
    const chip = css(el("div", "abs big", b), { right: 1080 - R, top: 622, background: col.mark, color: col.paper, borderRadius: "16px", padding: "0 18px 6px", fontSize: "50px", lineHeight: "70px", fontWeight: "800", transformOrigin: "100% 50%" });
    css(el("div", "tag", b, P.tag), { left: L, top: 632 });
    const oldMax = x0 + (P.cols.length - 1) * pitch + 1;
    return { ...f, update(t) {
      const p = easeInOut(seg(t, q.shift[0], q.shift[1])), sh = P.shift * p, rec = bump(seg(t, q.record, q.record + 1.2));
      let hot = 0;
      dots.forEach(d => {
        const x = x0 + (d.c + sh) * pitch, on = seg(t, d.at, d.at + 0.25), red = x >= lineX, fresh = x > oldMax;
        if (red && on >= 1) hot += 1;
        d.e.setAttribute("cx", x.toFixed(2)); d.e.setAttribute("opacity", on.toFixed(3));
        d.e.setAttribute("fill", fresh ? "#E2571F" : red ? col.mark : col.wet);
        d.e.setAttribute("r", (r * (1 + (red ? 0.22 * bump(seg(t, q.pulse, q.pulse + 0.8)) : 0) + (fresh ? 0.3 * rec : 0))).toFixed(2));
      });
      curve.setAttribute("d", smooth(tops(sh))); curve.setAttribute("opacity", seg(t, 2.6, 3.2).toFixed(3));
      before.setAttribute("opacity", (0.9 * p).toFixed(3));
      chip.textContent = P.chip + ": " + fa(hot) + " " + P.days;
      chip.style.scale = (1 + 0.1 * bump(seg(t, q.shift[1], q.shift[1] + 0.6))).toFixed(3);
      show(chip, seg(t, 2.8, 3.2));
    } };
  }

  // ── 4: heavy rain (drawn): a cloud, rain, a gauge that fills to the report's levels (an example on a scale of 100) ──
  function rain(sc) {
    const f = frame(sc), b = f.body, Rn = F.rain, q = F.cues.rain;
    const s = css(svg("svg", full(), b), { left: "0", top: "0" });
    const gx0 = 236, gx1 = 456, base = 1392, per = 3.5, ccx = (gx0 + gx1) / 2, ccy = 742;
    const streaks = Array.from({ length: 46 }, (_, i) => ({ e: svg("line", { stroke: col.wet, "stroke-linecap": "round" }, s), x: Math.max(112, ccx - 236 + (i * 131) % 480), ph: (i * 0.618) % 1, sp: 0.9 + (i % 5) * 0.11, rank: (i * 7) % 46 }));
    const cloud = svg("g", {}, s);
    [[-170, 26, 74], [-84, -30, 96], [26, -52, 116], [136, -14, 90], [204, 34, 62], [10, 40, 100], [-90, 44, 80], [110, 46, 78]].forEach(c => svg("circle", { cx: c[0], cy: c[1], r: c[2] }, cloud));
    svg("rect", { x: gx0, y: base - 124 * per, width: gx1 - gx0, height: 124 * per, rx: 20, fill: "#FBF7F0" }, s);
    const water = svg("rect", { x: gx0 + 6, width: gx1 - gx0 - 12, rx: 14, fill: col.wet }, s);
    svg("path", { d: `M${gx0},${base - 124 * per} L${gx0},${base - 20} Q${gx0},${base} ${gx0 + 20},${base} L${gx1 - 20},${base} Q${gx1},${base} ${gx1},${base - 20} L${gx1},${base - 124 * per}`, fill: "none", stroke: col.ink, "stroke-width": 7, "stroke-linecap": "round" }, s);
    const marks = Rn.marks.map((m, k) => {
      const y = base - m.v * per, ly = 1068 - k * 74;
      svg("line", { x1: gx1 - 46, x2: gx1 + 4, y1: y, y2: y, stroke: col.ink, "stroke-width": 5 }, s);
      svg("path", { d: `M${gx1 + 8},${y} L${gx1 + 44},${ly + 28}`, fill: "none", stroke: col.ink, "stroke-opacity": 0.5, "stroke-width": 3 }, s);
      return { m, lab: text(b, "lab", m.label, { left: gx1 + 52, top: ly }) };
    });
    css(el("div", "tag", b, Rn.tag), { left: L, top: base - 46 });
    f.fits = [text(b, "unit", Rn.foot, { right: 1080 - R, top: 1424 })];
    const level = t => { let v = 0; q.fill.forEach(r => { if (t >= r[0]) v = r[2] + (r[3] - r[2]) * easeInOut(seg(t, r[0], r[1])); }); return v; };
    return { ...f, update(t) {
      const v = level(t), heavy = clamp((v - 100) / 14), k = 1 + 0.16 * heavy, shade = Math.round(214 - 70 * heavy);
      cloud.setAttribute("transform", `translate(${ccx + 4 * Math.sin(t * 0.8)},${ccy}) scale(${k.toFixed(3)})`);
      cloud.setAttribute("fill", `rgb(${shade},${shade + 8},${shade + 20})`);
      streaks.forEach(d => {
        const p = (t * d.sp + d.ph) % 1, y = ccy + 80 + (base - ccy - 110) * p, len = 34 + 26 * heavy, on = d.rank < 22 + 24 * heavy;
        d.e.setAttribute("x1", d.x); d.e.setAttribute("x2", d.x - 8); d.e.setAttribute("y1", y); d.e.setAttribute("y2", y + len);
        d.e.setAttribute("stroke-width", (5 + 3 * heavy).toFixed(2)); d.e.setAttribute("opacity", on ? (0.55 * Math.sin(Math.PI * p)).toFixed(3) : 0);
      });
      const h = v * per; water.setAttribute("y", (base - h).toFixed(2)); water.setAttribute("height", Math.max(0, h).toFixed(2));   // the water's top is exactly at its mark
      marks.forEach(o => { const reached = v >= o.m.v - 0.05; css(o.lab, { fontWeight: reached ? "800" : "500", color: reached ? col.mark : col.ink, opacity: reached ? "1" : "0.55" }); });
    } };
  }

  // ── 5: the Earth again, the question, the line to send on ──
  function answer(sc) {
    const f = frame(sc), b = f.body, A = F.answer, q = F.cues.answer;
    const g = globe(b, MID, 772, 142);
    const card = css(el("div", "abs", b), { left: MID - 350, top: 960, width: 700, height: 290, borderRadius: "44px", background: col.mark, color: col.paper, textAlign: "center", boxShadow: "0 18px 34px rgba(160,49,41,.3)", paddingTop: "22px" });
    const ql = A.question.map(line => css(el("div", null, card, line), { fontWeight: "800", fontSize: "60px", lineHeight: "82px", whiteSpace: "nowrap" }));
    const tail = css(el("div", "abs", b), { left: 716, top: 1220, width: 50, height: 50, background: col.mark, rotate: "45deg", borderRadius: "10px" });
    const follow = css(el("div", "abs", b), { left: L, top: 1300, width: W, textAlign: "center", fontWeight: "800", fontSize: "46px", lineHeight: "62px", whiteSpace: "nowrap" });
    const w = A.follow.split(" "), cut = w.indexOf("که");
    const fl = [el("span", null, follow, w.slice(0, cut).join(" ")), el("span", null, follow, w.slice(cut).join(" "))];
    fl.forEach(x => { x.style.display = "block"; });
    f.follow = fl; f.q = ql;
    return { ...f, update(t, T) {
      g.draw(turn(T));
      const p = seg(t, q.question, q.question + 0.5), pulse = 1 + 0.018 * Math.sin(2 * Math.PI * Math.max(0, t - q.question - 0.5) / 1.6), k = (0.86 + 0.14 * easeOut(p)) * (p >= 1 ? pulse : 1);
      css(card, { opacity: easeOut(p).toFixed(3), scale: k.toFixed(4) }); css(tail, { opacity: easeOut(p).toFixed(3), scale: k.toFixed(4) });
      show(follow, easeOut(seg(t, q.follow, q.follow + 0.6)));
    } };
  }

  const builders = { hook, mean, pile, rain, answer };
  const scenes = C.scenes.map(sc => Object.assign(builders[sc.key](sc), { sc }));
  await document.fonts.ready;
  scenes.forEach(s => {
    s.root.style.display = "block";
    fit(s.lines, W, 54);
    fit([...s.head.querySelectorAll(".small")], W, 40);
    (s.fits || []).forEach(n => fit([n], W - 320, 34));
    if (s.follow) fit(s.follow, W, 36);
    if (s.q) fit(s.q, 640, 44);
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
