/* «آبِ هامون کجا رفت؟» in two parts (film.html?cut=p1 or p2): window.renderAt(t) draws the frame of time t (seconds)
   from /build/film.json, which src/hamoun3.py writes (every string, every number, each part's scenes, cues and
   camera, the views, the lines and the places). Nothing is typed here; the numbers in this file are pixels of the
   layout. Every frame is a pure function of t (the frames are rendered out of order by several workers).
   A part draws only its own scenes: what belongs to a scene is built and shown only if the part has that scene. */
"use strict";
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const ease = p => p * p * (3 - 2 * p);
const easeOut = p => 1 - Math.pow(1 - clamp(p), 3);
const lerp = (a, b, p) => a + (b - a) * p;
const SVGNS = "http://www.w3.org/2000/svg";
function el(tag, cls, parent, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; if (parent) parent.appendChild(e); return e; }
function svg(tag, attrs, parent) { const e = document.createElementNS(SVGNS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function css(e, o) { for (const k in o) e.style[k] = typeof o[k] === "number" ? o[k] + "px" : o[k]; return e; }
function marked(parent, s) {
  s.split(/(\{[^}]*\}|\[[^\]]*\])/).forEach(part => { if (!part) return; if (part[0] === "{") el("span", "key", parent, part.slice(1, -1)); else if (part[0] === "[") el("span", "bed", parent, part.slice(1, -1)); else parent.appendChild(document.createTextNode(part)); });
}
function show(e, p) { p = clamp(p); e.style.opacity = p.toFixed(3); e.style.visibility = p <= 0.001 ? "hidden" : "visible"; }
function fit(nodes, limit, floor, lh) {
  let size = parseFloat(getComputedStyle(nodes[0]).fontSize);
  const wide = () => Math.max(...nodes.map(n => n.scrollWidth));
  while (wide() > limit && size > floor) { size -= 1; nodes.forEach(n => css(n, { fontSize: size + "px", lineHeight: Math.round(size * lh) + "px" })); }
}
// a window in time: in over fi from a, out over fo before b (a window that starts at 0 is whole in frame 0)
const win = (t, a, b, fi = 0.3, fo = 0.25) => t < a || t > b ? 0 : Math.min(a <= 0 ? 1 : seg(t, a, a + fi), 1 - seg(t, b - fo, b));
// a line's running length (degrees on the ground at its own latitude), a point on it, a part of it
function measure(line) { const c = [0]; for (let i = 1; i < line.length; i++) c.push(c[i - 1] + Math.hypot((line[i][0] - line[i - 1][0]) * Math.cos(line[i][1] * Math.PI / 180), line[i][1] - line[i - 1][1])); return c; }
function along(line, cum, d) {
  if (d <= 0) return line[0]; const n = line.length - 1; if (d >= cum[n]) return line[n];
  let lo = 0, hi = n; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (cum[m] <= d) lo = m; else hi = m; }
  const p = (d - cum[lo]) / (cum[hi] - cum[lo]);
  return [lerp(line[lo][0], line[hi][0], p), lerp(line[lo][1], line[hi][1], p)];
}
function part(line, cum, d0, d1) {
  const out = [along(line, cum, d0)];
  for (let i = 0; i < line.length; i++) if (cum[i] > d0 && cum[i] < d1) out.push(line[i]);
  out.push(along(line, cum, d1)); return out;
}

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const cutName = new URLSearchParams(location.search).get("cut") || "p1", CUT = F.cuts[cutName];
  if (!CUT) throw new Error("no such part: " + cutName);
  const G = F.grid, SC = CUT.scenes, Q = CUT.cues, Wd = F.words, col = F.colours, END = CUT.end, S = F.springs, P = F.places;
  const ORDER = Object.keys(SC), has = n => n in SC, st = n => SC[n][0], en = n => SC[n][1];
  const sceneAt = t => { let c = ORDER[0]; for (const n of ORDER) if (t >= SC[n][0]) c = n; return c; };
  const within = (t, list) => (list || []).some(([a, b]) => t >= a && t < b);
  window.CUT = { name: cutName, end: END, scenes: SC };
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const names = new Set([F.ring]); S.forEach(s => { names.add(s.pic); if (s.water) names.add(s.water); });
  ["wide", "mid", "near"].forEach(k => names.add(F.ground[k].file)); F.dust.frames.forEach(f => names.add(f.file));
  const IM = {}; await Promise.all([...names].map(async n => { IM[n] = await load(n); }));
  await Promise.all(['900 88px "Vazirmatn"', '800 48px "Vazirmatn"', '700 48px "Vazirmatn"', '500 32px "Vazirmatn"', '400 118px "Lalezar"'].map(f => document.fonts.load(f, "آبِ هامون ۱۳۷۷")));
  const NOW = S[F.now], BEFORE = S[F.before], DRY = S[F.dry], ST = Q.spring_t || [];

  // ── the camera: a view is the lakes' place on screen (xa, ya) and a scale (frame pixels per picture pixel) ──
  const A = { lon: F.views.close[0], lat: F.views.close[1] };
  const VW = {};
  for (const k in F.views) { const [lon, lat, s] = F.views[k]; VW[k] = { s, xa: 540 + s * (A.lon - lon) / G.dlon, ya: 960 - s * (A.lat - lat) / G.dlat }; }
  const key = (v, m) => ({ s: VW[v].s * m, xa: 540 + (VW[v].xa - 540) * m, ya: 960 + (VW[v].ya - 960) * m });
  const K = CUT.camera;
  function cam(t) {
    let i = 0; while (i < K.length - 2 && t >= K[i + 1][0]) i++;
    const a = key(K[i][1], K[i][2]), b = key(K[i + 1][1], K[i + 1][2]);
    const raw = seg(t, K[i][0], K[i + 1][0]), p = K[i][1] === K[i + 1][1] ? raw : ease(raw);
    const s = Math.exp(lerp(Math.log(a.s), Math.log(b.s), p));
    const q = Math.abs(b.s - a.s) < 1e-9 ? p : (s - a.s) / (b.s - a.s);      // a zoom about one fixed point of the ground
    return { s, xa: lerp(a.xa, b.xa, q), ya: lerp(a.ya, b.ya, q) };
  }
  let V = cam(0);
  const X = lon => V.xa + V.s * (lon - A.lon) / G.dlon, Y = lat => V.ya - V.s * (lat - A.lat) / G.dlat;
  const path = pts => pts.map((p, i) => (i ? "L" : "M") + X(p[0]).toFixed(1) + "," + Y(p[1]).toFixed(1)).join("");

  // ── the layers, bottom to top ──
  const cv = el("canvas", null, stage); cv.id = "ground"; cv.width = 1080; cv.height = 1920;
  const ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  const map = svg("svg", { width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, stage);
  const glow = svg("filter", { id: "glow", x: "-50%", y: "-50%", width: "200%", height: "200%" }, svg("defs", {}, map));
  svg("feGaussianBlur", { stdDeviation: 6 }, glow);
  const farm = svg("path", { fill: "none", stroke: "#7ed957", "stroke-width": 34, "stroke-linecap": "round", "stroke-linejoin": "round", opacity: 0 }, map);
  const riverGlow = svg("path", { fill: "none", stroke: col.river, "stroke-width": 16, "stroke-linecap": "round", "stroke-linejoin": "round", filter: "url(#glow)", opacity: 0 }, map);
  const riverLine = svg("path", { fill: "none", stroke: col.river, "stroke-width": 7, "stroke-linecap": "round", "stroke-linejoin": "round", opacity: 0 }, map);
  const riverCore = svg("path", { fill: "none", stroke: "#ffffff", "stroke-width": 2.4, "stroke-linecap": "round", "stroke-linejoin": "round", opacity: 0 }, map);
  const beads = []; for (let i = 0; i < 26; i++) beads.push(svg("circle", { r: 5.5, fill: "#ffffff", opacity: 0 }, map));
  const defs = map.querySelector("defs"), fg = svg("linearGradient", { id: "fadeg", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  [[0, "#000"], [500 / 1920, "#000"], [570 / 1920, "#fff"], [1225 / 1920, "#fff"], [1282 / 1920, "#000"], [1, "#000"]].forEach(([o, c]) => svg("stop", { offset: o, "stop-color": c }, fg));
  svg("rect", { x: 0, y: 0, width: 1080, height: 1920, fill: "url(#fadeg)" }, svg("mask", { id: "fade", maskUnits: "userSpaceOnUse", x: 0, y: 0, width: 1080, height: 1920 }, defs));
  const lines = svg("g", { mask: "url(#fade)" }, map);
  const edge = (wd, dash) => [svg("path", { fill: "none", stroke: "rgba(10,6,2,0.55)", "stroke-width": wd + 5, "stroke-linejoin": "round", "stroke-linecap": "round" }, lines),
                              svg("path", { fill: "none", stroke: "#ffffff", "stroke-width": wd, "stroke-dasharray": dash, "stroke-linejoin": "round" }, lines)];
  const bAP = edge(3.5, "10 9"), bIP = edge(3.5, "10 9"), bIA = edge(6, "16 11");
  const dots = {}; for (const k of ["zabol", "kajaki", "lashkargah", "kamalkhan", "chahnimeh", "lake"]) dots[k] = [svg("circle", { r: 16, fill: "none", stroke: col.pin, "stroke-width": 4, opacity: 0 }, map), svg("circle", { r: 9, fill: k === "zabol" ? "#ffffff" : col.pin, stroke: k === "zabol" ? "#1d140c" : "#ffffff", "stroke-width": 3.5, opacity: 0 }, map)];
  const bedLine = [svg("path", { fill: "none", stroke: "rgba(10,6,2,0.5)", "stroke-width": 8, "stroke-linejoin": "round", opacity: 0 }, map),
                   svg("path", { fill: "none", stroke: "#7fd6ff", "stroke-width": 4, "stroke-linejoin": "round", opacity: 0 }, map)];
  const windLine = [svg("path", { fill: "none", stroke: "rgba(10,6,2,0.55)", "stroke-width": 17, "stroke-linecap": "round", opacity: 0 }, map),
                    svg("path", { fill: "none", stroke: "#ffffff", "stroke-width": 10, "stroke-linecap": "round", opacity: 0 }, map),
                    svg("path", { fill: "#ffffff", stroke: "rgba(10,6,2,0.55)", "stroke-width": 3, "stroke-linejoin": "round", opacity: 0 }, map)];
  const LIA = F.lines.ia, cIA = measure(LIA), RIV = F.lines.river, cR = measure(RIV), RL = cR[cR.length - 1];
  // the stretch of the river with the irrigated land: from Kajaki down to the head of the delta (Kamal Khan)
  const nearest = pt => { let b = 0, bd = 1e9; RIV.forEach((p, i) => { const d = Math.hypot(p[0] - pt[0], p[1] - pt[1]); if (d < bd) { bd = d; b = i; } }); return cR[b]; };
  const dKaj = nearest(P.kajaki), dKam = nearest(P.border_end);

  const shadeTop = el("div", null, stage), shadeBot = el("div", null, stage); shadeTop.id = "shade-top"; shadeBot.id = "shade-bot";
  const country = (name, where, size) => { const e = css(el("div", "country", stage, name), { fontSize: size, lineHeight: Math.round(size * 1.3) }); e.dataset.at = where; return e; };
  const labels = { close: [country(Wd.iran, "iran_close", 60), country(Wd.afg, "afg_close", 48)] };
  if (has("hook")) {
    labels.mid = [country(Wd.iran, "iran_mid", 78), country(Wd.afg, "afg_mid", 78)];
    labels.wide = [country(Wd.iran, "iran_wide", 56), country(Wd.afg, "afg_wide", 78), country(Wd.pak, "pak_wide", 66)];
  }
  if (has("dust")) {
    labels.dust = [country(Wd.iran, "iran_dust", 60), country(Wd.afg, "afg_dust", 62)];
    labels.disp = [country(Wd.iran, "iran_disp", 60), country(Wd.afg, "afg_disp", 64)];
  }
  const zabol = el("div", "place", stage, Wd.zabol);
  const make = (on, f) => on ? f() : null;
  const windName = make(has("dust"), () => css(el("div", "rivername", stage, Wd.wind), { fontSize: 46, lineHeight: 58, transform: "none" }));
  const bedName = make(has("dust"), () => css(el("div", "rivername", stage, Wd.bed), { fontSize: 48, lineHeight: 60, background: "rgba(8, 26, 52, 0.93)" }));   // nearly opaque: the border's dashes pass behind it
  const riverName = make(has("why"), () => el("div", "rivername", stage, Wd.river));
  const lakeName = make(has("hook"), () => css(el("div", "rivername", stage, Wd.lake), { color: "var(--gold)", fontSize: 48, lineHeight: 58, transform: "none" }));
  const pins = has("dams") ? Wd.pins.map(([at, nm, yr]) => { const e = el("div", at === "lashkargah" ? "pin farm" : "pin", stage); el("span", "nm", e, nm); yr.split(" // ").forEach(y => { if (y) el("span", "yr", e, y); }); e.dataset.at = at; return e; }) : [];
  const notes = has("lives") ? Wd.lives_notes.map((nm, i) => { const e = el("div", "pin", stage); el("span", "nm", e, nm); css(e, { top: 560 + i * 108 }); return e; }) : [];
  const notesFoot = make(has("lives"), () => css(el("div", "place", stage, Wd.lives_note), { left: 96, top: 560 + Wd.lives_notes.length * 108 + 6, fontSize: 40, lineHeight: 50 }));
  const wipe = el("div", null, stage); wipe.id = "wipe";

  // the headlines: one or two lines, small lines under them (smAt: when the small lines come)
  const heads = [];
  function head(name, text, small, a, b, smAt) {
    const box = el("div", "head", stage), ls = text.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
    ls.forEach(l => css(l, { fontSize: ls.length > 1 ? 76 : 88, lineHeight: ls.length > 1 ? 106 : 122 }));
    fit(ls, 828, 52, 1.39);
    const sm = (small ? small.split(" // ") : []).map((s, i) => { const e = el("span", i ? "small more" : "small", box, s); fit([e], 828, 40, 1.4); return e; });
    heads.push({ name, box, sm, a, b, smAt: smAt === undefined ? a : smAt });
  }
  if (has("hook")) head("hook", Wd.hook, null, 0, en("hook"));
  if (has("run")) { head("era1", Wd.era1, null, st("run"), ST[13]); head("era2", Wd.era2, null, ST[13], en("run")); }
  if (has("why")) head("why", Wd.why, null, st("why"), en("why"));
  if (has("dams")) head("dams", Wd.dams, null, st("dams"), en("dams"));
  if (has("now")) head("now", Wd.now, null, st("now"), Q.back[0] + 0.25);
  if (has("dust")) head("dust", Wd.dust_head, Wd.dust_small, 0, en("dust"), Q.dsmall);
  if (has("health")) head("health", Wd.health_head, Wd.health_small, st("health"), en("health"));
  if (has("lives")) head("lives", Wd.lives_head, Wd.lives_small, st("lives"), en("lives"));
  if (has("dispute")) head("dispute", Wd.dispute_head, null, st("dispute"), en("dispute"));
  if (has("end2")) head("end", Wd.end_head, null, st("end2") + 0.3, END + 9);

  // the spring's tag (its year and its water). Two of them: in a wipe each side of the line has its own spring. A
  // tag has two blocks (the year with its small line on the right, the number with its unit on the left); a block
  // shows only while it lies wholly on its own spring's side of the line: it goes as the line reaches it and the
  // other spring's block comes once the line has passed. So a number never stands beside the other spring's
  // picture, and no frame mixes the digits of two years.
  const mkTag = () => { const box = el("div", "tag", stage), yr = el("div", "yr", box), sb = el("div", "sub", box), val = el("div", "val", box);
    return { box, yr, sb, val, n: el("span", "n", val), u: el("span", "u", val, Wd.unit), sl: el("span", "subl", val) }; };
  const tagA = mkTag(), tagB = mkTag();
  function setTag(T, sp, sb, sl, top, on, cutX, side) {             // sb: the small line under the year; sl: under the number
    if (sp) { T.yr.textContent = Wd.spring.replace("{}", sp.label);
      if (sp.km2 === null) { T.n.textContent = Wd.gap; T.n.className = "n nogap"; T.u.style.display = "none"; }
      else { T.n.textContent = sp.shown; T.n.className = "n"; T.u.style.display = "block"; } }
    T.sb.textContent = sb; T.sl.textContent = sl; css(T.box, { top }); show(T.box, sp ? on : 0);
    let oYr = 1, oVal = 1;
    if (sp && cutX !== null) {
      const yrLeft = 924 - Math.max(T.yr.offsetWidth, T.sb.offsetWidth), valRight = 96 + T.val.offsetWidth, F = 36;
      if (side === "left") { oYr = seg(cutX, 924 - F, 924); oVal = seg(cutX, valRight - F, valRight); }
      else { oYr = 1 - seg(cutX, yrLeft, yrLeft + F); oVal = 1 - seg(cutX, 96, 96 + F); }
    }
    show(T.yr, oYr); show(T.sb, oYr); show(T.val, oVal);
  }
  // the hook's wipe: the line creeps in from frame 0 (something moves at once) and sweeps after about 0.7 s, so the
  // first spring's year can be read before the line reaches it
  const sig = (p, n) => { const a = Math.pow(p, n), b = Math.pow(1 - p, n); return a / (a + b); };
  const wipeP = u => 0.12 * u + 0.88 * sig(u, 2.6);
  const held = make(has("run"), () => css(el("div", "chip", stage, Wd.held), { top: 1040 }));
  const hedge = make(has("dams"), () => css(el("div", "chip", stage, Wd.share), { top: 1392 }));
  const when = make(has("dust"), () => { const e = el("div", null, stage); e.id = "when"; el("div", "d", e, Wd.dust_date); return e; });
  const whenH = when ? el("div", "h", when) : null;
  let dTop = 1100;
  const boxes = has("dispute") ? Wd.dispute_boxes.map(s => { const e = css(el("div", "chip", stage), { top: dTop, fontSize: 42, lineHeight: 56 }); s.split(" // ").forEach(l => el("span", null, e, l)); fit([e], 812, 36, 1.33); dTop += e.offsetHeight + 14; return e; }) : [];

  // the small chart: forty springs against their mean
  const chart = make(has("run"), () => el("div", "card", stage));
  let bars = [], mark = null;
  const BX = 22, BW = 784, PITCH = BW / S.length, BASE = 152, TALL = 92, barW = 13;
  if (chart) {
    const leg = el("div", "legend", chart);
    [["i", col.wet, Wd.legend[0]], ["i", col.dry, Wd.legend[1]], ["b", null, Wd.mean]].forEach(([tg, c, s]) => { const it = el("span", null, leg), sw = el(tg, null, it); if (c) sw.style.background = c; it.appendChild(document.createTextNode(s)); });
    const cs = svg("svg", { width: 828, height: 206, viewBox: "0 0 828 206" }, chart);
    const yMean = BASE - TALL * F.mean / F.vmax;
    svg("line", { x1: BX, x2: BX + BW, y1: BASE + 1.5, y2: BASE + 1.5, stroke: col.ink, "stroke-width": 3 }, cs);
    bars = S.map((s, k) => svg("rect", { x: BX + BW - (k + 0.5) * PITCH - barW / 2, width: barW, rx: 2.5, fill: s.km2 === null ? col.gapc : s.above ? col.wet : col.dry }, cs));
    svg("line", { x1: BX, x2: BX + BW, y1: yMean, y2: yMean, stroke: col.ink, "stroke-width": 3.5, "stroke-dasharray": "11 8" }, cs);
    mark = svg("rect", { width: barW + 8, rx: 5, fill: "none", stroke: col.ink, "stroke-width": 3.5 }, cs);
    css(el("div", "tick", chart, S[0].label), { right: 22 });
    css(el("div", "tick", chart, S[S.length - 1].label), { left: 22 });
    css(el("div", "tick", chart, S[13].label), { left: BX + BW - 13.5 * PITCH, transform: "translateX(-50%)" });
  }

  // the rain card: the winters' precipitation against the lake's water, later against earlier
  const rainCard = make(has("why"), () => el("div", "card", stage));
  const rows = rainCard ? [[Wd.rain_item, Wd.rain_less, Math.min(F.rain.cru, F.rain.era5), Math.max(F.rain.cru, F.rain.era5), "#5b8fc4", 12],
                           [Wd.lake_item, Wd.lake_less, F.rain.lake, F.rain.lake, col.wet, 108]].map(([nm, less, lo, hi, c, top]) => {
    const r = css(el("div", "row", rainCard), { top }); const n = el("div", "name", r, nm), l = el("div", "less", r, less); l.style.color = "#a03129";
    fit([n], 520, 30, 1.25);
    const tr = el("div", "track", r), sp = el("div", "span", tr), fl = el("div", "fill", tr); fl.style.background = c; sp.style.background = c;
    return { lo, hi, fl, sp };
  }) : [];

  // the last words: the next part (part 1, in the tag's place) or the call to send it on (part 2, under the tag)
  const follow = el("div", null, stage); follow.id = "follow";
  if (has("now")) { const box = el("div", "next", follow); Wd.teaser.forEach((s, i) => el("span", i ? "big" : "lead", box, s)); css(follow, { top: 1096 }); }
  else { Wd.follow.forEach(s => el("span", null, follow, s)); css(follow, { top: 1340 }); fit([...follow.children], 828, 40, 1.4); }
  const src = {};
  [["water", has("hook") || has("end2")], ["map", has("hook")], ["rain", has("why")], ["dust", has("dust")], ["lives", has("lives")], ["dispute", has("dispute")]]
    .forEach(([k, on]) => { if (on) { src[k] = el("div", "sources", stage, Wd["src_" + k]); fit([src[k]], 828, 26, 1.25); } });

  function put(sp, a) {
    const gx = X(G.lon0), gy = Y(G.lat1), gw = V.s * G.w, gh = V.s * G.h;
    ctx.globalAlpha = a; ctx.drawImage(IM[sp.pic], gx, gy, gw, gh);
    if (sp.held) { ctx.globalAlpha = a * 0.40; ctx.fillStyle = "#efe7d8"; ctx.fillRect(gx, gy, gw, gh); }
    if (sp.water) { ctx.globalAlpha = a; ctx.drawImage(IM[sp.water], gx, gy, gw, gh); }
    ctx.globalAlpha = 1;
  }
  const clipped = (x0, x1, f) => { ctx.save(); ctx.beginPath(); ctx.rect(x0, 0, x1 - x0, 1920); ctx.clip(); f(); ctx.restore(); };
  const place = (e, lon, lat, dx = 0, dy = 0) => css(e, { left: X(lon) + dx, top: Y(lat) + dy });

  window.renderAt = function (t0) {
    const t = clamp(t0, 0, END);
    V = cam(t);
    const cur = sceneAt(t), back = has("hook") && t >= Q.back[0];          // back: part 1's last frames return to frame 0

    // the ground and the spring's picture
    ctx.globalAlpha = 1; ctx.fillStyle = "#17110b"; ctx.fillRect(0, 0, 1080, 1920);
    for (const k of ["wide", "mid", "near"]) {
      const g = F.ground[k], a = k === "mid" ? seg(V.s, 0.165, 0.22) : k === "near" ? seg(V.s, 0.44, 0.58) : 1;
      if (a <= 0) continue;
      const x0 = X(g.w), y0 = Y(g.n);
      ctx.globalAlpha = a; ctx.drawImage(IM[g.file], x0, y0, X(g.e) - x0, Y(g.s) - y0);
    }
    ctx.globalAlpha = 1;
    let sp = null, k = -1, kt = -1, xLine = -1, cutX = null, spRight = null;   // cutX: the line of a wipe; spRight: the spring right of it
    if (cur === "hook" || back) {                     // 1377 under the line, 1405 behind it (and back again at the end)
      const wp = back ? 1 - ease(seg(t, Q.back[0], Q.back[1])) : wipeP(seg(t, Q.wipe[0], Q.wipe[1])), xw = 1080 * (1 - wp);
      put(BEFORE, 1);
      if (wp > 0) clipped(xw, 1080, () => put(NOW, 1));
      sp = BEFORE; spRight = NOW; cutX = xw;
      if (wp > 0.002 && wp < 0.998) xLine = xw;
    } else if (cur === "run") {
      for (let i = 0; i < S.length; i++) if (t >= ST[i]) k = i;
      if (k < 0) { put(NOW, 1); const p = ease(seg(t, Q.t0 - 0.45, Q.t0 - 0.03)); if (p > 0) put(S[0], p); if (t >= Q.t0 - 0.3) sp = S[0]; }
      else { if (k > 0) put(S[k - 1], 1); put(S[k], k > 0 ? ease(seg(t, ST[k], ST[k] + 0.14)) : 1);
        kt = 0; for (let i = 0; i < S.length; i++) if (t - 0.07 >= ST[i]) kt = i; sp = S[kt]; }
    } else if (cur === "dust" || cur === "health" || cur === "lives") put(DRY, 1);
    else if (cur === "dispute") { const p = ease(seg(t, st("dispute"), st("dispute") + 0.6)); if (p < 1) put(DRY, 1); if (p > 0) put(NOW, p); }
    else if (cur === "end2") {                        // this spring, then the full lake of 1377 from the left
      const w2 = ease(seg(t, Q.wipe2[0], Q.wipe2[1])), xr = 1080 * w2;
      put(NOW, 1);
      if (w2 > 0) clipped(0, xr, () => put(BEFORE, 1));
      sp = BEFORE; cutX = xr;                         // its tag comes in with it, left of the line
      if (w2 > 0.002 && w2 < 0.998) xLine = xr;
    } else { put(NOW, 1); if (cur === "now") sp = NOW; }
    css(wipe, { left: xLine - 3 }); show(wipe, xLine >= 0 ? 1 : 0);
    ctx.drawImage(IM[F.ring], X(G.lon0), Y(G.lat1), V.s * G.w, V.s * G.h);

    // the dust storm (part 2): three passes of one day over the whole frame; the bed's outline and name, the wind
    let dA = 0;
    if (has("dust")) {
      dA = seg(t, Q.dframes[0], Q.dframes[0] + 1.0) * (1 - seg(t, st("lives"), st("lives") + 1.0));
      if (dA > 0) { const D = F.dust, x0 = X(D.w), y0 = Y(D.n), w = X(D.e) - x0, h = Y(D.s) - y0;
        ctx.globalAlpha = dA; ctx.drawImage(IM[D.frames[0].file], x0, y0, w, h);
        for (let i = 1; i < D.frames.length; i++) { const a = ease(seg(t, Q.dframes[i], Q.dframes[i] + 0.9)); if (a > 0) { ctx.globalAlpha = dA * a; ctx.drawImage(IM[D.frames[i].file], x0, y0, w, h); } }
        ctx.globalAlpha = 1; }
      const bedOn = dA * seg(t, Q.bed[0], Q.bed[1]);
      if (bedOn > 0) { const d = F.lines.lake.map(r => path(r) + "Z").join(""); bedLine.forEach(e => e.setAttribute("d", d)); }
      bedLine.forEach((e, i) => e.setAttribute("opacity", (bedOn * (i ? 1 : 0.9)).toFixed(3)));
      place(bedName, P.bed_name[0], P.bed_name[1]); show(bedName, bedOn);
      const windOn = dA * seg(t, Q.wind[0], Q.wind[0] + 0.5);
      if (windOn > 0) { const x0 = X(P.wind0[0]), y0 = Y(P.wind0[1]), x1 = X(P.wind1[0]), y1 = Y(P.wind1[1]), L = Math.hypot(x1 - x0, y1 - y0), ux = (x1 - x0) / L, uy = (y1 - y0) / L;
        const g = easeOut(seg(t, Q.wind[0], Q.wind[1])), ex = x0 + (x1 - x0) * g, ey = y0 + (y1 - y0) * g, hx = ex + ux * 34, hy = ey + uy * 34;
        const shaft = `M${x0.toFixed(1)},${y0.toFixed(1)}L${ex.toFixed(1)},${ey.toFixed(1)}`;
        windLine[0].setAttribute("d", shaft); windLine[1].setAttribute("d", shaft);
        windLine[2].setAttribute("d", `M${hx.toFixed(1)},${hy.toFixed(1)}L${(ex - uy * 26).toFixed(1)},${(ey + ux * 26).toFixed(1)}L${(ex + uy * 26).toFixed(1)},${(ey - ux * 26).toFixed(1)}Z`); }
      windLine.forEach(e => e.setAttribute("opacity", windOn.toFixed(3)));
      // the wind's name leaves with the question (the number's lines need its place); the arrow stays
      css(windName, { left: 96, top: Y(P.wind0[1]) - 84 }); show(windName, windOn * (1 - seg(t, st("health") - 0.3, st("health"))));
      show(when, win(t, 0, st("lives"), 0.4, 0.3));
      whenH.textContent = Wd.dust_hours[t < Q.dframes[1] + 0.45 ? 0 : t < Q.dframes[2] + 0.45 ? 1 : 2];
    }
    shadeTop.style.opacity = (1 - 0.35 * dA).toFixed(3); shadeBot.style.opacity = (1 - 0.45 * dA).toFixed(3);

    // the border: part 1 draws it once in the hook and takes it away for the loop; part 2 has it from frame 0,
    // but not on the dry bed's picture
    let bOn = 1, bp = 1;
    if (has("hook")) { bp = ease(seg(t, Q.border[0], Q.border[1])); bOn = back ? 1 - seg(t, Q.back[0], Q.back[0] + 0.3) : 1; }
    if (has("lives")) bOn = 1 - seg(t, st("lives"), st("lives") + 0.6) * (1 - seg(t, st("dispute"), st("dispute") + 0.5));
    const dIA = path(part(LIA, cIA, 0, cIA[cIA.length - 1] * bp));
    bIA.forEach((e, i) => { e.setAttribute("d", dIA); e.setAttribute("opacity", (bOn * (bp > 0 ? 1 : 0) * (i ? 0.95 : 1)).toFixed(3)); });
    const far = bOn * (has("hook") ? seg(t, Q.border[1] - 0.3, Q.border[1] + 0.3) : 1) * (1 - seg(V.s, 0.5, 0.7));
    [[bIP, F.lines.ip], [bAP, F.lines.ap]].forEach(([pair, line]) => pair.forEach(e => { if (far > 0) e.setAttribute("d", path(line)); e.setAttribute("opacity", (far * 0.85).toFixed(3)); }));
    const inDisp = has("dispute") && t >= st("dispute") + 0.5 && t < en("dispute");
    bIA[1].setAttribute("stroke", inDisp ? col.gold : "#ffffff"); bIA[1].setAttribute("stroke-width", inDisp ? 9 : 6);

    // the countries' names (one set for each view) and Zabol
    const lab = Q.labels ? Q.labels.map(a => seg(t, a, a + 0.3)) : [1, 1, 1];
    const bare = (has("lives") && t >= st("lives") && t < st("dispute") + 0.4) || cur === "end2";   // no names on the dry bed, none at the end
    const rainOn = has("why") ? win(t, Q.card, en("why"), 0.4, 0.25) : 0;
    const scale = { close: bare ? 0 : 0.9 * seg(V.s, 0.62, 0.74),
                    mid: (within(t, Q.mid) ? 1 : 0) * seg(V.s, 0.24, 0.3) * (1 - seg(V.s, 0.415, 0.46)),   // gone before a zoom-in carries them out of the safe area
                    wide: 1 - seg(V.s, 0.143, 0.158),
                    dust: has("dust") ? 1 - seg(t, st("lives") - 0.2, st("lives") + 0.3) : 0,
                    disp: has("dispute") ? win(t, st("dispute") + 0.9, st("end2") + 0.3, 0.4, 0.3) : 0 };
    for (const v in labels) labels[v].forEach((e, i) => { const [lon, lat] = P[e.dataset.at]; place(e, lon, lat);
      show(e, bOn * scale[v] * lab[Math.min(i, 1)] * (e.dataset.at === "pak_wide" && !(has("dams") && t >= st("dams")) ? 0 : 1)); });
    const zOn = bare ? 0 : bOn * lab[2] * seg(V.s, 0.3, 0.38);
    css(zabol, { left: X(P.zabol[0]) - 22 - zabol.offsetWidth, top: Y(P.zabol[1]) - 30 }); show(zabol, zOn);
    const dot = (name, on, pulse) => { const [lon, lat] = name === "lake" ? [A.lon - 0.12, A.lat + 0.12] : P[name], [ring, core] = dots[name];
      core.setAttribute("cx", X(lon)); core.setAttribute("cy", Y(lat)); core.setAttribute("opacity", on.toFixed(3));
      ring.setAttribute("cx", X(lon)); ring.setAttribute("cy", Y(lat)); ring.setAttribute("r", (16 + 22 * pulse).toFixed(1)); ring.setAttribute("opacity", (on * (1 - pulse)).toFixed(3)); };
    dot("zabol", zOn, 1);

    // the river: part 1 draws it from its head to the lakes, then it flows; only in the far views
    const rT = Q.river ? Q.river[0] : 0, rp = Q.river ? ease(seg(t, Q.river[0], Q.river[1])) : 1;
    const rOn = (within(t, Q.river_on) ? 1 : 0) * (1 - seg(V.s, 0.5, 0.72));
    const dR = rOn > 0 ? path(part(RIV, cR, 0, RL * rp)) : "";
    [[riverGlow, 0.9], [riverLine, 1], [riverCore, 0.9]].forEach(([e, o]) => { e.setAttribute("d", dR); e.setAttribute("opacity", (rOn * o).toFixed(3)); });
    beads.forEach((b, i) => { const f = ((i / beads.length) + (t - rT) * 0.055) % 1, on = rOn * (f < rp ? 1 : 0) * Math.min(1, f * 12, (1 - f) * 12);
      if (on > 0) { const [lon, lat] = along(RIV, cR, f * RL); b.setAttribute("cx", X(lon)); b.setAttribute("cy", Y(lat)); } b.setAttribute("opacity", (on * 0.95).toFixed(3)); });
    const wideOn = rOn * (1 - seg(V.s, 0.17, 0.215));
    if (riverName) { place(riverName, P.river_name[0], P.river_name[1]); show(riverName, wideOn * seg(t, rT + 1.0, rT + 1.4)); }
    let lakeOn = 0;
    if (lakeName) {
      lakeOn = Math.max(wideOn * seg(t, Q.river[1] - 0.2, Q.river[1] + 0.2), win(t, Q.labels[2] + 0.1, en("hook"), 0.3, 0.3));
      place(lakeName, A.lon - 0.12, A.lat + 0.12, V.s < 0.2 ? 26 : -118, V.s < 0.2 ? -34 : -230); show(lakeName, lakeOn);
    }
    dot("lake", V.s < 0.2 ? lakeOn : 0, 0.5 + 0.5 * Math.sin((t - rT) * 4));

    // the dams and the irrigated land, in the river's order (part 1)
    const pOn = has("dams") && t >= st("dams") ? 1 - seg(t, en("dams") - 0.1, en("dams") + 0.4) : 0;
    const fOn = pOn > 0 ? pOn * seg(t, Q.pins[1], Q.pins[1] + 0.5) * (1 - seg(V.s, 0.15, 0.2)) : 0;
    if (fOn > 0) farm.setAttribute("d", path(part(RIV, cR, dKaj, dKam))); farm.setAttribute("opacity", (fOn * 0.78).toFixed(3));
    const OFF = { kajaki: [28, -8, "l"], lashkargah: [-34, -196, "r"], kamalkhan: [0, 30, "c"], chahnimeh: [-48, 34, "r"] };
    pins.forEach((e, i) => { const at = e.dataset.at, [lon, lat] = P[at], on = pOn * seg(t, Q.pins[i], Q.pins[i] + 0.3) * (i < 2 ? 1 - seg(t, Q.leave - 0.3, Q.leave) : seg(V.s, 0.3, 0.38));   // the wide view's two pins go before the camera leaves it (the pan carries them out of the safe area)
      const pop = easeOut(seg(t, Q.pins[i], Q.pins[i] + 0.35));
      const [dx, dy, anchor] = OFF[at], wd = e.offsetWidth;
      css(e, { left: X(lon) + dx - (anchor === "r" ? wd : anchor === "c" ? wd / 2 : 0), top: Y(lat) + dy, transform: `scale(${(0.7 + 0.3 * pop).toFixed(3)})` }); show(e, on);
      dot(at, on, seg(t, Q.pins[i], Q.pins[i] + 0.9)); });

    // the headlines
    heads.forEach(h => { let o = win(t, h.a, h.b); if (h.name === "hook" && back) o = seg(t, Q.back[0] + 0.25, Q.back[0] + 0.6);
      show(h.box, o); h.box.style.transform = `translateY(${(14 * (1 - ease(seg(t, h.a, h.a + 0.3))) * (h.a > 0 ? 1 : 0)).toFixed(1)}px)`;
      h.sm.forEach(e => show(e, h.smAt > h.a ? seg(t, h.smAt, h.smAt + 0.35) : 1)); });

    // the spring's tag, the note of a spring without a clean picture. In a wipe: tagA is the spring left of the
    // line, tagB the spring right of it
    let tagOn = 0, tagTop = 1150, sub = "";
    let subLeft = "";                                 // the first spring's note stands under its number: the block the line reaches last
    if (back) { tagOn = seg(t, Q.back[0] + 0.3, Q.back[0] + 0.6); subLeft = Wd.wet; }
    else if (cur === "hook") { tagOn = 1 - seg(t, Q.swap - 0.25, Q.swap); subLeft = Wd.wet; }
    else if (cur === "run") { tagOn = seg(t, Q.t0 - 0.3, Q.t0) * (1 - seg(t, en("run") - 0.25, en("run"))); tagTop = 1116; }
    else if (cur === "now") { tagOn = seg(t, st("now") + 0.6, st("now") + 0.9) * (1 - seg(t, Q.teaser - 0.3, Q.teaser)); tagTop = 1066; sub = Wd.mean_value; }
    else if (cur === "end2") { tagOn = seg(t, Q.wipe2[0] - 0.1, Q.wipe2[0]); tagTop = 1140; }
    setTag(tagA, sp, sub, subLeft, tagTop, tagOn, cutX, "left");
    setTag(tagB, spRight, Wd.this_spring, "", tagTop, tagOn, cutX, "right");
    if (held) { let o = 0;
      if (cur === "run") S.forEach((s, i) => { if (s.held && s.km2 !== null) o = Math.max(o, win(t, ST[i] - 0.08, (i + 1 < S.length ? ST[i + 1] : en("run")) + 0.25, 0.1, 0.25)); });
      show(held, o * tagOn); }
    if (hedge) show(hedge, win(t, Q.hedge, en("dams"), 0.4, 0.3));
    notes.forEach((e, i) => { const on = win(t, Q.notes[i], en("lives"), 0.3, 0.3), pop = easeOut(seg(t, Q.notes[i], Q.notes[i] + 0.35));
      css(e, { left: i % 2 ? 924 - e.offsetWidth : 96, transform: `scale(${(0.7 + 0.3 * pop).toFixed(3)})` }); show(e, on); });
    if (notesFoot) show(notesFoot, win(t, Q.notes[Q.notes.length - 1] + 0.2, en("lives"), 0.3, 0.3));
    boxes.forEach((e, i) => show(e, win(t, Q.boxes[i], en("dispute"), 0.35, 0.3)));

    // the small chart (part 1)
    if (chart) {
      const chartOn = Math.max(win(t, st("run") + 0.3, en("run"), 0.4, 0.25), win(t, st("now") + 0.6, Q.back[0] + 0.2, 0.4, 0.25));
      show(chart, chartOn);
      if (chartOn > 0) {
        const all = t >= en("run");
        bars.forEach((b, i) => { const g = all ? 1 : easeOut(seg(t, ST[i], ST[i] + 0.22)), h = S[i].km2 === null ? 7 * g : Math.max(2.5, TALL * S[i].km2 / F.vmax) * g;
          b.setAttribute("y", BASE - h); b.setAttribute("height", h); b.setAttribute("opacity", g > 0 ? 1 : 0); });
        const at = all ? S.length - 1 : k < 0 ? -1 : kt;
        if (at >= 0) { const h = S[at].km2 === null ? 7 : Math.max(2.5, TALL * S[at].km2 / F.vmax);
          mark.setAttribute("x", BX + BW - (at + 0.5) * PITCH - barW / 2 - 4); mark.setAttribute("y", BASE - h - 5); mark.setAttribute("height", h + 9); mark.setAttribute("opacity", 1); }
        else mark.setAttribute("opacity", 0);
      }
    }

    // the rain card (part 1)
    if (rainCard) { show(rainCard, rainOn);
      if (rainOn > 0) { const p = ease(seg(t, Q.card + 0.5, Q.card + 1.6));
        rows.forEach(r => { css(r.fl, { width: (100 * lerp(1, r.lo, p)).toFixed(2) + "%" }); css(r.sp, { right: (100 * r.lo).toFixed(2) + "%", width: (100 * (r.hi - r.lo) * p).toFixed(2) + "%" }); }); } }

    show(follow, has("now") ? win(t, Q.teaser, Q.back[0] + 0.2, 0.35, 0.25) : seg(t, Q.follow, Q.follow + 0.35));
    if (has("hook")) {
      show(src.water, back ? seg(t, Q.back[0] + 0.3, Q.back[0] + 0.6) : Math.max(win(t, 0, Q.swap), win(t, st("run") + 0.3, en("run")), win(t, st("now") + 0.6, Q.back[0] + 0.2)));
      show(src.map, Math.max(win(t, Q.swap + 0.3, en("hook")), win(t, st("dams"), en("dams"))));
      show(src.rain, win(t, st("why") + 0.4, en("why")));
    } else {
      show(src.dust, win(t, 0, st("lives"))); show(src.lives, win(t, st("lives") + 0.6, en("lives")));
      show(src.dispute, win(t, st("dispute") + 0.6, en("dispute"))); show(src.water, seg(t, st("end2") + 0.6, st("end2") + 0.9));
    }
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
