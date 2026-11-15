/* «آبِ هورالعظیم کجا رفت؟»: window.renderAt(t) draws the frame of time t (seconds) from /build/film.json, which
   src/hoor.py writes (every string, number, the clock, the colours). Every frame is a pure function of t. */
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
const win = (t, a, b, fi = 0.3, fo = 0.25) => t < a || t > b ? 0 : Math.min(a <= 0 ? 1 : seg(t, a, a + fi), 1 - seg(t, b - fo, b));
const faNum = n => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, "٬").replace(/\d/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]);

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const C = F.clock, Wd = F.words, col = F.colours, END = F.end, G = F.grid, B = F.bars, P = F.places;
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const years = [...new Set(B.map(b => b.pic))];
  const IM = {};
  await Promise.all(years.map(async y => { IM["p" + y] = await load("p" + y + ".jpg"); IM["v" + y] = await load("v" + y + ".png"); }));
  await Promise.all(['900 88px "Vazirmatn"', '800 48px "Vazirmatn"', '700 48px "Vazirmatn"', '500 32px "Vazirmatn"', '400 118px "Lalezar"'].map(f => document.fonts.load(f, "هورالعظیم ۱۴۰۵")));

  // the camera: the picture covers the frame, centred; a slow push in and out over the whole film
  const [LW, LS, LE, LN] = G.box;
  let S = 1, OX = 0, OY = 0;
  function cam(t) {
    const base = Math.max(1080 / G.w, 1920 / G.h);
    S = base * (1.0 + 0.05 * Math.sin(Math.PI * t / END));
    OX = 540 - S * G.w / 2; OY = 960 - S * G.h / 2;
  }
  const X = lon => OX + S * G.w * (lon - LW) / (LE - LW), Y = lat => OY + S * G.h * (LN - lat) / (LN - LS);

  const cv = el("canvas", null, stage); cv.id = "ground"; cv.width = 1080; cv.height = 1920;
  const ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  el("div", null, stage).id = "shade-top"; el("div", null, stage).id = "shade-bot";
  const lay = svg("svg", { width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, stage);
  const borderG = svg("g", {}, lay);
  const bpaths = F.border.map(() => svg("path", { fill: "none", stroke: "#fff", "stroke-width": 6, "stroke-dasharray": "18 12", "stroke-linecap": "round" }, borderG));
  const dykeP = svg("path", { fill: "none", stroke: col.gold, "stroke-width": 12, "stroke-linecap": "round", opacity: 0 }, lay);
  const wipe = el("div", null, stage); wipe.id = "wipe";

  const heads = {};
  [["hook", Wd.hook, null], ["era1", Wd.era1, null], ["era2", Wd.era2, null], ["side", Wd.side, Wd.side_small],
   ["why", Wd.why, Wd.share], ["close", Wd.close, null]].forEach(([name, text, small]) => {
    const box = el("div", "head", stage), lines = text.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
    fit(lines, 828, 58, 1.39);
    const sm = small ? el("span", "small", box, small) : null; if (sm) fit([sm], 828, 40, 1.4);
    heads[name] = { box, sm };
  });

  const tag = el("div", null, stage); tag.id = "tag";
  const tagYr = el("div", "yr", tag), tagVal = el("div", "val", tag), tagN = el("span", "n", tagVal), tagU = el("span", "u", tagVal, Wd.unit);
  const tagHeld = el("div", "held", tag, Wd.held); css(tagHeld, { position: "absolute", right: 0, top: 150 });

  const label = (text, cls) => el("div", "tagline" + (cls ? " " + cls : ""), stage, text);
  const L = { iran: label(Wd.iran), iraq: label(Wd.iraq), karkheh: label(Wd.karkheh), tigris: label(Wd.tigris), dyke: label(Wd.dyke, "gold") };

  // the springs: one bar a spring, the line of 860 km2 dashed
  const card = el("div", null, stage); card.id = "bars";
  const CW = 828, CH = 320, BX0 = 24, BX1 = CW - 24, BY0 = 262, BY1 = 62;
  const vmax = Math.max(...B.map(b => b.km2 || 0));
  const yv = v => BY0 - (BY0 - BY1) * v / vmax;
  const bs = svg("svg", { width: CW, height: CH, viewBox: `0 0 ${CW} ${CH}` }, card);
  const bw = (BX1 - BX0) / B.length;
  // right to left: the first spring on the right (RTL reading)
  const xOf = i => BX1 - (i + 1) * bw;
  const rects = B.map((b, i) => svg("rect", { x: xOf(i) + 2, width: bw - 4, y: BY0, height: 0, rx: 3,
    fill: b.km2 === null ? "#bdb3a4" : (b.year < 1999 ? col.wet : (b.km2 > F.line ? col.wet : "#B5763A")) }, bs));
  svg("line", { x1: BX0, x2: BX1, y1: yv(F.line), y2: yv(F.line), stroke: col.ink, "stroke-width": 3, "stroke-dasharray": "10 7" }, bs);
  svg("line", { x1: BX0, x2: BX1, y1: BY0, y2: BY0, stroke: col.ink, "stroke-width": 3 }, bs);
  const lg = el("div", "lg", card, faNum(F.line) + " کیلومترمربع"); css(lg, { left: xOf(25), top: yv(F.line) - 46 });
  const ax0 = el("div", "ax", card, B[0].label), ax1 = el("div", "ax", card, B[B.length - 1].label);
  css(ax0, { right: 12 }); css(ax1, { left: 12 });
  const axS = el("div", "ax", card, B[F.clock.split ? 13 : 0].label); css(axS, { left: xOf(13) + bw / 2 - 40 });
  const cursor = svg("rect", { y: BY1 - 10, height: BY0 - BY1 + 10, width: bw, fill: "rgba(29,20,12,0.12)" }, bs);

  const follow = el("div", null, stage); follow.id = "follow"; Wd.follow.forEach((s, i) => el("span", i ? "gold" : null, follow, s)); fit([...follow.children], 828, 40, 1.4);
  const src = { water: el("div", "sources", stage, Wd.src_water), map: el("div", "sources", stage, Wd.src_map) };
  Object.values(src).forEach(e => fit([e], 828, 22, 1.25));

  const path = pts => pts.map((p, i) => (i ? "L" : "M") + X(p[0]).toFixed(1) + " " + Y(p[1]).toFixed(1)).join(" ");
  const picture = (y, a, veil) => {
    const w = S * G.w, h = S * G.h;
    ctx.globalAlpha = a; ctx.drawImage(IM["p" + y], OX, OY, w, h);
    if (veil > 0) { ctx.globalAlpha = a * veil; ctx.drawImage(IM["v" + y], OX, OY, w, h); }
    ctx.globalAlpha = 1;
  };
  const springAt = t => { let k = -1; C.spring_t.forEach((s, i) => { if (t >= s) k = i; }); return k; };
  const FULL = F.full, NOW = F.now, SIDE = F.side_year;
  const byYear = y => B.find(b => b.year === y);

  window.renderAt = function (t0) {
    const t = clamp(t0, 0, END);
    cam(t);
    ctx.fillStyle = "#17110b"; ctx.fillRect(0, 0, 1080, 1920);
    // which pictures: A on the left side of a wipe, B on the right (the wipe runs from right to left)
    let A = FULL, Bp = NOW, wp = 0, veil = 1, held = false, shownYear = FULL;
    const k = springAt(t);
    if (t < C.hook[1]) { wp = ease(seg(t, C.wipe1[0], C.wipe1[1])); A = FULL; Bp = NOW; shownYear = wp >= 0.5 ? NOW : FULL; }
    else if (t < C.side[0]) { const b = B[Math.max(0, k)]; A = b.pic; Bp = b.pic; wp = 0; shownYear = b.year; held = b.held; }
    else if (t < C.close[0]) { const wpp = ease(seg(t, C.side_wipe[0], C.side_wipe[1])); A = B[B.length - 1].pic; Bp = SIDE; wp = wpp; shownYear = wpp >= 0.5 ? SIDE : NOW; }
    else if (t < C.back[0]) { wp = ease(seg(t, C.now_wipe[0], C.now_wipe[1])); A = SIDE; Bp = NOW; shownYear = wp >= 0.5 ? NOW : SIDE; }
    else { wp = 1 - ease(seg(t, C.back[0], C.back[1])); A = FULL; Bp = NOW; shownYear = wp >= 0.5 ? NOW : FULL; }
    const veilOn = t < C.hook[1] ? ease(seg(t, 0.9, 1.6)) * 0 + 1 : 1;
    const ap = byYear(A), bp = byYear(Bp);
    picture(A, 1, veilOn);
    if (wp > 0) { const xw = 1080 * (1 - wp); ctx.save(); ctx.beginPath(); ctx.rect(xw, 0, 1080 - xw, 1920); ctx.clip(); picture(Bp, 1, veilOn); ctx.restore();
      css(wipe, { left: xw - 3 }); show(wipe, wp > 0.002 && wp < 0.998 ? 1 : 0); } else show(wipe, 0);
    if (held) { ctx.fillStyle = "rgba(40,36,30,0.45)"; ctx.fillRect(0, 0, 1080, 1920); }

    // the border: drawn on in the hook, then kept
    const bd = t < C.back[0] ? ease(seg(t, C.border[0], C.border[1])) : 1;
    bpaths.forEach((p, i) => { p.setAttribute("d", path(F.border[i])); const len = p.getTotalLength();
      p.style.strokeDasharray = bd < 1 ? `${len * bd} ${len}` : "18 12"; p.setAttribute("opacity", bd > 0 ? 0.95 : 0); });
    const dk = win(t, C.pins[2], C.why[1]);
    // the embankment: the straight run of the border through the marsh (the boundary's own line, the dyke beside it)
    const straight = F.border.flat().filter(p => p[1] > 31.0 && p[1] < 31.8);
    dykeP.setAttribute("d", path(straight)); dykeP.setAttribute("opacity", (0.85 * dk).toFixed(3));

    // the headlines
    show(heads.hook.box, t < C.hook[1] ? win(t, 0, C.hook[1]) : t >= C.back[0] ? seg(t, C.back[0], C.back[1]) : 0);
    const scene = (name, a, b) => { const o = win(t, a, b); show(heads[name].box, o); heads[name].box.style.transform = `translateY(${(14 * (1 - ease(seg(t, a, a + 0.3)))).toFixed(1)}px)`; };
    scene("era1", C.run[0], C.split); scene("era2", C.split, C.run[1]); scene("side", C.side[0], C.side[1]); scene("why", C.why[0], C.why[1]);
    if (heads.why.sm) show(heads.why.sm, seg(t, C.share, C.share + 0.3));
    if (heads.side.sm) show(heads.side.sm, seg(t, C.split_on, C.split_on + 0.3));
    show(heads.close.box, win(t, C.close[0], C.back[0], 0.3, 0.4));
    show(follow, win(t, C.follow, C.back[0], 0.35, 0.4));

    // the tag: year and open water of the picture on screen
    const yr = B.find(b => b.year === shownYear);
    tagYr.textContent = Wd.spring.replace("{}", yr.label);
    tagN.textContent = yr.km2 === null ? "—" : faNum(yr.km2);
    show(tagHeld, held ? 1 : 0);
    const inRun = t >= C.run[0] && t < C.run[1];
    css(tag, { top: inRun ? 980 : 1290 });
    const tagOn = t >= C.back[0] ? 1 : t < C.hook[1] ? 1 : Math.max(win(t, C.run[0], C.run[1]), win(t, C.side[0], C.side[1]), win(t, C.close[0], C.follow - 0.1));
    show(tag, tagOn);

    // the springs card
    const cardOn = win(t, C.run[0] - 0.2, C.run[1]);
    show(card, cardOn);
    B.forEach((b, i) => { const v = b.km2 || 0, on = ease(seg(t, C.spring_t[i], C.spring_t[i] + 0.25)) * (t < C.run[1] ? 1 : 1);
      const y = yv(v * on); rects[i].setAttribute("y", y.toFixed(1)); rects[i].setAttribute("height", (BY0 - y).toFixed(1)); });
    cursor.setAttribute("x", xOf(Math.max(0, k)).toFixed(1)); cursor.setAttribute("opacity", inRun && k >= 0 ? 1 : 0);

    // labels on the map
    const place = (e, key, o) => { const [lon, lat] = P[key], hw = e.offsetWidth / 2; css(e, { left: clamp(X(lon), 96 + hw, 984 - hw), top: Y(lat) }); show(e, o); };
    const lab = t < C.hook[1] ? seg(t, C.labels, C.labels + 0.3) : t < C.run[0] ? 1 : Math.max(win(t, C.side[0], C.side[1]), win(t, C.why[0], C.why[1]), t >= C.back[0] ? 1 : 0);
    place(L.iran, "iran", lab); place(L.iraq, "iraq", lab);
    place(L.karkheh, "karkheh", win(t, C.pins[0], C.why[1])); place(L.tigris, "tigris", win(t, C.pins[1], C.why[1])); place(L.dyke, "dyke", dk);

    show(src.water, Math.max(t < C.run[1] ? 1 : 0, win(t, C.side[0], C.side[1]), win(t, C.close[0], END)) * (1 - win(t, C.why[0], C.why[1])));
    show(src.map, win(t, C.why[0], C.why[1]));
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
