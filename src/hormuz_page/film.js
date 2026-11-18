/* The Hormuz NO2 film (film.html): window.renderAt(t) draws the frame of time t (seconds) from /build/film.json,
   which src/hormuz.py writes (every string, number, the clock, the colours). Nothing is typed here; the numbers in
   this file are pixels of the layout. Every frame is a pure function of t (the frames are rendered out of order by
   several workers).
   Two pictures: the whole Gulf as a wide panel in the middle of the stage (scenes a, b, e) and the strait with the
   Gulf of Oman as the whole frame (scenes c, d, h).
   The scenes: a the whole Gulf, last year's NO2 wiped to this year's and back; b what the glow is, with the names;
   c the strait: the lane drawn with ships moving along it, the ships of every week as columns, the picture wiped to
   this year as the columns fall; e the whole Gulf this year, the ports and plants inside the strait with their
   change; f the strait this year, and those places' change in every part of the year (before, during, after) as
   columns; h the strait this year and the question; then frame 0 again. */
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
const WIDE = 888, LOW = 828, DIS = 0.4;                  // the headline's column; the column below y 1000; the dissolve between two pictures
const PT = 490, PH = 960;                                // the whole-Gulf panel: its top and its height on the stage (the sources stand under it)

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const C = F.clock, Wd = F.words, col = F.colours, END = F.end, P = F.places;
  window.CUT = { name: "a", end: END };
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const IM = {};
  await Promise.all([["eThen", F.east.then], ["eNow", F.east.now], ["gThen", F.gulf.then], ["gNow", F.gulf.now]].map(async ([k, f]) => { IM[k] = await load(f); }));
  await Promise.all(['900 84px "Vazirmatn"', '800 44px "Vazirmatn"', '700 50px "Vazirmatn"', '500 34px "Vazirmatn"', '400 96px "Lalezar"'].map(f => document.fonts.load(f, "خ۱")));

  const ORDER = ["a", "b", "c", "e", "f", "h"];
  const PANEL = { a: true, b: true, e: true };           // the scenes on the whole-Gulf panel; the others fill the frame with the strait
  const SAME = { b: "a", h: "f" };                       // scenes that keep the picture of the scene before them: no dissolve
  const EAST = F.east.box, GULF = F.gulf.box;
  // the 9:16 picture is the frame at scale 1 (Web Mercator); a slow push m about the frame's centre; lon/lat to the frame under that push
  const projE = m => { const y0 = MERC(EAST[3]), y1 = MERC(EAST[1]); return (lon, lat) => [540 + m * 1080 * ((lon - EAST[0]) / (EAST[2] - EAST[0]) - 0.5), 960 + m * 1920 * ((y0 - MERC(lat)) / (y0 - y1) - 0.5)]; };
  const projG = (lon, lat) => [1080 * (lon - GULF[0]) / (GULF[2] - GULF[0]), PT + PH * (MERC(GULF[3]) - MERC(lat)) / (MERC(GULF[3]) - MERC(GULF[1]))];
  const pushOf = (name, t) => name === "c" ? 1 + 0.035 * seg(t, C.c[0], C.c[1]) : 1 + 0.04 * seg(t, C.f[0], C.out[0]);   // a slow push while a picture stands

  // ── the layers, bottom to top ──
  const cv = el("canvas", null, stage); cv.id = "ground"; cv.width = 1080; cv.height = 1920;
  const ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  el("div", null, stage).id = "shade-top"; el("div", null, stage).id = "shade-bot";
  const lay = svg("svg", { class: "lay", width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, stage);
  const defs = svg("defs", {}, lay);
  svg("rect", { x: 0, y: 590, width: 1080, height: 960 }, svg("clipPath", { id: "mapzone" }, defs));      // the lane keeps out of the headline
  const glow = svg("filter", { id: "glow", x: "-50%", y: "-50%", width: "200%", height: "200%" }, defs); svg("feGaussianBlur", { stdDeviation: 5 }, glow);
  const laneG = svg("g", { "clip-path": "url(#mapzone)" }, lay);
  const laneBack = svg("path", { fill: "none", stroke: "rgba(12,9,6,0.55)", "stroke-width": 13, "stroke-linecap": "round", "stroke-linejoin": "round" }, laneG);
  const laneGlow = svg("path", { fill: "none", stroke: col.gold, "stroke-width": 12, "stroke-linecap": "round", "stroke-linejoin": "round", filter: "url(#glow)", opacity: 0.7 }, laneG);
  const laneLine = svg("path", { fill: "none", stroke: col.gold, "stroke-width": 5.5, "stroke-dasharray": "20 13", "stroke-linecap": "round", "stroke-linejoin": "round" }, laneG);
  const beads = []; for (let i = 0; i < 14; i++) beads.push(svg("circle", { r: 7, fill: "#fff", stroke: "rgba(12,9,6,0.7)", "stroke-width": 2.5, opacity: 0 }, laneG));
  const frameG = svg("g", {}, lay);                       // the panel's two edges
  [PT, PT + PH].forEach(y => svg("line", { x1: 0, x2: 1080, y1: y, y2: y, stroke: "#fff", "stroke-width": 3, opacity: 0.85 }, frameG));
  const dotG = svg("g", {}, lay);                         // scene e: a dot on every place that is named
  const dots = F.inside.map(() => svg("circle", { r: 9, fill: col.gold, stroke: "#1d140c", "stroke-width": 3, opacity: 0 }, dotG));
  const wipe = el("div", null, stage); wipe.id = "wipe";

  // the headlines: one box a scene (the hook is scene a's)
  const heads = {};
  [["a", Wd.hook], ["b", Wd.head_b], ["c", Wd.head_c], ["e", Wd.head_e], ["f", Wd.head_f], ["h", Wd.head_h]].forEach(([name, text]) => {
    const box = el("div", "head", stage), lines = text.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
    lines.forEach(l => fit([l], WIDE, 50, 1.42));         // each line by itself: a short line keeps its size
    heads[name] = { box };
  });
  const tag = el("div", null, stage); tag.id = "tag";

  // the names
  const chip = (text, cls) => el("div", cls || "chip", stage, text);
  const B_NAMES = [[chip(Wd.g_iran), "g_iran"], [chip(Wd.g_saudi), "g_saudi"], [chip(Wd.g_uae), "g_uae"], [chip(Wd.g_gulf, "land sea"), "g_gulf"], [chip(Wd.g_strait), "g_strait"]];   // on a dark plate: the glow under them is bright
  const nBandar = chip(Wd.bandar), nStrait = chip(Wd.strait), nIran = chip(Wd.e_iran, "land"), nLane = chip(Wd.lane, "chip gold");
  const sites = F.inside.map(k => chip(Wd["s_" + k]));

  // the colour bar: little on the right, much on the left, as the words run
  const bar = el("div", null, stage); bar.id = "bar";
  el("div", "title", bar, Wd.bar_title);
  const stops = F.scale.ramp.map(([p, c]) => `rgba(${c[0]},${c[1]},${c[2]},${(0.25 + 0.75 * Math.min(1, p * 1.6)).toFixed(2)}) ${(100 * p).toFixed(0)}%`).join(", ");
  css(el("div", "strip", bar), { background: `linear-gradient(to left, ${stops})` });
  const ends = el("div", "ends", bar); el("span", null, ends, Wd.bar_low); el("span", null, ends, Wd.bar_high);
  el("div", "unit", bar, Wd.bar_unit);

  // card c: the ships of every week of the window, last year's and this year's side by side (the same weeks of both
  // years), the weeks running from the right to the left (as the words do)
  const SH = F.ships, NW = SH.then.length, PX0 = 26, PW = 776, PITCH = PW / NW, BARW = PITCH * 0.38, BASE = 294, TALL = 176;
  const VMAX = Math.max(...SH.then, ...SH.now) * 1.04;
  const xOf = k => PX0 + PW - (k + 0.5) * PITCH;
  const cardC = el("div", "card", stage);
  const cs = svg("svg", { width: 828, height: 410, viewBox: "0 0 828 410" }, cardC);
  const tbars = SH.then.map((v, k) => svg("rect", { x: (xOf(k) + 1).toFixed(2), width: BARW.toFixed(2), rx: 2, fill: col.then }, cs));
  const nbars = SH.now.map((v, k) => svg("rect", { x: (xOf(k) - BARW - 1).toFixed(2), width: BARW.toFixed(2), rx: 2, fill: col.now }, cs));
  svg("line", { x1: PX0, x2: PX0 + PW, y1: BASE + 1.5, y2: BASE + 1.5, stroke: col.ink, "stroke-width": 3 }, cs);
  css(el("div", "t", cardC, Wd.c_unit), { right: 26, top: 10 });
  const cThen = css(el("div", "t big then", cardC, Wd.c_then), { right: 26, top: 58 });
  const cNow = css(el("div", "t big now", cardC, Wd.c_now), { left: 26, top: 58 });
  css(el("div", "t", cardC, Wd.c_from), { right: 26, top: 300 }); css(el("div", "t", cardC, Wd.c_to), { left: 26, top: 300 });
  const cNote = css(el("div", "t", cardC, Wd.c_note), { right: 26, top: 352 });

  // card f: the places inside the strait against last year, one column for every part of the year, the parts running
  // from the right to the left; a column hangs below the line when this year has less
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

  const LANE = F.lane;
  const pic = (im, m, a) => { ctx.globalAlpha = a; ctx.drawImage(im, 540 - 540 * m, 960 - 960 * m, 1080 * m, 1920 * m); ctx.globalAlpha = 1; };
  // the line's place: scene a, last year's picture is on the left of x; x runs to 0 (this year) and out again to 1080
  // (the line creeps in from frame 0, so the first frames already move, and sweeps after about half a second)
  const sig = (p, n) => { const a = Math.pow(p, n), b = Math.pow(1 - p, n); return a / (a + b); };
  const creep = u => 0.1 * u + 0.9 * sig(u, 2.6);
  const xA = t => t < C.a_back[0] ? 1080 * (1 - creep(seg(t, C.a_go[0], C.a_go[1]))) : 1080 * ease(seg(t, C.a_back[0], C.a_back[1]));
  const xC = t => 1080 * (1 - ease(seg(t, C.c_wipe[0], C.c_wipe[1])));
  const xOfScene = (name, t) => name === "a" ? xA(t) : name === "b" ? 1080 : name === "c" ? xC(t) : 0;
  function ground(name, t, a) {                          // one scene's picture at time t with opacity a; returns the line's x
    const x = xOfScene(name, t);
    if (PANEL[name]) {
      // behind the panel: the same picture, large, dark and out of focus (no bare band above and below it)
      ctx.save(); ctx.filter = "blur(26px) brightness(0.34)"; ctx.globalAlpha = a;
      ctx.drawImage(x < 540 ? IM.gNow : IM.gThen, -540, 0, 2160, 1920); ctx.restore();
      ctx.save(); ctx.beginPath(); ctx.rect(0, PT, 1080, PH); ctx.clip();
      ctx.globalAlpha = a; ctx.drawImage(IM.gThen, 0, PT, 1080, PH);
      if (x < 1080) { ctx.beginPath(); ctx.rect(x, PT, 1080 - x, PH); ctx.clip(); ctx.drawImage(IM.gNow, 0, PT, 1080, PH); }
      ctx.globalAlpha = 1; ctx.restore(); return x;
    }
    const m = pushOf(name, t);
    pic(IM.eThen, m, a);
    if (x < 1080) { ctx.save(); ctx.beginPath(); ctx.rect(x, 0, 1080 - x, 1920); ctx.clip(); pic(IM.eNow, m, a); ctx.restore(); }
    return x;
  }
  const path = pts => pts.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");
  const upTo = (pts, f) => { const k = f * (pts.length - 1), k0 = Math.min(Math.floor(k), pts.length - 2), frc = k - k0; return pts.slice(0, k0 + 1).concat([[lerp(pts[k0][0], pts[k0 + 1][0], frc), lerp(pts[k0][1], pts[k0 + 1][1], frc)]]); };

  window.renderAt = function (t0) { draw(clamp(t0, 0, END)); };

  function draw(t) {
    const back = t >= C.out[0];                          // the last frames return to frame 0
    const cur = back ? "h" : ORDER.filter(k => t >= C[k][0]).pop(), i = ORDER.indexOf(cur);
    ctx.fillStyle = "#120d09"; ctx.fillRect(0, 0, 1080, 1920);
    // the ground: the scene's picture; a new picture comes in over the one before it in its first DIS seconds
    const fresh = i > 0 && !back && !SAME[cur] ? seg(t, C[cur][0], C[cur][0] + DIS) : 1;
    if (fresh < 1) ground(ORDER[i - 1], t, 1);
    let wx = ground(cur, t, fresh);
    const home = back ? ease(seg(t, C.out[0], END - 1 / F.fps)) : 0;       // 1 on the last frame: frame 0's picture and words
    if (home > 0) { ground("a", 0, home); wx = -1; }
    const panel = !!PANEL[cur] && !back;
    css(wipe, { left: wx - 3, top: panel ? PT : 0, height: panel ? PH : 1920 }); show(wipe, wx > 2 && wx < 1078 && fresh >= 1 ? 1 : 0);
    // the panel's edges: with the panel (and with frame 0 as it returns)
    const prevPanel = i > 0 && !!PANEL[ORDER[i - 1]];
    frameG.setAttribute("opacity", (back ? home : panel ? (prevPanel ? 1 : fresh) : prevPanel ? 1 - fresh : 0).toFixed(3));
    // how much of each scene's words stand: in after the scene starts, out before the next (two headlines never stand together)
    const on = {}; ORDER.forEach(k => { on[k] = back ? (k === "a" ? seg(home, 0.55, 1) : k === "h" ? 1 - seg(home, 0, 0.4) : 0) : win(t, C[k][0] + (k === "a" ? 0 : 0.15), C[k][1] + (k === "h" ? 1 : 0), 0.3, 0.3); });
    const pE = projE(pushOf(cur === "c" ? "c" : "f", t));

    // the headlines
    ORDER.forEach(k => {
      show(heads[k].box, on[k]);
      heads[k].box.style.transform = k === "a" || back ? "none" : `translateY(${(14 * (1 - ease(seg(t, C[k][0] + 0.15, C[k][0] + 0.45)))).toFixed(1)}px)`;
    });
    show(follow, back ? on.h : win(t, C.follow, C.h[1] + 1, 0.35, 0.3));

    // the tag: the year whose picture holds most of the frame (in the panel's corner, or under the headline)
    const xs = back ? 1080 : xOfScene(cur, t);
    tag.textContent = xs >= 540 ? Wd.tag_then : Wd.tag_now;
    show(tag, back ? on.a : cur === "a" || cur === "b" ? win(t, 0, C.b[1], 0.3, 0.3) : cur === "h" ? 0 : on[cur]);

    // the names of scene b (the whole Gulf)
    const put = (e, q, o, dx = 0, dy = 0) => { const hw = e.offsetWidth / 2, lim = q[1] + dy + e.offsetHeight / 2 > 1000 ? 924 : 984;
      css(e, { left: clamp(q[0] + dx, 96 + hw, lim - hw), top: q[1] + dy }); show(e, o); };
    B_NAMES.forEach(([e, place], j) => put(e, projG(P[place][0], P[place][1]), (back ? 0 : on.b) * seg(t, C.names_b + 0.25 * j, C.names_b + 0.25 * j + 0.3)));

    // the lane (scene c): drawn from inside the Gulf to the open sea; the ships move along it while last year's picture stands
    const east = cur === "c" && !back;
    const lOn = east ? win(t, C.lane[0], C.c[1], 0.2, 0.3) : 0;
    laneG.setAttribute("opacity", lOn.toFixed(3));
    if (lOn > 0.001) {
      const lp = LANE.map(q => pE(q[0], q[1])), f = ease(seg(t, C.lane[0], C.lane[1]));
      const dl = path(upTo(lp, Math.max(f, 0.001)));
      [laneBack, laneGlow, laneLine].forEach(e => e.setAttribute("d", dl));
      beads.forEach((b, j) => { const u = ((j / beads.length) + (t - C.lane[0]) * 0.05) % 1, q = lp[Math.round(u * (lp.length - 1))];
        const o = (u < f ? 1 : 0) * Math.min(1, u * 12, (1 - u) * 12) * (q[0] < xs - 4 ? 1 : 0);        // none where this year's picture stands
        b.setAttribute("cx", q[0].toFixed(1)); b.setAttribute("cy", q[1].toFixed(1)); b.setAttribute("opacity", (0.95 * o).toFixed(3)); });
    }
    const nOn = east ? win(t, C.names_c, C.c[1], 0.3, 0.3) : 0;
    put(nBandar, pE(P.bandar[0], P.bandar[1]), nOn, 150, -74);
    put(nStrait, pE(P.strait[0], P.strait[1]), nOn * seg(t, C.names_c + 0.25, C.names_c + 0.55), 236, 6);
    put(nIran, pE(P.e_iran[0], P.e_iran[1]), nOn * seg(t, C.names_c + 0.5, C.names_c + 0.8));
    put(nLane, pE(P.lane[0], P.lane[1]), (back ? 0 : on.c) * seg(t, C.lane_chip, C.lane_chip + 0.3));       // beside the lane's bend, above the card

    // scene e: the places, one after another: a dot on the place, its name and its change above it
    F.inside.forEach((k, j) => { const q = projG(P[k][0], P[k][1]), o = (back ? 0 : on.e) * seg(t, C.sites[j], C.sites[j] + 0.3);
      dots[j].setAttribute("cx", q[0].toFixed(1)); dots[j].setAttribute("cy", q[1].toFixed(1)); dots[j].setAttribute("opacity", o.toFixed(3));
      dots[j].setAttribute("r", (9 + 10 * (1 - easeOut(seg(t, C.sites[j], C.sites[j] + 0.6)))).toFixed(1));
      put(sites[j], q, o, F.site_at[k][0], F.site_at[k][1]); });

    // the colour bar: with the panel (after the first wipe has gone)
    show(bar, back ? 0 : cur === "a" || cur === "b" ? win(t, C.bar_a, C.b[1], 0.3, 0.3) : cur === "e" ? on.e : 0);

    // card c: the weeks' columns come from the right, last year's and then this year's; the two means; the note
    const cOn = win(t, C.card_c[0], C.card_c[1], 0.35, 0.3);
    show(cardC, cOn);
    if (cOn > 0.001) {
      const mid = (C.weeks[0] + C.weeks[1]) / 2;                           // last year's columns first, then this year's
      const rise = (bars, vals, a, b, least) => vals.forEach((v, k) => { const g0 = lerp(a, b, k / NW), h = Math.max(least, TALL * v / VMAX) * easeOut(seg(t, g0, g0 + 0.3));
        bars[k].setAttribute("y", (BASE - h).toFixed(1)); bars[k].setAttribute("height", h.toFixed(1)); });
      rise(tbars, SH.then, C.weeks[0], mid - 0.4, 1.5); rise(nbars, SH.now, mid, C.weeks[1] - 0.3, 3);
      show(cThen, seg(t, mid - 0.6, mid - 0.3)); show(cNow, seg(t, C.c_vals, C.c_vals + 0.3)); show(cNote, seg(t, C.c_note, C.c_note + 0.3));
    }
    // card f: the columns come from the right, part after part
    const fOn = win(t, C.card_f[0], C.card_f[1], 0.35, 0.3);
    show(cardF, fOn);
    if (fOn > 0.001) {
      CP.forEach((q, k) => { const g0 = lerp(C.parts[0], C.parts[1], k / NP), g = easeOut(seg(t, g0, g0 + 0.4)), h = Math.max(3, Math.abs(q.value) * PXP) * g;
        pbars[k].setAttribute("y", (q.value < 0 ? ZERO : ZERO - h).toFixed(1)); pbars[k].setAttribute("height", h.toFixed(1)); });
      show(fKey, seg(t, C.f_key, C.f_key + 0.3)); show(fLow, seg(t, C.f_key - 0.4, C.f_key - 0.1));
      fTicks.forEach((e, n) => show(e, seg(t, lerp(C.parts[0], C.parts[1], F.chart.ticks[n] / NP), lerp(C.parts[0], C.parts[1], F.chart.ticks[n] / NP) + 0.3)));
    }

    ORDER.forEach(k => show(src[k], on[k]));
  }
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
