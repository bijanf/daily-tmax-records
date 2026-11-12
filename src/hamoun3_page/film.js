/* «آبِ هامون کجا رفت؟»: window.renderAt(t) draws the frame of time t (seconds) from /build/film.json, which
   src/hamoun3.py writes (every string, every number, the clock, the camera's views, the lines and the places).
   Nothing is typed here; the numbers in this file are pixels of the layout. Every frame is a pure function of t
   (the frames are rendered out of order by several workers). */
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
  s.split(/(\{[^}]*\})/).forEach(part => { if (!part) return; if (part[0] === "{") el("span", "key", parent, part.slice(1, -1)); else parent.appendChild(document.createTextNode(part)); });
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
  const G = F.grid, C = F.clock, Wd = F.words, col = F.colours, END = F.end, S = F.springs, P = F.places;
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const names = new Set([F.ring]); S.forEach(s => { names.add(s.pic); if (s.water) names.add(s.water); });
  ["wide", "mid", "near"].forEach(k => names.add(F.ground[k].file));
  const IM = {}; await Promise.all([...names].map(async n => { IM[n] = await load(n); }));
  await Promise.all(['900 88px "Vazirmatn"', '800 48px "Vazirmatn"', '700 48px "Vazirmatn"', '500 32px "Vazirmatn"', '400 118px "Lalezar"'].map(f => document.fonts.load(f, "آبِ هامون ۱۳۷۷")));
  const NOW = S[F.now], BEFORE = S[F.before], T13 = S[13].t;

  // ── the camera: a view is the lakes' place on screen (xa, ya) and a scale (frame pixels per picture pixel) ──
  const A = { lon: F.views.close[0], lat: F.views.close[1] };
  const VW = {};
  for (const k in F.views) { const [lon, lat, s] = F.views[k]; VW[k] = { s, xa: 540 + s * (A.lon - lon) / G.dlon, ya: 960 - s * (A.lat - lat) / G.dlat }; }
  const key = (v, m) => ({ s: VW[v].s * m, xa: 540 + (VW[v].xa - 540) * m, ya: 960 + (VW[v].ya - 960) * m });
  const K = [[0, "close", 1.0], [C.where, "close", 1.05], [C.out1[1], "mid", 1.0], [C.run, "mid", 0.97], [C.in1[1], "close", 1.0],
             [C.why, "close", 1.05], [C.out2[1], "wide", 1.0], [C.mid2[0], "wide", 0.97], [C.mid2[1], "mid", 1.0], [C.now, "mid", 0.98],
             [C.in2[1], "close", 1.0], [C.back[0], "close", 1.04], [END, "close", 1.0]];
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
  const LIA = F.lines.ia, cIA = measure(LIA), RIV = F.lines.river, cR = measure(RIV), RL = cR[cR.length - 1];
  // the stretch of the river with the irrigated land: from Kajaki down to the head of the delta (Kamal Khan)
  const nearest = pt => { let b = 0, bd = 1e9; RIV.forEach((p, i) => { const d = Math.hypot(p[0] - pt[0], p[1] - pt[1]); if (d < bd) { bd = d; b = i; } }); return cR[b]; };
  const dKaj = nearest(P.kajaki), dKam = nearest(P.border_end);

  el("div", null, stage).id = "shade-top"; el("div", null, stage).id = "shade-bot";
  const country = (name, where, size) => { const e = css(el("div", "country", stage, name), { fontSize: size, lineHeight: Math.round(size * 1.3) }); e.dataset.at = where; return e; };
  const labels = { close: [country(Wd.iran, "iran_close", 60), country(Wd.afg, "afg_close", 48)],
                   mid: [country(Wd.iran, "iran_mid", 78), country(Wd.afg, "afg_mid", 78)],
                   wide: [country(Wd.iran, "iran_wide", 56), country(Wd.afg, "afg_wide", 78), country(Wd.pak, "pak_wide", 66)] };
  const zabol = el("div", "place", stage, Wd.zabol);
  const riverName = el("div", "rivername", stage, Wd.river), kush = el("div", "place", stage, Wd.kush), lakeName = el("div", "place", stage, Wd.lake);
  css(lakeName, { color: "var(--gold)", fontWeight: 900 });
  const pins = Wd.pins.map(([at, nm, yr]) => { const e = el("div", at === "lashkargah" ? "pin farm" : "pin", stage); el("span", "nm", e, nm); yr.split(" // ").forEach(y => el("span", "yr", e, y)); e.dataset.at = at; return e; });
  const wipe = el("div", null, stage); wipe.id = "wipe";

  // the headlines: [name, lines, small line, from, to]
  const heads = [["hook", Wd.hook, null, 0, C.where], ["where", Wd.where, null, C.where, C.run], ["era1", Wd.era1, null, C.run, T13],
                 ["era2", Wd.era2, null, T13, C.why], ["why", Wd.why, Wd.periods, C.why, C.where2],
                 ["where2", Wd.where2, Wd.where2_small, C.where2, C.now], ["now", Wd.now, Wd.ask, C.now, C.back[0] + 0.25]]
    .map(([name, textLines, small, a, b]) => {
      const box = el("div", "head", stage), lines = textLines.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
      fit(lines, 828, 58, 1.39);
      const sm = small ? el("span", "small", box, small) : null; if (sm) fit([sm], 828, 40, 1.4);
      return { name, box, sm, a, b };
    });

  const tag = el("div", null, stage); tag.id = "tag";
  const tagYr = el("div", "yr", tag), tagSub = el("div", "sub", tag), tagVal = el("div", "val", tag), tagN = el("span", "n", tagVal), tagU = el("span", "u", tagVal, Wd.unit);
  const held = el("div", "chip", stage); css(held, { top: 1040 }); el("span", null, held, Wd.held.join(" "));
  fit([held], 760, 34, 1.35);
  const hedge = el("div", "chip", stage, Wd.share); css(hedge, { top: 1392 });

  // the small chart: forty springs against their mean
  const chart = el("div", "card", stage), leg = el("div", "legend", chart);
  [["i", col.wet, Wd.legend[0]], ["i", col.dry, Wd.legend[1]], ["b", null, Wd.mean]].forEach(([tg, c, s]) => { const it = el("span", null, leg), sw = el(tg, null, it); if (c) sw.style.background = c; it.appendChild(document.createTextNode(s)); });
  const cs = svg("svg", { width: 828, height: 206, viewBox: "0 0 828 206" }, chart);
  const BX = 22, BW = 784, PITCH = BW / S.length, BASE = 152, TALL = 92, barW = 13;
  const yMean = BASE - TALL * F.mean / F.vmax;
  svg("line", { x1: BX, x2: BX + BW, y1: BASE + 1.5, y2: BASE + 1.5, stroke: col.ink, "stroke-width": 3 }, cs);
  const bars = S.map((s, k) => svg("rect", { x: BX + BW - (k + 0.5) * PITCH - barW / 2, width: barW, rx: 2.5, fill: s.km2 === null ? col.gapc : s.above ? col.wet : col.dry }, cs));
  svg("line", { x1: BX, x2: BX + BW, y1: yMean, y2: yMean, stroke: col.ink, "stroke-width": 3.5, "stroke-dasharray": "11 8" }, cs);
  const mark = svg("rect", { width: barW + 8, rx: 5, fill: "none", stroke: col.ink, "stroke-width": 3.5 }, cs);
  css(el("div", "tick", chart, S[0].label), { right: 22 });
  css(el("div", "tick", chart, S[S.length - 1].label), { left: 22 });
  css(el("div", "tick", chart, S[13].label), { left: BX + BW - 13.5 * PITCH, transform: "translateX(-50%)" });

  // the rain card: the winters' precipitation against the lake's water, later against earlier
  const rainCard = el("div", "card", stage);
  const rows = [[Wd.rain_item, Wd.rain_less, Math.min(F.rain.cru, F.rain.era5), Math.max(F.rain.cru, F.rain.era5), "#5b8fc4", 12],
                [Wd.lake_item, Wd.lake_less, F.rain.lake, F.rain.lake, col.wet, 108]].map(([nm, less, lo, hi, c, top]) => {
    const r = css(el("div", "row", rainCard), { top }); const n = el("div", "name", r, nm), l = el("div", "less", r, less); l.style.color = "#a03129";
    fit([n], 520, 30, 1.25);
    const tr = el("div", "track", r), sp = el("div", "span", tr), fl = el("div", "fill", tr); fl.style.background = c; sp.style.background = c;
    return { lo, hi, fl, sp };
  });

  const follow = el("div", null, stage); follow.id = "follow"; Wd.follow.forEach(s => el("span", null, follow, s)); fit([...follow.children], 828, 40, 1.4);
  const src = { water: el("div", "sources", stage, Wd.src_water), map: el("div", "sources", stage, Wd.src_map), rain: el("div", "sources", stage, Wd.src_rain) };
  Object.values(src).forEach(e => fit([e], 828, 26, 1.25));

  function put(sp, a) {
    const gx = X(G.lon0), gy = Y(G.lat1), gw = V.s * G.w, gh = V.s * G.h;
    ctx.globalAlpha = a; ctx.drawImage(IM[sp.pic], gx, gy, gw, gh);
    if (sp.held) { ctx.globalAlpha = a * 0.40; ctx.fillStyle = "#efe7d8"; ctx.fillRect(gx, gy, gw, gh); }
    if (sp.water) { ctx.globalAlpha = a; ctx.drawImage(IM[sp.water], gx, gy, gw, gh); }
    ctx.globalAlpha = 1;
  }
  const place = (e, lon, lat, dx = 0, dy = 0) => css(e, { left: X(lon) + dx, top: Y(lat) + dy });

  window.renderAt = function (t0) {
    const t = clamp(t0, 0, END);
    V = cam(t);
    const hook = t < C.where, loop = t >= C.back[0], run = t >= C.run && t < C.why;

    // the ground and the spring's picture
    ctx.globalAlpha = 1; ctx.fillStyle = "#17110b"; ctx.fillRect(0, 0, 1080, 1920);
    for (const k of ["wide", "mid", "near"]) {
      const g = F.ground[k], a = k === "mid" ? seg(V.s, 0.165, 0.22) : k === "near" ? seg(V.s, 0.44, 0.58) : 1;
      if (a <= 0) continue;
      const x0 = X(g.w), y0 = Y(g.n);
      ctx.globalAlpha = a; ctx.drawImage(IM[g.file], x0, y0, X(g.e) - x0, Y(g.s) - y0);
    }
    ctx.globalAlpha = 1;
    let sp = null, wp = -1, k = -1, kt = -1;
    const rainOn = win(t, C.card, C.where2, 0.4, 0.25);
    if (hook || loop) {
      wp = hook ? ease(seg(t, C.wipe[0], C.wipe[1])) : 1 - ease(seg(t, C.back[0], C.back[1]));
      const xw = 1080 * (1 - wp);
      put(BEFORE, 1);
      if (wp > 0) { ctx.save(); ctx.beginPath(); ctx.rect(xw, 0, 1080 - xw, 1920); ctx.clip(); put(NOW, 1); ctx.restore(); }
      sp = wp >= 0.5 ? NOW : BEFORE;
      css(wipe, { left: xw - 3 }); show(wipe, wp > 0.002 && wp < 0.998 ? 1 : 0);
    } else {
      show(wipe, 0);
      if (run) {
        for (let i = 0; i < S.length; i++) if (t >= S[i].t) k = i;
        if (k < 0) { put(NOW, 1); const p = ease(seg(t, C.t0 - 0.45, C.t0 - 0.03)); if (p > 0) put(S[0], p); if (t >= C.t0 - 0.3) sp = S[0]; }
        else { if (k > 0) put(S[k - 1], 1); put(S[k], k > 0 ? ease(seg(t, S[k].t, S[k].t + 0.14)) : 1);
          kt = 0; for (let i = 0; i < S.length; i++) if (t - 0.07 >= S[i].t) kt = i; sp = S[kt]; }
      } else { put(NOW, 1); if (t >= C.now) sp = NOW; }
    }
    ctx.drawImage(IM[F.ring], X(G.lon0), Y(G.lat1), V.s * G.w, V.s * G.h);

    // the border: drawn once (the "where" scene), then it stays; not in the hook, not in the loop's last frames
    const bOn = hook ? 0 : loop ? 1 - seg(t, C.back[0], C.back[0] + 0.3) : 1, bp = ease(seg(t, C.border[0], C.border[1]));
    const dIA = path(part(LIA, cIA, 0, cIA[cIA.length - 1] * bp));
    bIA.forEach((e, i) => { e.setAttribute("d", dIA); e.setAttribute("opacity", (bOn * (bp > 0 ? 1 : 0) * (i ? 0.95 : 1)).toFixed(3)); });
    const far = bOn * seg(t, C.border[1] - 0.3, C.border[1] + 0.3) * (1 - seg(V.s, 0.5, 0.7));
    [[bIP, F.lines.ip], [bAP, F.lines.ap]].forEach(([pair, line]) => pair.forEach(e => { if (far > 0) e.setAttribute("d", path(line)); e.setAttribute("opacity", (far * 0.85).toFixed(3)); }));
    const lab = [seg(t, C.labels[0], C.labels[0] + 0.3), seg(t, C.labels[1], C.labels[1] + 0.3), seg(t, C.labels[2], C.labels[2] + 0.3)];
    const atMid = (t >= C.out1[0] && t < C.in1[1]) || (t >= C.mid2[0] && t < C.in2[1]) ? 1 : 0;
    const scale = { close: seg(V.s, 0.62, 0.74), mid: atMid * seg(V.s, 0.24, 0.3) * (1 - seg(V.s, 0.46, 0.58)), wide: 1 - seg(V.s, 0.17, 0.215) };
    for (const v in labels) labels[v].forEach((e, i) => { const [lon, lat] = P[e.dataset.at]; place(e, lon, lat);
      show(e, bOn * scale[v] * lab[Math.min(i, 1)] * (v === "close" ? 0.9 : 1) * (e.dataset.at === "pak_wide" && rainOn > 0 ? 0 : 1)); });
    const zOn = bOn * lab[2] * seg(V.s, 0.3, 0.38);
    css(zabol, { left: X(P.zabol[0]) - 22 - zabol.offsetWidth, top: Y(P.zabol[1]) - 30 }); show(zabol, zOn);
    const dot = (name, on, pulse) => { const [lon, lat] = name === "lake" ? [A.lon - 0.12, A.lat + 0.12] : P[name], [ring, core] = dots[name];
      core.setAttribute("cx", X(lon)); core.setAttribute("cy", Y(lat)); core.setAttribute("opacity", on.toFixed(3));
      ring.setAttribute("cx", X(lon)); ring.setAttribute("cy", Y(lat)); ring.setAttribute("r", (16 + 22 * pulse).toFixed(1)); ring.setAttribute("opacity", (on * (1 - pulse)).toFixed(3)); };
    dot("zabol", zOn, 1);

    // the river: drawn from its head to the lakes, then it flows; only in the far views
    const rOn = (t >= C.river[0] && t < C.now + 0.8 ? 1 : 0) * (1 - seg(V.s, 0.5, 0.72)), rp = ease(seg(t, C.river[0], C.river[1]));
    const dR = rOn > 0 ? path(part(RIV, cR, 0, RL * rp)) : "";
    [[riverGlow, 0.9], [riverLine, 1], [riverCore, 0.9]].forEach(([e, o]) => { e.setAttribute("d", dR); e.setAttribute("opacity", (rOn * o).toFixed(3)); });
    beads.forEach((b, i) => { const f = ((i / beads.length) + (t - C.river[0]) * 0.055) % 1, on = rOn * (f < rp ? 1 : 0) * Math.min(1, f * 12, (1 - f) * 12);
      if (on > 0) { const [lon, lat] = along(RIV, cR, f * RL); b.setAttribute("cx", X(lon)); b.setAttribute("cy", Y(lat)); } b.setAttribute("opacity", (on * 0.95).toFixed(3)); });
    const wideOn = rOn * (1 - seg(V.s, 0.17, 0.215));
    place(kush, P.kush[0], P.kush[1]); css(kush, { transform: "translate(-50%, -50%)" }); show(kush, wideOn * seg(t, C.river[0] + 0.2, C.river[0] + 0.6));
    place(riverName, P.river_name[0], P.river_name[1]); show(riverName, wideOn * seg(t, C.river[0] + 1.0, C.river[0] + 1.4));
    const lakeOn = Math.max(wideOn * seg(t, C.river[1] - 0.2, C.river[1] + 0.2), win(t, C.labels[2] + 0.2, C.run, 0.3, 0.3));
    place(lakeName, A.lon - 0.12, A.lat + 0.12, V.s < 0.2 ? 26 : -118, V.s < 0.2 ? -34 : -230); show(lakeName, lakeOn);
    dot("lake", V.s < 0.2 ? lakeOn : 0, 0.5 + 0.5 * Math.sin((t - C.river[1]) * 4));

    // the dams and the irrigated land, in the river's order
    const pOn = t >= C.where2 && t < C.now + 0.5 ? 1 - seg(t, C.now, C.now + 0.5) : 0;
    const fOn = pOn * seg(t, C.pins[1], C.pins[1] + 0.5) * (1 - seg(V.s, 0.15, 0.2));
    if (fOn > 0) farm.setAttribute("d", path(part(RIV, cR, dKaj, dKam))); farm.setAttribute("opacity", (fOn * 0.78).toFixed(3));
    const OFF = { kajaki: [34, -8, "l"], lashkargah: [-34, -196, "r"], kamalkhan: [0, 30, "c"], chahnimeh: [-34, 34, "r"] };
    pins.forEach((e, i) => { const at = e.dataset.at, [lon, lat] = P[at], on = pOn * seg(t, C.pins[i], C.pins[i] + 0.3) * (i < 2 ? 1 - seg(V.s, 0.15, 0.2) : seg(V.s, 0.3, 0.38));
      const pop = easeOut(seg(t, C.pins[i], C.pins[i] + 0.35));
      const [dx, dy, anchor] = OFF[at], wd = e.offsetWidth;
      css(e, { left: X(lon) + dx - (anchor === "r" ? wd : anchor === "c" ? wd / 2 : 0), top: Y(lat) + dy, transform: `scale(${(0.7 + 0.3 * pop).toFixed(3)})` }); show(e, on);
      dot(at, on, seg(t, C.pins[i], C.pins[i] + 0.9)); });

    // the headlines
    heads.forEach(h => { let o = win(t, h.a, h.b); if (h.name === "hook" && loop) o = seg(t, C.back[0] + 0.25, C.back[0] + 0.6);
      show(h.box, o); h.box.style.transform = `translateY(${(14 * (1 - ease(seg(t, h.a, h.a + 0.3))) * (h.a > 0 ? 1 : 0)).toFixed(1)}px)`;
      if (h.sm && h.name === "now") show(h.sm, seg(t, C.ask, C.ask + 0.35)); });

    // the spring's tag (its year and its water), the note of a spring without a clean picture
    const tagOn = hook ? 1 : loop ? seg(t, C.back[0] + 0.3, C.back[0] + 0.6) : run ? seg(t, C.t0 - 0.3, C.t0) * (1 - seg(t, C.why - 0.25, C.why)) : t >= C.now ? seg(t, C.now + 0.6, C.now + 0.9) * (1 - seg(t, C.follow - 0.3, C.follow)) : 0;
    if (sp) {
      tagYr.textContent = Wd.spring.replace("{}", sp.label);
      if (sp.km2 === null) { tagN.textContent = Wd.gap; tagN.className = "n nogap"; tagU.style.display = "none"; }
      else { tagN.textContent = sp.shown; tagN.className = "n"; tagU.style.display = "block"; }
    }
    tagSub.textContent = hook || loop ? (sp === BEFORE ? Wd.wet : Wd.this_spring) : !run && t >= C.now ? Wd.mean_value : "";
    css(tag, { top: hook || loop ? 1150 : run ? 1128 : 1088 }); show(tag, sp ? tagOn : 0);
    show(hedge, win(t, C.pins[2] + 0.5, C.now, 0.4, 0.3));
    let heldOn = 0;
    if (run) S.forEach((s, i) => { if (s.held && s.km2 !== null) heldOn = Math.max(heldOn, win(t, s.t - 0.08, (i + 1 < S.length ? S[i + 1].t : C.why) + 0.25, 0.1, 0.25)); });
    show(held, heldOn * tagOn);

    // the small chart
    const chartOn = Math.max(win(t, C.run + 0.3, C.why, 0.4, 0.25), win(t, C.now + 0.6, C.back[0] + 0.2, 0.4, 0.25));
    show(chart, chartOn);
    if (chartOn > 0) {
      const all = t >= C.why;
      bars.forEach((b, i) => { const g = all ? 1 : easeOut(seg(t, S[i].t, S[i].t + 0.22)), h = S[i].km2 === null ? 7 * g : Math.max(2.5, TALL * S[i].km2 / F.vmax) * g;
        b.setAttribute("y", BASE - h); b.setAttribute("height", h); b.setAttribute("opacity", g > 0 ? 1 : 0); });
      const cur = all ? S.length - 1 : k < 0 ? -1 : kt;
      if (cur >= 0) { const h = S[cur].km2 === null ? 7 : Math.max(2.5, TALL * S[cur].km2 / F.vmax);
        mark.setAttribute("x", BX + BW - (cur + 0.5) * PITCH - barW / 2 - 4); mark.setAttribute("y", BASE - h - 5); mark.setAttribute("height", h + 9); mark.setAttribute("opacity", 1); }
      else mark.setAttribute("opacity", 0);
    }

    // the rain card
    show(rainCard, rainOn);
    if (rainOn > 0) { const p = ease(seg(t, C.card + 0.5, C.card + 1.6));
      rows.forEach(r => { css(r.fl, { width: (100 * lerp(1, r.lo, p)).toFixed(2) + "%" }); css(r.sp, { right: (100 * r.lo).toFixed(2) + "%", width: (100 * (r.hi - r.lo) * p).toFixed(2) + "%" }); }); }

    show(follow, win(t, C.follow, C.back[0] + 0.2, 0.35, 0.25));
    show(src.water, hook ? 1 : loop ? seg(t, C.back[0] + 0.3, C.back[0] + 0.6) : Math.max(win(t, C.run + 0.3, C.why), win(t, C.now + 0.6, C.back[0] + 0.2)));
    show(src.map, Math.max(win(t, C.where + 0.4, C.run), win(t, C.where2, C.now)));
    show(src.rain, win(t, C.why + 0.4, C.where2));
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
