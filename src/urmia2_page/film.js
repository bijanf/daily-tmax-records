/* «دریاچه‌ی ارومیه واقعاً برگشته؟»: window.renderAt(t) draws the frame of time t (seconds) from /build/film.json, which
   src/urmia2.py writes (every string, number, the clock, the views, the colours). Every frame is a pure function of t. */
"use strict";
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const ease = p => p * p * (3 - 2 * p);
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

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const G = F.grid, C = F.clock, Wd = F.words, col = F.colours, END = F.end, P = F.places, GA = F.gauge, FA = F.facts;
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const IM = {}; await Promise.all([F.pics.y2025, F.pics.y2026, F.ring, F.ground.file].map(async n => { IM[n] = await load(n); }));
  await Promise.all(['900 88px "Vazirmatn"', '800 48px "Vazirmatn"', '700 48px "Vazirmatn"', '500 32px "Vazirmatn"', '400 118px "Lalezar"'].map(f => document.fonts.load(f, "دریاچه‌ی ارومیه ۱۴۰۴")));

  // ── the camera: the lake's centre (lon, lat) sits at frame (xa, ya); one slow push about the frame's centre ──
  const [CLON, CLAT] = F.views.centre;
  let V = null;
  function cam(t) {
    const p = ease(seg(t, C.shift1[0], C.shift1[1])) * (1 - ease(seg(t, C.shift2[0], C.shift2[1])));
    const h = F.views.hook, d = F.views.data;
    const xa = lerp(h[0], d[0], p), ya = lerp(h[1], d[1], p), s0 = lerp(h[2], d[2], p);
    const m = 1 + 0.04 * Math.sin(Math.PI * t / END);
    return { s: s0 * m, xa: 540 + (xa - 540) * m, ya: 960 + (ya - 960) * m, p };
  }
  const X = lon => V.xa + V.s * (lon - CLON) / G.dlon, Y = lat => V.ya - V.s * (lat - CLAT) / G.dlat;

  const cv = el("canvas", null, stage); cv.id = "ground"; cv.width = 1080; cv.height = 1920;
  const ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  el("div", null, stage).id = "shade-top"; el("div", null, stage).id = "shade-bot";
  const wipe = el("div", null, stage); wipe.id = "wipe";

  // the headlines
  const heads = {};
  [["hook", Wd.hook, null], ["up", Wd.up, Wd.up_small], ["area", Wd.area, Wd.area_small], ["summer", Wd.summer, Wd.summer_small],
   ["gap", Wd.gap, Wd.gap_small], ["close", Wd.close, null]].forEach(([name, text, small]) => {
    const box = el("div", "head", stage), lines = text.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
    fit(lines, 828, 58, 1.39);
    const sm = small ? el("span", "small", box, small) : null; if (sm) fit([sm], 828, 40, 1.4);
    heads[name] = box;
  });

  const tag = el("div", null, stage); tag.id = "tag";
  const tagYr = el("div", "yr", tag);

  // places
  const mkPlace = (name, side) => ({ dot: el("div", "dot", stage), name: el("div", "place", stage, name), side });
  const places = { urmia: mkPlace(Wd.urmia, "r"), tabriz: mkPlace(Wd.tabriz, "l") };

  // the gauge card
  const [cx, cy, cw, ch] = GA.card;
  const card = el("div", "card", stage);
  css(card, { left: cx, top: cy, width: cw, height: ch });
  el("div", "gt", card, Wd.gauge_title);
  const TX = 14, TW = 110, TOP = 90, PM = GA.per_m, TH = GA.tube_px;                     // the tube, in the card's pixels
  const yL = L => TOP + TH - (L - GA.tube_bottom) * PM;                                   // its bottom is last year's level
  const gs = svg("svg", { width: cw, height: ch, viewBox: `0 0 ${cw} ${ch}` }, card);
  const defs = svg("defs", {}, gs);
  svg("rect", { x: TX, y: TOP, width: TW, height: TH, rx: 18 }, svg("clipPath", { id: "tubeclip" }, defs));
  const hp = svg("pattern", { id: "hatch", width: 16, height: 16, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" }, defs);
  svg("rect", { width: 16, height: 16, fill: "rgba(120,170,230,0.18)" }, hp);
  svg("line", { x1: 0, y1: 0, x2: 0, y2: 16, stroke: "rgba(28,92,171,0.75)", "stroke-width": 5 }, hp);
  svg("rect", { x: TX, y: TOP, width: TW, height: TH, rx: 18, fill: "#e7dfd1" }, gs);
  const inner = svg("g", { "clip-path": "url(#tubeclip)" }, gs);
  const pale = svg("rect", { x: TX, width: TW, fill: "url(#hatch)" }, inner);
  const water = svg("rect", { x: TX, width: TW, fill: col.wet }, inner);
  const top = svg("rect", { x: TX, width: TW, height: 5, fill: "#6fa6e6" }, inner);
  const paleLine = svg("rect", { x: TX + 1.5, width: TW - 3, fill: "none", stroke: col.wet, "stroke-width": 3 }, inner);
  svg("rect", { x: TX, y: TOP, width: TW, height: TH, rx: 18, fill: "none", stroke: col.ink, "stroke-width": 4 }, gs);
  const gl = [];
  const mkLabel = (text, L, cls) => {
    const c = cls ? col.eco : col.ink, tick = svg("g", {}, gs);
    svg("line", { x1: TX + TW, x2: TX + TW + 18, y1: yL(L), y2: yL(L), stroke: c, "stroke-width": 3.5, "stroke-linecap": "round" }, tick);
    svg("circle", { cx: TX + TW, cy: yL(L), r: 8, fill: c, stroke: "#fff", "stroke-width": 2 }, tick);
    const d = el("div", "gl" + (cls ? " " + cls : ""), card);
    [].concat(text).forEach(line => el("span", null, d, line));
    gl.push({ d, tick }); return gl[gl.length - 1];
  };
  const Lbl = { last: mkLabel(Wd.g_last, FA.last), now: mkLabel(Wd.g_now, FA.now), june: mkLabel(Wd.g_june, FA.june), eco: mkLabel(Wd.g_eco, FA.eco, "eco") };
  gl.forEach((g, i) => css(g.d, { top: yL([FA.last, FA.now, FA.june, FA.eco][i]) - g.d.offsetHeight / 2 }));
  const ecoLine = svg("line", { x1: TX - 4, x2: TX + TW + 18, y1: yL(FA.eco), y2: yL(FA.eco), stroke: col.eco, "stroke-width": 5, "stroke-dasharray": "12 8" }, gs);

  const follow = el("div", null, stage); follow.id = "follow"; Wd.follow.forEach((s, i) => el("span", i ? "gold" : null, follow, s)); fit([...follow.children], 828, 40, 1.4);
  const src = { pic: el("div", "sources", stage, Wd.src_pic), level: el("div", "sources", stage, Wd.src_level), june: el("div", "sources", stage, Wd.src_june) };
  Object.values(src).forEach(e => fit([e], 828, 22, 1.25));

  const level = t => {                                    // the water in the gauge (m)
    let L = FA.last + (FA.now - FA.last) * ease(seg(t, C.rise[0], C.rise[1]));
    if (t >= C.june_in[0]) L = FA.now + (FA.june - FA.now) * ease(seg(t, C.june_in[0], C.june_in[1]));
    if (t >= C.june_out[0]) L = FA.june + (FA.now - FA.june) * ease(seg(t, C.june_out[0], C.june_out[1]));
    return L;
  };
  const picture = (img, a) => { const gx = X(G.lon0), gy = Y(G.lat1); ctx.globalAlpha = a; ctx.drawImage(IM[img], gx, gy, V.s * G.w, V.s * G.h); ctx.globalAlpha = 1; };

  window.renderAt = function (t0) {
    const t = clamp(t0, 0, END);
    V = cam(t);
    // the ground and the pictures
    ctx.globalAlpha = 1; ctx.fillStyle = "#17110b"; ctx.fillRect(0, 0, 1080, 1920);
    const g = F.ground, x0 = X(g.w), y0 = Y(g.n);
    ctx.drawImage(IM[g.file], x0, y0, X(g.e) - x0, Y(g.s) - y0);
    const A = F.pics.y2025, B = F.pics.y2026;
    let wp = -1, year = 2025;                               // wp: the share of the frame already in 2026 (a wipe), else -1
    if (t < C.wipe1[1]) wp = ease(seg(t, C.wipe1[0], C.wipe1[1]));
    else if (t < C.fade[0]) wp = 1;
    else if (t < C.wipe2[0]) { const a = seg(t, C.fade[0], C.fade[1]); picture(B, 1); picture(A, a); wp = -2; year = a >= 0.5 ? 2025 : 2026; }
    else if (t < C.wipe2[1]) wp = ease(seg(t, C.wipe2[0], C.wipe2[1]));
    else if (t < C.wipe3[0]) wp = 1;
    else wp = 1 - ease(seg(t, C.wipe3[0], C.wipe3[1]));
    if (wp > -2) {
      const xw = 1080 * (1 - wp);
      picture(A, 1);
      if (wp > 0) { ctx.save(); ctx.beginPath(); ctx.rect(xw, 0, 1080 - xw, 1920); ctx.clip(); picture(B, 1); ctx.restore(); }
      year = wp >= 0.5 ? 2026 : 2025;
      css(wipe, { left: xw - 3 }); show(wipe, wp > 0.002 && wp < 0.998 ? 1 : 0);
    } else show(wipe, 0);
    ctx.drawImage(IM[F.ring], X(G.lon0), Y(G.lat1), V.s * G.w, V.s * G.h);

    // headlines and small lines by scene
    const hookOn = t < C.up ? win(t, 0, C.up) : t >= C.wipe3[0] ? seg(t, C.wipe3[0], C.wipe3[1]) : 0;
    show(heads.hook, hookOn);
    const scene = (name, a, b) => { const o = win(t, a, b); show(heads[name], o); heads[name].style.transform = `translateY(${(14 * (1 - ease(seg(t, a, a + 0.3)))).toFixed(1)}px)`; };
    scene("up", C.up, C.area); scene("area", C.area, C.summer); scene("summer", C.summer, C.gap); scene("gap", C.gap, C.close);
    show(heads.close, win(t, C.close, C.wipe3[0], 0.3, 0.4));
    heads.close.style.transform = `translateY(${(14 * (1 - ease(seg(t, C.close, C.close + 0.3)))).toFixed(1)}px)`;
    show(follow, win(t, C.follow, C.wipe3[0], 0.35, 0.4));

    const cardP = ease(seg(t, C.shift1[0], C.shift1[1])) * (1 - ease(seg(t, C.shift2[0], C.shift2[1])));
    // the tag: the year of the picture (its sub line only in the hook and the loop)
    const followOn = seg(t, C.follow - 0.3, C.follow) * (1 - seg(t, C.wipe3[0], C.wipe3[0] + 0.3));
    const tagOn = t >= C.wipe3[0] ? seg(t, C.wipe3[0], C.wipe3[1]) : 1 - followOn;
    css(tagYr, { fontSize: lerp(118, 94, cardP) + "px" });
    tagYr.textContent = year === 2025 ? Wd.year25 : Wd.year26;
    const hookLike = t < C.up || t >= C.wipe3[0];
    css(tag, { top: lerp(1320, 1330, cardP) }); show(tag, t >= C.wipe3[0] ? tagOn : t < C.up ? 1 : tagOn);

    // sources
    const s1 = Math.max(win(t, 0, C.up), win(t, C.area, C.summer), win(t, C.close, C.wipe3[0], 0.3, 0.4), t >= C.wipe3[0] ? seg(t, C.wipe3[0], C.wipe3[1]) : 0);
    show(src.pic, s1);
    show(src.level, Math.max(win(t, C.up, C.area), win(t, C.gap, C.close)));
    show(src.june, win(t, C.summer, C.gap));

    // places
    const tab = t < C.up ? 1 - seg(t, C.up, C.up + 0.3) : seg(t, C.shift2[1] - 0.15, C.shift2[1]);
    [["urmia", 1], ["tabriz", tab]].forEach(([k, o]) => {
      const pl = places[k], [lon, lat] = P[k], x = X(lon), y = Y(lat);
      css(pl.dot, { left: x, top: y });
      css(pl.name, pl.side === "r" ? { left: x + 22, right: "auto", top: y } : { left: x - 22 - pl.name.offsetWidth, top: y });
      show(pl.dot, o); show(pl.name, o);
    });

    // the gauge
    css(card, { transform: `translateX(${(-(cw + 120) * (1 - cardP)).toFixed(1)}px)` }); show(card, cardP > 0.001 ? 1 : 0);
    const L = level(t), yw = yL(L);
    water.setAttribute("y", yw); water.setAttribute("height", TOP + TH - yw + 4);
    top.setAttribute("y", yw); top.setAttribute("opacity", L > FA.last + 0.002 ? 0.8 : 0);
    const pp = ease(seg(t, C.parts[0], C.parts[1]));
    pale.setAttribute("y", yL(FA.eco)); pale.setAttribute("height", yL(FA.now) - yL(FA.eco)); pale.setAttribute("opacity", pp);
    paleLine.setAttribute("y", yL(FA.eco)); paleLine.setAttribute("height", yL(FA.now) - yL(FA.eco)); paleLine.setAttribute("opacity", pp);
    const lab = { last: 1, now: seg(t, 6.2, 6.6), june: seg(t, C.june_in[0], C.june_in[0] + 0.4), eco: seg(t, C.eco[0], C.eco[1]) };
    for (const k in Lbl) { Lbl[k].d.style.opacity = lab[k].toFixed(3); Lbl[k].tick.style.opacity = lab[k].toFixed(3); }
    ecoLine.setAttribute("opacity", lab.eco.toFixed(3));
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
