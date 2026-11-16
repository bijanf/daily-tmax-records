/* «آبِ کارون کجا رفت؟» (karunflow_fa): window.renderAt(t) draws the frame of time t (seconds) from /build/film.json, which
   src/karunflow.py writes (every string, every number, the clock, the colours). Every frame is a pure function of t.
   The film: the map of the river (the mosaic of 2016, the gauge record's last year) with the station at Ahvaz and a
   labelled gauge panel: 1379-1386 against 1387-1395, the second bar reaching half within 2 s; the lowest nine years of the
   record; the mean year of each period on a chart (the spring flood); the dry years and what changed upstream on the
   map; the closing question with the record's end; the last 0.7 s return to frame 0's state (the loop). Only period
   means and mean years are drawn (GRDC's terms), never a year's value. */
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
const FAD = "۰۱۲۳۴۵۶۷۸۹";
const faN = n => { const s = String(Math.round(n)); return (s.length > 3 ? s.slice(0, -3) + "٬" + s.slice(-3) : s).replace(/\d/g, d => FAD[d]); };

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const C = F.cut, S = C.scenes, Q = C.cues, Wd = F.words, col = F.colours, END = F.end, CD = F.card, P = F.places;
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const IM = { card: await load(CD.file), loc: await load(F.locator.file) };
  await Promise.all(['900 88px "Vazirmatn"', '800 48px "Vazirmatn"', '700 48px "Vazirmatn"', '500 32px "Vazirmatn"', '400 66px "Lalezar"'].map(f => document.fonts.load(f, "کارون ۱۳۹۵")));

  // the map: the card is the frame (1080 x 1920) at scale 1; a slow push about the centre, back to 1 at the end (the loop)
  const BOX = CD.box;
  const proj = m => (lon, lat) => [540 + m * 1080 * ((lon - BOX[0]) / (BOX[2] - BOX[0]) - 0.5), 960 + m * 1920 * ((BOX[3] - lat) / (BOX[3] - BOX[1]) - 0.5)];
  const cv = el("canvas", null, stage); cv.id = "ground"; cv.width = 1080; cv.height = 1920;
  const ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  el("div", null, stage).id = "shade-top"; el("div", null, stage).id = "shade-bot";
  const lay = svg("svg", { width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, stage);
  const riverCase = svg("path", { fill: "none", stroke: "rgba(16,11,6,0.75)", "stroke-width": 11, "stroke-linecap": "round", "stroke-linejoin": "round" }, lay);
  const riverLine = svg("path", { fill: "none", stroke: col.river, "stroke-width": 6, "stroke-linecap": "round", "stroke-linejoin": "round" }, lay);
  const defs = svg("defs", {}, lay), mk = svg("marker", { id: "head", viewBox: "0 0 10 10", refX: 6, refY: 5, markerWidth: 4.2, markerHeight: 4.2, orient: "auto" }, defs);
  svg("path", { d: "M0 0 L10 5 L0 10 z", fill: col.gold }, mk);
  const arrow = svg("path", { fill: "none", stroke: col.gold, "stroke-width": 9, "stroke-linecap": "round", "marker-end": "url(#head)" }, lay);

  const loc = el("div", null, stage); loc.id = "locator"; loc.appendChild(IM.loc); el("div", "dot", loc);

  const heads = {};
  [["hook", Wd.hook, []], ["low", Wd.low_head, [Wd.low_small]], ["year", Wd.year_head, []], ["why", Wd.why_head, [Wd.why_small, Wd.share]], ["close", Wd.close, [Wd.caveat]]].forEach(([name, text, smalls]) => {
    const box = el("div", "head", stage), lines = text.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
    fit(lines, 828, 58, 1.39);
    const sm = smalls.map(s => { const e = el("span", "small", box, s); fit([e], 828, 38, 1.4); return e; });
    heads[name] = { box, sm };
  });

  // the station and its gauge panel
  const link = el("div", null, stage); link.id = "link";
  const station = el("div", "dotw", stage), stationLab = el("div", "tagline", stage, Wd.station);
  const panel = el("div", null, stage); panel.id = "panel";
  el("div", "title", panel, Wd.gauge);
  const RIGHT = 828, LABW = 250, BARMAX = 480, VMAX = 600;            // inside the panel's rows (right = the row's right edge)
  const rows = F.pair.map((p, i) => {
    const row = css(el("div", "row", panel), { top: 86 + 92 * i });
    el("div", "lab", row, p.label);
    const bar = css(el("div", "bar", row), { background: i ? col.after : col.before, right: LABW + 10 });
    const val = el("div", "val", row);
    return { row, bar, val, len: BARMAX * p.value / VMAX, p };
  });
  el("div", "unit", panel, Wd.unit);
  const tickX = len => RIGHT + 30 - LABW - 10 - len;                    // a bar's left end, in the panel's own x
  const half = css(el("div", "tick", panel), { left: tickX(rows[0].len / 2) }), halfLab = css(el("div", "ticklab", panel, Wd.half), { left: tickX(rows[0].len / 2), top: 250 });
  const four = css(el("div", "tick w", panel), { left: tickX(BARMAX * 400 / VMAX) }), fourLab = css(el("div", "ticklab w", panel, faN(400)), { left: tickX(BARMAX * 400 / VMAX), top: 250 });

  // the mean year: October at the right; one curve for each period, drawn left to right in time = right to left
  const chart = el("div", null, stage); chart.id = "chart";
  const cs = svg("svg", { width: 888, height: 790, viewBox: "0 0 888 790", direction: "ltr" }, chart);
  const X0 = 838, X1 = 120, Y0 = 640, Y1 = 170, YMAX = 1000;
  const cx = i => X0 - (i + 0.5) * (X0 - X1) / 12, cy = v => Y0 - (Y0 - Y1) * v / YMAX;
  [0, 500, 1000].forEach(v => {
    svg("line", { x1: X1 - 10, x2: X0, y1: cy(v), y2: cy(v), stroke: "rgba(255,255,255,0.22)", "stroke-width": 2 }, cs);
    const tx = svg("text", { x: X1 - 22, y: cy(v) + 11, "text-anchor": "end", class: "axis" }, cs); tx.textContent = faN(v);
  });
  for (let k = 1; k < 4; k++) svg("line", { x1: X0 - k * 3 * (X0 - X1) / 12, x2: X0 - k * 3 * (X0 - X1) / 12, y1: Y0, y2: Y0 + 26, stroke: "rgba(255,255,255,0.45)", "stroke-width": 2 }, cs);
  Wd.seasons.forEach((s, k) => { const tx = svg("text", { x: X0 - (k * 3 + 1.5) * (X0 - X1) / 12, y: Y0 + 66, "text-anchor": "middle", class: "season" }, cs); tx.textContent = s; });
  const uLab = svg("text", { x: 30, y: Y1 - 48, "text-anchor": "start", class: "axis" }, cs); uLab.textContent = Wd.unit;
  const curve = (vals, colour) => {
    const pts = vals.map((v, i) => [cx(i), cy(v)]);
    const d = pts.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");
    const p = svg("path", { d, fill: "none", stroke: colour, "stroke-width": 10, "stroke-linecap": "round", "stroke-linejoin": "round" }, cs);
    const L = p.getTotalLength(); p.setAttribute("stroke-dasharray", L.toFixed(1)); return { p, L, pts };
  };
  const cb = curve(F.year.before, col.before), ca = curve(F.year.after, col.after);
  const APR = 6, springLine = svg("line", { x1: cx(APR), x2: cx(APR), y1: cy(F.year.after[APR]) - 14, y2: cy(F.year.before[APR]) + 14, stroke: col.gold, "stroke-width": 6, "stroke-dasharray": "14 10" }, cs);
  const legend = Wd.legend.map((s, i) => { const e = css(el("div", "legend", chart), { right: 30, top: 24 + 54 * i }); const sw = el("i", null, e); sw.style.background = i ? col.after : col.before; e.appendChild(document.createTextNode(s)); return e; });

  // the causes on the map: the Gotvand lake, the water carried out of the basin to the east
  const lakeDot = el("div", "dotw", stage), lakeLab = el("div", "tagline", stage, Wd.lake);
  const transferLab = el("div", "arrowlab", stage, Wd.transfer);

  const follow = el("div", null, stage); follow.id = "follow"; Wd.follow.forEach((s, i) => el("span", i ? "gold" : null, follow, s)); fit([...follow.children], 828, 40, 1.4);
  const src = { gauge: el("div", "sources", stage, Wd.src_gauge), map: el("div", "sources", stage, Wd.src_map), why: el("div", "sources", stage, Wd.src_why) };
  Object.values(src).forEach(e => fit([e], 888, 22, 1.25));

  window.renderAt = async function (t0) { draw(clamp(t0, 0, END)); };

  function draw(t) {
    const back = t >= Q.back[0], ret = back ? ease(seg(t, Q.back[0], Q.back[0] + 0.35)) : 0;   // the loop's return to frame 0
    const m = 1 + 0.035 * Math.sin(Math.PI * t / END) ** 2, pr = proj(m);
    ctx.fillStyle = "#17110b"; ctx.fillRect(0, 0, 1080, 1920);
    ctx.drawImage(IM.card, 540 - 540 * m, 960 - 960 * m, 1080 * m, 1920 * m);
    const pts = CD.river.map(p => pr(p[0], p[1])), d = pts.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");
    riverCase.setAttribute("d", d); riverLine.setAttribute("d", d);

    const inHook = t < S.hook[1], inLow = t >= S.low[0] && t < S.low[1], inYear = t >= S.year[0] && t < S.year[1];
    const gaugeOn = Math.max(t < S.low[1] ? 1 - seg(t, S.low[1] - 0.3, S.low[1]) : 0, ret);

    // the headlines
    const sceneHead = (name, a, b, fo = 0.25) => { const o = win(t, a, b, 0.3, fo); show(heads[name].box, o); heads[name].box.style.transform = `translateY(${(14 * (1 - ease(seg(t, a, a + 0.3)))).toFixed(1)}px)`; };
    show(heads.hook.box, Math.max(inHook ? win(t, 0, S.hook[1]) : 0, ret));
    sceneHead("low", S.low[0], S.low[1]); show(heads.low.sm[0], seg(t, Q.low_small, Q.low_small + 0.3));
    sceneHead("year", S.year[0], S.year[1]);
    sceneHead("why", S.why[0], S.why[1]); show(heads.why.sm[0], seg(t, Q.small, Q.small + 0.3)); show(heads.why.sm[1], seg(t, Q.share, Q.share + 0.3));
    sceneHead("close", S.close[0] + 0.3, Q.back[0], 0.3); show(heads.close.sm[0], seg(t, Q.caveat, Q.caveat + 0.3));
    show(follow, win(t, Q.follow, Q.back[0], 0.35, 0.3));

    // the station and the gauge panel
    const qa = pr(P.ahvaz[0], P.ahvaz[1]);
    css(station, { left: qa[0], top: qa[1] }); show(station, gaugeOn);
    css(stationLab, { left: qa[0] + 170, top: qa[1] - 4 }); show(stationLab, gaugeOn);
    css(link, { left: qa[0] - 2, top: qa[1] + 12, height: Math.max(0, 1128 - qa[1] - 12) }); show(link, gaugeOn);
    show(panel, gaugeOn);
    const g2 = back ? 0 : ease(seg(t, Q.grow[0], Q.grow[1]));
    rows.forEach((r, i) => {
      const f = i ? g2 : 1, len = r.len * f;
      css(r.bar, { width: len }); r.val.textContent = r.p.shown;
      css(r.val, { left: tickX(len) - 30 - 14 }); show(r.val, i ? (back ? 0 : seg(t, Q.grow[1] - 0.25, Q.grow[1])) : 1);
    });
    const hOn = back ? 0 : seg(t, Q.tick[0], Q.tick[1]); show(half, hOn); show(halfLab, hOn);
    const fOn = back ? 0 : inLow ? seg(t, Q.low_small, Q.low_small + 0.3) : 0; show(four, fOn); show(fourLab, fOn);
    show(halfLab, hOn * (1 - fOn));                                   // the 400 mark takes the label row in the second scene

    // the mean year
    const chOn = win(t, S.year[0], S.year[1], 0.4, 0.3); show(chart, chOn);
    cb.p.setAttribute("stroke-dashoffset", (cb.L * (1 - ease(seg(t, Q.curve_b[0], Q.curve_b[1])))).toFixed(1));
    ca.p.setAttribute("stroke-dashoffset", (ca.L * (1 - ease(seg(t, Q.curve_a[0], Q.curve_a[1])))).toFixed(1));
    cb.p.setAttribute("opacity", seg(t, Q.curve_b[0], Q.curve_b[0] + 0.05).toFixed(3)); ca.p.setAttribute("opacity", seg(t, Q.curve_a[0], Q.curve_a[0] + 0.05).toFixed(3));
    show(legend[0], seg(t, Q.curve_b[0], Q.curve_b[0] + 0.3)); show(legend[1], seg(t, Q.curve_a[0], Q.curve_a[0] + 0.3));
    springLine.setAttribute("opacity", seg(t, Q.spring, Q.spring + 0.3).toFixed(3));

    // the causes on the map
    const whyOn = win(t, S.why[0], S.why[1], 0.3, 0.3);
    const qd = pr(P.dam[0], P.dam[1]), lakeOn = whyOn * seg(t, Q.lake, Q.lake + 0.3);
    css(lakeDot, { left: qd[0], top: qd[1] }); show(lakeDot, lakeOn);
    css(lakeLab, { left: Math.max(96 + lakeLab.offsetWidth / 2, qd[0] - 24 - lakeLab.offsetWidth / 2), top: qd[1] + 50 }); show(lakeLab, lakeOn);
    const aOn = whyOn * seg(t, Q.transfer, Q.transfer + 0.4), grow = ease(seg(t, Q.transfer, Q.transfer + 0.6));
    const A0 = [905, 660], A1 = [975, 585];                           // out of the basin to the east, below the headline, inside x 984
    arrow.setAttribute("d", `M${A0[0]} ${A0[1]} L${lerp(A0[0], A1[0], grow).toFixed(1)} ${lerp(A0[1], A1[1], grow).toFixed(1)}`);
    arrow.setAttribute("opacity", aOn.toFixed(3));
    css(transferLab, { left: A0[0] - transferLab.offsetWidth - 18, top: A0[1] - 22 }); show(transferLab, aOn);

    // the river's line: on throughout, quieter under the chart
    lay.style.opacity = (1 - 0.6 * chOn).toFixed(3);
    show(loc, Math.max(win(t, 0, Q.locator[1], 0.3, 0.4), ret));

    // the sources: the gauge's under the panel and the chart, the map's under the map
    css(src.gauge, { top: 1452 }); css(src.map, { top: 1494 }); css(src.why, { top: 1452 });
    show(src.gauge, Math.max(t < S.year[1] ? 1 - seg(t, S.year[1] - 0.3, S.year[1]) : 0, ret));
    show(src.map, inYear ? 1 - chOn : 1);
    show(src.why, whyOn);
  }
  await window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
