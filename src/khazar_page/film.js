/* «آبِ خزر کجا رفت؟» (film.html?cut=a or b: the two cuts differ only in the hook's first line): window.renderAt(t)
   draws the frame of time t (seconds) from /build/film.json, which src/khazar.py writes (every string, number, the
   clock, the colours). Nothing is typed here; the numbers in this file are pixels of the layout. Every frame is a
   pure function of t (the frames are rendered out of order by several workers).
   The scenes: a the north-east now with the shore of 2001 as a gold line, wiped back to 2001 and forward again, a
   50-km ruler; b every late summer 2001-2026 with the sea's level running and the rectangle of the published
   measurement; c the Volga drawn on the map, its dams in the order they began to work; e the river's 84 years as
   columns against their average; f Iran's coast and the sea's level under the same columns; g why it falls (drawn
   vapour over the sea); h the north-east again and the question; then frame 0 again (the loop). */
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

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const cut = new URLSearchParams(location.search).get("cut") || "b";
  const C = F.clock, Wd = F.words, col = F.colours, END = F.end, P = F.places, RUN = F.run, YT = C.years;
  const HOOK = cut === "a" ? Wd.hook_a : Wd.hook_b;
  window.CUT = { name: cut, end: END };
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const IM = { y: [] };
  await Promise.all(RUN.map(async (r, i) => { IM.y[i] = await load(r.pic); }).concat(
    [["shore", F.ne.shore], ["wide", F.wide.file], ["south", F.south.file], ["loc", F.locator.file]].map(async ([k, f]) => { IM[k] = await load(f); })));
  IM.then = IM.y[0]; IM.now = IM.y[RUN.length - 1];
  await Promise.all(['900 84px "Vazirmatn"', '900 60px "Vazirmatn"', '800 44px "Vazirmatn"', '700 50px "Vazirmatn"', '500 28px "Vazirmatn"', '400 104px "Lalezar"'].map(f => document.fonts.load(f, "خزر ۱۴۰۵ −۲٫۱")));

  const ORDER = ["a", "b", "c", "e", "f", "g", "h"];
  const SAME = { b: "a", e: "c", g: "f" };               // scenes that keep the picture of the scene before them: no dissolve
  const BOX = { a: F.ne.box, b: F.ne.box, h: F.ne.box, c: F.wide.box, e: F.wide.box, f: F.south.box, g: F.south.box };
  // a picture is the frame at scale 1 (Web Mercator); a slow push m about the frame's centre; lon/lat to the frame under that push
  const proj = (box, m) => { const y0 = MERC(box[3]), y1 = MERC(box[1]); return (lon, lat) => [540 + m * 1080 * ((lon - box[0]) / (box[2] - box[0]) - 0.5), 960 + m * 1920 * ((y0 - MERC(lat)) / (y0 - y1) - 0.5)]; };
  const push = (name, t) => name === "a" ? 1 + 0.04 * Math.pow(Math.sin(Math.PI * seg(t, 0, C.a[1])), 2)
    : name === "b" ? 1 : name === "h" ? 1 + 0.03 * seg(t, C.h[0], C.out[0])
    : name === "c" || name === "e" ? 1 + 0.05 * seg(t, C.c[0], C.e[1] + DIS)
    : 1 + 0.05 * seg(t, C.f[0], C.g[1] + DIS);

  // ── the layers, bottom to top ──
  const cv = el("canvas", null, stage); cv.id = "ground"; cv.width = 1080; cv.height = 1920;
  const ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  el("div", null, stage).id = "shade-top"; el("div", null, stage).id = "shade-bot";
  const lay = svg("svg", { class: "lay", width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, stage);
  const defs = svg("defs", {}, lay);
  svg("rect", { x: 0, y: 590, width: 1080, height: 880 }, svg("clipPath", { id: "mapzone" }, defs));      // map lines keep out of the headline and the source lines
  const glow = svg("filter", { id: "glow", x: "-50%", y: "-50%", width: "200%", height: "200%" }, defs); svg("feGaussianBlur", { stdDeviation: 6 }, glow);
  const mapG = svg("g", { "clip-path": "url(#mapzone)" }, lay);
  const borderBack = svg("path", { fill: "none", stroke: "rgba(16,11,6,0.55)", "stroke-width": 6, "stroke-linejoin": "round" }, mapG);
  const borderLine = svg("path", { fill: "none", stroke: "#fff", "stroke-width": 2.6, "stroke-dasharray": "10 9", "stroke-linejoin": "round", opacity: 0.8 }, mapG);
  const riverG = svg("g", {}, mapG);
  const mkRiver = wd => [svg("path", { fill: "none", stroke: col.river, "stroke-width": wd + 10, "stroke-linecap": "round", "stroke-linejoin": "round", filter: "url(#glow)", opacity: 0.85 }, riverG),
    svg("path", { fill: "none", stroke: col.river, "stroke-width": wd, "stroke-linecap": "round", "stroke-linejoin": "round" }, riverG),
    svg("path", { fill: "none", stroke: "#fff", "stroke-width": wd / 3, "stroke-linecap": "round", "stroke-linejoin": "round", opacity: 0.9 }, riverG)];
  const volgaP = mkRiver(8), kamaP = mkRiver(6);
  const beads = []; for (let i = 0; i < 16; i++) beads.push(svg("circle", { r: 5.5, fill: "#fff", opacity: 0 }, riverG));
  const pinG = svg("g", {}, lay);
  const pins = F.dams.map(() => [svg("circle", { r: 16, fill: "none", stroke: col.pin, "stroke-width": 4, opacity: 0 }, pinG), svg("circle", { r: 10, fill: col.pin, stroke: "#fff", "stroke-width": 3.5, opacity: 0 }, pinG)]);
  // scene b: the rectangle of the published measurement; scene a: the ruler
  const rectG = svg("g", {}, lay);
  const rectBack = svg("path", { fill: "none", stroke: "rgba(16,11,6,0.7)", "stroke-width": 10, "stroke-linejoin": "round" }, rectG);
  const rectLine = svg("path", { fill: "none", stroke: "#fff", "stroke-width": 5, "stroke-dasharray": "18 12", "stroke-linejoin": "round" }, rectG);
  const rulerG = svg("g", {}, lay);
  const rulerBack = svg("path", { fill: "none", stroke: "rgba(16,11,6,0.8)", "stroke-width": 14, "stroke-linecap": "round" }, rulerG);
  const rulerLine = svg("path", { fill: "none", stroke: "#fff", "stroke-width": 7, "stroke-linecap": "round" }, rulerG);
  // scene g: water leaving the sea's surface
  const wispG = svg("g", {}, lay);
  svg("rect", { x: 0, y: 648, width: 1080, height: 820 }, svg("clipPath", { id: "seazone" }, defs));      // the vapour keeps below the small line
  wispG.setAttribute("clip-path", "url(#seazone)");
  const WISPS = [[50.9, 38.2], [51.8, 38.15], [52.7, 38.2], [53.5, 38.05], [50.5, 37.7], [51.4, 37.75], [52.3, 37.7], [53.2, 37.65], [51.0, 37.25], [51.9, 37.2], [52.8, 37.15], [53.6, 37.25], [50.1, 38.05]];
  const wisps = WISPS.map(() => [svg("path", { fill: "none", stroke: "rgba(8,26,52,0.6)", "stroke-width": 18, "stroke-linecap": "round", "stroke-linejoin": "round", opacity: 0 }, wispG),
    svg("path", { fill: "none", stroke: "#fff", "stroke-width": 9, "stroke-linecap": "round", "stroke-linejoin": "round", opacity: 0 }, wispG)]);
  const wipe = el("div", null, stage); wipe.id = "wipe";

  // the locator (scene a): the whole sea, Iran's border and name, the film's frame as a gold box
  const loc = el("div", null, stage); loc.id = "locator"; loc.appendChild(IM.loc);
  const fr = F.locator.frame;
  css(el("div", "here", loc), { left: (100 * fr[0]).toFixed(2) + "%", top: (100 * fr[1]).toFixed(2) + "%", width: (100 * (fr[2] - fr[0])).toFixed(2) + "%", height: (100 * (fr[3] - fr[1])).toFixed(2) + "%" });
  css(el("div", "iran", loc, Wd.loc_iran), { left: (100 * F.locator.iran[0]).toFixed(2) + "%", top: (100 * F.locator.iran[1]).toFixed(2) + "%" });

  // the headlines: one box a scene (the hook is scene a's), a small line under some
  const heads = {};
  [["a", HOOK, null], ["b", Wd.head_b, null], ["c", Wd.head_c, null], ["e", Wd.head_e, null], ["f", Wd.head_f, Wd.small_f], ["g", Wd.head_g, Wd.small_g], ["h", Wd.head_h, null]].forEach(([name, text, small]) => {
    const box = el("div", "head", stage), lines = text.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
    lines.forEach(l => fit([l], WIDE, 50, 1.42));         // each line by itself: a short line keeps its size
    const sm = small ? el("span", "small", box, small) : null; if (sm) fit([sm], WIDE, 40, 1.4);
    heads[name] = { box, sm };
  });
  const tag = el("div", null, stage); tag.id = "tag";
  const tagYr = el("div", "yr", tag), tagVal = el("div", "val", tag), tagN = el("span", "n", tagVal), tagNum = el("span", "num", tagN), tagU = el("span", "u", tagVal, Wd.unit_b);
  el("span", "m", tagN, Wd.metre);

  // the names: [scene, element, place, dx, dy]
  const chip = (text, cls) => el("div", cls || "chip", stage, text);
  const NAMES = [["a", chip(Wd.shore, "chip gold"), "shore", 0, 0], ["h", chip(Wd.shore, "chip gold"), "shore", 0, 0],
    ["c", chip(Wd.russia, "land"), "russia", 0, 0], ["c", chip(Wd.kazakhstan, "land"), "kazakhstan", 0, 0], ["c", chip(Wd.sea, "land sea"), "sea_wide", 0, 0],
    ["e", chip(Wd.russia, "land"), "russia", 0, 0],
    ["f", chip(Wd.gilan, "land"), "gilan", 0, 0], ["f", chip(Wd.mazandaran, "land"), "mazandaran", 0, 0]];
  const rulerChip = chip(Wd.ruler), rectChip = chip(Wd.rect), chipC = chip("", "chip water"), vapourChip = chip(Wd.vapour, "chip water big"), yearChip = chip("", "chip year");
  Wd.chip_c.split(" // ").forEach(s => el("span", null, chipC, s));

  // the card (scenes e and f): the Volga's years as columns against their average; under them the sea's level
  const CH = F.chart, NY = CH.years.length, PX0 = 26, PW = 776, PITCH = PW / NY, BARW = 6.2, VMAX = 340;
  const xOf = k => PX0 + PW - (k + 0.5) * PITCH;         // the years run from the right to the left, as the words do
  const card = el("div", null, stage); card.id = "card";
  const legE = el("div", "legend", card), legF = el("div", "legend", card);
  const item = (leg, tg, text, cls) => { const it = el("span", null, leg); el(tg, cls || null, it); it.appendChild(document.createTextNode(text)); };
  item(legE, "i", Wd.leg_up); item(legE, "i", Wd.leg_down, "dry"); el("span", null, legE, Wd.leg_unit);  // the two colours, the columns' unit
  item(legF, "i", Wd.leg_up); item(legF, "i", Wd.leg_down, "dry"); item(legF, "u", Wd.leg_line);
  const cs = svg("svg", { width: 828, height: 410, viewBox: "0 0 828 410" }, card);
  const band = svg("rect", { fill: col.gold, opacity: 0 }, cs);
  const bars = CH.flow.map((v, k) => svg("rect", { x: xOf(k) - BARW / 2, width: BARW, rx: 1.6, fill: v === null ? "none" : v >= CH.mean ? col.wet : col.dry }, cs));
  const base = svg("line", { x1: PX0, x2: PX0 + PW, stroke: col.ink, "stroke-width": 3 }, cs);
  const meanLine = svg("line", { x1: PX0, x2: PX0 + PW, stroke: col.ink, "stroke-width": 3.5, "stroke-dasharray": "11 8" }, cs);
  const lateBox = svg("rect", { rx: 6, fill: "none", stroke: "#8b2a1e", "stroke-width": 4 }, cs);
  const guide = svg("line", { stroke: "#0d6b6b", "stroke-width": 3, "stroke-dasharray": "7 7", opacity: 0 }, cs);
  const levelLine = svg("path", { fill: "none", stroke: "#0d6b6b", "stroke-width": 6, "stroke-linejoin": "round", "stroke-linecap": "round" }, cs);
  const kOf = y => CH.years.indexOf(y);
  const tick0 = css(el("div", "tick", card, Wd.tick0), { right: 26 }), tick1 = css(el("div", "tick", card, Wd.tick1), { left: 26 });
  const tickLow = css(el("div", "tick", card, Wd.y_low), { left: xOf(kOf(CH.rise[0])), transform: "translateX(-50%)" });      // the band's first year
  const tickHigh = css(el("div", "tick", card, Wd.y_high), { left: xOf(kOf(CH.rise[1])), transform: "translateX(-50%)" });   // and its last
  const lateNote = css(el("div", "tick late", card, Wd.late), { left: 26 });
  const noteE = css(el("div", "tick mean", card), { left: 540, transform: "translateX(-50%)" });   // the dashed line's value, beside the four years' value
  el("b", null, noteE); noteE.appendChild(document.createTextNode(Wd.leg_mean));
  const LV = CH.level.filter(v => v !== null), LMIN = Math.min(...LV) - 8, LMAX = Math.max(...LV) + 8;

  const follow = el("div", null, stage); follow.id = "follow"; el("span", null, follow, Wd.follow);
  const src = {}; ORDER.forEach(k => { src[k] = el("div", "sources", stage); const ls = Wd["src_" + k].split(" // ").map(s => el("span", null, src[k], s)); fit(ls, LOW, 22, 1.36); });

  const VOLGA = F.rivers.volga, KAMA = F.rivers.kama;
  const pic = (im, m, a) => { ctx.globalAlpha = a; ctx.drawImage(im, 540 - 540 * m, 960 - 960 * m, 1080 * m, 1920 * m); ctx.globalAlpha = 1; };
  // two pictures and a wipe: `first` on the left of x, `second` on the right
  function wiped(first, second, m, x, a) {
    pic(first, m, a);
    if (x < 1080) { ctx.save(); ctx.beginPath(); ctx.rect(x, 0, 1080 - x, 1920); ctx.clip(); pic(second, m, a); ctx.restore(); }
  }
  // scene a: the last summer on the left of x; x runs to 0 (back to the first summer) and out again to 1080
  const xA = t => t < C.a_back[0] ? 1080 : t < C.a_fwd[0] ? 1080 * (1 - ease(seg(t, C.a_back[0], C.a_back[1]))) : 1080 * ease(seg(t, C.a_fwd[0], C.a_fwd[1]));
  const yearAt = t => { let k = 0; for (let i = 0; i < YT.length; i++) if (t >= YT[i]) k = i; return k; };
  function ground(name, t, a) {                          // one scene's picture at time t with opacity a; returns the wipe's x (or -1)
    const m = push(name, t);
    if (name === "a") { const x = xA(t); wiped(IM.now, IM.then, m, x, a); pic(IM.shore, m, a); return x; }
    if (name === "b") {
      if (t < YT[0]) { pic(IM.now, m, a); const p = ease(seg(t, C.b[0] + 0.15, YT[0] - 0.05)); if (p > 0) pic(IM.then, m, a * p); }
      else { const k = yearAt(t); if (k > 0) pic(IM.y[k - 1], m, a); pic(IM.y[k], m, a * (k > 0 ? ease(seg(t, YT[k], YT[k] + 0.12)) : 1)); }
      pic(IM.shore, m, a); return -1;
    }
    if (name === "h") { pic(IM.now, m, a); pic(IM.shore, m, a); return -1; }
    pic(name === "c" || name === "e" ? IM.wide : IM.south, m, a);
    return -1;
  }
  const path = pts => pts.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");
  const upTo = (pts, f) => { const k = f * (pts.length - 1), k0 = Math.min(Math.floor(k), pts.length - 2), frc = k - k0; return pts.slice(0, k0 + 1).concat([[lerp(pts[k0][0], pts[k0 + 1][0], frc), lerp(pts[k0][1], pts[k0 + 1][1], frc)]]); };

  window.renderAt = function (t0) { draw(clamp(t0, 0, END)); };

  function draw(t) {
    const back = t >= C.out[0];                          // the last frames return to frame 0
    const cur = back ? "h" : ORDER.filter(k => t >= C[k][0]).pop(), i = ORDER.indexOf(cur);
    ctx.fillStyle = "#17110b"; ctx.fillRect(0, 0, 1080, 1920);
    // the ground: the scene's picture; a new picture comes in over the one before it in its first DIS seconds
    const fresh = i > 0 && !back && !SAME[cur] ? seg(t, C[cur][0], C[cur][0] + DIS) : 1;
    if (fresh < 1) ground(ORDER[i - 1], t, 1);
    let wx = ground(cur, t, fresh);
    const home = back ? ease(seg(t, C.out[0], END - 1 / F.fps)) : 0;       // 1 on the last frame: frame 0's picture and words
    if (home > 0) { ground("a", 0, home); wx = -1; }
    css(wipe, { left: wx - 3 }); show(wipe, wx > 2 && wx < 1078 && fresh >= 1 ? 1 : 0);
    // how much of each scene's words stand: in after the scene starts, out before the next (two headlines never stand together)
    const on = {}; ORDER.forEach(k => { on[k] = back ? (k === "a" ? seg(home, 0.55, 1) : k === "h" ? 1 - seg(home, 0, 0.4) : 0) : win(t, C[k][0] + (k === "a" ? 0 : 0.15), C[k][1] + (k === "h" ? 1 : 0), 0.3, 0.3); });
    const pr = {}; ORDER.forEach(k => { if (on[k] > 0.001 || k === cur) pr[k] = proj(BOX[k], push(k, back && k === "a" ? 0 : t)); });

    // the headlines
    ORDER.forEach(k => {
      show(heads[k].box, on[k]);
      heads[k].box.style.transform = k === "a" || back ? "none" : `translateY(${(14 * (1 - ease(seg(t, C[k][0] + 0.15, C[k][0] + 0.45)))).toFixed(1)}px)`;
    });
    show(heads.f.sm, seg(t, C.small_f, C.small_f + 0.3));
    show(heads.g.sm, seg(t, C.small_g, C.small_g + 0.3));
    show(follow, back ? on.h : win(t, C.follow, C.h[1] + 1, 0.35, 0.3));

    // the tag: scene a: the summer whose picture holds most of the frame; scene b: the year and the sea's level against 2001
    const xa = back ? 1080 : xA(t);
    if (cur === "a" || back) { tagYr.textContent = xa >= 540 ? Wd.tag_now : Wd.tag_then; show(tagVal, 0); show(tag, back ? on.a : on.a); }
    else if (cur === "b") { const k = t < YT[0] ? 0 : yearAt(t); tagYr.textContent = RUN[k].label; tagNum.textContent = RUN[k].level; show(tagVal, 1);
      show(tag, on.b * seg(t, YT[0] - 0.35, YT[0] - 0.05)); }
    else show(tag, 0);

    // the names and the marks
    const put = (e, q, o, dx = 0, dy = 0, lim = 984) => { const hw = e.offsetWidth / 2; css(e, { left: clamp(q[0] + dx, 96 + hw, lim - hw), top: q[1] + dy }); show(e, o); };
    NAMES.forEach(([k, e, place, dx, dy]) => {
      const o = on[k] * (k === "c" && place !== "russia" ? 1 - seg(t, C.c[1] - 0.4, C.c[1] - 0.1) : 1);
      if (o <= 0.001) { show(e, 0); return; }
      const q = pr[k](P[place][0], P[place][1]);
      put(e, q, o, dx, dy, q[1] + e.offsetHeight / 2 > 1000 ? 924 : 984);      // below y 1000 the column is narrower
    });
    // the ruler (scene a, after the wipe has come back; scene h)
    const rOn = back ? 0 : on.a * seg(t, C.ruler, C.ruler + 0.35);       // not in frame 0, so not in the loop's last frames
    rulerG.setAttribute("opacity", rOn.toFixed(3));
    if (rOn > 0.001) { const p = pr.a, q0 = p(F.ruler[0][0], F.ruler[0][1]), q1 = p(F.ruler[1][0], F.ruler[1][1]);
      const g = easeOut(seg(t, C.ruler, C.ruler + 0.5)), x1 = lerp(q0[0], q1[0], g);
      const d = `M${q0[0].toFixed(1)} ${q0[1].toFixed(1)}L${x1.toFixed(1)} ${q0[1].toFixed(1)}M${q0[0].toFixed(1)} ${(q0[1] - 16).toFixed(1)}v32M${x1.toFixed(1)} ${(q0[1] - 16).toFixed(1)}v32`;
      rulerBack.setAttribute("d", d); rulerLine.setAttribute("d", d);
      put(rulerChip, [(q0[0] + q1[0]) / 2, q0[1] - 58], rOn * seg(t, C.ruler + 0.3, C.ruler + 0.6), 0, 0, 924); }
    else show(rulerChip, 0);
    // the rectangle (scene b)
    const bOn = on.b * seg(t, C.rect, C.rect + 0.35);
    rectG.setAttribute("opacity", bOn.toFixed(3));
    if (bOn > 0.001) { const [w, s, e, n] = F.rect, c4 = [pr.b(w, n), pr.b(e, n), pr.b(e, s), pr.b(w, s)], d = path(c4) + "Z";
      rectBack.setAttribute("d", d); rectLine.setAttribute("d", d);
      put(rectChip, [(c4[0][0] + c4[1][0]) / 2, c4[0][1] - 40], bOn); }
    else show(rectChip, 0);

    // the map (scenes c and e): the borders, the Volga and the Kama drawn from their heads, the dams in the order they began to work
    const mOn = Math.max(on.c, on.e, cur === "c" || cur === "e" ? fresh : 0) * (cur === "c" || cur === "e" ? 1 : 0);
    mapG.setAttribute("opacity", mOn.toFixed(3)); pinG.setAttribute("opacity", mOn.toFixed(3));
    if (mOn > 0.001) {
      const p = proj(BOX.c, push("c", t));
      const d = F.rivers.borders.map(l => path(l.map(q => p(q[0], q[1])))).join(" ");
      borderBack.setAttribute("d", d); borderLine.setAttribute("d", d);
      const f = ease(seg(t, C.river[0], C.river[1]));
      const vp = VOLGA.map(q => p(q[0], q[1])), kp = KAMA.map(q => p(q[0], q[1]));
      const dv = f > 0 ? path(upTo(vp, f)) : "", dk = f > 0 ? path(upTo(kp, Math.min(1, f * 1.6))) : "";
      volgaP.forEach(e => e.setAttribute("d", dv)); kamaP.forEach(e => e.setAttribute("d", dk));
      beads.forEach((b, j) => { const u = ((j / beads.length) + (t - C.river[0]) * 0.06) % 1, o = (u < f ? 1 : 0) * Math.min(1, u * 14, (1 - u) * 14);
        if (o > 0) { const q = vp[Math.round(u * (vp.length - 1))]; b.setAttribute("cx", q[0].toFixed(1)); b.setAttribute("cy", q[1].toFixed(1)); } b.setAttribute("opacity", (0.95 * o).toFixed(3)); });
      let newest = -1;
      pins.forEach(([ring, core], j) => { const q = p(F.dams[j].lon, F.dams[j].lat), o = seg(t, C.pins[j], C.pins[j] + 0.18), pulse = seg(t, C.pins[j], C.pins[j] + 0.8);
        if (t >= C.pins[j]) newest = j;
        core.setAttribute("cx", q[0].toFixed(1)); core.setAttribute("cy", q[1].toFixed(1)); core.setAttribute("opacity", o.toFixed(3));
        ring.setAttribute("cx", q[0].toFixed(1)); ring.setAttribute("cy", q[1].toFixed(1)); ring.setAttribute("r", (16 + 26 * pulse).toFixed(1)); ring.setAttribute("opacity", (o * (1 - pulse)).toFixed(3)); });
      if (newest >= 0 && on.c > 0.001) { const dm = F.dams[newest]; yearChip.textContent = dm.label; const q = p(dm.lon, dm.lat);
        const od = newest === 0 ? seg(t, C.pins[0], C.pins[0] + 0.18) : 1;                                // the first chip comes with its dot
        put(yearChip, q, on.c * od, dm.at === "left" ? -96 : 0, dm.at === "left" ? -8 : -58); }           // above its own dot (left of it where a chip stands above)
      else show(yearChip, 0);
      put(chipC, p(P.chip_c[0], P.chip_c[1]), on.c * seg(t, C.chip_c, C.chip_c + 0.35), 0, 0, 924);
    } else { show(yearChip, 0); show(chipC, 0); }

    // the card (scenes e and f): the columns grow in scene e; in scene f they make room for the sea's level under them
    const cOn = win(t, C.card[0], C.card[1], 0.35, 0.3);
    show(card, cOn);
    if (cOn > 0.001) {
      const sh = ease(seg(t, C.f[0] + 0.2, C.f[0] + 0.8));                  // 0 in scene e, 1 in scene f
      const BASE = lerp(338, 214, sh), TALL = lerp(262, 146, sh);
      const grow = k => easeOut(seg(t, lerp(C.bars[0], C.bars[1], k / NY), lerp(C.bars[0], C.bars[1], k / NY) + 0.35));
      CH.flow.forEach((v, k) => { if (v === null) return; const h = TALL * v / VMAX * grow(k); bars[k].setAttribute("y", (BASE - h).toFixed(1)); bars[k].setAttribute("height", h.toFixed(1)); });
      base.setAttribute("y1", BASE + 1.5); base.setAttribute("y2", BASE + 1.5);
      const ym = BASE - TALL * CH.mean / VMAX, mo = seg(t, C.bars[1] - 0.4, C.bars[1]);
      meanLine.setAttribute("y1", ym.toFixed(1)); meanLine.setAttribute("y2", ym.toFixed(1)); meanLine.setAttribute("opacity", mo.toFixed(3));
      const shOut = 1 - seg(sh, 0, 0.45), shIn = seg(sh, 0.55, 1);         // scene e's words leave before scene f's come: never both
      const k0 = kOf(CH.late[0]), k1 = kOf(CH.late[1]), lo = seg(t, C.late, C.late + 0.3) * shOut;
      const hl = TALL * Math.max(...CH.flow.slice(k0, k1 + 1)) / VMAX;
      lateBox.setAttribute("x", (xOf(k1) - BARW / 2 - 5).toFixed(1)); lateBox.setAttribute("width", (xOf(k0) - xOf(k1) + BARW + 10).toFixed(1));
      lateBox.setAttribute("y", (BASE - hl - 6).toFixed(1)); lateBox.setAttribute("height", (hl + 10).toFixed(1)); lateBox.setAttribute("opacity", lo.toFixed(3));
      show(lateNote, lo); show(noteE, shOut * seg(t, C.bars[1] - 0.3, C.bars[1]));
      show(legE, shOut); show(legF, shIn);
      // the years of the rise: a band over both rows; the sea's level as a line, drawn from the first year to the last
      const r0 = kOf(CH.rise[0]), r1 = kOf(CH.rise[1]), rl = kOf(CH.low);   // the band: the wet years; the guide: the level of the year before them
      band.setAttribute("x", (xOf(r1) - PITCH / 2).toFixed(1)); band.setAttribute("width", (xOf(r0) - xOf(r1) + PITCH).toFixed(1));
      band.setAttribute("y", 62); band.setAttribute("height", 288); band.setAttribute("opacity", (0.36 * shIn).toFixed(3));
      const yL = v => 344 - 108 * (v - LMIN) / (LMAX - LMIN);
      const lp = seg(t, C.line[0], C.line[1]), upto = lp * (NY - 1);
      let dl = "", pen = false;
      CH.level.forEach((v, k) => { if (v === null || k > upto + 0.001) return; dl += (pen ? "L" : "M") + xOf(k).toFixed(1) + " " + yL(v).toFixed(1); pen = true; });
      levelLine.setAttribute("d", dl); levelLine.setAttribute("opacity", lp > 0 ? 1 : 0);
      const gl = seg(t, C.line[1], C.line[1] + 0.5);                        // the level of 1977, carried to the last year
      guide.setAttribute("x1", xOf(rl)); guide.setAttribute("x2", lerp(xOf(rl), xOf(NY - 1), gl)); guide.setAttribute("y1", yL(CH.level[rl])); guide.setAttribute("y2", yL(CH.level[rl])); guide.setAttribute("opacity", gl > 0 ? 0.9 : 0);
      show(tick0, 1); show(tick1, Math.max(1 - seg(t, C.late - 0.25, C.late), shIn)); show(tickLow, shIn); show(tickHigh, shIn);
    }

    // scene g: the sea's water leaving as vapour (drawn lines that rise and fade), with its name
    const gOn = on.g;
    wispG.setAttribute("opacity", gOn.toFixed(3));
    if (gOn > 0.001) {
      wisps.forEach((pair, j) => { const q = pr.g(WISPS[j][0], WISPS[j][1]), u = ((t - C.g[0]) / 2.4 + j * 0.37) % 1, y = q[1] + 40 - 96 * u, x = q[0], a = Math.min(1, 2.2 * Math.sin(Math.PI * u)) * seg(y - 32, 652, 700);   // whole or not there: none is cut at the small line
        const d = `M${x.toFixed(1)} ${(y + 76).toFixed(1)}c-30 -19 30 -33 0 -52s30 -33 0 -52M${(x - 22).toFixed(1)} ${(y - 6).toFixed(1)}l22 -26l22 26`;   // a rising, waving line with an arrow's tip
        pair.forEach((w, n) => { w.setAttribute("d", d); w.setAttribute("opacity", ((n ? 0.95 : 0.8) * a).toFixed(3)); }); });
      put(vapourChip, pr.g(P.vapour[0], P.vapour[1]), gOn * seg(t, C.vapour, C.vapour + 0.35), 0, 0, 924);
    } else show(vapourChip, 0);

    // the locator and the sources
    show(loc, back ? on.a : win(t, 0, C.locator[1], 0.3, 0.4));
    ORDER.forEach(k => show(src[k], on[k]));
  }
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
