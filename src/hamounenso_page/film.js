/* «ال‌نینو برای هامون آب می‌آورد؟» (film.html?cut=main): window.renderAt(t) draws the frame of time t (seconds) from
   /build/film.json, which src/hamounenso.py writes (every string, every number, the scenes, cues and camera, the
   views, the lines, the places and the tiles). Nothing is typed here; the numbers in this file are pixels of the
   layout. Every frame is a pure function of t (the frames are rendered out of order by several workers). The camera,
   the wipe, the spring's tag, the border and the river are hamoun3_page's; the tally and the rain bars are new. */
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
  const CUT = F.cuts.main, SC = CUT.scenes, Q = CUT.cues, Wd = F.words, col = F.colours, END = CUT.end, G = F.grid, P = F.places;
  const ORDER = Object.keys(SC), st = n => SC[n][0], en = n => SC[n][1];
  const sceneAt = t => { let c = ORDER[0]; for (const n of ORDER) if (t >= SC[n][0]) c = n; return c; };
  window.CUT = { name: "main", end: END, scenes: SC };
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const SA = F.a, SB = F.b, SU = F.but, TL = F.tally, KINDS = ["en", "ne", "ln"];
  const names = new Set([F.ring, SA.pic, SA.water, SB.pic, SB.water, SU.pic, SU.water]);
  ["wide", "mid", "near"].forEach(k => names.add(F.ground[k].file));
  KINDS.forEach(k => TL[k].forEach(s => names.add(s.tile)));
  const IM = {}; await Promise.all([...names].map(async n => { IM[n] = await load(n); }));
  await Promise.all(['900 88px "Vazirmatn"', '800 48px "Vazirmatn"', '700 48px "Vazirmatn"', '500 32px "Vazirmatn"', '400 118px "Lalezar"'].map(f => document.fonts.load(f, "آبِ هامون ۱۳۹۹")));

  // ── the camera (hamoun3_page): a view is the lakes' place on screen (xa, ya) and a scale ──
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
    const q = Math.abs(b.s - a.s) < 1e-9 ? p : (s - a.s) / (b.s - a.s);
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
  const dots = {}; for (const k of ["zabol", "lake"]) dots[k] = [svg("circle", { r: 16, fill: "none", stroke: col.pin, "stroke-width": 4, opacity: 0 }, map), svg("circle", { r: 9, fill: k === "zabol" ? "#ffffff" : col.pin, stroke: k === "zabol" ? "#1d140c" : "#ffffff", "stroke-width": 3.5, opacity: 0 }, map)];
  const LIA = F.lines.ia, cIA = measure(LIA), RIV = F.lines.river, cR = measure(RIV), RL = cR[cR.length - 1];

  const shadeTop = el("div", null, stage), shadeBot = el("div", null, stage); shadeTop.id = "shade-top"; shadeBot.id = "shade-bot";
  const tcv = el("canvas", null, stage); tcv.id = "tiles"; tcv.width = 1080; tcv.height = 1920;
  const tctx = tcv.getContext("2d"); tctx.imageSmoothingEnabled = true; tctx.imageSmoothingQuality = "high";
  const country = (name, where, size) => { const e = css(el("div", "country", stage, name), { fontSize: size, lineHeight: Math.round(size * 1.3) }); e.dataset.at = where; return e; };
  const labels = { close: [country(Wd.iran, "iran_close", 60), country(Wd.afg, "afg_close", 48)],
                   wide: [country(Wd.iran, "iran_wide", 56), country(Wd.afg, "afg_wide", 78)] };
  const zabol = el("div", "place", stage, Wd.zabol);
  const riverName = el("div", "rivername", stage, Wd.river);
  const lakeName = css(el("div", "rivername", stage, Wd.lake), { color: "var(--gold)", fontSize: 48, lineHeight: 58, transform: "none" });
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
  head("hook", Wd.hook, null, 0, en("hook"));
  head("tally1", Wd.tally1, null, st("tally"), Q.swap);
  head("tally2", Wd.tally2, null, Q.swap, en("tally"));
  head("why", Wd.why, null, st("why"), en("why"));
  head("now", Wd.now, Wd.now_small, st("now"), en("now"), Q.small);
  head("end", Wd.end, null, st("end") + 0.3, END + 9);

  // the spring's tag (hamoun3_page): the year with its small line on the right, the number with its unit on the left;
  // in a wipe each block shows only while it lies wholly on its own spring's side of the line
  const mkTag = () => { const box = el("div", "tag", stage), yr = el("div", "yr", box), sb = el("div", "sub", box), val = el("div", "val", box);
    return { box, yr, sb, val, n: el("span", "n", val), u: el("span", "u", val, Wd.unit), sl: el("span", "subl", val) }; };
  const tagA = mkTag(), tagB = mkTag();
  function setTag(T, sp, sb, top, on, cutX, side) {
    if (sp) { T.yr.textContent = Wd.spring.replace("{}", sp.label); T.n.textContent = sp.shown; }
    T.sb.textContent = sb; T.sl.textContent = ""; css(T.box, { top }); show(T.box, sp ? on : 0);
    let oYr = 1, oVal = 1;
    if (sp && cutX !== null) {
      const yrLeft = 924 - Math.max(T.yr.offsetWidth, T.sb.offsetWidth), valRight = 96 + T.val.offsetWidth, FW = 36;
      if (side === "left") { oYr = seg(cutX, 924 - FW, 924); oVal = seg(cutX, valRight - FW, valRight); }
      else { oYr = 1 - seg(cutX, yrLeft, yrLeft + FW); oVal = 1 - seg(cutX, 96, 96 + FW); }
    }
    show(T.yr, oYr); show(T.sb, oYr); show(T.val, oVal);
  }
  const sig = (p, n) => { const a = Math.pow(p, n), b = Math.pow(1 - p, n); return a / (a + b); };
  const wipeP = u => 0.12 * u + 0.88 * sig(u, 2.6);

  // the tally: three columns (El Niño on the right, the first to read), tiles three to a row, newest last
  const TW = 80, TH = Math.round(TW * F.tile[1] / F.tile[0]), GAPX = 8, HALF = (3 * TW + 2 * GAPX) / 2, PITCH = TH + 36, TOP = 690;
  const CX = { en: 786, ne: 510, ln: 234 };
  const heads3 = KINDS.map((k, i) => { const e = css(el("div", "colhead", stage), { left: CX[k], top: 556, background: col[k] });
    el("span", "lead", e, Wd.col_lead); el("span", "nm", e, Wd.cols[i]); return e; });
  const tiles = [], tlabels = [];
  KINDS.forEach((k, ci) => TL[k].forEach((s, i) => {
    const r = Math.floor(i / 3), c = i % 3, x = CX[k] + HALF - TW - c * (TW + GAPX), y = TOP + r * PITCH;
    tiles.push({ k, s, x, y, at: Q.cols[ci].tiles[i] });
    tlabels.push(css(el("div", "tlabel", stage, s.label), { left: x + TW / 2, top: y + TH + 2 }));
  }));
  const counts = KINDS.map((k, i) => { const e = css(el("div", "count", stage), { left: CX[k], top: TOP + 4 * PITCH + 12 });
    el("i", null, e); e.appendChild(document.createTextNode(Wd.counts[i])); return e; });
  const dryLabel = css(el("div", "drylabel", stage), { top: TOP + 4 * PITCH + 108 });
  el("i", null, dryLabel); dryLabel.appendChild(document.createTextNode(Wd.dry));
  const enBox = { x: CX.en - HALF - 8, y: TOP - 12, w: 2 * HALF + 16, h: 3 * PITCH + 22 };   // the El Niño column's frame at the payoff (12 px clear of the labels and of the next column)

  // the rain card: El Niño and La Niña winters upstream against the 40 winters' mean (CRU and ERA5 as a range)
  const card = css(el("div", "card", stage), { top: 1196 });   // ends at 1402, above the sources' three lines (1418-1538)
  const SCALE = 25;                                   // % at the full length of a bar
  const rows = [[Wd.rows[0], Wd.rain_more, F.rain.en, col.more, 12], [Wd.rows[1], Wd.rain_less, F.rain.ln, col.less, 108]].map(([nm, txt, v, c, top]) => {
    const r = css(el("div", "row", card), { top }); const n = el("div", "name", r, nm), l = el("div", "less", r, txt); l.style.color = c;
    fit([n], 400, 30, 1.25);
    const tr = el("div", "track", r), sp = el("div", "span", tr), fl = el("div", "fill", tr); fl.style.background = c; sp.style.background = c;
    const a = v.map(Math.abs); return { lo: Math.min(...a) / SCALE, hi: Math.max(...a) / SCALE, fl, sp };
  });

  // the last words and the sources (a source may have two lines: stacked up from the bottom line)
  const endPic = css(el("div", "chip", stage, Wd.end_pic), { top: 1176 });   // the end's full lake is the hook's El Niño spring (1398), said on it
  const follow = el("div", null, stage); follow.id = "follow";
  Wd.follow.forEach(s => el("span", null, follow, s)); css(follow, { top: 1330 }); fit([...follow.children], 828, 40, 1.4);
  const srcs = {};
  for (const k of ["water", "tally", "rain", "now"]) {
    const ls = Wd["src_" + k].split(" // ");
    srcs[k] = ls.map((s, i) => { const e = css(el("div", "sources", stage, s), { top: 1498 - 40 * (ls.length - 1 - i) }); fit([e], 828, 24, 1.25); return e; });
  }
  const srcMap = css(el("div", "sources", stage, Wd.src_map), { top: 1418 }); fit([srcMap], 828, 24, 1.25);   // above the rain's two lines

  function put(sp, a) {
    const gx = X(G.lon0), gy = Y(G.lat1), gw = V.s * G.w, gh = V.s * G.h;
    ctx.globalAlpha = a; ctx.drawImage(IM[sp.pic], gx, gy, gw, gh);
    ctx.drawImage(IM[sp.water], gx, gy, gw, gh);
    ctx.globalAlpha = 1;
  }
  const clipped = (x0, x1, f) => { ctx.save(); ctx.beginPath(); ctx.rect(x0, 0, x1 - x0, 1920); ctx.clip(); f(); ctx.restore(); };
  const place = (e, lon, lat, dx = 0, dy = 0) => css(e, { left: X(lon) + dx, top: Y(lat) + dy });
  const dot = (name, on, pulse) => { const [lon, lat] = name === "lake" ? [A.lon - 0.12, A.lat + 0.12] : P[name], [ring, core] = dots[name];
    core.setAttribute("cx", X(lon)); core.setAttribute("cy", Y(lat)); core.setAttribute("opacity", on.toFixed(3));
    ring.setAttribute("cx", X(lon)); ring.setAttribute("cy", Y(lat)); ring.setAttribute("r", (16 + 22 * pulse).toFixed(1)); ring.setAttribute("opacity", (on * (1 - pulse)).toFixed(3)); };

  window.renderAt = function (t0) {
    const t = clamp(t0, 0, END);
    V = cam(t);
    const cur = sceneAt(t), back = t >= Q.back[0];   // back: the last frames return to frame 0

    // the ground and the spring's picture
    ctx.globalAlpha = 1; ctx.fillStyle = "#17110b"; ctx.fillRect(0, 0, 1080, 1920);
    for (const k of ["wide", "mid", "near"]) {
      const g = F.ground[k], a = k === "mid" ? seg(V.s, 0.165, 0.22) : k === "near" ? seg(V.s, 0.44, 0.58) : 1;
      if (a <= 0) continue;
      const x0 = X(g.w), y0 = Y(g.n);
      ctx.globalAlpha = a; ctx.drawImage(IM[g.file], x0, y0, X(g.e) - x0, Y(g.s) - y0);
    }
    ctx.globalAlpha = 1;
    let xLine = -1, cutX = null;
    if (cur === "hook") {                             // 1398 (after El Niño) under the line, 1397 (after La Niña) behind it
      const wp = wipeP(seg(t, Q.wipe[0], Q.wipe[1])), xw = 1080 * (1 - wp);
      put(SA, 1);
      if (wp > 0) clipped(xw, 1080, () => put(SB, 1));
      cutX = xw;
      if (wp > 0.002 && wp < 0.998) xLine = xw;
    } else if (cur === "tally" || cur === "why") put(SB, 1);
    else if (cur === "now") { const p = ease(seg(t, Q.pic[0], Q.pic[1])); if (p < 1) put(SB, 1); if (p > 0) put(SU, p); }
    else {                                            // the end: 1403, then 1398 from the left (the loop's frame 0)
      const w2 = ease(seg(t, Q.wipe2[0], Q.wipe2[1])), xr = 1080 * w2;
      put(SU, 1);
      if (w2 > 0) clipped(0, xr, () => put(SA, 1));
      if (w2 > 0.002 && w2 < 0.998) xLine = xr;
    }
    css(wipe, { left: xLine - 3 }); show(wipe, xLine >= 0 ? 1 : 0);
    ctx.drawImage(IM[F.ring], X(G.lon0), Y(G.lat1), V.s * G.w, V.s * G.h);

    // the tally's panel and tiles
    const dim = win(t, Q.dim[0], en("tally"), 0.5, 0.45);
    tctx.clearRect(0, 0, 1080, 1920);
    if (dim > 0) {
      tctx.globalAlpha = 0.86 * dim; tctx.fillStyle = "#120d08"; tctx.fillRect(0, 0, 1080, 1920);
      tiles.forEach(T => { const p = easeOut(seg(t, T.at, T.at + 0.28)); if (p <= 0) return;
        const sc = 0.82 + 0.18 * p, w = TW * sc, h = TH * sc;
        tctx.globalAlpha = dim * p; tctx.drawImage(IM[T.s.tile], T.x + (TW - w) / 2, T.y + (TH - h) / 2, w, h); });
      const hl = dim * seg(t, Q.swap, Q.swap + 0.4);
      if (hl > 0) { tctx.globalAlpha = hl; tctx.strokeStyle = col.gold; tctx.lineWidth = 6;
        tctx.beginPath(); tctx.roundRect(enBox.x, enBox.y, enBox.w, enBox.h, 22); tctx.stroke(); }
      tctx.globalAlpha = 1;
    }
    heads3.forEach(e => show(e, dim * seg(t, st("tally") + 0.3, st("tally") + 0.6)));
    tiles.forEach((T, i) => show(tlabels[i], dim * seg(t, T.at + 0.1, T.at + 0.35)));
    counts.forEach((e, i) => { const a = Q.cols[i].count; show(e, dim * seg(t, a, a + 0.3)); e.style.transform = `translateX(-50%) scale(${(0.8 + 0.2 * easeOut(seg(t, a, a + 0.35))).toFixed(3)})`; });
    show(dryLabel, dim * seg(t, Q.cols[0].count, Q.cols[0].count + 0.3));
    shadeTop.style.opacity = "1"; shadeBot.style.opacity = "1";

    // the border: drawn in the hook, under the panel in the tally, gone in the end (frame 0 has none)
    const bp = ease(seg(t, Q.border[0], Q.border[1]));
    const bOn = (1 - dim) * (cur === "end" ? 1 - seg(t, st("end"), st("end") + 0.5) : 1);
    const dIA = path(part(LIA, cIA, 0, cIA[cIA.length - 1] * bp));
    bIA.forEach((e, i) => { e.setAttribute("d", dIA); e.setAttribute("opacity", (bOn * (bp > 0 ? 1 : 0) * (i ? 0.95 : 1)).toFixed(3)); });
    const far = bOn * (1 - seg(V.s, 0.5, 0.7));
    [[bIP, F.lines.ip], [bAP, F.lines.ap]].forEach(([pair, line]) => pair.forEach(e => { if (far > 0) e.setAttribute("d", path(line)); e.setAttribute("opacity", (far * 0.85).toFixed(3)); }));

    // the countries' names (close: the hook and the caveat; wide: the rain) and Zabol
    const lab = Q.labels.map(a => seg(t, a, a + 0.3));
    const closeOn = cur === "hook" ? 1 : cur === "now" ? seg(t, Q.pic[1], Q.pic[1] + 0.3) : 0;
    const sc = { close: closeOn * 0.9 * seg(V.s, 0.62, 0.74) * (cur === "hook" ? 1 : 1), wide: (cur === "why" || cur === "now") ? 1 - seg(V.s, 0.143, 0.158) : 0 };
    for (const v in labels) labels[v].forEach((e, i) => { const [lon, lat] = P[e.dataset.at]; place(e, lon, lat);
      show(e, bOn * sc[v] * (v === "close" && cur === "hook" ? lab[Math.min(i, 1)] : 1)); });
    const zOn = closeOn * bOn * (cur === "hook" ? lab[2] : 1) * seg(V.s, 0.3, 0.38);
    css(zabol, { left: X(P.zabol[0]) - 22 - zabol.offsetWidth, top: Y(P.zabol[1]) - 30 }); show(zabol, zOn);
    dot("zabol", zOn, 1);

    // the river (the rain): from its head in the Hindu Kush to the lakes, then it flows
    const rp = ease(seg(t, Q.river[0], Q.river[1]));
    const rOn = (cur === "why" ? 1 : cur === "now" ? 1 - seg(t, st("now"), st("now") + 0.6) : 0) * (1 - seg(V.s, 0.5, 0.72));
    const dR = rOn > 0 ? path(part(RIV, cR, 0, RL * rp)) : "";
    [[riverGlow, 0.9], [riverLine, 1], [riverCore, 0.9]].forEach(([e, o]) => { e.setAttribute("d", dR); e.setAttribute("opacity", (rOn * o).toFixed(3)); });
    beads.forEach((b, i) => { const f = ((i / beads.length) + (t - Q.river[0]) * 0.055) % 1, on = rOn * (f < rp ? 1 : 0) * Math.min(1, f * 12, (1 - f) * 12);
      if (on > 0) { const [lon, lat] = along(RIV, cR, f * RL); b.setAttribute("cx", X(lon)); b.setAttribute("cy", Y(lat)); } b.setAttribute("opacity", (on * 0.95).toFixed(3)); });
    const wideOn = rOn * (1 - seg(V.s, 0.17, 0.215));
    place(riverName, P.river_wide[0], P.river_wide[1]); show(riverName, wideOn * seg(t, Q.river[0] + 1.0, Q.river[0] + 1.4));
    const lakeOn = wideOn * seg(t, Q.river[1] - 0.2, Q.river[1] + 0.2);
    place(lakeName, A.lon - 0.12, A.lat + 0.12, 26, -34); show(lakeName, lakeOn);
    dot("lake", lakeOn, 0.5 + 0.5 * Math.sin((t - Q.river[0]) * 4));

    // the headlines (the hook comes back in the last frames: the loop)
    heads.forEach(h => { let o = win(t, h.a, h.b);
      if (h.name === "hook" && back) o = seg(t, Q.back[0] + 0.25, Q.back[0] + 0.6);
      if (h.name === "end" && back) o *= 1 - seg(t, Q.back[0], Q.back[0] + 0.3);
      show(h.box, o); h.box.style.transform = `translateY(${(14 * (1 - ease(seg(t, h.a, h.a + 0.3))) * (h.a > 0 ? 1 : 0)).toFixed(1)}px)`;
      h.sm.forEach(e => show(e, h.smAt > h.a ? seg(t, h.smAt, h.smAt + 0.35) : 1)); });

    // the tags: the hook's two springs, the caveat's spring, frame 0's spring again at the end
    let a1 = null, s1 = "", on1 = 0, a2 = null, on2 = 0, top = 1150;
    if (cur === "hook") { a1 = SA; s1 = Wd.after_en; a2 = SB; on1 = on2 = 1 - seg(t, en("hook") - 0.3, en("hook")); }
    else if (cur === "now") { a1 = SU; s1 = Wd.after_en; on1 = seg(t, Q.pic[1], Q.pic[1] + 0.3) * (1 - seg(t, en("now") - 0.3, en("now"))); }
    else if (back) { a1 = SA; s1 = Wd.after_en; on1 = seg(t, Q.back[0] + 0.3, Q.back[0] + 0.6); }
    setTag(tagA, a1, s1, top, on1, cur === "hook" ? cutX : null, "left");
    setTag(tagB, a2, Wd.after_ln, top, on2, cutX, "right");

    // the rain card
    const cardOn = win(t, Q.card, en("why"), 0.4, 0.25); show(card, cardOn);
    if (cardOn > 0) { const p = ease(seg(t, Q.card + 0.4, Q.card + 1.5));
      rows.forEach(r => { css(r.fl, { width: (100 * r.lo * p).toFixed(2) + "%" }); css(r.sp, { right: (100 * r.lo * p).toFixed(2) + "%", width: (100 * (r.hi - r.lo) * p).toFixed(2) + "%" }); }); }

    show(follow, seg(t, Q.follow, Q.follow + 0.35) * (1 - seg(t, Q.back[0], Q.back[0] + 0.3)));
    show(endPic, cur === "end" ? seg(t, Q.wipe2[1] - 0.2, Q.wipe2[1] + 0.1) * (1 - seg(t, Q.back[0], Q.back[0] + 0.3)) : 0);
    // the sources of each moment
    const srcOn = { water: Math.max(win(t, 0, en("hook")), back ? seg(t, Q.back[0] + 0.3, Q.back[0] + 0.6) : 0, win(t, st("end") + 0.5, Q.back[0] + 0.1)),
                    tally: win(t, st("tally") + 0.4, en("tally")), rain: win(t, Q.card, en("why")), now: win(t, Q.small, en("now")) };
    for (const k in srcs) srcs[k].forEach(e => show(e, srcOn[k] || 0));
    show(srcMap, win(t, Q.card, en("why")));
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
