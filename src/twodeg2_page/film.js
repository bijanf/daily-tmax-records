/* «۲ درجه گرم‌تر، یعنی چه؟», third cut: window.renderAt(t) draws the frame of time t (seconds) from
   /build/film.json, which src/twodeg2.py writes (every string, every number, the clock and the cues). Nothing is
   typed here; the only numbers this file writes are the counts of its own drawings (dots past the line, water
   molecules in the box), in Persian digits. Every frame is a pure function of t (the frames are rendered out of
   order by several workers): the molecules' paths are closed formulas of t, not a simulation. */
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
  if (!nodes.length) return;
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
    const halo = css(el("div", "abs", parent), { left: cx - Rg, top: cy - Rg, width: size, height: size, borderRadius: "50%", boxShadow: "0 0 44px 12px rgba(110,160,235,.55), 0 28px 46px rgba(46,33,24,.32)" });
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
    return { halo, draw(lonC) {
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
    if (sc.small) el("span", "small", head, sc.small);
    const body = css(el("div", "abs", root), { inset: "0" });
    el("div", "sources", root, sc.source || F.source);
    return { root, head, lines, body, fits: [] };
  }

  // ── 1: the Earth and a ring of 50 year-boxes; ONE card under it carries the whole sentence (the event, the warming
  //       level, the count). The reel opens on the end state, runs back to the time before industry and counts up again;
  //       the boxes light only up to the report's levels and the card names the level they are counting up to ──
  function hook(sc) {
    const f = frame(sc), b = f.body, H = F.hook, q = F.cues.hook, cx = MID, cy = 862, Rg = 244, Rr = 308, n0 = H.levels.map(x => x.n);
    const g = globe(b, cx, cy, Rg);
    const boxes = H.order.map((_, k) => {
      const a = (-90 + k * 7.2) * Math.PI / 180;
      return css(el("div", "abs", b), { left: cx + Rr * Math.cos(a) - 14, top: cy + Rr * Math.sin(a) - 14, width: 28, height: 28, borderRadius: "8px", background: col.land, rotate: (k * 7.2) + "deg" });
    });
    const card = css(el("div", "abs", b), { left: L, top: 1206, width: W, borderRadius: "28px", background: col.mark, color: col.paper, textAlign: "center", padding: "12px 16px 16px", boxShadow: "0 18px 34px rgba(160,49,41,.28)" });
    const ev = css(el("div", null, card, H.event), { fontWeight: "700", fontSize: "44px", lineHeight: "62px", whiteSpace: "nowrap", opacity: "0.94" });
    const now = css(el("div", null, card), { fontWeight: "900", fontSize: "66px", lineHeight: "92px", whiteSpace: "nowrap" });
    const note = css(text(b, "unit", "", { left: MID, top: 1406 }), { translate: "-50% 0" });
    const onAt = i => { let t0 = 1e9; q.rise.forEach((r, k) => { if (i >= n0[k] && i < n0[k + 1]) t0 = r[0] + (i - n0[k] + 1) / (n0[k + 1] - n0[k]) * (r[1] - r[0]); }); return t0; };   // when year-box i lights on the way up
    const offAt = i => q.rewind[0] + (n0[3] - i) / (n0[3] - n0[0]) * (q.rewind[1] - q.rewind[0]);                                                                              // when it goes dark on the way back
    const warm = t => { if (t < q.rewind[1]) return 2 * (1 - easeInOut(seg(t, q.rewind[0], q.rewind[1]))); let v = 0; q.rise.forEach(r => { if (t >= r[0]) v = r[2] + (r[3] - r[2]) * easeInOut(seg(t, r[0], r[1])); }); return v; };
    f.prep = () => {                                                // one type size for the card's changing line, so that it does not jump
      let size = 66;
      const wide = () => Math.max(...H.levels.map(x => { now.textContent = x.line; return now.scrollWidth; }));
      while (wide() > now.clientWidth && size > 44) { size -= 1; css(now, { fontSize: size + "px", lineHeight: Math.round(size * 1.4) + "px" }); }
      size = 44;
      while (ev.scrollWidth > ev.clientWidth && size > 34) { size -= 1; css(ev, { fontSize: size + "px", lineHeight: Math.round(size * 1.4) + "px" }); }
    };
    return { ...f, update(t, T) {
      g.draw(turn(T) + q.spin[2] * (1 - easeOut(seg(t, q.spin[0], q.spin[1]))));
      const w = warm(t) / 2, hc = [110 + 122 * w, 160 - 68 * w, 235 - 195 * w].map(Math.round);
      g.halo.style.boxShadow = `0 0 ${(44 + 16 * w).toFixed(1)}px ${(12 + 8 * w).toFixed(1)}px rgba(${hc.join(",")},${(0.55 + 0.15 * w).toFixed(3)}), 0 28px 46px rgba(46,33,24,.32)`;
      let lit = 0;
      H.order.forEach((k, i) => {
        const on = i < n0[0] || (i < n0[3] && (t < offAt(i) || t >= onAt(i)));
        const pop = i < n0[0] ? (t > q.rewind[1] && t < q.rise[0][0] ? 0.8 * bump(((t - q.rewind[1]) % 1) / 0.6) : 0) : bump(seg(t - onAt(i), 0, 0.4));   // the one box of the time before industry beats while it waits
        if (on) lit += 1;
        css(boxes[k], { background: on ? col.mark : col.land, scale: (on ? 1 + 0.34 * pop : 1).toFixed(3), boxShadow: on ? "0 0 0 4px rgba(160,49,41,.22)" : "none" });
      });
      let k = 0; while (k < 3 && lit > n0[k]) k += 1;               // the card names the level the ring is counting up to (or running back from), from its first box on
      now.textContent = H.levels[k].line; note.textContent = H.levels[k].note;
      now.style.scale = (1 + 0.07 * bump(k ? seg(t - onAt(n0[k - 1]), 0, 0.6) : 0)).toFixed(3);
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

  // ── a small 3D kit on a 2D canvas: points are [x, y, z] with y up; the camera looks a little down and swings slowly ──
  function canvas(parent) { const cv = css(el("canvas", "abs", parent), { left: "0", top: "0", width: 1080, height: 1920 }); cv.width = 1080; cv.height = 1920; return cv; }
  function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let x = Math.imul(a ^ (a >>> 15), 1 | a); x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; }; }
  function camera(cx, cy, scale, yaw, pitch, dist) {
    const cw = Math.cos(yaw), sw = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const rot = p => { const x = p[0] * cw + p[2] * sw, z = p[2] * cw - p[0] * sw; return [x, p[1] * cp - z * sp, p[1] * sp + z * cp]; };
    const pro = p => { const r = rot(p), k = dist / (dist - r[2]) * scale; return [cx + r[0] * k, cy - r[1] * k, r[2], k]; };
    return { rot, pro };
  }
  function ball(ctx, x, y, r, light, body, shade) {              // a lit sphere: the light comes from the upper left
    const g = ctx.createRadialGradient(x - 0.36 * r, y - 0.42 * r, 0.05 * r, x, y, r);
    g.addColorStop(0, light); g.addColorStop(0.52, body); g.addColorStop(1, shade);
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
  }
  const fold = (v, lo, hi) => { const n = hi - lo, u = (((v - lo) % (2 * n)) + 2 * n) % (2 * n); return lo + (u < n ? u : 2 * n - u); };   // a straight path, mirrored at two walls
  const mixc = (a, c, w) => `rgb(${a.map((v, i) => Math.round(v + (c[i] - v) * w)).join(",")})`;
  const BLUE = ["#bcd8fc", "#1c5cab", "#0b2c5e"], WHITE = ["#ffffff", "#f4f0e8", "#b4aa9b"], GREY = ["#f3eee5", "#c2b6a4", "#8a7d6b"], NEW = "#E2571F";
  function tumble(rnd) {                                         // a molecule's own frame (two unit vectors at right angles), its turning rate and phase
    const unit = () => { const z = 2 * rnd() - 1, a = 6.2832 * rnd(), r = Math.sqrt(1 - z * z); return [r * Math.cos(a), z, r * Math.sin(a)]; };
    const n = unit(); let e1 = unit(); const d = e1[0] * n[0] + e1[1] * n[1] + e1[2] * n[2]; e1 = e1.map((v, i) => v - d * n[i]);
    const len = Math.hypot(e1[0], e1[1], e1[2]); e1 = e1.map(v => v / len);
    return { e1, e2: [n[1] * e1[2] - n[2] * e1[1], n[2] * e1[0] - n[0] * e1[2], n[0] * e1[1] - n[1] * e1[0]], spin: (rnd() < 0.5 ? -1 : 1) * (1.0 + 1.6 * rnd()), ph: 6.2832 * rnd(), unit };
  }
  // a water molecule (a blue ball with two small white ones, 104.5 degrees apart) or an air molecule (two grey balls), at (x, y), radius r
  function molecule(ctx, cam, m, x, y, r, t, ring) {
    const a = m.spin * t + m.ph, c = Math.cos(a), s = Math.sin(a);
    const u = [0, 1, 2].map(i => m.e1[i] * c + m.e2[i] * s), w = [0, 1, 2].map(i => m.e2[i] * c - m.e1[i] * s);
    if (!m.kind) {
      const d = cam.rot(u), o = 0.62 * r, far = d[2] < 0 ? 1 : -1;
      ball(ctx, x + far * d[0] * o, y - far * d[1] * o, r, ...GREY); ball(ctx, x - far * d[0] * o, y + far * d[1] * o, r, ...GREY);
      return;
    }
    const hs = [1, -1].map(sg => cam.rot([0, 1, 2].map(i => 0.612 * u[i] + sg * 0.791 * w[i])));
    const hyd = h => { const hx = x + h[0] * 0.98 * r, hy = y - h[1] * 0.98 * r; ball(ctx, hx, hy, 0.6 * r, ...WHITE); ctx.strokeStyle = "rgba(46,33,24,.36)"; ctx.lineWidth = 1.4; ctx.beginPath(); ctx.arc(hx, hy, 0.6 * r, 0, 6.2832); ctx.stroke(); };
    hs.filter(h => h[2] < 0).forEach(hyd);
    ball(ctx, x, y, r, ...BLUE);
    hs.filter(h => h[2] >= 0).forEach(hyd);
    if (ring) { ctx.strokeStyle = NEW; ctx.lineWidth = Math.max(2.6, 0.24 * r); ctx.beginPath(); ctx.arc(x, y, 1.78 * r, 0, 6.2832); ctx.stroke(); }   // the ones that came with the warming
  }
  function icon(parent, kind) {                                   // a small still molecule for a label
    const cv = el("canvas", null, parent), w = kind ? 80 : 70, h = kind ? 62 : 44; cv.width = w; cv.height = h; css(cv, { width: w, height: h, flex: "none" });
    const c = cv.getContext("2d");
    if (kind) { [[22, 44], [58, 44]].forEach(o => { ball(c, o[0], o[1], 11, ...WHITE); c.strokeStyle = "rgba(46,33,24,.4)"; c.lineWidth = 1.4; c.beginPath(); c.arc(o[0], o[1], 11, 0, 6.2832); c.stroke(); }); ball(c, 40, 26, 19, ...BLUE); }
    else { ball(c, 24, 22, 15, ...GREY); ball(c, 46, 22, 15, ...GREY); }
    return cv;
  }

  // ── 4: the law behind the rain (Clausius-Clapeyron), drawn: a glass box of air over the sea, seen in three dimensions;
  //       grey pairs are air, blue ones water vapour. With each degree the box holds about 7 % more vapour: 7 more water
  //       molecules leave the sea (100, 107, 114: a drawing on the gauge's scale). Warmer air also moves a little faster ──
  function vapour(sc) {
    const f = frame(sc), b = f.body, V = F.vapour, q = F.cues.vapour, cv = canvas(b), ctx = cv.getContext("2d"), rnd = rng(11);
    const bx = 1, bz = 0.74, by = 2.0, yw = 0.42, CX = MID + 36, CY = 962, SC = 252, DIST = 7.5;
    const lev = t => { let v = 0; q.warm.forEach(r => { if (t >= r[0]) v = r[2] + (r[3] - r[2]) * easeInOut(seg(t, r[0], r[1])); }); return v; };
    const clock = t => { const n = Math.max(1, Math.ceil(t * 30)); let s = 0; for (let i = 0; i < n; i++) s += 1 + V.faster * lev((i + 0.5) * t / n); return s * t / n; };   // the molecules' own time: it runs faster in warmer air
    const make = (kind, r, speed) => {
      const m = tumble(rnd), dir = m.unit(), sp = speed * (0.7 + 0.6 * rnd()), pad = r * 1.75;
      const lo = [-bx + pad, yw + pad + 0.03, -bz + pad], hi = [bx - pad, by - pad, bz - pad];
      return Object.assign(m, { kind, r, lo, hi, p: lo.map((v, i) => v + (hi[i] - v) * rnd()), v: dir.map(x => x * sp), born: -1, extra: 0 });
    };
    const air = Array.from({ length: V.air }, () => make(0, 0.04, 0.44)), water = Array.from({ length: V.counts[2] }, () => make(1, 0.052, 0.36));
    q.warm.forEach((r, k) => { const a = V.counts[k], n = V.counts[k + 1] - a; for (let i = 0; i < n; i++) Object.assign(water[a + i], { born: r[0] + (i + 0.4) / n * (r[1] - r[0] - 0.2), extra: k + 1 }); });
    const where = (m, t, s) => { const p = [0, 1, 2].map(i => fold(m.p[i] + m.v[i] * s, m.lo[i], m.hi[i])); if (m.born >= 0) p[1] = yw + (p[1] - yw) * easeOut(seg(t, m.born, m.born + V.launch)); return p; };
    const chip = css(el("div", "abs big", b), { left: L, top: 604, background: col.ink, color: col.paper, borderRadius: "16px", padding: "0 18px 6px", fontSize: "44px", lineHeight: "64px", fontWeight: "800", transformOrigin: "0 50%" });
    css(el("div", "tag", b, V.tag), { right: 1080 - R, top: 612 });
    const count = css(el("div", "abs big", b), { right: 1080 - R, top: 1352, background: col.mark, color: col.paper, borderRadius: "18px", padding: "0 12px 4px 22px", fontSize: "54px", lineHeight: "76px", fontWeight: "800", display: "flex", alignItems: "center", gap: "12px", transformOrigin: "100% 50%", boxShadow: "0 10px 22px rgba(160,49,41,.26)" });
    icon(count, 1); const num = el("span", null, count);
    const gas = css(el("div", "abs big", b), { left: L, top: 1360, background: "#FBF7F0", color: col.ink, borderRadius: "16px", padding: "0 10px 4px 20px", fontSize: "44px", lineHeight: "60px", fontWeight: "700", display: "flex", alignItems: "center", gap: "10px", boxShadow: "0 3px 10px rgba(20,12,6,.2)", transformOrigin: "0 50%" });
    icon(gas, 0); el("span", null, gas, V.gas);
    return { ...f, update(t) {
      const v = lev(t), s = clock(t), yaw = (V.yaw[0] + V.yaw[1] * Math.sin(6.2832 * t / V.yaw[2])) * Math.PI / 180, cam = camera(CX, CY, SC, yaw, V.pitch * Math.PI / 180, DIST);
      const P = (x, y, z) => cam.pro([x, y - by / 2, z]);
      const path = pts => { ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.closePath(); };
      const sides = [[[-bx, bz], [bx, bz], [0, 0, 1]], [[bx, bz], [bx, -bz], [1, 0, 0]], [[bx, -bz], [-bx, -bz], [0, 0, -1]], [[-bx, -bz], [-bx, bz], [-1, 0, 0]]].map(([a, c, n]) => {
        const mid = cam.rot([(a[0] + c[0]) / 2, 0, (a[1] + c[1]) / 2]), nn = cam.rot(n);
        return { a, c, n, front: -nn[0] * mid[0] - nn[1] * mid[1] + nn[2] * (DIST - mid[2]) > 0 };
      });
      const wall = (sd, y0, y1) => [P(sd.a[0], y0, sd.a[1]), P(sd.c[0], y0, sd.c[1]), P(sd.c[0], y1, sd.c[1]), P(sd.a[0], y1, sd.a[1])];
      const floor = y => [P(-bx, y, bz), P(bx, y, bz), P(bx, y, -bz), P(-bx, y, -bz)];
      ctx.clearRect(0, 0, 1080, 1920); ctx.lineJoin = "round"; ctx.lineCap = "round";
      ctx.save(); ctx.filter = "blur(24px)"; ctx.fillStyle = "rgba(46,33,24,.34)"; path(floor(0).map(p => [p[0], p[1] + 30])); ctx.fill(); ctx.restore();   // the box's shadow on the paper
      path(floor(0)); ctx.fillStyle = "rgba(255,255,255,.5)"; ctx.fill();
      sides.filter(sd => !sd.front).forEach(sd => { path(wall(sd, 0, by)); ctx.fillStyle = "rgba(255,255,255,.46)"; ctx.fill(); ctx.strokeStyle = "rgba(46,33,24,.22)"; ctx.lineWidth = 3; ctx.stroke(); });
      // the sea: its lit top and the two walls that face the camera
      sides.filter(sd => sd.front).forEach(sd => { const w = wall(sd, 0, yw), g = ctx.createLinearGradient(0, w[3][1], 0, w[0][1]), side = sd.n[0] !== 0;
        g.addColorStop(0, side ? "#2362b3" : "#2d74c8"); g.addColorStop(1, side ? "#0f3469" : "#143f7f"); path(w); ctx.fillStyle = g; ctx.fill(); });
      const top = floor(yw), tg = ctx.createLinearGradient(0, top[2][1], 0, top[0][1]); tg.addColorStop(0, "#7db3ee"); tg.addColorStop(1, "#3f85d4"); path(top); ctx.fillStyle = tg; ctx.fill();
      ctx.save(); path(top); ctx.clip(); ctx.strokeStyle = "rgba(255,255,255,.5)"; ctx.lineWidth = 3;
      [-0.56, -0.2, 0.16, 0.52].forEach((z, k) => { ctx.beginPath(); for (let i = 0; i <= 40; i++) { const x = -bx + 2 * bx * i / 40, o = P(x, yw + 0.016 * Math.sin(5.2 * x + 1.9 * t + 2.4 * k), z); i ? ctx.lineTo(o[0], o[1]) : ctx.moveTo(o[0], o[1]); } ctx.stroke(); });
      water.forEach(m => { const age = t - m.born; if (m.born < 0 || age < 0 || age > 1.1) return;                      // the ring a leaving molecule draws on the sea
        const p = where(m, m.born, clock(m.born)), rr = 0.04 + 0.26 * easeOut(age / 1.1); ctx.strokeStyle = `rgba(255,255,255,${(0.9 * (1 - age / 1.1)).toFixed(3)})`; ctx.lineWidth = 4;
        ctx.beginPath(); for (let i = 0; i <= 28; i++) { const a = 6.2832 * i / 28, o = P(p[0] + rr * Math.cos(a), yw, p[2] + rr * Math.sin(a)); i ? ctx.lineTo(o[0], o[1]) : ctx.moveTo(o[0], o[1]); } ctx.stroke(); });
      ctx.restore();
      const front = sides.filter(sd => sd.front && sd.n[2] === 1)[0];
      if (front) { const o = P(0, yw * 0.46, bz); ctx.save(); ctx.font = "800 42px Vazirmatn"; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.direction = "rtl"; ctx.fillStyle = "rgba(255,255,255,.94)"; ctx.fillText(V.sea, o[0], o[1]); ctx.restore(); }
      // the molecules, the far ones first and paler
      const list = [];
      air.forEach(m => { const p = where(m, t, s); list.push({ m, o: P(p[0], p[1], p[2]) }); });
      water.forEach(m => { if (m.born >= 0 && t < m.born) return; const p = where(m, t, s); list.push({ m, o: P(p[0], p[1], p[2]) }); });
      list.sort((a, c) => a.o[2] - c.o[2]);
      const z0 = list[0].o[2], zr = list[list.length - 1].o[2] - z0 || 1;
      let n = V.counts[0];
      list.forEach(e => { const m = e.m, d = (e.o[2] - z0) / zr, r = m.r * e.o[3], age = t - m.born;
        if (m.extra) { if (age >= 0.3) n += 1; if (age < 1.8) { const gl = ctx.createRadialGradient(e.o[0], e.o[1], 0, e.o[0], e.o[1], 4.2 * r); gl.addColorStop(0, `rgba(226,87,31,${(0.62 * (1 - age / 1.8)).toFixed(3)})`); gl.addColorStop(1, "rgba(226,87,31,0)"); ctx.globalAlpha = 1; ctx.fillStyle = gl; ctx.beginPath(); ctx.arc(e.o[0], e.o[1], 4.2 * r, 0, 6.2832); ctx.fill(); } }
        ctx.globalAlpha = m.kind ? 0.66 + 0.34 * d : 0.42 + 0.4 * d;
        molecule(ctx, cam, m, e.o[0], e.o[1], r, s, m.extra); });
      ctx.globalAlpha = 1;
      // the glass in front: a warm cast that grows with the degrees, a sheen, the edges
      sides.filter(sd => sd.front).forEach(sd => { const w = wall(sd, 0, by), g = ctx.createLinearGradient(w[3][0], w[3][1], w[1][0], w[1][1]);
        g.addColorStop(0, "rgba(255,255,255,.26)"); g.addColorStop(0.4, "rgba(255,255,255,.02)"); g.addColorStop(1, "rgba(255,255,255,.14)"); path(w); ctx.fillStyle = g; ctx.fill();
        path(wall(sd, yw, by)); ctx.fillStyle = `rgba(226,87,31,${(0.05 * v).toFixed(3)})`; ctx.fill();
        path(w); ctx.strokeStyle = "rgba(46,33,24,.84)"; ctx.lineWidth = 5; ctx.stroke(); });
      path(floor(by)); ctx.fillStyle = `rgba(255,255,255,.12)`; ctx.fill(); ctx.strokeStyle = "rgba(46,33,24,.84)"; ctx.lineWidth = 5; ctx.stroke();
      if (front) { const a = P(-bx + 0.09, by - 0.16, bz), c = P(-bx + 0.09, yw + 0.5, bz); ctx.strokeStyle = "rgba(255,255,255,.7)"; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(c[0], c[1]); ctx.stroke(); }
      // the thermometer beside the box: three marks (before, 1 degree, 2 degrees)
      const tx = 142, tT = 744, tB = 1140, ty = k => tB - (0.26 + 0.29 * k) * (tB - tT);
      ctx.fillStyle = "#FBF7F0"; ctx.strokeStyle = col.ink; ctx.lineWidth = 5;
      ctx.beginPath(); ctx.roundRect(tx - 15, tT, 30, tB - tT + 40, 15); ctx.fill(); ctx.stroke();
      ctx.fillStyle = col.mark; ctx.beginPath(); ctx.arc(tx, tB + 34, 34, 0, 6.2832); ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.roundRect(tx - 8, ty(v), 16, tB + 20 - ty(v), 8); ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,.55)"; ctx.beginPath(); ctx.arc(tx - 11, tB + 24, 8, 0, 6.2832); ctx.fill();
      [0, 1, 2].forEach(k => { ctx.strokeStyle = col.ink; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(tx + 20, ty(k)); ctx.lineTo(tx + 36, ty(k)); ctx.stroke(); });
      const k = v > 1.02 ? 2 : v > 0.02 ? 1 : 0;                      // the chip names the degree as the warming starts: the cause, then the molecules that leave
      chip.textContent = V.chip[k]; chip.style.background = k ? col.mark : col.ink;
      chip.style.scale = (1 + 0.12 * bump(k ? seg(t - q.warm[k - 1][0], 0, 0.6) : 0)).toFixed(3);
      num.textContent = V.water + ": " + fa(n) + " " + V.unit;
      const tick = water.reduce((a, m) => m.extra ? Math.max(a, bump(seg(t - m.born - 0.3, 0, 0.3))) : a, 0);
      count.style.scale = (1 + 0.07 * tick + 0.1 * bump(seg(t - q.legend[1], 0, 0.7))).toFixed(3);
      gas.style.scale = (1 + 0.14 * bump(seg(t - q.legend[0], 0, 0.7))).toFixed(3);
    } };
  }

  // ── 5: what that vapour does to heavy rain (drawn): it rises into a cloud that swells with each degree (seven ringed
  //       molecules a degree, as in the box), and the rain fills a gauge to the report's levels (an example on a scale of 100) ──
  function rain(sc) {
    const f = frame(sc), b = f.body, Rn = F.rain, q = F.cues.rain, cv = canvas(b), ctx = cv.getContext("2d"), rnd = rng(5);
    const off = document.createElement("canvas"), OX = 450, OY = 600; off.width = 900; off.height = 720; const oc = off.getContext("2d");   // the cloud is drawn here first, then its base is shaded
    const gx0 = 236, gx1 = 456, base = 1392, per = 3.5, gcx = (gx0 + gx1) / 2, grx = (gx1 - gx0) / 2, gry = 22, rim = base - 124 * per, ccx = 372, cby = 846, flat = camera(0, 0, 1, 0, 0, 9);
    const level = t => { let v = 0; q.fill.forEach(r => { if (t >= r[0]) v = r[2] + (r[3] - r[2]) * easeInOut(seg(t, r[0], r[1])); }); return v; };
    const pour = t => Math.max(...q.fill.map(r => Math.min(seg(t, r[0] - 0.4, r[0] - 0.05), 1 - seg(t, r[1] - 0.15, r[1] + 0.25))));   // it rains while the gauge fills
    const puffs = [], puff = (X, Y, Z, r, grow) => puffs.push({ X, Y, Z, r, grow, ph: rnd() });
    for (let i = 0; i < 34; i++) { const X = -190 + 380 * rnd(), w = 1 - Math.abs(X) / 236; puff(X, 26 + 52 * rnd() * w, -84 + 168 * rnd(), 40 + 44 * w * (0.55 + 0.45 * rnd()), 0); }           // the body
    for (let i = 0; i < 18; i++) { const X = -124 + 248 * rnd(); puff(X, 84 + 66 * rnd() * (1 - Math.abs(X) / 176), -56 + 112 * rnd(), 34 + 30 * rnd(), 0); }                                // the crown
    for (let i = 0; i < 18; i++) { const a = 6.2832 * (i + 0.6 * rnd()) / 18; puff(208 * Math.cos(a), 16 + 18 * rnd(), 92 * Math.sin(a), 28 + 18 * rnd(), 0); }                               // the rim
    for (let i = 0; i < 20; i++) { const X = -108 + 216 * rnd(); puff(X, 128 + 92 * rnd() * (1 - Math.abs(X) / 152), -50 + 100 * rnd(), 32 + 26 * rnd(), 0.12 + 0.88 * i / 20); }              // the tower that grows with the warming
    function cloud(t, heavy, form) {
      const yaw = 0.22 * Math.sin(6.2832 * t / 9), c = Math.cos(yaw), s = Math.sin(yaw), S = form * (1 + 0.13 * heavy);
      oc.clearRect(0, 0, 900, 720);
      oc.save(); oc.beginPath(); oc.moveTo(0, 0); oc.lineTo(900, 0); oc.lineTo(900, OY - 6); oc.quadraticCurveTo(OX, OY + 34, 0, OY - 6); oc.closePath(); oc.clip();   // a flat base, a little round
      puffs.map(p => { const x = p.X * c + p.Z * s, z = p.Z * c - p.X * s, k = (1 + z / 1600) * S, g = p.grow ? easeOut(clamp((heavy * 1.12 - p.grow * 0.92) / 0.22)) : 1;
        return { p, x: OX + x * k, y: OY - p.Y * k, z, r: p.r * k * g * (1 + 0.045 * Math.sin(6.2832 * (t / 2.8 + p.ph))) }; }).filter(e => e.r > 1).sort((a, e) => a.z - e.z)
        .forEach(e => { const w = (1 - clamp(e.p.Y / 230)) * (0.22 + 0.5 * heavy), g = oc.createRadialGradient(e.x - 0.3 * e.r, e.y - 0.36 * e.r, 0.1 * e.r, e.x, e.y, e.r);   // a soft bump, not a ball
          const body = [247 - 74 * w, 249 - 66 * w, 252 - 50 * w];   // no dark rim: the puffs melt into one mass, only their lit sides show
          g.addColorStop(0, mixc([255, 255, 255], body, Math.min(1, 1.15 * w))); g.addColorStop(0.6, mixc(body, body, 0)); g.addColorStop(1, mixc(body, [body[0] * 0.95, body[1] * 0.95, body[2] * 0.96], 1));
          oc.fillStyle = g; oc.beginPath(); oc.arc(e.x, e.y, e.r, 0, 6.2832); oc.fill(); });
      oc.restore();
      oc.globalCompositeOperation = "source-atop";                 // light and shade over the whole cloud, inside its outline
      const sun = oc.createRadialGradient(OX - 130 * S, OY - 215 * S, 10, OX - 130 * S, OY - 215 * S, 300 * S); sun.addColorStop(0, "rgba(255,255,255,.75)"); sun.addColorStop(1, "rgba(255,255,255,0)"); oc.fillStyle = sun; oc.fillRect(0, 0, 900, 720);
      const side = oc.createLinearGradient(OX, 0, OX + 250 * S, 0); side.addColorStop(0, "rgba(64,74,100,0)"); side.addColorStop(1, `rgba(64,74,100,${(0.16 + 0.1 * heavy).toFixed(3)})`); oc.fillStyle = side; oc.fillRect(0, 0, 900, 720);
      const g = oc.createLinearGradient(0, OY - 130 * S, 0, OY + 28); g.addColorStop(0, "rgba(56,66,92,0)"); g.addColorStop(1, `rgba(48,60,92,${(0.34 + 0.3 * heavy).toFixed(3)})`); oc.fillStyle = g; oc.fillRect(0, 0, 900, 720);
      oc.globalCompositeOperation = "source-over";
    }
    const drops = Array.from({ length: 120 }, () => ({ X: -228 + 396 * rnd(), d: 2 * rnd() - 1, ph: rnd(), sp: 1.5 + 0.7 * rnd() }));   // x 144 to 540: clear of the labels
    const up = [], extra = F.vapour.counts[1] - F.vapour.counts[0];
    for (let i = 0; i < 30; i++) up.push(Object.assign(tumble(rnd), { kind: 1, t0: -1.3 + 2.1 * rnd(), dur: 1.5 + 0.3 * rnd(), x0: 104 + 112 * rnd(), y0: 1040 + 370 * rnd(), x1: ccx - 196 + 250 * rnd(), ring: 0 }));   // the vapour that makes the cloud
    q.fill.slice(1).forEach((r, k) => { for (let i = 0; i < extra; i++) up.push(Object.assign(tumble(rnd), { kind: 1, t0: r[0] - 1.8 + 0.1 * i, dur: 1.5, x0: 106 + 104 * rnd(), y0: 1280 + 120 * rnd(), x1: ccx - 196 + 250 * rnd(), ring: k + 1 })); });   // the extra vapour of each degree
    const marks = Rn.marks.map((m, k) => ({ m, y: base - m.v * per, ly: 1068 - k * 74, lab: text(b, "lab", m.label, { left: gx1 + 106, top: 1068 - k * 74 }) }));
    css(el("div", "tag", b, Rn.tag), { left: L, top: 566 });   // clear of the vapour that rises on the left
    f.fits = [text(b, "unit", Rn.foot, { right: 1080 - R, top: 1424 })];
    return { ...f, update(t) {
      const v = level(t), heavy = clamp((v - 100) / 14), hc = clamp((level(t + 0.55) - 100) / 14), wet = pour(t), ys = base - Math.max(0, v) * per;
      ctx.clearRect(0, 0, 1080, 1920); ctx.lineJoin = "round"; ctx.lineCap = "round";
      up.forEach(m => { const u = seg(t, m.t0, m.t0 + m.dur); if (u <= 0 || u >= 1) return;
        const e = easeInOut(u), x = m.x0 + (m.x1 - m.x0) * Math.pow(e, 4) + 10 * Math.sin(7 * u + m.ph) * (1 - e), y = m.y0 + (cby - 70 - m.y0) * e, r = 17 - 4 * u;   // straight up beside the gauge, then into the cloud
        ctx.globalAlpha = Math.min(1, u / 0.12) * (1 - seg(u, 0.84, 1));
        if (m.ring) { const gl = ctx.createRadialGradient(x, y, 0, x, y, 4 * r); gl.addColorStop(0, "rgba(226,87,31,.5)"); gl.addColorStop(1, "rgba(226,87,31,0)"); ctx.fillStyle = gl; ctx.beginPath(); ctx.arc(x, y, 4 * r, 0, 6.2832); ctx.fill(); }
        molecule(ctx, flat, m, x, y, r, t, m.ring); });
      ctx.globalAlpha = 1;
      const fall = (e, k) => { if (k >= 54 + 66 * heavy) return; const inside = Math.abs(ccx + e.X - gcx) < grx - 18 && Math.abs(e.d) <= 0.5, end = inside ? ys - 2 : base + 10 + 14 * e.d, y0 = cby - 10, p = (t * e.sp + e.ph) % 1, y = y0 + (end - y0) * p;
        const len = (36 + 30 * heavy) * (1 + 0.25 * e.d), tail = Math.min(len, y - y0);
        ctx.strokeStyle = col.wet; ctx.globalAlpha = wet * (0.42 + 0.2 * (e.d + 1)) * Math.min(1, p / 0.08) * (1 - seg(p, 0.95, 1)); ctx.lineWidth = (4.5 + 3 * heavy) * (1 + 0.25 * e.d);
        ctx.beginPath(); ctx.moveTo(ccx + e.X + 8 * tail / len, y - tail); ctx.lineTo(ccx + e.X, y); ctx.stroke(); };
      drops.forEach((e, k) => { if (e.d < -0.5) fall(e, k); });                                      // the rain behind the gauge
      ctx.globalAlpha = 1;
      ctx.beginPath(); ctx.moveTo(gx0, rim); ctx.lineTo(gx0, base); ctx.ellipse(gcx, base, grx, gry, 0, Math.PI, 0, true); ctx.lineTo(gx1, rim); ctx.ellipse(gcx, rim, grx, gry, 0, 0, Math.PI, true); ctx.closePath();
      ctx.fillStyle = "rgba(251,247,240,.9)"; ctx.fill();                                            // the glass
      if (v > 0.2) {
        const wg = ctx.createLinearGradient(gx0, 0, gx1, 0); wg.addColorStop(0, "#3a82d6"); wg.addColorStop(0.5, "#1c5cab"); wg.addColorStop(1, "#123f7d");
        ctx.beginPath(); ctx.moveTo(gx0 + 5, ys); ctx.lineTo(gx0 + 5, base - 2); ctx.ellipse(gcx, base - 2, grx - 5, gry - 3, 0, Math.PI, 0, true); ctx.lineTo(gx1 - 5, ys); ctx.ellipse(gcx, ys, grx - 5, gry - 3, 0, 0, Math.PI, false); ctx.closePath(); ctx.fillStyle = wg; ctx.fill();
        const sg = ctx.createLinearGradient(gx0, 0, gx1, 0); sg.addColorStop(0, "#9cc7f5"); sg.addColorStop(1, "#4d8fdb");
        ctx.beginPath(); ctx.ellipse(gcx, ys, grx - 5, gry - 3, 0, 0, 6.2832); ctx.fillStyle = sg; ctx.fill();   // the water's top is exactly at its mark
        for (let i = 0; i < 4; i++) { const p = (t * 1.7 + i / 4) % 1, rx = 8 + 30 * p; ctx.strokeStyle = `rgba(255,255,255,${(0.85 * (1 - p) * wet).toFixed(3)})`; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.ellipse(gcx + (-0.56 + 0.38 * i) * (grx - 30), ys + (i % 2 ? 4 : -3), rx, rx * 0.26, 0, 0, 6.2832); ctx.stroke(); }
      }
      drops.forEach((e, k) => { if (Math.abs(e.d) <= 0.5) fall(e, k); });                            // the rain that falls into it and beside it
      ctx.globalAlpha = 1; ctx.strokeStyle = col.ink; ctx.lineWidth = 6;
      ctx.beginPath(); ctx.moveTo(gx0, rim); ctx.lineTo(gx0, base); ctx.ellipse(gcx, base, grx, gry, 0, Math.PI, 0, true); ctx.lineTo(gx1, rim); ctx.stroke();
      ctx.lineWidth = 5; ctx.beginPath(); ctx.ellipse(gcx, rim, grx, gry, 0, 0, 6.2832); ctx.stroke();
      ctx.strokeStyle = "rgba(255,255,255,.6)"; ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(gx0 + 24, rim + 46); ctx.lineTo(gx0 + 24, base - 40); ctx.stroke();
      marks.forEach(o => { ctx.strokeStyle = col.ink; ctx.lineWidth = 5; ctx.beginPath(); ctx.ellipse(gcx, o.y, grx, gry, 0, -0.12, 0.95); ctx.stroke();
        ctx.strokeStyle = "rgba(46,33,24,.5)"; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(gx1 + 8, o.y); ctx.lineTo(gx1 + 96, o.ly + 28); ctx.stroke();
        const reached = v >= o.m.v - 0.05; css(o.lab, { fontWeight: reached ? "800" : "500", color: reached ? col.mark : col.ink, opacity: reached ? "1" : "0.55" }); });
      drops.forEach((e, k) => { if (e.d > 0.5) fall(e, k); });                                       // the rain in front
      ctx.globalAlpha = 1;
      cloud(t, hc, 0.74 + 0.26 * easeOut(seg(t, -0.2, 1.3)));
      ctx.save(); ctx.filter = "blur(1.4px)"; ctx.shadowColor = "rgba(46,33,24,.30)"; ctx.shadowBlur = 34; ctx.shadowOffsetY = 20; ctx.drawImage(off, ccx - OX, cby - OY); ctx.restore();
    } };
  }

  // ── 6: the Earth again, the question, the line to send on ──
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

  const builders = { hook, mean, pile, vapour, rain, answer };
  const scenes = C.scenes.map(sc => Object.assign(builders[sc.key](sc), { sc }));
  await document.fonts.ready;
  scenes.forEach(s => {
    s.root.style.display = "block";
    fit(s.lines, W, 54);
    fit([...s.head.querySelectorAll(".small")], W, 40);
    (s.fits || []).forEach(n => fit([n], W, 34));
    if (s.follow) fit(s.follow, W, 36);
    if (s.q) fit(s.q, 640, 44);
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
