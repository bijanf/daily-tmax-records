/* «یخچال‌های البرز»: window.renderAt(t) draws the frame of time t (seconds) from /build/film.json, which src/alborzice.py
   writes (every string, every number, the clock and the pictures). Nothing is typed here; the numbers in this file are
   pixels of the layout and fractions of a scene's length. Every frame is a pure function of t (frames are rendered out of
   order by several workers): the sunlight packets, the meltwater drops, the ring's arrow are closed formulas of t.
   film.html?overlay=1 draws ONLY the overlay texts of the two face scenes on a transparent page. */
"use strict";
const L = 96, R = 924, W = 828, MID = 510;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, p) => a + (b - a) * p;
const easeOut = p => 1 - Math.pow(1 - clamp(p), 3);
const ease = p => { p = clamp(p); return p * p * (3 - 2 * p); };
const bump = p => Math.sin(Math.PI * clamp(p));
const fa = s => String(s).replace(/\d/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]).replace(".", "٫");
const SVGNS = "http://www.w3.org/2000/svg";
function el(tag, cls, parent, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; if (parent) parent.appendChild(e); return e; }
function svg(tag, attrs, parent) { const e = document.createElementNS(SVGNS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function css(e, o) { for (const k in o) e.style[k] = typeof o[k] === "number" ? o[k] + "px" : o[k]; return e; }
function marked(parent, s) {
  s.split(/(\{[^}]*\})/).forEach(part => { if (!part) return; if (part[0] === "{") el("span", "key", parent, part.slice(1, -1)); else parent.appendChild(document.createTextNode(part)); });
}
function fit(nodes, limit, floor, lh = 1.4) {
  if (!nodes.length) return;
  let size = parseFloat(getComputedStyle(nodes[0]).fontSize);
  const wide = () => Math.max(...nodes.map(n => n.scrollWidth));
  while (wide() > limit && size > floor) { size -= 1; nodes.forEach(n => css(n, { fontSize: size + "px", lineHeight: Math.round(size * lh) + "px" })); }
}
const show = (e, p) => { p = clamp(p); e.style.opacity = p.toFixed(3); e.style.visibility = p <= 0.001 ? "hidden" : "visible"; };
const full = () => ({ width: 1080, height: 1920, viewBox: "0 0 1080 1920" });
// a window in seconds: in over fi from a (whole at 0), out over fo before b (whole at the scene's end)
const win = (dt, a, b, len, fi = 0.28, fo = 0.22) => dt < a || dt > b ? 0 : Math.min(a <= 1e-6 ? 1 : seg(dt, a, a + fi), b >= len - 1e-6 ? 1 : 1 - seg(dt, b - fo, b));
const mixc = (a, c, w) => `rgb(${a.map((v, i) => Math.round(v + (c[i] - v) * w)).join(",")})`;
function rng(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let x = Math.imul(a ^ (a >>> 15), 1 | a); x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; }; }

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const OV = new URLSearchParams(location.search).get("overlay") === "1";
  if (OV) document.documentElement.classList.add("ov");
  const C = F.cuts.a, col = F.colours, END = C.end, NS = C.scenes.length;
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const pending = [];
  const progress = el("div", null, stage); progress.id = "progress";
  const segs = C.scenes.map(() => el("i", null, el("div", "seg", progress)));
  el("div", "tagbar", stage, F.tag);

  // ── helpers that build parts of a scene ──
  function frame(sc) {
    const root = el("div", "scene", stage), base = el("div", "scene base", root), ov = el("div", "scene", root);
    return { root, base, ov, sc, len: sc.length, fits: [], heads: [], smalls: [], sources: [] };
  }
  function heads(f, photo, top) {                       // the headline steps of a scene: one block at a time, one key phrase in the red box
    f.sc.heads.forEach(h => {
      const wrap = css(el("div", "head" + (photo ? " onphoto" : ""), f.base), top ? { top } : {}), card = el("div", "hc", wrap);
      const lines = h.text.split(" // ").map(s => { const ln = el("span", "line", card); marked(ln, s); return ln; });
      f.heads.push({ h, wrap, lines });
    });
  }
  function smalls(f, o, wrap) {                         // the small lines (positions o: css)
    f.sc.smalls.forEach(s => { const e = css(el("div", "small" + (wrap ? " wrap" : ""), f.base, s.text), o); f.smalls.push({ s, e }); });
  }
  function sources(f, photo) {
    f.sc.sources.forEach(s => { const e = el("div", "sources" + (photo ? " onphoto" : ""), f.base, s.text); f.sources.push({ s, e }); });
  }
  function tick(f, dt) {                                // headlines, small lines and sources follow the clock
    f.heads.forEach(x => show(x.wrap, win(dt, x.h.a * f.len, x.h.b * f.len, f.len)));
    f.smalls.forEach(x => show(x.e, win(dt, x.s.a * f.len, x.s.b * f.len, f.len)));
    f.sources.forEach(x => show(x.e, win(dt, x.s.a * f.len, x.s.b * f.len, f.len)));
  }
  function layer(f, files, o = {}) {                    // whole-frame pictures, cross-faded by a position along the list
    const box = el("div", "layer", f.base);
    const imgs = files.map(n => { const im = el("img", null, box); im.src = "/build/" + n; pending.push(im.decode().catch(() => {})); return im; });
    return { box, imgs, set(pos, scale) {
      const n = imgs.length; pos = clamp(pos, 0, n - 1);
      const a = Math.floor(pos + 1e-9), fr = pos - a, w = ease((fr - 0.3) / 0.4);
      imgs.forEach((im, i) => { const o = i === a ? 1 : i === a + 1 ? w : 0; im.style.opacity = o.toFixed(3); im.style.visibility = o <= 0.001 ? "hidden" : "visible"; });
      box.style.transform = `scale(${(scale || 1).toFixed(4)})`;
      return Math.min(n - 1, a + (w > 0.5 ? 1 : 0));    // the summer that dominates the picture now
    } };
  }
  const chip = (f, cls, o) => css(el("div", "chip " + cls, f.base), o);
  const years = k => F[k].years, files = k => years(k).map(y => F.pics[k][y.year]);

  // the bar chart of measured summers: slots by Persian year (oldest at the right), a bar only for a summer in the data
  function chart(f, parent, k, o) {
    const Y = years(k), p0 = Y[0].py, p1 = Y[Y.length - 1].py, n = p1 - p0 + 1, slot = W / n, bw = o.bw;
    const X = py => R - (py - p0 + 0.5) * slot, H = v => v * o.h / o.vmax;
    const g = el("div", "abs", parent); css(g, { left: 0, top: 0, width: 1080, height: 1920, zIndex: "3" });
    const s = css(svg("svg", full(), g), { left: 0, top: 0 });
    svg("line", { x1: L - 6, x2: R + 6, y1: o.base + 1.5, y2: o.base + 1.5, stroke: col.ink, "stroke-width": 3, "stroke-linecap": "round" }, s);
    for (let py = Math.ceil(p0 / 10) * 10; py <= p1; py += 10) {
      svg("line", { x1: X(py), x2: X(py), y1: o.base + 2, y2: o.base + 12, stroke: col.ink, "stroke-width": 3 }, s);
      css(el("div", "lab", g, fa(py)), { left: X(py), top: o.base + 12, fontSize: o.lab, lineHeight: o.lab * 1.3 + "px", translate: "-50% 0", fontWeight: "700" });
    }
    const bars = Y.map(y => svg("rect", { x: X(y.py) - bw / 2, width: bw, rx: Math.min(4, bw / 3), fill: col.bar }, s));
    const run = o.run, rmax = Math.max(...Y.filter(y => y.py >= run[0] && y.py <= run[1]).map(y => y.km2));
    const brk = svg("path", { fill: "none", stroke: col.mark, "stroke-width": 4, "stroke-linecap": "round", "stroke-linejoin": "round" }, s);
    const bx0 = X(run[0]) + slot / 2, bx1 = X(run[1]) - slot / 2, by = o.base - H(rmax) - (o.gap || 16);
    brk.setAttribute("d", `M${bx0},${by + 12} L${bx0},${by} L${bx1},${by} L${bx1},${by + 12}`);
    const bl = css(el("div", "lab", g, F[k].bracket), { left: Math.max(86, (bx0 + bx1) / 2 - 105), top: by - o.lab * 1.4 - 6, fontSize: o.lab, lineHeight: o.lab * 1.3 + "px", color: col.mark, fontWeight: "800" });
    const meds = (o.meds || []).map(m => {                // a median line of an era (drawn from the right), a label chip above the plot
      const a0 = Math.max(m.range[0], p0), a1 = Math.min(m.range[1], p1), xa = X(a0) + slot / 2, xb = X(a1) - slot / 2, y = o.base - H(m.v);
      const ln = svg("line", { x1: xa, x2: xa, y1: y, y2: y, stroke: col.ink, "stroke-width": 4, "stroke-dasharray": "12 8", "stroke-linecap": "round" }, s);
      const cn = svg("line", { x1: xa - 50, x2: xa - 50, y1: o.base - o.h - 8, y2: y, stroke: col.ink, "stroke-opacity": 0.45, "stroke-width": 2.5 }, s);
      const lb = css(el("div", "chip", g, m.label), { left: (xa + xb) / 2, top: o.base - o.h - 8 - 44, fontSize: 30, lineHeight: "40px", translate: "-50% 0", padding: "0 14px 2px", fontWeight: "700" });
      return { xa, xb, y, ln, cn, lb };
    });
    return { g, update(d) {                               // d: grow (0..1 per bar), cur (index or -1), red (0..1), med (0..1)
      Y.forEach((y, i) => {
        const gr = ease(d.grow[i]), hh = Math.max(0, H(y.km2) * gr), isRun = y.py >= run[0] && y.py <= run[1];
        bars[i].setAttribute("y", (o.base - hh).toFixed(1)); bars[i].setAttribute("height", hh.toFixed(1));
        bars[i].setAttribute("fill", d.red > 0.5 && isRun ? col.mark : i === d.cur ? col.ink : col.bar);
      });
      brk.setAttribute("opacity", d.red.toFixed(3)); show(bl, d.red);
      meds.forEach(m => { const p = ease(d.med); m.ln.setAttribute("x2", (m.xa + (m.xb - m.xa) * p).toFixed(1)); m.ln.setAttribute("y1", m.y); m.ln.setAttribute("y2", m.y);
        m.ln.setAttribute("opacity", clamp(p * 6).toFixed(3)); m.cn.setAttribute("opacity", (0.9 * seg(p, 0.5, 1)).toFixed(3)); show(m.lb, seg(p, 0.3, 0.8)); });
    } };
  }
  const grows = (Y, a, w) => Y.map((_, k) => k <= a ? 1 : k === a + 1 ? w : 0);   // bars follow the picture: the next bar rises while its picture fades in

  // ── 1 hook: Damavand's end of summer, rewound to the oldest summer ──
  function hook(sc) {
    const f = frame(sc), Y = years("dam"), n = Y.length, NO = F.pics.orbit || 0;
    // the mountain turns: F.pics.orbit frames (src/alborzice3d.py --orbit), the summers running back and the camera settling
    // on the view of the next scenes; one <img>, its file set for the frame and awaited (window.WAIT), so nothing is preloaded
    const lay = NO ? null : layer(f, files("dam"));
    const box = NO ? el("div", "layer", f.base) : null, im = NO ? el("img", null, box) : null;
    let shown = -1;
    heads(f, true); sources(f, true);
    const yc = chip(f, "", { left: L, top: 600 });           // on the left: the white lies on the right-hand flank
    f.update = (dt, u) => {
      const pos = (n - 1) * (1 - seg(u, 0.06, 0.94));
      let cur;
      if (NO) {
        const k = Math.round(clamp(u) * (NO - 1)), a = Math.floor(pos + 1e-9), w = ease((pos - a - 0.3) / 0.4);
        cur = Math.min(n - 1, a + (w > 0.5 ? 1 : 0));
        if (k !== shown) { shown = k; im.src = "/build/orbit/f" + String(k).padStart(4, "0") + ".jpg"; window.WAIT = im.decode().catch(() => {}); }
      } else cur = lay.set(pos, 1 + 0.06 * u);
      yc.textContent = F.dam.chip + fa(Y[cur].py); tick(f, dt);
    };
    return f;
  }
  // ── 2 face1: the oldest summer, still pushing in; the overlay: the name tag and one subtitle line ──
  function face1(sc) {
    const f = frame(sc), lay = layer(f, [files("dam")[0]]);
    heads(f, true); sources(f, true);
    const tg = css(el("div", "ovcard", f.ov), { right: 156, top: 1290, padding: "8px 30px 14px", textAlign: "right" });   // under the chin
    css(el("div", null, tg, F.face.name), { fontWeight: "900", fontSize: "52px", lineHeight: "68px" });
    css(el("div", null, tg, F.face.role), { fontWeight: "500", fontSize: "34px", lineHeight: "46px", color: "#4a3a2e" });
    const sb = css(el("div", "ovcard", f.ov), { right: 156, top: 1440, padding: "6px 26px 12px", fontWeight: "700", fontSize: "38px", lineHeight: "52px", textAlign: "right" });
    const sbl = F.face.sub.split(" // ").map(t => { const l = el("span", "l", sb); marked(l, t); return l; });
    f.fits.push(...sbl);
    const t_in = (F.face.tag_at || 0.6) / f.len;            // the tag comes once the owner is on screen
    f.update = (dt, u) => {
      lay.set(0, (F.pics.orbit ? 1 : 1.06) + 0.04 * u); tick(f, dt);
      show(tg, easeOut(seg(u, t_in + 0.03, t_in + 0.10))); const s0 = (F.face.sub_at || 0) / f.len || t_in + 0.14; show(sb, easeOut(seg(u, s0, s0 + 0.06)));
    };
    return f;
  }
  // ── 3 dam: the summers run forward, counter and bars in step ──
  function dam(sc) {
    const f = frame(sc), Y = years("dam"), n = Y.length, D = F.dam, lay = layer(f, files("dam"));
    heads(f, true); sources(f, true);
    css(el("div", "cardbox", f.base), { left: L - 22, top: 1146, width: W + 44, height: 336 });
    smalls(f, { right: 156, top: 1160, width: W, textAlign: "right", fontSize: "32px", lineHeight: "42px" }, true);
    const ch = chart(f, f.base, "dam", { base: 1400, h: 120, vmax: 3.3, bw: 14, lab: 34, run: D.run, gap: 14 });
    const yc = chip(f, "", { left: L, top: 600 });
    const cn = css(el("div", "chip dark", f.base), { left: L, top: 690, padding: "4px 30px 16px", textAlign: "center" });
    const num = css(el("div", null, cn), { fontWeight: "900", fontSize: "120px", lineHeight: "132px" });
    css(el("div", null, cn, D.unit), { fontWeight: "500", fontSize: "34px", lineHeight: "44px" });
    f.update = (dt, u) => {
      const pos = (n - 2) * seg(u, 0.03, 0.5) + seg(u, 0.78, 0.86), a = Math.min(n - 1, Math.floor(pos + 1e-9)), w = ease((pos - a - 0.3) / 0.4);
      const cur = lay.set(pos, 1), red = ease(seg(u, 0.57, 0.64));
      yc.textContent = D.chip + fa(Y[cur].py); num.textContent = fa(Y[cur].km2.toFixed(2));
      cn.style.scale = (1 + 0.05 * bump(seg(pos - a, 0.3, 0.7))).toFixed(3);
      ch.update({ grow: grows(Y, a, a < n - 1 ? w : 0), cur: red > 0.5 ? -1 : cur, red, med: 0 });
      tick(f, dt);
    };
    return f;
  }
  // ── 4 takht: the top-down picture, a big bar chart, the two medians ──
  function takht(sc) {
    const f = frame(sc), Y = years("takht"), n = Y.length, T = F.takht;
    const pic = css(el("div", "win", f.base), { left: 0, top: 480, width: 1080, height: 560, borderRadius: 0 });
    const lay = layer(f, []); f.base.removeChild(lay.box);
    const imgs = files("takht").map(nm => { const im = el("img", null, pic); im.src = "/build/" + nm; pending.push(im.decode().catch(() => {})); return im; });
    const set = pos => { const a = Math.floor(pos + 1e-9), w = ease((pos - a - 0.3) / 0.4);
      imgs.forEach((im, i) => { const o = i === a ? 1 : i === a + 1 ? w : 0; im.style.opacity = o.toFixed(3); im.style.visibility = o <= 0.001 ? "hidden" : "visible"; });
      return Math.min(n - 1, a + (w > 0.5 ? 1 : 0)); };
    heads(f, false); sources(f, false);
    const pl = chip(f, "dark", { right: 156, top: 500, fontSize: 60, lineHeight: "80px", padding: "0 24px 6px" }); pl.textContent = T.place; f.base.removeChild(pl); pic.appendChild(pl); css(pl, { right: 60, top: 20 });
    const p2 = css(el("div", "chip", pic, T.place2), { right: 60, top: 118, fontSize: 30, lineHeight: "40px", fontWeight: "700", padding: "0 14px 2px" });
    const yc = css(el("div", "chip", pic), { left: 40, top: 20 });
    const ch = chart(f, f.base, "takht", { base: 1372, h: 250, vmax: 2.8, bw: 14, lab: 34, run: T.run, gap: 70,
      meds: [{ range: T.early, v: T.median_early, label: T.med_early }, { range: T.late, v: T.median_late, label: T.med_late }] });
    smalls(f, { right: 156, top: 1432 }, false);
    f.fits.push(...f.smalls.map(x => x.e));
    f.update = (dt, u) => {
      const pos = (n - 2) * seg(u, 0.26, 0.48) + seg(u, 0.84, 0.90), a = Math.min(n - 1, Math.floor(pos + 1e-9)), w = ease((pos - a - 0.3) / 0.4);
      imgs.forEach(im => { im.style.transformOrigin = "50% 30%"; im.style.scale = (1 + 0.05 * u).toFixed(4); });
      const cur = set(pos), red = ease(seg(u, 0.70, 0.76)), g = grows(Y, a, a < n - 1 ? w : 0);
      g[0] *= seg(u, 0.20, 0.27); show(ch.g, seg(u, 0.0, 0.08));
      yc.textContent = T.chip + fa(Y[cur].py);
      ch.update({ grow: g, cur: red > 0.5 || u < 0.2 ? -1 : cur, red, med: seg(u, 0.50, 0.60) });
      tick(f, dt);
    };
    return f;
  }

  // ── a small 3D kit on a 2D canvas: points are [x, y, z] with y up; the camera looks a little down and swings slowly ──
  function canvas(parent) { const cv = css(el("canvas", "abs", parent), { left: "0", top: "0", width: 1080, height: 1920 }); cv.width = 1080; cv.height = 1920; return cv; }
  function camera(cx, cy, scale, yaw, pitch, dist) {
    const cw = Math.cos(yaw), sw = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const rot = p => { const x = p[0] * cw + p[2] * sw, z = p[2] * cw - p[0] * sw; return [x, p[1] * cp - z * sp, p[1] * sp + z * cp]; };
    const pro = p => { const r = rot(p), k = dist / (dist - r[2]) * scale; return [cx + r[0] * k, cy - r[1] * k, r[2], k]; };
    return { rot, pro, dist };
  }
  function ball(ctx, x, y, r, light, body, shade) {      // a lit sphere: the light comes from the upper left
    const g = ctx.createRadialGradient(x - 0.36 * r, y - 0.42 * r, 0.05 * r, x, y, r);
    g.addColorStop(0, light); g.addColorStop(0.52, body); g.addColorStop(1, shade);
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
  }
  const SUN = ["#fff2c9", "#ff9a2e", "#c4560c"], BLUE = ["#ffffff", "#a8d0fa", "#4d8fdb"], DROP = ["#bcd8fc", "#1c5cab", "#0b2c5e"];
  const norm = v => { const m = Math.hypot(...v); return v.map(x => x / m); };
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

  // ── 5 mech: two slabs on a slope under the sun; ten packets of sunlight on each; the ring of the feedback ──
  function mech(sc) {
    const f = frame(sc), M = F.mech, len = sc.len = sc.length, cv = canvas(f.base), ctx = cv.getContext("2d"), rnd = rng(7);
    heads(f, false); sources(f, false); smalls(f, { right: 156, top: 1444 }, false); f.fits.push(...f.smalls.map(x => x.e));
    const TH = 0.2, cT = Math.cos(TH), sT = Math.sin(TH), A = 0.62, HH = 0.34, D = 0.5, U0 = [0.86, -0.86];
    const toW = (u, v, w) => [u * cT - v * sT, u * sT + v * cT, w], dirW = n => [n[0] * cT - n[1] * sT, n[0] * sT + n[1] * cT, n[2]];
    const LIGHT = norm([0.3, 1, 0.6]), SUNP = [0.0, 1.95, -0.5], NT = dirW([0, 1, 0]);
    const N = 10, FL = 0.03, IMP0 = 0.034, DI = 0.043, SPEED = 2.5;           // fractions of the scene: a packet's flight, the first impact, the gap between rounds
    const ev = [0, 1].map(s => Array.from({ length: N }, (_, k) => {
      const bounce = s === 0 ? k !== M.snow_sink : k === M.ice_bounce, ui = (-0.42 + 0.84 * rnd()) * A, wi = (-0.6 + 1.2 * rnd()) * D, jx = (rnd() - 0.5) * 0.5, jz = (rnd() - 0.5) * 0.2;
      const I = toW(U0[s] + ui, HH, wi), S = [SUNP[0] + jx, SUNP[1], SUNP[2] + jz], d = norm([I[0] - S[0], I[1] - S[1], I[2] - S[2]]), dn = dot(d, NT);
      return { s, k, bounce, imp: (IMP0 + DI * k + 0.012 * s) * len, I, S, r: [d[0] - 2 * dn * NT[0], d[1] - 2 * dn * NT[1], d[2] - 2 * dn * NT[2]], ui };
    }));
    const all = ev.flat();
    const counts = (t, s) => ev[s].filter(e => e.bounce && t >= e.imp).length;
    const heat = (t, s) => ev[s].reduce((a, e) => a + (e.bounce ? 0 : 0.1 * ease(seg(t, e.imp, e.imp + 0.6))), 0);
    // labels under the slabs (placed where the slabs stand before they shrink)
    const c0 = camera(540, 1010, 236, 0, 0.42, 7.5), under = U0.map(u => c0.pro(toW(u, -0.2, 0.95)));
    const ly = Math.max(under[0][1], under[1][1]) + 22;
    const names = [M.snow, M.ice].map((s, i) => css(el("div", "lab", f.base, s), { left: under[i][0], top: ly, fontSize: 40, lineHeight: "54px", translate: "-50% 0", fontWeight: "800" }));
    const cnts = [0, 1].map(i => css(el("div", "lab", f.base), { left: under[i][0], top: ly + 56, fontSize: 38, lineHeight: "52px", translate: "-50% 0" }));
    const cdig = cnts.map((c, i) => { const d = css(el("span", null, c), { fontSize: "64px", fontWeight: "900", color: i ? "#2E2118" : col.mark }); el("span", null, c, " " + M.of); return d; });
    const pcts = [0, 1].map(i => css(el("div", "chip", f.base, M.pct[i]), { left: under[i][0], top: ly + 116, translate: "-50% 0", fontSize: 46, lineHeight: "62px", fontWeight: "900", color: i ? "#2E2118" : col.mark }));
    // the ring
    const RC = [540, 1245], RR = 140, ang = [-Math.PI / 2, Math.PI / 6, 5 * Math.PI / 6];
    const rpos = [{ left: RC[0], top: RC[1] - RR - 92, translate: "-50% 0" }, { right: 156, top: RC[1] + 96 }, { left: L, top: RC[1] + 96 }];
    const words = M.ring.map((s, i) => css(el("div", "chip", f.base, s), Object.assign({ fontSize: 46, lineHeight: "62px" }, rpos[i])));
    const T0 = 0.62, T1 = 1.0;
    const theta = tau => -Math.PI / 2 + 0.9 * tau + 0.5 * 1.15 * tau * tau;          // the arrow's angle: it turns faster and faster
    f.update = (dt, u) => {
      const t = dt, sh = ease(seg(u, 0.60, 0.68)), ringp = ease(seg(u, 0.64, 0.72));
      const yaw = (-0.1 + 0.2 * Math.sin(6.2832 * t / 13)), cam = camera(540, lerp(1010, 745, sh), lerp(236, 150, sh), yaw, 0.42, 7.5);
      const P = (x, y, z) => cam.pro([x, y, z]);
      ctx.clearRect(0, 0, 1080, 1920); ctx.lineJoin = "round"; ctx.lineCap = "round";
      // the sun: a disc and soft rays that breathe
      const sp = P(...SUNP), sa = 1 - sh;
      if (sa > 0.01) { ctx.save(); ctx.globalAlpha = sa; const rs = 54 + 4 * Math.sin(3 * t), g = ctx.createRadialGradient(sp[0], sp[1], 0, sp[0], sp[1], rs * 3.2);
        g.addColorStop(0, "rgba(255,190,70,.75)"); g.addColorStop(1, "rgba(255,190,70,0)"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(sp[0], sp[1], rs * 3.2, 0, 6.2832); ctx.fill();
        ctx.strokeStyle = "rgba(255,150,40,.9)"; ctx.lineWidth = 6; for (let i = 0; i < 12; i++) { const a = 0.52 * i + 0.1 * t, r0 = rs + 12, r1 = rs + 30 + 8 * Math.sin(2 * t + i); ctx.beginPath(); ctx.moveTo(sp[0] + r0 * Math.cos(a), sp[1] + r0 * Math.sin(a)); ctx.lineTo(sp[0] + r1 * Math.cos(a), sp[1] + r1 * Math.sin(a)); ctx.stroke(); }
        ball(ctx, sp[0], sp[1], rs, ...SUN); ctx.restore(); }
      // faces of a box (local frame), lit by the sun, the visible ones only
      const vis = (nn, mid) => -nn[0] * mid[0] - nn[1] * mid[1] + nn[2] * (cam.dist - mid[2]) > 0;
      function poly(pts, fill, stroke) { ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 3; ctx.stroke(); } }
      function box(u0, a, h, d, v0, top, side, hot, edge) {
        const c = (u, v, w) => toW(u0 + u, v, w), faces = [
          [[0, 1, 0], [c(-a, h, -d), c(a, h, -d), c(a, h, d), c(-a, h, d)], 1],
          [[0, 0, 1], [c(-a, v0, d), c(a, v0, d), c(a, h, d), c(-a, h, d)], 0],
          [[1, 0, 0], [c(a, v0, d), c(a, v0, -d), c(a, h, -d), c(a, h, d)], 0],
          [[-1, 0, 0], [c(-a, v0, -d), c(-a, v0, d), c(-a, h, d), c(-a, h, -d)], 0],
          [[0, 0, -1], [c(a, v0, -d), c(-a, v0, -d), c(-a, h, -d), c(a, h, -d)], 0]];
        faces.forEach(([n, pts, isTop]) => {
          const nw = dirW(n), mid = cam.rot(pts.reduce((m, p) => [m[0] + p[0] / 4, m[1] + p[1] / 4, m[2] + p[2] / 4], [0, 0, 0]));
          if (!vis(cam.rot(nw), mid)) return;
          const s = 0.6 + 0.4 * Math.max(0, dot(nw, LIGHT)), base = isTop ? top : side, rgb = base.map(x => Math.min(255, x * s));
          poly(pts.map(p => P(...p)), mixc(rgb, [255, 112, 30], hot * (isTop ? 0.30 : 0.12)), edge);
        });
      }
      // the slope (ground), then the slabs far to near
      const GU = 1.62, GD = 0.98;
      ctx.save(); ctx.filter = "blur(14px)"; ctx.fillStyle = "rgba(46,33,24,.28)";
      U0.forEach(u => { const pts = [[u - A - 0.06, 0, -D - 0.04], [u + A + 0.1, 0, -D - 0.04], [u + A + 0.1, 0, D + 0.1], [u - A - 0.06, 0, D + 0.1]].map(p => P(...toW(p[0], 0.01, p[2]))); poly(pts, "rgba(46,33,24,.30)"); });
      ctx.restore();
      box(0, GU, 0, GD, -0.22, [214, 201, 179], [150, 134, 110], 0, "rgba(46,33,24,.35)");
      const order = [0, 1].sort((a, b) => P(U0[a], 0, 0)[2] - P(U0[b], 0, 0)[2]);
      order.forEach(s => {
        const hs = heat(t, s), top = s === 0 ? [255, 255, 255] : [62, 80, 108], side = s === 0 ? [214, 226, 242] : [40, 52, 74], c = P(...toW(U0[s], HH / 2, 0));
        if (hs > 0.02) { const g = ctx.createRadialGradient(c[0], c[1], 10, c[0], c[1], 260 * c[3] / 250); g.addColorStop(0, `rgba(255,120,40,${(0.55 * hs).toFixed(3)})`); g.addColorStop(1, "rgba(255,120,40,0)"); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(c[0], c[1], 260 * c[3] / 250, 0, 6.2832); ctx.fill(); }
        box(U0[s], A, HH, D, 0, top, side, Math.min(1, hs * 1.15), "rgba(46,33,24,.4)");
        if (s === 0) { ctx.save(); ctx.globalAlpha = 0.5; ctx.strokeStyle = "#fff"; ctx.lineWidth = 5; const a = P(...toW(U0[0] - 0.5, HH, -D + 0.08)), b = P(...toW(U0[0] + 0.1, HH, -D + 0.08)); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); ctx.restore(); }
      });
      // the packets, drops and bounced rays, far ones first
      const items = [];
      all.forEach(e => {
        const t0 = e.imp - FL * len, tf = (t - t0) / (FL * len);
        if (tf > 0 && tf < 1) { const p = [0, 1, 2].map(i => lerp(e.S[i], e.I[i], tf)), q = [0, 1, 2].map(i => lerp(e.S[i], e.I[i], Math.max(0, tf - 0.18))); items.push({ k: "in", p: P(...p), q: P(...q) }); return; }
        const tau = t - e.imp;
        if (tau >= 0 && tau < 0.25) { const fl = 1 - tau / 0.25, c = P(...e.I); ctx.strokeStyle = `rgba(255,${e.bounce ? 255 : 200},${e.bounce ? 255 : 120},${(0.8 * fl).toFixed(3)})`; ctx.lineWidth = 5; ctx.beginPath(); ctx.ellipse(c[0], c[1], (10 + 44 * (1 - fl)) * c[3] / 250, (4 + 16 * (1 - fl)) * c[3] / 250, 0, 0, 6.2832); ctx.stroke(); }
        if (e.bounce && tau >= 0 && tau < 0.95) { const p = [0, 1, 2].map(i => e.I[i] + e.r[i] * SPEED * tau), q = [0, 1, 2].map(i => e.I[i] + e.r[i] * SPEED * Math.max(0, tau - 0.12)); items.push({ k: "out", p: P(...p), q: P(...q), a: 1 - seg(tau, 0.5, 0.95) }); }
        if (!e.bounce && tau >= 0 && tau < 0.3) { const p = [0, 1, 2].map(i => e.I[i] - NT[i] * 0.09 * tau / 0.3); items.push({ k: "sink", p: P(...p), a: 1 - tau / 0.3 }); }
        if (!e.bounce) {                                      // the meltwater: it slides down the slab's top, falls off its low edge
          const td = tau - 0.4, run = e.ui + A, ts = run / 0.45;
          if (td > 0 && td < ts + 0.45) { let p; if (td < ts) p = toW(U0[e.s] + e.ui - 0.45 * td, HH + 0.02, e.I[2]); else { const g = td - ts, b = toW(U0[e.s] - A, HH + 0.02, e.I[2]); p = [b[0] - 0.1 * g, b[1] - 0.5 * 3.4 * g * g, b[2]]; }
            items.push({ k: "drop", p: P(...p), a: 1 - seg(td, ts + 0.22, ts + 0.42) }); }
        }
      });
      items.sort((a, b) => a.p[2] - b.p[2]);
      items.forEach(it => {
        const x = it.p[0], y = it.p[1], k = it.p[3] / 250;
        if (it.k === "in" || it.k === "out") {
          const tail = it.k === "in" ? "255,150,40" : "150,200,255";
          ctx.save(); ctx.globalAlpha = it.k === "out" ? it.a : 1; const g = ctx.createLinearGradient(it.q[0], it.q[1], x, y); g.addColorStop(0, `rgba(${tail},0)`); g.addColorStop(1, `rgba(${tail},.85)`);
          ctx.strokeStyle = g; ctx.lineWidth = 15 * k; ctx.beginPath(); ctx.moveTo(it.q[0], it.q[1]); ctx.lineTo(x, y); ctx.stroke();
          ball(ctx, x, y, 17 * k, ...(it.k === "in" ? SUN : BLUE)); ctx.restore();
        } else if (it.k === "sink") { ctx.save(); ctx.globalAlpha = it.a; ball(ctx, x, y, 17 * k * it.a, ...SUN); ctx.restore(); }
        else { ctx.save(); ctx.globalAlpha = it.a; ball(ctx, x, y, 12 * k, ...DROP); ctx.restore(); }
      });
      // counters and labels
      [0, 1].forEach(i => {
        cdig[i].textContent = fa(counts(t, i));
        show(names[i], 1 - sh); show(cnts[i], 1 - sh);
        const py = lerp(ly + 116, 880, sh); css(pcts[i], { top: py }); show(pcts[i], easeOut(seg(u, 0.49, 0.55)));
      });
      // the ring: three words, a ring, an arrow that turns faster and faster
      const rp = ringp;
      if (rp > 0.01) {
        const tau = Math.max(0, t - T0 * len), th = theta(tau);
        ctx.save(); ctx.globalAlpha = rp; ctx.strokeStyle = "#d6cab6"; ctx.lineWidth = 16; ctx.beginPath(); ctx.arc(RC[0], RC[1], RR, 0, 6.2832); ctx.stroke();
        for (let i = 0; i < 16; i++) { const a0 = th - 1.9 * (i + 1) / 16, a1 = th - 1.9 * i / 16; ctx.strokeStyle = `rgba(160,49,41,${(0.95 * (1 - i / 16)).toFixed(3)})`; ctx.lineWidth = 16; ctx.lineCap = "butt"; ctx.beginPath(); ctx.arc(RC[0], RC[1], RR, a0, a1 + 0.01); ctx.stroke(); }
        const hx = RC[0] + RR * Math.cos(th), hy = RC[1] + RR * Math.sin(th), tx = -Math.sin(th), ty = Math.cos(th), nx = Math.cos(th), ny = Math.sin(th);
        ctx.fillStyle = col.mark; ctx.beginPath(); ctx.moveTo(hx + 34 * tx, hy + 34 * ty); ctx.lineTo(hx - 10 * tx + 26 * nx, hy - 10 * ty + 26 * ny); ctx.lineTo(hx - 10 * tx - 26 * nx, hy - 10 * ty - 26 * ny); ctx.closePath(); ctx.fill();
        ctx.restore();
        words.forEach((w, i) => { const d = (((th - ang[i]) % 6.2832) + 6.2832) % 6.2832, near = d < 1.15 || d > 6.2832 - 0.35;
          w.style.background = near ? col.mark : "#FBF7F0"; w.style.color = near ? col.paper : col.ink; show(w, rp); w.style.scale = (near ? 1.07 : 1).toFixed(3); });
      } else words.forEach(w => show(w, 0));
      tick(f, dt);
    };
    return f;
  }

  // ── 6 budget: the top-down picture, summer 1374 then 1404, and a glass gauge that falls 20 cm a year ──
  function budget(sc) {
    const f = frame(sc), B = F.budget, len = sc.length, T = F.takht, Y = years("takht");
    const yi = py => Y.findIndex(y => y.py === py), i0 = yi(B.early_py), i1 = yi(B.late_py);
    const wn = css(el("div", "win", f.base), { left: L, top: 480, height: 760, width: W });
    const im = [i0, i1].map(i => { const e = el("img", null, wn); e.src = "/build/" + F.pics.takht[Y[i].year]; pending.push(e.decode().catch(() => {})); return e; });
    heads(f, false); sources(f, false); smalls(f, { right: 156, top: 1398, width: W, textAlign: "right", fontSize: "32px", lineHeight: "44px" }, true);
    const yc = css(el("div", "chip", wn), { left: 22, bottom: 22 });
    const co = css(el("div", "chip red", wn), { fontSize: 36, lineHeight: "50px", fontWeight: "800" });
    const arr = css(svg("svg", { width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, f.base), { left: 0, top: 0 });
    const cl = svg("path", { fill: "none", stroke: "#fff", "stroke-width": 6, "stroke-linecap": "round", "stroke-linejoin": "round", filter: "drop-shadow(0 2px 3px rgba(0,0,0,.6))" }, arr);
    const ring = svg("circle", { r: 26, fill: "none", stroke: "#fff", "stroke-width": 6, filter: "drop-shadow(0 2px 3px rgba(0,0,0,.6))" }, arr);
    const gcv = canvas(f.base), gx = gcv.getContext("2d");
    const G = B.gauge, steps = G.to_py - G.from_py, gcx = 668, grx = 50, gry = 16, gTop = 560, gBot = 1180, per = (gBot - gTop) / (steps + 0.6);
    const gyc = css(el("div", "chip", f.base), { left: gcx, top: 1204, translate: "-50% 0", fontSize: 44 });
    const glab = css(el("div", "lab", f.base, G.label), { right: 156, top: gTop + per * 0.2, fontSize: 30, lineHeight: "40px", fontWeight: "700", maxWidth: 150, whiteSpace: "normal", textAlign: "right" });
    f.fits.push(...f.smalls.map(x => x.e));
    const T1 = 0.60, T2 = 0.80;                          // the gauge's year ticks run between these fractions of the scene
    f.update = (dt, u) => {
      const sw = ease(seg(u, 0.34, 0.40)), shr = ease(seg(u, 0.55, 0.63)), pw = lerp(W, 500, shr), ph = 760, D = (1.6 + 0.07 * u) * W;
      css(wn, { width: pw }); const ccx = pw / 2, ccy = ph / 2;
      im.forEach((e, i) => { css(e, { width: D, height: D, left: ccx - D / 2, top: ccy - D / 2, objectFit: "fill" }); e.style.opacity = (i ? sw : 1).toFixed(3); });
      yc.textContent = B.chip + fa(Y[sw > 0.5 ? i1 : i0].py);
      const tx = L + ccx + (B.xy[0] - 0.5) * D * 0.3, ty = 480 + ccy + (B.xy[1] - 0.5) * D * 0.3;       // the callout points at the white (xy in picture fractions)
      co.textContent = sw > 0.5 ? B.callout[1] : B.callout[0]; css(co, { left: Math.max(14, (pw - 26 - 0) / 2 - 150), top: 22 });
      co.style.left = "auto"; co.style.right = "20px"; co.style.maxWidth = (pw - 40) + "px"; co.style.whiteSpace = "normal"; co.style.textAlign = "center";
      const cw = co.offsetWidth, chh = co.offsetHeight, cxm = L + pw - 20 - cw / 2, cym = 480 + 22 + chh;
      cl.setAttribute("d", `M${cxm},${cym + 4} L${tx},${ty - 30}`); ring.setAttribute("cx", tx); ring.setAttribute("cy", ty);
      // the gauge
      const gp = seg(u, 0.55, 0.62), k = clamp((u - T1) / (T2 - T1)) * steps, kk = Math.floor(k + 1e-9), fr = k - kk, lv = Math.min(steps, kk + ease(seg(fr, 0.0, 0.45)));
      const rim = gTop, base = gBot, ys = rim + 0.3 * per + lv * per;
      gx.clearRect(0, 0, 1080, 1920); gx.globalAlpha = gp; gx.lineJoin = "round";
      if (gp > 0.01) {
        gx.beginPath(); gx.moveTo(gcx - grx, rim); gx.lineTo(gcx - grx, base); gx.ellipse(gcx, base, grx, gry, 0, Math.PI, 0, true); gx.lineTo(gcx + grx, rim); gx.ellipse(gcx, rim, grx, gry, 0, 0, Math.PI, true); gx.closePath();
        gx.fillStyle = "rgba(251,247,240,.9)"; gx.fill();
        const wg = gx.createLinearGradient(gcx - grx, 0, gcx + grx, 0); wg.addColorStop(0, "#3a82d6"); wg.addColorStop(0.5, "#1c5cab"); wg.addColorStop(1, "#123f7d");
        gx.beginPath(); gx.moveTo(gcx - grx + 5, ys); gx.lineTo(gcx - grx + 5, base - 2); gx.ellipse(gcx, base - 2, grx - 5, gry - 3, 0, Math.PI, 0, true); gx.lineTo(gcx + grx - 5, ys); gx.ellipse(gcx, ys, grx - 5, gry - 3, 0, 0, Math.PI, false); gx.closePath(); gx.fillStyle = wg; gx.fill();
        const sg = gx.createLinearGradient(gcx - grx, 0, gcx + grx, 0); sg.addColorStop(0, "#9cc7f5"); sg.addColorStop(1, "#4d8fdb"); gx.beginPath(); gx.ellipse(gcx, ys, grx - 5, gry - 3, 0, 0, 6.2832); gx.fillStyle = sg; gx.fill();
        gx.strokeStyle = col.ink; gx.lineWidth = 6; gx.beginPath(); gx.moveTo(gcx - grx, rim); gx.lineTo(gcx - grx, base); gx.ellipse(gcx, base, grx, gry, 0, Math.PI, 0, true); gx.lineTo(gcx + grx, rim); gx.stroke();
        gx.lineWidth = 5; gx.beginPath(); gx.ellipse(gcx, rim, grx, gry, 0, 0, 6.2832); gx.stroke();
        for (let i = 0; i <= steps; i++) { const y = rim + 0.3 * per + i * per; gx.strokeStyle = col.ink; gx.lineWidth = i === 0 || i === 1 ? 5 : 3; gx.beginPath(); gx.moveTo(gcx + grx, y); gx.lineTo(gcx + grx + 22, y); gx.stroke(); }
        gx.strokeStyle = col.mark; gx.lineWidth = 4; const y0 = rim + 0.3 * per, y1 = y0 + per; gx.beginPath(); gx.moveTo(gcx + grx + 32, y0); gx.lineTo(gcx + grx + 44, y0); gx.lineTo(gcx + grx + 44, y1); gx.lineTo(gcx + grx + 32, y1); gx.stroke();
        gx.strokeStyle = "rgba(255,255,255,.6)"; gx.lineWidth = 8; gx.beginPath(); gx.moveTo(gcx - grx + 18, rim + 40); gx.lineTo(gcx - grx + 18, base - 40); gx.stroke();
      }
      show(gyc, gp); gyc.textContent = fa(G.from_py + Math.min(steps, kk + (fr > 0.2 ? 1 : 0)));
      show(glab, seg(u, 0.64, 0.7));
      tick(f, dt);
    };
    return f;
  }

  // ── 7 thr: sixteen dots, one of them the glaciers; a warming bar from 0 (right) with the estimate band ──
  function thr(sc) {
    const f = frame(sc), Th = F.thr, len = sc.length, s = css(svg("svg", full(), f.base), { left: 0, top: 0 });
    heads(f, false); sources(f, false); smalls(f, { right: 156, top: 1250, width: W, textAlign: "right", fontSize: "34px", lineHeight: "48px" }, true);
    const pitch = W / Th.dots, dots = [], DY = 640;
    for (let i = 0; i < Th.dots; i++) dots.push(svg("circle", { cx: R - pitch / 2 - i * pitch, cy: DY, r: 18, fill: i === Th.red ? col.mark : "#8f8272" }, s));
    const rx = R - pitch / 2 - Th.red * pitch;
    const ll = svg("line", { x1: rx, x2: rx, y1: DY + 28, y2: DY + 78, stroke: col.mark, "stroke-width": 4 }, s);
    const lab = css(el("div", "chip red", f.base, Th.red_label), { left: Math.max(L, rx - 150), top: DY + 80, fontSize: 40, lineHeight: "56px" });
    const bx = d => R - d / Th.max * W, BY = 1010, BH = 70;
    svg("rect", { x: L, y: BY, width: W, height: BH, rx: 20, fill: col.land }, s);
    const band = svg("rect", { x: bx(Th.band[1]), y: BY - 26, width: bx(Th.band[0]) - bx(Th.band[1]), height: BH + 52, rx: 14, fill: col.mark, "fill-opacity": 0.2, stroke: col.mark, "stroke-opacity": 0.5, "stroke-width": 3, "stroke-dasharray": "10 8" }, s);
    const fill = svg("rect", { y: BY, height: BH, rx: 20, fill: col.bar }, s);
    const mk = svg("path", { fill: "none", stroke: col.mark, "stroke-width": 8, "stroke-linecap": "round" }, s); mk.setAttribute("d", `M${bx(Th.mark)},${BY - 28} L${bx(Th.mark)},${BY + BH + 12}`);
    const axl = [0, 1, 2, 3].map(d => css(el("div", "lab", f.base, fa(d)), { left: bx(d), top: BY + BH + 24, fontSize: 38, lineHeight: "50px", translate: "-50% 0", color: d === Th.mark ? col.mark : col.ink, fontWeight: d === Th.mark ? "900" : "700" }));
    const now = css(el("div", "chip dark", f.base, Th.now_label), { fontSize: 38, lineHeight: "52px", translate: "-50% 0", top: BY - 100 });
    const bl = css(el("div", "chip", f.base, Th.band_label), { top: BY + BH + 84, fontSize: 36, lineHeight: "50px", fontWeight: "700" });
    f.fits.push(...f.smalls.map(x => x.e));
    f.update = (dt, u) => {
      dots.forEach((d, i) => { const p = easeOut(seg(u, 0.02 + i * 0.012, 0.07 + i * 0.012)); d.setAttribute("opacity", p.toFixed(3)); d.setAttribute("r", (i === Th.red ? 24 + 4 * bump(seg(u, 0.2, 0.3)) : 18) * (0.4 + 0.6 * p)); });
      show(lab, seg(u, 0.20, 0.26)); ll.setAttribute("opacity", seg(u, 0.2, 0.26));
      const v = Th.now * ease(seg(u, 0.27, 0.40)); fill.setAttribute("x", bx(v)); fill.setAttribute("width", R - bx(v));
      css(now, { left: bx(v) }); show(now, seg(u, 0.30, 0.38));
      const bp = ease(seg(u, 0.47, 0.56)); band.setAttribute("opacity", bp.toFixed(3)); mk.setAttribute("opacity", (ease(seg(u, 0.45, 0.52)) * (u > 0.56 ? 0.78 + 0.22 * Math.cos(6.2832 * (u - 0.56) * f.len / 1.6) : 1)).toFixed(3)); show(bl, bp);
      css(bl, { left: (bx(Th.band[0]) + bx(Th.band[1])) / 2, translate: "-50% 0" });
      tick(f, dt);
    };
    return f;
  }

  // ── 8 fut: two glass columns of ice that melt down to 29 % and 2 % ──
  function fut(sc) {
    const f = frame(sc), Fu = F.fut, len = sc.length, cv = canvas(f.base), g = cv.getContext("2d");
    heads(f, false); sources(f, false); smalls(f, { right: 156, top: 1430 }, false); f.fits.push(...f.smalls.map(x => x.e));
    const cx = [690, 330], rx = 108, ry = 22, top = 600, base = 1180, H = base - top;
    const labs = Fu.cols.map((c, i) => css(el("div", "lab", f.base, c.label), { left: cx[i], top: base + 56, fontSize: 46, lineHeight: "62px", translate: "-50% 0", fontWeight: "800" }));
    const res = Fu.cols.map((c, i) => css(el("div", "chip red", f.base, c.text), { left: cx[i], top: base + 128, fontSize: 40, lineHeight: "56px", translate: "-50% 0" }));
    f.update = (dt, u) => {
      g.clearRect(0, 0, 1080, 1920); g.lineJoin = "round";
      Fu.cols.forEach((c, i) => {
        const p = ease(seg(u, 0.12, i ? 0.52 : 0.42)), keep = 1 - (1 - c.keep) * p, h = H * keep, ys = base - h, x0 = cx[i] - rx, x1 = cx[i] + rx;
        g.save(); g.filter = "blur(20px)"; g.fillStyle = "rgba(46,33,24,.3)"; g.beginPath(); g.ellipse(cx[i] + 14, base + 26, rx + 20, ry + 8, 0, 0, 6.2832); g.fill(); g.restore();
        g.beginPath(); g.moveTo(x0, top); g.lineTo(x0, base); g.ellipse(cx[i], base, rx, ry, 0, Math.PI, 0, true); g.lineTo(x1, top); g.ellipse(cx[i], top, rx, ry, 0, 0, Math.PI, true); g.closePath(); g.fillStyle = "rgba(251,247,240,.9)"; g.fill();
        if (h > 2) {
          const wg = g.createLinearGradient(x0, 0, x1, 0); wg.addColorStop(0, "#dff0fb"); wg.addColorStop(0.45, "#aad4f2"); wg.addColorStop(1, "#6fa9d8");
          g.beginPath(); g.moveTo(x0 + 6, ys); g.lineTo(x0 + 6, base - 2); g.ellipse(cx[i], base - 2, rx - 6, ry - 3, 0, Math.PI, 0, true); g.lineTo(x1 - 6, ys); g.ellipse(cx[i], ys, rx - 6, ry - 3, 0, 0, Math.PI, false); g.closePath(); g.fillStyle = wg; g.fill();
          g.fillStyle = "#e9f6ff"; g.beginPath(); g.ellipse(cx[i], ys, rx - 6, ry - 3, 0, 0, 6.2832); g.fill();
          g.strokeStyle = "rgba(255,255,255,.7)"; g.lineWidth = 3; for (let j = 1; j < 5; j++) { const y = ys + h * j / 5; g.beginPath(); g.moveTo(x0 + 10, y); g.lineTo(x0 + 10 + 40 * ((j * 37) % 3 + 1) / 3, y - 8); g.stroke(); }
          for (let j = 0; j < 3; j++) { const q = (dt * 0.9 + j / 3 + i * 0.2) % 1, dy = ys + 10 + (base - ys - 10) * q * q; if (p > 0.02 && p < 0.98) { g.fillStyle = "rgba(28,92,171,.85)"; g.beginPath(); g.ellipse(cx[i] - 40 + 40 * j, dy, 6, 9, 0, 0, 6.2832); g.fill(); } }
        }
        g.strokeStyle = col.ink; g.lineWidth = 6; g.beginPath(); g.moveTo(x0, top); g.lineTo(x0, base); g.ellipse(cx[i], base, rx, ry, 0, Math.PI, 0, true); g.lineTo(x1, top); g.stroke();
        g.lineWidth = 5; g.beginPath(); g.ellipse(cx[i], top, rx, ry, 0, 0, 6.2832); g.stroke();
        g.strokeStyle = "rgba(255,255,255,.6)"; g.lineWidth = 9; g.beginPath(); g.moveTo(x0 + 24, top + 50); g.lineTo(x0 + 24, base - 40); g.stroke();
        g.setLineDash([12, 9]); g.strokeStyle = "rgba(46,33,24,.5)"; g.lineWidth = 3; g.beginPath(); g.moveTo(x0 - 10, top + 6); g.lineTo(x1 + 10, top + 6); g.stroke(); g.setLineDash([]);
        show(res[i], seg(u, i ? 0.52 : 0.42, (i ? 0.52 : 0.42) + 0.1));
      });
      tick(f, dt);
    };
    return f;
  }

  // ── 9 close: the 1404 picture; the overlay: the subtitle, the card, the follow line ──
  function close(sc) {
    const f = frame(sc), Y = years("dam"), lay = layer(f, [F.pics.close || files("dam")[Y.length - 1]]), Cc = F.close;
    sources(f, true);
    const lines = (parent, text) => text.split(" // ").map(s => { const l = el("span", "l", parent); marked(l, s); return l; });
    const sub = css(el("div", "ovcard", f.ov), { right: 156, top: 1230, padding: "10px 30px 18px", fontWeight: "800", fontSize: "46px", lineHeight: "64px" }), sl = lines(sub, Cc.sub);
    const card = css(el("div", "ovcard", f.ov), { left: L, top: 1120, width: W, padding: "18px 20px 30px", fontWeight: "800", fontSize: "60px", lineHeight: "88px" }), cl = lines(card, Cc.card);
    const fol = css(el("div", "ovcard", f.ov), { left: L, top: 1180, width: W, padding: "16px 20px 26px", fontWeight: "800", fontSize: "52px", lineHeight: "74px" }), fl = lines(fol, Cc.follow);
    f.fits.push(...sl, ...cl, ...fl);
    f.update = (dt, u) => {
      lay.set(0, 1 + 0.04 * u); tick(f, dt);
      const w = (a, b) => win(dt, a * f.len, b * f.len, f.len, 0.35, 0.3);
      show(sub, w(0, Cc.cuts[0])); show(card, w(Cc.cuts[0], Cc.cuts[1])); show(fol, w(Cc.cuts[1], 1));
    };
    return f;
  }

  const builders = { hook, face1, dam, takht, mech, budget, thr, fut, close };
  const scenes = C.scenes.map(sc => Object.assign(builders[sc.key](sc), { sc }));
  await Promise.all(pending);
  await document.fonts.load('800 70px "Vazirmatn"', "آخرِ تابستان ۱۴۰۴"); await document.fonts.load('900 60px "Vazirmatn"', "آخرِ ۱۴۰۴"); await document.fonts.ready;
  scenes.forEach(s => {
    s.root.style.display = "block";
    s.heads.forEach(x => fit(x.lines, W - (x.wrap.classList.contains("onphoto") ? 64 : 0), 54, 1.4));
    s.smalls.forEach(x => { if (!x.e.classList.contains("wrap")) fit([x.e], W, 30); });
    fit(s.fits.filter(e => !e.classList.contains("wrap")), W - 60, 30);
    s.root.style.display = "none";
  });
  window.renderAt = function (t) {
    t = clamp(t, 0, END - 1e-6);
    let i = 0;
    while (i + 1 < NS && t >= C.scenes[i + 1].start) i += 1;
    const sc = C.scenes[i], u0 = (t - sc.start) / sc.length;
    // a narrated scene turns with the narrator: knots [time fraction, picture fraction] bend the scene's own clock
    let u = u0, p = [0, 0];
    for (const q of (sc.warp || []).concat([[1, 1]])) { if (u0 <= q[0]) { u = p[1] + (q[1] - p[1]) * (u0 - p[0]) / Math.max(1e-9, q[0] - p[0]); break; } p = q; }
    const dt = u * sc.length;
    const mix = i > 0 && !OV && !sc.hard_in ? clamp((t - sc.start) / 0.3) : 1;   // hard_in: the scene before was the owner on camera      // 0.3 s over the last moment of the scene before
    scenes.forEach((s, k) => { s.root.style.display = k === i || (k === i - 1 && mix < 1) ? "block" : "none"; s.root.style.opacity = "1"; });
    if (mix < 1) { scenes[i - 1].update(C.scenes[i - 1].length - 1e-4, 1 - 1e-6); scenes[i].root.style.opacity = mix.toFixed(3); }
    scenes[i].update(dt, u);
    segs.forEach((s, k) => { s.style.width = (k < i ? 100 : k > i ? 0 : 100 * u0).toFixed(3) + "%"; });
    const wait = window.WAIT; window.WAIT = null;
    return wait ? wait.then(() => i) : i;                  // a frame that set a picture is ready when the picture is
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
