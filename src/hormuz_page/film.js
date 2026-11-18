/* The Hormuz NO2 film (film.html): window.renderAt(t) draws the frame of time t (seconds) from /build/film.json,
   which src/hormuz.py writes (every string, number, the clock, the colours, the colour scale). Nothing is typed here;
   the numbers in this file are pixels of the layout. Every frame is a pure function of t (the frames are rendered out
   of order by several workers).
   One map through the whole film: the Persian Gulf, the Strait of Hormuz and the Gulf of Oman together, a wide panel
   in the middle of the stage, last year's picture or this year's.
   The scenes: a last year's NO2 wiped to this year's and back; b what the colour is, with the names of the countries,
   the two seas and the strait; c the ships: the lane drawn through the strait with dots moving along it (as many dots
   for last year as its count is larger than this year's one), the two counts in a strip, the map wiped to this year;
   e this year's map, the six places inside the Persian Gulf with their change and the three places on the Gulf of
   Oman by name; f the six places' change in every part of the year (before, during, after) as columns on the map's
   lower half; h the question; then frame 0 again. */
"use strict";
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const ease = p => p * p * (3 - 2 * p);
const easeOut = p => 1 - Math.pow(1 - clamp(p), 3);
const lerp = (a, b, p) => a + (b - a) * p;
const SVGNS = "http://www.w3.org/2000/svg";
const MERC = lat => Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360));
function el(tag, cls, parent, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; if (parent) parent.appendChild(e); return e; }
function svg(tag, attrs, parent) { const e = document.createElementNS(SVGNS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function css(e, o) { for (const k in o) e.style[k] = typeof o[k] === "number" ? o[k] + "px" : o[k]; return e; }
function marked(parent, s) {
  s.split(/(\{[^}]*\})/).forEach(part => { if (!part) return; if (part[0] === "{") el("span", "key", parent, part.slice(1, -1)); else parent.appendChild(document.createTextNode(part)); });
}
function show(e, p) { p = clamp(p); e.style.opacity = p.toFixed(3); e.style.visibility = p <= 0.001 ? "hidden" : "visible"; }
function fit(nodes, limit, floor, lh) {                 // limit = the width of the nodes' own box (a block's scrollWidth is never below it)
  let size = parseFloat(getComputedStyle(nodes[0]).fontSize);
  const wide = () => Math.max(...nodes.map(n => n.scrollWidth));
  while (wide() > limit && size > floor) { size -= 1; nodes.forEach(n => css(n, { fontSize: size + "px", lineHeight: Math.round(size * lh) + "px" })); }
}
// a window in time: in over fi from a, out over fo before b (a window that starts at 0 is whole in frame 0)
const win = (t, a, b, fi = 0.3, fo = 0.25) => t < a || t > b ? 0 : Math.min(a <= 0 ? 1 : seg(t, a, a + fi), 1 - seg(t, b - fo, b));
const WIDE = 888, LOW = 828;                             // the headline's column; the column below y 1000
const PT = 496;                                          // the panel's top on the stage (the headline stands above it, the sources under it)

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const C = F.clock, Wd = F.words, col = F.colours, END = F.end, P = F.places;
  window.CUT = { name: "a", end: END };
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  document.body.classList.add(F.scale.palette);           // the look of the map (the colour bar's card follows it)
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const THEN = await load(F.wide.then), NOW = await load(F.wide.now);
  await Promise.all(['900 84px "Vazirmatn"', '800 44px "Vazirmatn"', '700 50px "Vazirmatn"', '500 34px "Vazirmatn"', '400 96px "Lalezar"'].map(f => document.fonts.load(f, "خ۱")));

  const ORDER = ["a", "b", "c", "e", "f", "h"];
  const BOX = F.wide.box;                                // W, S, E, N of the panel (Web Mercator)
  const PH = Math.round(1080 * (MERC(BOX[3]) - MERC(BOX[1])) / ((BOX[2] - BOX[0]) * Math.PI / 180));     // the panel's height
  const proj = (lon, lat) => [1080 * (lon - BOX[0]) / (BOX[2] - BOX[0]), PT + PH * (MERC(BOX[3]) - MERC(lat)) / (MERC(BOX[3]) - MERC(BOX[1]))];

  // ── the layers, bottom to top ──
  const cv = el("canvas", null, stage); cv.id = "ground"; cv.width = 1080; cv.height = 1920;
  const ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  // the two soft shades that carry the words (the top and the bottom of the stage), under the panel
  const gTop = ctx.createLinearGradient(0, 0, 0, 660), gBot = ctx.createLinearGradient(0, 1920, 0, 1400);
  [[0, 0.78], [0.42, 0.62], [0.78, 0.26], [1, 0]].forEach(([p, a]) => gTop.addColorStop(p, `rgba(12,9,6,${a})`));
  [[0, 0.74], [0.5, 0.5], [0.82, 0.2], [1, 0]].forEach(([p, a]) => gBot.addColorStop(p, `rgba(12,9,6,${a})`));
  const lay = svg("svg", { class: "lay", width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, stage);
  const defs = svg("defs", {}, lay);
  svg("rect", { x: 0, y: PT, width: 1080, height: PH }, svg("clipPath", { id: "mapzone" }, defs));        // the lane stays on the panel
  const laneG = svg("g", { "clip-path": "url(#mapzone)" }, lay);
  const laneBack = svg("path", { fill: "none", stroke: "rgba(12,9,6,0.7)", "stroke-width": 12, "stroke-linecap": "round", "stroke-linejoin": "round" }, laneG);
  const laneLine = svg("path", { fill: "none", stroke: "#fff", "stroke-width": 5, "stroke-dasharray": "18 13", "stroke-linecap": "round", "stroke-linejoin": "round" }, laneG);
  const bead = () => svg("circle", { r: 10, fill: "#fff", stroke: "rgba(12,9,6,0.85)", "stroke-width": 3, opacity: 0 }, laneG);
  const beadsThen = Array.from({ length: F.beads.then }, bead), beadsNow = Array.from({ length: F.beads.now }, bead);
  // a line from a name to the point it names (the strait; in scene e every place), under the names' plates
  const lead = () => { const g = svg("g", { opacity: 0 }, lay);
    return { g, back: svg("line", { stroke: "rgba(12,9,6,0.75)", "stroke-width": 8, "stroke-linecap": "round" }, g), line: svg("line", { stroke: "#fff", "stroke-width": 4, "stroke-linecap": "round" }, g) }; };
  const leadTo = (L, x1, y1, x2, y2, o) => { [L.back, L.line].forEach(l => { l.setAttribute("x1", x1.toFixed(1)); l.setAttribute("y1", y1.toFixed(1)); l.setAttribute("x2", x2.toFixed(1)); l.setAttribute("y2", y2.toFixed(1)); }); L.g.setAttribute("opacity", o.toFixed(3)); };
  const leadStrait = lead(), leadIn = F.inside.map(lead), leadOut = F.outside.map(lead);
  const straitDot = svg("circle", { r: 5.5, fill: "#fff", stroke: "rgba(12,9,6,0.85)", "stroke-width": 2.5, opacity: 0 }, lay);
  const frameG = svg("g", {}, lay);                       // the panel's two edges
  [PT, PT + PH].forEach(y => svg("line", { x1: 0, x2: 1080, y1: y, y2: y, stroke: "#fff", "stroke-width": 3, opacity: 0.85 }, frameG));
  const dotG = svg("g", {}, lay);                         // scene e: a dot on every place that is named (white: inside the Gulf; dark: on the Gulf of Oman)
  const dots = F.inside.map(() => svg("circle", { r: 9, fill: "#fff", stroke: "#1d140c", "stroke-width": 3.5, opacity: 0 }, dotG));
  const odots = F.outside.map(() => svg("circle", { r: 9, fill: "#1d140c", stroke: "#fff", "stroke-width": 3.5, opacity: 0 }, dotG));
  const wipe = el("div", null, stage); wipe.id = "wipe";

  // the headlines: one box a scene (the hook is scene a's)
  const heads = {};
  [["a", Wd.hook], ["b", Wd.head_b], ["c", Wd.head_c], ["e", Wd.head_e], ["f", Wd.head_f], ["h", Wd.head_h]].forEach(([name, text]) => {
    const box = el("div", "head", stage), lines = text.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
    lines.forEach(l => fit([l], WIDE, 50, 1.42));         // each line by itself: a short line keeps its size
    heads[name] = { box };
  });
  const tag = el("div", null, stage); tag.id = "tag";       // the year, and under it the days (the same under both years)
  const tagYear = el("span", "year", tag); el("span", "days", tag, Wd.tag_days);

  // the names: a dark plate for a country or a place, a blue plate for a sea and the strait, a paper plate for the lane
  const chip = (text, cls) => el("div", cls || "chip", stage, text);
  const WATER = { g_gulf: true, g_strait: true, g_sea: true };
  const names = F.names_b.map(k => [chip(Wd[k], WATER[k] ? "chip sea" : "chip"), k]);
  const nLane = chip(Wd.lane, "chip paper");
  const twoLine = s => { const e = el("div", "chip site", stage), q = s.split(" // "); el("span", "n", e, q[0]); el("span", "v", e, q[1]); return e; };
  const sites = F.inside.map(k => twoLine(Wd["s_" + k]));
  const outs = F.outside.map(k => chip(Wd["o_" + k], "chip out"));

  // the colour bar, a paper card: little on the right, much on the left, as the words run; the scale is the picture's own
  const bar = el("div", null, stage); bar.id = "bar";
  el("div", "title", bar, Wd.bar_title);
  const row = el("div", "row", bar);
  el("span", "end", row, Wd.bar_low);
  const strip = el("div", "strip", row);
  css(el("div", "fill", strip), { background: `linear-gradient(to left, ${F.scale.stops.map(([p, c, a]) => `rgba(${c[0]},${c[1]},${c[2]},${a}) ${(100 * p).toFixed(0)}%`).join(", ")})` });
  F.scale.ticks.forEach(([v, p], k) => { css(el("i", "tick", strip, Wd["bar_t" + k]), { right: (100 * p).toFixed(2) + "%" }); css(el("b", "notch", strip), { right: (100 * p).toFixed(2) + "%" }); });
  el("span", "end", row, Wd.bar_high);
  el("div", "unit", bar, Wd.bar_unit);

  // scene c's strip, a paper card on the panel's foot: ships a day, last year's and this year's, what is not counted,
  // and what the count cannot say about the map
  const count = el("div", "card count", stage);
  const crow = el("div", "row", count);
  el("span", "unit", crow, Wd.c_unit);
  const cThen = el("span", "big then", crow, Wd.c_then), cNow = el("span", "big now", crow, Wd.c_now);
  const cNote = el("div", "note", count, Wd.c_note), cShare = el("div", "note", count, Wd.c_share);

  // card f: the places inside the Gulf against last year, one column for every part of the year, the parts running
  // from the right to the left; a column hangs below the line when this year has less
  const PX0 = 26, PW = 776;
  const CP = F.chart.parts, NP = CP.length, FP = PW / NP, FBW = FP * 0.66, ZERO = 150, PXP = 3.6;      // PXP: pixels per per cent
  const fx = k => PX0 + PW - (k + 0.5) * FP;
  const cardF = el("div", "card", stage);
  const fs = svg("svg", { width: 828, height: 410, viewBox: "0 0 828 410" }, cardF);
  const pbars = CP.map((q, k) => svg("rect", { x: (fx(k) - FBW / 2).toFixed(1), width: FBW.toFixed(1), rx: 5, fill: q.when === "closure" ? col.now : col.rest }, fs));
  svg("line", { x1: PX0, x2: PX0 + PW, y1: ZERO, y2: ZERO, stroke: col.ink, "stroke-width": 3 }, fs);
  css(el("div", "t", cardF, Wd.f_title), { right: 26, top: 10 });
  const fKey = css(el("div", "t now", cardF), { left: 26, top: 58 }); el("i", "now", fKey); fKey.appendChild(document.createTextNode(Wd.f_key));
  const fTicks = F.chart.ticks.map((k, n) => css(el("div", "t", cardF, Wd["t_" + F.chart.tick_keys[n]]), { left: fx(k), top: 354, transform: "translateX(-50%)" }));
  const KL = F.chart.low, fLow = css(el("div", "t now", cardF, Wd.f_low), { left: fx(KL), top: ZERO + Math.abs(CP[KL].value) * PXP + 6, transform: "translateX(-50%)" });

  const follow = el("div", null, stage); follow.id = "follow"; el("span", null, follow, Wd.follow);
  const src = {}; ORDER.forEach(k => { src[k] = el("div", "sources", stage); const ls = Wd["src_" + k].split(" // ").map(s => el("span", null, src[k], s)); fit(ls, LOW, 34, 1.36); });   // never under 34 px: a line that is too long shows in the sweep

  const LANE = F.lane.map(q => proj(q[0], q[1]));
  // the inventory's ridge is a clean line only from the middle of the Gulf on (west of it the lanes fan out to the
  // ports), so the lane fades in at its western end instead of starting with a cut
  [["laneFadeBack", "12,9,6", 0.7, laneBack], ["laneFade", "255,255,255", 1, laneLine]].forEach(([id, rgb, a, e]) => {
    const g = svg("linearGradient", { id, gradientUnits: "userSpaceOnUse", x1: LANE[0][0], y1: 0, x2: LANE[0][0] + 120, y2: 0 }, defs);
    svg("stop", { offset: 0, "stop-color": `rgba(${rgb},0)` }, g); svg("stop", { offset: 1, "stop-color": `rgba(${rgb},${a})` }, g);
    e.setAttribute("stroke", `url(#${id})`); });
  // the line's place: last year's picture is on the left of x. Scene a: x runs to 0 (this year) and out again to 1080
  // (the line creeps in from frame 0, so the first frames already move, and sweeps after about half a second);
  // scene b: last year; scene c: wiped to this year; after it: this year
  const sig = (p, n) => { const a = Math.pow(p, n), b = Math.pow(1 - p, n); return a / (a + b); };
  const creep = u => 0.1 * u + 0.9 * sig(u, 2.6);
  const xA = t => t < C.a_back[0] ? 1080 * (1 - creep(seg(t, C.a_go[0], C.a_go[1]))) : 1080 * ease(seg(t, C.a_back[0], C.a_back[1]));
  const xC = t => 1080 * (1 - ease(seg(t, C.c_wipe[0], C.c_wipe[1])));
  const xAt = t => t < C.b[0] ? xA(t) : t < C.c[0] ? 1080 : t < C.e[0] ? xC(t) : 0;
  function ground(x, a) {                                // the map with the line at x, at opacity a
    // behind the panel: the same picture, large, dark and out of focus (no bare band above and below it); it follows the line
    ctx.save(); ctx.filter = "blur(26px) brightness(0.4)"; ctx.globalAlpha = a; ctx.drawImage(THEN, -540, 0, 2160, 1920);
    if (x < 1080) { ctx.globalAlpha = a * (1 - x / 1080); ctx.drawImage(NOW, -540, 0, 2160, 1920); }
    ctx.restore();
    ctx.globalAlpha = a; ctx.fillStyle = gTop; ctx.fillRect(0, 0, 1080, 660); ctx.fillStyle = gBot; ctx.fillRect(0, 1400, 1080, 520);
    ctx.save(); ctx.beginPath(); ctx.rect(0, PT, 1080, PH); ctx.clip();
    ctx.drawImage(THEN, 0, PT, 1080, PH);
    if (x < 1080) { ctx.beginPath(); ctx.rect(x, PT, 1080 - x, PH); ctx.clip(); ctx.drawImage(NOW, 0, PT, 1080, PH); }
    ctx.restore(); ctx.globalAlpha = 1;
  }
  const path = pts => pts.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");
  const upTo = (pts, f) => { const k = f * (pts.length - 1), k0 = Math.min(Math.floor(k), pts.length - 2), frc = k - k0; return pts.slice(0, k0 + 1).concat([[lerp(pts[k0][0], pts[k0 + 1][0], frc), lerp(pts[k0][1], pts[k0 + 1][1], frc)]]); };
  const along = (pts, u) => { const k = clamp(u) * (pts.length - 1), k0 = Math.min(Math.floor(k), pts.length - 2), frc = k - k0; return [lerp(pts[k0][0], pts[k0 + 1][0], frc), lerp(pts[k0][1], pts[k0 + 1][1], frc)]; };

  window.renderAt = function (t0) { draw(clamp(t0, 0, END)); };

  function draw(t) {
    const back = t >= C.out[0];                          // the last frames return to frame 0
    const cur = back ? "h" : ORDER.filter(k => t >= C[k][0]).pop();
    ctx.fillStyle = "#120d09"; ctx.fillRect(0, 0, 1080, 1920);
    const xs = xAt(t);
    ground(xs, 1);
    const home = back ? ease(seg(t, C.out[0], END - 1 / F.fps)) : 0;       // 1 on the last frame: frame 0's picture and words
    if (home > 0) ground(1080, home);
    css(wipe, { left: xs - 4, top: PT, height: PH }); show(wipe, !back && xs > 2 && xs < 1078 ? 1 : 0);
    // how much of each scene's words stand: in after the scene starts, out before the next (two headlines never stand together)
    const on = {}; ORDER.forEach(k => { on[k] = back ? (k === "a" ? seg(home, 0.55, 1) : k === "h" ? 1 - seg(home, 0, 0.4) : 0) : win(t, C[k][0] + (k === "a" ? 0 : 0.15), C[k][1] + (k === "h" ? 1 : 0), 0.3, 0.3); });

    // the headlines
    ORDER.forEach(k => {
      show(heads[k].box, on[k]);
      heads[k].box.style.transform = k === "a" || back ? "none" : `translateY(${(14 * (1 - ease(seg(t, C[k][0] + 0.15, C[k][0] + 0.45)))).toFixed(1)}px)`;
    });
    show(follow, back ? on.h : win(t, C.follow, C.h[1] + 1, 0.35, 0.3));

    // the tag: the year whose picture holds most of the panel (in its corner), through the whole film
    const year = back ? (home > 0.5 ? 1080 : 0) : xs;
    tagYear.textContent = year >= 540 ? Wd.tag_then : Wd.tag_now;
    show(tag, back ? Math.abs(2 * home - 1) : 1);

    // the names (scene b): the countries go with the scene; the two seas and the strait stay through scene c
    const put = (e, q, o, dx = 0, dy = 0) => { const hw = e.offsetWidth / 2, lim = q[1] + dy + e.offsetHeight / 2 > 1000 ? 924 : 984;
      const x = clamp(q[0] + dx, 96 + hw, lim - hw); css(e, { left: x, top: q[1] + dy }); show(e, o); return [x, q[1] + dy, hw, e.offsetHeight / 2]; };
    names.forEach(([e, k], j) => { const t0 = C.names_b + C.names_gap * j;
      const o = back ? 0 : WATER[k] ? win(t, t0, C.c[1], 0.3, 0.3) : on.b * seg(t, t0, t0 + 0.3);
      const at = put(e, proj(P[k][0], P[k][1]), o);
      if (k === "g_strait") {                              // from the name's lower left corner to the strait
        const s = proj(P.strait[0], P.strait[1]);
        leadTo(leadStrait, at[0] - at[2] + 6, at[1] + 16, s[0], s[1], o);
        straitDot.setAttribute("cx", s[0].toFixed(1)); straitDot.setAttribute("cy", s[1].toFixed(1)); straitDot.setAttribute("opacity", o.toFixed(3));
      } });

    // the lane (scene c): drawn from inside the Gulf to the open sea; dots move along it, last year's many on last
    // year's picture and this year's one on this year's
    const lOn = cur === "c" && !back ? win(t, C.lane[0], C.c[1], 0.2, 0.3) : 0;
    laneG.setAttribute("opacity", lOn.toFixed(3));
    if (lOn > 0.001) {
      const f = ease(seg(t, C.lane[0], C.lane[1]));
      const dl = path(upTo(LANE, Math.max(f, 0.001)));
      [laneBack, laneLine].forEach(e => e.setAttribute("d", dl));
      const set = (b, q, o) => { b.setAttribute("cx", q[0].toFixed(1)); b.setAttribute("cy", q[1].toFixed(1)); b.setAttribute("opacity", (0.97 * o).toFixed(3)); };
      beadsThen.forEach((b, j) => { const u = ((j / beadsThen.length) + (t - C.lane[0]) * 0.05) % 1, q = along(LANE, u);
        set(b, q, (u < f ? 1 : 0) * Math.min(1, u * 14, (1 - u) * 14) * (q[0] < xs - 6 ? 1 : 0)); });
      beadsNow.forEach((b, j) => { const u = (0.2 + j / beadsNow.length + (t - C.c_wipe[0]) * 0.05) % 1, q = along(LANE, u);
        set(b, q, t >= C.c_wipe[0] && q[0] > xs + 6 ? 1 : 0); });
    }
    put(nLane, proj(P.lane[0], P.lane[1]), (back ? 0 : on.c) * seg(t, C.lane_chip, C.lane_chip + 0.3));

    // scene e: the places inside the Gulf, one after another (a dot, a line to the name with the change), then the three outside by name
    const mark = (k, dot, chipE, L, t0) => { const q = proj(P[k][0], P[k][1]), o = (back ? 0 : on.e) * seg(t, t0, t0 + 0.3);
      dot.setAttribute("cx", q[0].toFixed(1)); dot.setAttribute("cy", q[1].toFixed(1)); dot.setAttribute("opacity", o.toFixed(3));
      dot.setAttribute("r", (9 + 10 * (1 - easeOut(seg(t, t0, t0 + 0.6)))).toFixed(1));
      const at = put(chipE, q, o, F.site_at[k][0], F.site_at[k][1]);
      // the line runs from the dot to the edge of the name's plate (none when the dot touches the plate)
      const dx = q[0] - at[0], dy = q[1] - at[1], sc = Math.min(at[2] / Math.max(Math.abs(dx), 1e-6), at[3] / Math.max(Math.abs(dy), 1e-6));
      leadTo(L, q[0], q[1], at[0] + dx * Math.min(sc, 1), at[1] + dy * Math.min(sc, 1), sc < 0.9 ? o : 0); };
    F.inside.forEach((k, j) => mark(k, dots[j], sites[j], leadIn[j], C.sites[j]));
    F.outside.forEach((k, j) => mark(k, odots[j], outs[j], leadOut[j], C.outs[j]));

    // the colour bar: with the map, after the first wipe has gone (scene c's strip and scene f's card take its place)
    show(bar, back ? 0 : cur === "a" || cur === "b" ? win(t, C.bar_a, C.b[1], 0.3, 0.3) : cur === "e" ? on.e : 0);

    // scene c's strip: last year's count, then this year's as the picture is wiped, then the note
    const cOn = back ? 0 : win(t, C.strip[0], C.strip[1], 0.35, 0.3);
    show(count, cOn);
    if (cOn > 0.001) { show(cThen, seg(t, C.c_then, C.c_then + 0.3)); show(cNow, seg(t, C.c_now, C.c_now + 0.3)); show(cNote, seg(t, C.c_note, C.c_note + 0.3)); show(cShare, seg(t, C.c_share, C.c_share + 0.3)); }

    // card f: the columns come from the right, part after part
    const fOn = win(t, C.card_f[0], C.card_f[1], 0.35, 0.3);
    show(cardF, fOn);
    if (fOn > 0.001) {
      CP.forEach((q, k) => { const g0 = lerp(C.parts[0], C.parts[1], k / NP), g = easeOut(seg(t, g0, g0 + 0.4)), h = Math.max(3, Math.abs(q.value) * PXP) * g;
        pbars[k].setAttribute("y", (q.value < 0 ? ZERO : ZERO - h).toFixed(1)); pbars[k].setAttribute("height", h.toFixed(1)); });
      show(fKey, seg(t, C.f_key, C.f_key + 0.3)); show(fLow, seg(t, C.f_low, C.f_low + 0.3));
      fTicks.forEach((e, n) => show(e, seg(t, lerp(C.parts[0], C.parts[1], F.chart.ticks[n] / NP), lerp(C.parts[0], C.parts[1], F.chart.ticks[n] / NP) + 0.3)));
    }

    ORDER.forEach(k => show(src[k], on[k]));
  }
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
