/* «۲ درجه گرم‌تر، یعنی چه؟»: window.renderAt(t) draws the frame of time t (seconds) from /build/film.json, which
   src/twodeg2.py writes (every string, every number and the clock). Nothing is typed here; the only numbers this
   file writes are the running counts of its own drawings (boxes turned red, dots past the line), in Persian digits.
   Times inside a scene follow the narration script's lines (seconds after the scene's start). */
"use strict";
const L = 96, R = 924, W = 828, MID = (L + R) / 2;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const easeOut = p => 1 - Math.pow(1 - p, 3);
const easeInOut = p => p * p * (3 - 2 * p);
const bump = p => Math.sin(Math.PI * clamp(p));
const fa = s => String(s).replace(/\d/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]);
const SVGNS = "http://www.w3.org/2000/svg";
const DROP = "M0,-47 C10,-28 33,-8 33,14 A33,33 0 1,1 -33,14 C-33,-8 -10,-28 0,-47 Z";
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

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const C = F.cuts.a, col = F.colours;
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const progress = el("div", null, stage); progress.id = "progress";
  const segs = C.scenes.map(() => el("i", null, el("div", "seg", progress)));
  el("div", "pill", stage, F.pill);

  function frame(sc) {
    const root = el("div", "scene", stage);
    const head = el("div", "head", root);
    const lines = sc.title.split(" // ").map(s => { const ln = el("span", "line", head); marked(ln, s); return ln; });
    el("span", "small", head, sc.small);
    const body = css(el("div", "abs", root), { inset: "0" });
    el("div", "sources", root, F.source);
    return { root, head, lines, body, fits: [] };
  }

  // ── 1: the heat that came once in 50 years: three strips of 50 year-boxes ──
  function hook(sc) {
    const f = frame(sc), b = f.body, H = F.hook;
    const pop = [[-1, -1], [2.4, 4.0], [5.0, 8.0]];                 // when a strip's red boxes turn (the last at «چهارده بار میاد»)
    let y = 632;
    const strips = H.strips.map((s, j) => {
      const lab = text(b, "lab", s.label + ": ", { right: 1080 - R, top: y });
      const count = el("b", null, lab, s.count); css(count, { color: col.mark, fontWeight: "800" });
      const boxes = [];
      for (let k = 0; k < 50; k++) {
        const c = k % 25, r = Math.floor(k / 25);
        boxes.push(css(el("div", "abs", b), { left: R - (c + 1) * 33.12 + 2, top: y + 68 + r * 36, width: 29, height: 29, borderRadius: "7px", background: col.land }));
      }
      const range = s.range ? text(b, "unit", s.range, { right: 1080 - R, top: y + 68 + 76 }) : null;
      y += 68 + 76 + (s.range ? 56 : 14) + 22;
      return { s, count, boxes, range, t0: pop[j][0], t1: pop[j][1] };
    });
    f.fits = [text(b, "unit", H.key, { right: 1080 - R, top: y + 4 }), text(b, "unit", H.base, { right: 1080 - R, top: y + 56 })];
    return { ...f, update(t) {
      strips.forEach(st => {
        const n = st.s.hot.length;
        st.s.hot.forEach((k, i) => {
          const at = st.t0 < 0 ? -1 : st.t0 + (st.t1 - st.t0) * i / Math.max(1, n - 1), p = seg(t, at, at + 0.3), box = st.boxes[k];
          css(box, { background: p > 0 ? col.mark : col.land, scale: (1 + 0.5 * bump(p)).toFixed(3), boxShadow: p > 0 ? "0 0 0 3px rgba(160,49,41,.25)" : "none" });
        });
        const done = st.t0 < 0 ? 1 : seg(t, st.t1 + 0.1, st.t1 + 0.5);
        show(st.count, done); if (st.range) show(st.range, done);
      });
    } };
  }

  // ── 2: a mean of the whole Earth; the body's temperature (an analogy); land warms more than the ocean ──
  function mean(sc) {
    const f = frame(sc), b = f.body, M = F.mean;
    const mh = Math.round(W * (F.map.lat1 - F.map.lat0) / 360);
    const card = css(el("div", "card", b), { left: L, top: 626, width: W, height: mh });
    css(el("img", null, card), { filter: "saturate(1.1) brightness(1.06)" }).src = "/build/" + F.map.file;
    const sweep = css(el("div", "abs", card), { top: 0, width: 220, height: mh, background: "linear-gradient(90deg,rgba(255,244,214,0),rgba(255,244,214,.38),rgba(255,244,214,0))" });
    css(el("div", "chip", card, M.map_chip), { right: 14, bottom: 14 });
    // the body's thermometer (left), 36 to 40 degrees
    const gy = v => 1392 - (v - 36) * 72;
    const g1 = css(el("div", "abs", b), { inset: "0" });
    text(g1, "lab", M.body[0], { left: L, top: 1042 }).style.fontWeight = "700";
    css(el("div", "tag", g1, M.analogy), { left: L + 196, top: 1048 });
    css(el("div", "abs", g1), { left: 150, top: gy(40), width: 40, height: gy(36) - gy(40), borderRadius: "20px", background: col.land, boxShadow: "0 0 0 3px " + col.ink });
    const merc = css(el("div", "abs", g1), { left: 157, width: 26, borderRadius: "13px", background: col.mark });
    css(el("div", "abs", g1), { left: 136, top: gy(36) - 22, width: 68, height: 68, borderRadius: "50%", background: col.mark, boxShadow: "0 0 0 3px " + col.ink });
    const m37 = text(g1, "lab", M.body[1], { left: 232, top: gy(37) - 30 }), m39 = text(g1, "lab", M.body[2], { left: 232, top: gy(39) - 30 });
    css(m39, { color: col.mark, fontWeight: "800" });
    [37, 39].forEach(v => css(el("div", "abs", g1), { left: 196, top: gy(v) - 2, width: 26, height: 4, background: col.ink }));
    // land and ocean (right): the ocean's bar is 1, the land's 1.4 to 1.7
    const g2 = css(el("div", "abs", b), { inset: "0" });
    const unit = 190, x1 = R, lo = F.land_ocean[0], hi = F.land_ocean[1];
    text(g2, "lab", M.land[0], { right: 1080 - R, top: 1042 });
    const ocean = css(el("div", "abs", g2), { top: 1104, height: 44, borderRadius: "12px", background: col.wet });
    text(g2, "lab", M.land[1], { right: 1080 - R, top: 1168 });
    const land = css(el("div", "abs", g2), { top: 1230, height: 44, borderRadius: "12px", background: col.mark });
    const landHi = css(el("div", "abs", g2), { top: 1230, height: 44, borderRadius: "12px", background: "repeating-linear-gradient(135deg," + col.mark + " 0 8px,#d99a92 8px 16px)" });
    css(el("div", "abs unit wrap", g2, M.land_note), { left: 520, top: 1296, width: R - 520, fontWeight: "700", color: col.ink });   // two lines, clear of the thermometer
    return { ...f, update(t) {
      sweep.style.left = (-220 + (W + 220) * ((t / 5) % 1)) + "px";
      show(g1, easeOut(seg(t, 6.4, 7.0)));
      const v = 37 + 2 * easeInOut(seg(t, 7.8, 9.4));
      css(merc, { top: gy(v), height: gy(36) - gy(v) + 10 });
      show(m39, seg(t, 9.2, 9.6));
      show(g2, easeOut(seg(t, 10.2, 10.8)));
      const p = easeOut(seg(t, 10.6, 11.8));
      css(ocean, { left: x1 - unit * p, width: unit * p });
      css(landHi, { left: x1 - unit * hi * p, width: unit * hi * p });
      css(land, { left: x1 - unit * lo * p, width: unit * lo * p });
    } };
  }

  // ── 3: a pile of 100 summer days; the pile moves a little, the very hot days are counted (the drawing's own count) ──
  function pile(sc) {
    const f = frame(sc), b = f.body, P = F.pile;
    const s = css(svg("svg", { width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, b), { left: "0", top: "0" });
    const x0 = 128, pitch = 50, r = 11, dy = 25, base = 1310, lineX = x0 + P.line * pitch - pitch / 2;
    const ghost = svg("g", { opacity: 0 }, s), dots = [];
    P.cols.forEach((n, c) => { for (let k = 0; k < n; k++) {
      svg("circle", { cx: x0 + c * pitch, cy: base - k * dy - r - 4, r, fill: col.pale }, ghost);
      dots.push({ c, k, e: svg("circle", { cy: base - k * dy - r - 4, r, fill: col.wet }, s), at: 0.2 + c * 0.13 + k * 0.035 });
    } });
    svg("line", { x1: lineX, x2: lineX, y1: 880, y2: base + 4, stroke: col.ink, "stroke-width": 5, "stroke-dasharray": "14 10" }, s);
    svg("line", { x1: L, x2: R, y1: base, y2: base, stroke: col.ink, "stroke-width": 4, "stroke-linecap": "round" }, s);
    const chip = css(el("div", "abs big", b), { right: 1080 - R, top: 640, background: col.mark, color: col.paper, borderRadius: "16px", padding: "0 18px 6px", fontSize: "52px", lineHeight: "72px", fontWeight: "800" });
    css(el("div", "tag", b, P.tag), { left: L, top: 652 });
    const state = text(b, "lab", P.before, { right: 1080 - R, top: 738 }); state.style.fontWeight = "700";
    text(b, "unit", P.cold, { left: L, top: base + 14 }); text(b, "unit", P.hot, { right: 1080 - R, top: base + 14 });
    return { ...f, update(t) {
      const p = easeInOut(seg(t, 8.0, 10.6));
      let hot = 0;
      dots.forEach(d => {
        const x = x0 + (d.c + P.shift * p) * pitch, on = seg(t, d.at, d.at + 0.25), red = x >= lineX;
        if (red && on >= 1) hot += 1;
        d.e.setAttribute("cx", x.toFixed(2)); d.e.setAttribute("opacity", on.toFixed(3)); d.e.setAttribute("fill", red ? col.mark : col.wet);
        d.e.setAttribute("r", (r * (1 + (red ? 0.25 * bump(seg(t, 5.4, 6.2)) : 0))).toFixed(2));
      });
      ghost.setAttribute("opacity", (0.9 * p).toFixed(3));
      chip.textContent = P.chip + ": " + fa(hot) + " " + P.days;
      chip.style.scale = (1 + 0.1 * bump(seg(t, 10.6, 11.2))).toFixed(3);
      show(chip, seg(t, 2.6, 3.0));
      state.textContent = p > 0.5 ? P.after : P.before;
    } };
  }

  // ── 4: the report's numbers for the 50-year heat, and how much hotter ──
  function heat(sc) {
    const f = frame(sc), b = f.body, H = F.heat;
    const at = [0.4, 5.6, 8.6];
    const tiles = H.tiles.map((tl, j) => {
      const cx = R - 138 - j * 276, g = css(el("div", "abs", b), { left: cx - 126, top: 626, width: 252, height: 252, textAlign: "center" });
      css(el("div", "big", g, tl.n), { fontSize: "132px", lineHeight: "150px", color: j === 2 ? col.mark : col.ink });
      css(el("div", "lab", g, tl.label), { fontWeight: "700" });
      css(el("div", "unit ltr", g, tl.range), { direction: "rtl" });
      return g;
    });
    f.fits = [text(b, "unit", H.unit, { right: 1080 - R, top: 884 })];
    const g2 = css(el("div", "abs", b), { inset: "0" });
    text(g2, "lab", H.hotter_title, { right: 1080 - R, top: 962 }).style.fontWeight = "700";
    const bars = H.hotter.map((h, j) => {
      const y = 1030 + j * 78;
      text(g2, "lab", h.label, { right: 1080 - R, top: y });
      const bar = css(el("div", "abs", g2), { top: y + 8, height: 42, borderRadius: "12px", background: j === 2 ? col.mark : "#c98a80" });
      const val = css(text(g2, "lab ltr", h.value, { top: y }), { fontWeight: "800", direction: "rtl" });
      return { h, bar, val };
    });
    const note = css(el("div", "abs lab wrap", b, H.note), { left: L + 5, top: 1290, width: W - 10, padding: "10px 22px 14px", borderRadius: "20px", background: "#FBF7F0", boxShadow: "0 0 0 3px " + col.ink + ", 0 14px 26px rgba(46,33,24,.16)", fontSize: "42px", lineHeight: "60px" });
    return { ...f, update(t) {
      tiles.forEach((g, j) => { const p = easeOut(seg(t, at[j], at[j] + 0.5)); css(g, { opacity: p.toFixed(3), transform: `translateY(${(20 * (1 - p)).toFixed(2)}px)`, scale: (1 + 0.06 * bump(seg(t, at[j] + 0.5, at[j] + 1.0))).toFixed(3) }); });
      show(g2, easeOut(seg(t, 10.2, 10.8)));
      bars.forEach((o, j) => { const p = easeOut(seg(t, 10.5 + j * 0.25, 11.5 + j * 0.25)), w = 140 * o.h.v * p; css(o.bar, { left: R - 250 - w, width: w }); css(o.val, { right: 1080 - (R - 250 - w) + 14, opacity: p > 0.9 ? "1" : "0" }); });
      const q = easeOut(seg(t, 12.2, 12.8)); css(note, { opacity: q.toFixed(3), transform: `translateY(${(18 * (1 - q)).toFixed(2)}px)` });
    } };
  }

  // ── 5: heavy rain: wetter at each level of warming ──
  function rain(sc) {
    const f = frame(sc), b = f.body, Rn = F.rain;
    const s = css(svg("svg", { width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, b), { left: "0", top: "0" });
    const fall = Array.from({ length: 14 }, (_, i) => ({ e: svg("path", { d: DROP, fill: col.wet, opacity: 0.22 }, s), x: L + 30 + (i * 197) % (W - 60), ph: (i * 0.37) % 1, sp: 0.5 + (i % 4) * 0.12 }));
    f.fits = [css(text(b, "lab", Rn.title, { right: 1080 - R, top: 632 }), { fontWeight: "700" })];
    const base = 1240, top = 760;
    const bars = Rn.bars.map((br, j) => {
      const cx = R - 138 - j * 276, hmax = (base - top - 90) * br.v / 14;
      const bar = css(el("div", "abs", b), { left: cx - 80, width: 160, borderRadius: "20px 20px 6px 6px", background: col.wet });
      const val = css(text(b, "big", br.value, { left: cx, top: 0 }), { fontSize: "62px", lineHeight: "76px", translate: "-50% 0", color: col.wet });
      css(text(b, "lab", br.label, { left: cx, top: base + 10 }), { translate: "-50% 0", fontWeight: "700" });
      css(text(b, "unit", br.times, { left: cx, top: base + 66 }), { translate: "-50% 0" });
      return { bar, val, hmax, at: 0.5 + j * 1.2 };
    });
    css(el("div", "abs", b), { left: L, top: base, width: W, height: 4, background: col.ink, borderRadius: "2px" });
    f.fits.push(text(b, "unit", Rn.unit, { right: 1080 - R, top: base + 128 }));
    return { ...f, update(t) {
      fall.forEach(d => { const p = (t * d.sp + d.ph) % 1; d.e.setAttribute("transform", `translate(${d.x},${700 + 520 * p}) scale(0.34)`); d.e.setAttribute("opacity", (0.26 * Math.sin(Math.PI * p)).toFixed(3)); });
      bars.forEach(o => { const p = easeOut(seg(t, o.at, o.at + 1.0)), h = o.hmax * p; css(o.bar, { top: base - h, height: h }); css(o.val, { top: base - h - 84, opacity: p > 0.2 ? "1" : "0" }); });
    } };
  }

  // ── 6: droughts in drying regions: times per 10 years, with the range ──
  function drought(sc) {
    const f = frame(sc), b = f.body, Dr = F.drought;
    const unit = 600 / Dr.vmax, xv = v => R - 170 - v * unit;
    const rows = Dr.rows.map((rw, j) => {
      const y = 640 + j * 152;
      css(text(b, "lab", rw.label, { right: 1080 - R, top: y }), { fontWeight: "700" });
      const bar = css(el("div", "abs", b), { top: y + 66, height: 44, borderRadius: "12px", background: j === 3 ? col.dry : "#b08a63" });
      const val = css(text(b, "lab", rw.value, { top: y + 58 }), { fontWeight: "800", color: j === 3 ? col.mark : col.ink });
      const wh = rw.hi > rw.lo ? css(el("div", "abs", b), { left: xv(rw.hi), top: y + 86, width: (rw.hi - rw.lo) * unit, height: 4, background: col.ink }) : null;
      const caps = rw.hi > rw.lo ? [rw.lo, rw.hi].map(v => css(el("div", "abs", b), { left: xv(v) - 2, top: y + 74, width: 4, height: 28, background: col.ink })) : [];
      return { rw, bar, val, wh, caps, at: 0.4 + j * 0.9 };
    });
    f.fits = [text(b, "unit", Dr.unit, { right: 1080 - R, top: 640 + 4 * 152 + 6 })];
    return { ...f, update(t) {
      rows.forEach(o => {
        const p = easeOut(seg(t, o.at, o.at + 0.8)), w = o.rw.v * unit * p;
        css(o.bar, { left: R - 170 - w, width: w });
        css(o.val, { right: 1080 - R, opacity: p > 0.5 ? "1" : "0" });
        const q = seg(t, o.at + 0.7, o.at + 1.1); if (o.wh) show(o.wh, q); o.caps.forEach(c => show(c, q));
      });
    } };
  }

  // ── 7: the summary and the question ──
  function answer(sc) {
    const f = frame(sc), b = f.body, A = F.answer;
    const rows = A.rows.map((line, k) => css(text(b, "big", line, { left: MID, top: 668 + k * 100 }), { fontSize: "64px", lineHeight: "90px", fontWeight: "800", translate: "-50% 0" }));
    const card = css(el("div", "abs", b), { left: MID - 340, top: 1000, width: 680, height: 290, borderRadius: "44px", background: col.mark, color: col.paper, textAlign: "center", boxShadow: "0 18px 34px rgba(160,49,41,.3)", paddingTop: "22px" });
    A.question.forEach(line => css(el("div", null, card, line), { fontWeight: "800", fontSize: "60px", lineHeight: "82px", whiteSpace: "nowrap" }));
    const tail = css(el("div", "abs", b), { left: 716, top: 1260, width: 50, height: 50, background: col.mark, rotate: "45deg", borderRadius: "10px" });
    const follow = css(el("div", "abs", b), { left: L, top: 1332, width: W, textAlign: "center", fontWeight: "800", fontSize: "46px", lineHeight: "62px", whiteSpace: "nowrap" });
    const w = A.follow.split(" "), cut = w.indexOf("که");
    const fl = [el("span", null, follow, w.slice(0, cut).join(" ")), el("span", null, follow, w.slice(cut).join(" "))];
    fl.forEach(x => { x.style.display = "block"; });
    f.fits = rows; f.follow = fl;
    return { ...f, update(t) {
      rows.forEach((r, k) => { const p = easeOut(seg(t, 0.4 + k * 0.8, 0.9 + k * 0.8)); css(r, { opacity: p.toFixed(3), transform: `translateY(${(22 * (1 - p)).toFixed(2)}px)` }); });
      const q = seg(t, 3.6, 4.1), pulse = 1 + 0.018 * Math.sin(2 * Math.PI * Math.max(0, t - 4.1) / 1.6), sc2 = (0.86 + 0.14 * easeOut(q)) * (q >= 1 ? pulse : 1);
      css(card, { opacity: easeOut(q).toFixed(3), scale: sc2.toFixed(4) }); css(tail, { opacity: easeOut(q).toFixed(3), scale: sc2.toFixed(4) });
      show(follow, easeOut(seg(t, 5.0, 5.6)));
    } };
  }

  const builders = { hook, mean, pile, heat, rain, drought, answer };
  const scenes = C.scenes.map(sc => Object.assign(builders[sc.key](sc), { sc }));
  await document.fonts.ready;
  await Promise.all([...document.images].map(im => im.decode().catch(() => null)));
  scenes.forEach(s => {
    s.root.style.display = "block";
    fit(s.lines, W, 54);
    fit([...s.head.querySelectorAll(".small")], W, 40);
    (s.fits || []).forEach(n => fit([n], W, 36));
    if (s.follow) fit(s.follow, W, 36);
    s.root.style.display = "none";
  });
  window.renderAt = function (t) {
    t = clamp(t, 0, C.end - 1e-6);
    let i = 0;
    while (i + 1 < C.scenes.length && t >= C.scenes[i + 1].start) i += 1;
    const sc = C.scenes[i], dt = t - sc.start;
    scenes.forEach((s, k) => { s.root.style.display = k === i ? "block" : "none"; });
    scenes[i].update(dt, sc.length);
    const enter = i === 0 ? 1 : easeOut(seg(dt, 0, 0.35));
    css(scenes[i].body, { opacity: (0.25 + 0.75 * enter).toFixed(3), transform: `translateY(${(14 * (1 - enter)).toFixed(2)}px)` });
    segs.forEach((s, k) => { s.style.width = (k < i ? 100 : k > i ? 0 : 100 * dt / sc.length).toFixed(3) + "%"; });
    return i;
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
