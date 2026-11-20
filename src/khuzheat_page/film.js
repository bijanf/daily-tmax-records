/* The Khuzestan heat film (film.html): window.renderAt(t) draws the frame of time t (seconds) from /build/film.json,
   which src/khuzheat.py writes (every string, number, the clock, the colours). Nothing is typed here; the numbers in
   this file are pixels of the layout. Every frame is a pure function of t (the frames are rendered out of order by
   several workers).
   The picture: a city from space fills the frame (Abadan in scenes a and b, Ahvaz in c and d), with a slow push.
   The scenes: a the days of 48 C in a year as dots, the years around 1950 on the right and the last ten years on the
   left, the last ten coming one dot after another, and the station marked on the picture; b every year as a column
   (the other estimate, a model's), the columns rising from the right, with the mean of the first and of the last
   ten years; c Ahvaz, its two decades as dots and the hottest day of its data; d the question; then frame 0 again. */
"use strict";
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const ease = p => p * p * (3 - 2 * p);
const easeOut = p => 1 - Math.pow(1 - clamp(p), 3);
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
const WIDE = 888, LOW = 828, DIS = 0.5;                  // the headline's column; the column below y 1000; the dissolve between the two cities

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const C = F.clock, Wd = F.words, col = F.colours, END = F.end;
  window.CUT = { name: "a", end: END };
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const PIC = { abadan: await load(F.pictures.abadan.file), ahvaz: await load(F.pictures.ahvaz.file) };
  await Promise.all(['900 84px "Vazirmatn"', '800 44px "Vazirmatn"', '700 50px "Vazirmatn"', '500 34px "Vazirmatn"', '400 96px "Lalezar"'].map(f => document.fonts.load(f, "خ۱")));

  const ORDER = ["a", "b", "c", "d"];
  const CITY = { a: "abadan", b: "abadan", c: "ahvaz", d: "ahvaz" };
  // a slow push while a city's picture stands; a place (lon, lat) on the frame under that push
  const span = { abadan: [C.a[0], C.b[1]], ahvaz: [C.c[0], C.out[1]] };
  const pushOf = (city, t) => 1 + 0.06 * seg(t, span[city][0], span[city][1]);
  const proj = (city, m) => { const B = F.pictures[city].box, y0 = MERC(B[3]), y1 = MERC(B[1]);
    return (lon, lat) => [540 + m * 1080 * ((lon - B[0]) / (B[2] - B[0]) - 0.5), 960 + m * 1920 * ((y0 - MERC(lat)) / (y0 - y1) - 0.5)]; };

  // ── the layers, bottom to top ──
  const cv = el("canvas", null, stage); cv.id = "ground"; cv.width = 1080; cv.height = 1920;
  const ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  const gTop = ctx.createLinearGradient(0, 0, 0, 720), gBot = ctx.createLinearGradient(0, 1920, 0, 1380);
  [[0, 0.62], [0.5, 0.5], [0.82, 0.2], [1, 0]].forEach(([p, a]) => gTop.addColorStop(p, `rgba(12,9,6,${a})`));
  [[0, 0.62], [0.55, 0.5], [0.85, 0.2], [1, 0]].forEach(([p, a]) => gBot.addColorStop(p, `rgba(12,9,6,${a})`));
  function ground(city, t, a) {
    const m = pushOf(city, t);
    ctx.globalAlpha = a; ctx.drawImage(PIC[city], 540 - 540 * m, 960 - 960 * m, 1080 * m, 1920 * m);
    ctx.fillStyle = gTop; ctx.fillRect(0, 0, 1080, 720); ctx.fillStyle = gBot; ctx.fillRect(0, 1380, 1080, 540); ctx.globalAlpha = 1;
  }

  // the headlines: one box a scene (the hook is scene a's)
  const heads = {};
  [["a", Wd.hook], ["b", Wd.head_b], ["c", Wd.head_c], ["d", Wd.head_d]].forEach(([name, text]) => {
    const box = el("div", "head", stage), lines = text.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
    lines.forEach(l => fit([l], WIDE, 50, 1.42));
    heads[name] = box;
  });
  // the station on each picture: a ring on its place and its name beside it (on the side that has room)
  const mark = side => ({ pin: el("div", "pin", stage), name: el("div", "chip " + side, stage, Wd.station) });
  const stA = mark("east"), stH = mark("west");

  // a plate of dots: the earlier years on the right, the later on the left; each dot one day
  const R = 15, PITCH = 40;                             // a dot's radius and the grid's pitch
  function plate(nThen, nNow, tagThen, tagNow, numThen, numNow, withLegend) {
    const box = el("div", "plate", stage), g = svg("svg", { width: 828, height: 420, viewBox: "0 0 828 420" }, box);
    svg("line", { x1: 560, x2: 560, y1: 24, y2: 330, stroke: "rgba(243,234,216,0.35)", "stroke-width": 3 }, g);
    css(el("div", "tag", box, tagThen), { right: 26 }); css(el("div", "tag", box, tagNow), { right: 294 });
    const nt = css(el("div", "num", box, numThen), { right: 26 }), nn = css(el("div", "num", box, numNow), { right: 294 });
    // the dots fill their column from the right, row after row; the earlier years in one row
    const grid = (n, x0, perRow) => Array.from({ length: n }, (_, k) => svg("circle", { cx: x0 - (k % perRow) * PITCH, cy: 190 + Math.floor(k / perRow) * PITCH, r: R, fill: col.hot, stroke: "rgba(255,255,255,0.9)", "stroke-width": 2.5, opacity: 0 }, g));
    const then = grid(nThen, 828 - 26 - R, 6), now = grid(nNow, 828 - 294 - R, 12);
    if (withLegend) { const lg = el("div", "legend", box); el("i", null, lg); lg.appendChild(document.createTextNode(Wd.dots)); }
    return { box, then, now, nt, nn };
  }
  const plA = plate(F.dots.then, F.dots.now, Wd.tag_then, Wd.tag_now, Wd.n_then, Wd.n_now, true);
  const plC = plate(F.dots.c0, F.dots.c1, Wd.tag_c0, Wd.tag_c1, Wd.n_c0, Wd.n_c1, false);
  const cTop = el("div", "chip top", stage); cTop.appendChild(document.createTextNode(Wd.c_top)); el("span", "day", cTop, Wd.c_day);

  // the card of the years (scene b): one column a year, the years from the right to the left as the words run; the
  // column's height is the year's days of 48 C; the mean of the first ten and of the last ten complete years as lines
  const B = F.bars, NY = B.years.length, PX0 = 30, PW = 668, PY0 = 96, PY1 = 716, STEP = PW / NY, BW = STEP - 2.6;
  const yOf = v => PY1 - (PY1 - PY0) * v / B.top, xOf = k => PX0 + PW - (k + 1) * STEP + 1.3;
  const card = el("div", "card", stage);
  css(el("div", "t", card, Wd.b_legend), { right: 26, top: 16 });
  const g = svg("svg", { width: 828, height: 900, viewBox: "0 0 828 900" }, card);
  svg("line", { x1: PX0, x2: PX0 + PW, y1: PY1, y2: PY1, stroke: "rgba(29,20,12,0.55)", "stroke-width": 2 }, g);
  B.ticks.forEach(v => { svg("line", { x1: PX0, x2: PX0 + PW, y1: yOf(v), y2: yOf(v), stroke: "rgba(29,20,12,0.16)", "stroke-width": 2 }, g);
    css(el("div", "t m", card, Wd.tick.replace("{n}", v.toLocaleString("fa-IR"))), { left: PX0 + PW + 12, top: yOf(v) }); });
  const bars = B.counts.map((v, k) => svg("path", { fill: col.hot }, g));
  function bar(k, h) {                                   // a column with its top rounded, standing on the line
    const x = xOf(k), r = Math.min(3, h / 2, BW / 2), y = PY1 - h;
    bars[k].setAttribute("d", h <= 0.2 ? "" : `M${x} ${PY1}V${y + r}Q${x} ${y} ${x + r} ${y}H${x + BW - r}Q${x + BW} ${y} ${x + BW} ${y + r}V${PY1}Z`);
  }
  // a mean: a white line under an ink line (so it reads over the columns), across its ten years
  const means = B.means.map(mn => { const x1 = xOf(mn.k1) - 2, x2 = xOf(mn.k0) + BW + 2, y = yOf(mn.value);
    return [svg("line", { x1, x2, y1: y, y2: y, stroke: col.paper, "stroke-width": 11, "stroke-linecap": "round" }, g),
            svg("line", { x1, x2, y1: y, y2: y, stroke: col.ink, "stroke-width": 5, "stroke-linecap": "round" }, g)]; });
  css(el("div", "t", card, Wd.b_first), { left: PX0 + PW - 84, top: PY1 + 6 }); css(el("div", "t", card, Wd.b_last), { left: PX0, top: PY1 + 6 });
  const sums = [Wd.b_then, Wd.b_now].map((text, n) => { const e = css(el("div", "t sum", card), { right: 26, top: 782 + 54 * n }); el("i", null, e); e.appendChild(document.createTextNode(text)); return e; });

  const follow = el("div", null, stage); follow.id = "follow"; el("span", null, follow, Wd.follow);
  const src = {}; ORDER.forEach(k => { src[k] = el("div", "sources", stage); const ls = Wd["src_" + k].split(" // ").map(s => el("span", null, src[k], s)); fit(ls, LOW, 34, 1.36); });

  window.renderAt = function (t0) { draw(clamp(t0, 0, END)); };

  function dots(list, t, t0, t1, on) {                   // the dots come one after another between t0 and t1
    list.forEach((d, k) => { const s = t0 + (t1 - t0) * k / Math.max(1, list.length), p = easeOut(seg(t, s, s + 0.22));
      d.setAttribute("opacity", (on * p).toFixed(3)); d.setAttribute("r", (R * (0.4 + 0.6 * p)).toFixed(1)); });
  }

  function draw(t) {
    const back = t >= C.out[0];                          // the last frames return to frame 0
    const cur = back ? "d" : ORDER.filter(k => t >= C[k][0]).pop();
    ctx.fillStyle = "#120d09"; ctx.fillRect(0, 0, 1080, 1920);
    const city = CITY[cur], fresh = cur === "c" ? seg(t, C.c[0], C.c[0] + DIS) : 1;
    if (fresh < 1) ground("abadan", t, 1);
    ground(city, t, fresh);
    const home = back ? ease(seg(t, C.out[0], END - 1 / F.fps)) : 0;       // 1 on the last frame: frame 0's picture and words
    if (home > 0) ground("abadan", 0, home);
    const on = {}; ORDER.forEach(k => { on[k] = back ? (k === "a" ? seg(home, 0.55, 1) : k === "d" ? 1 - seg(home, 0, 0.4) : 0) : win(t, C[k][0] + (k === "a" ? 0 : 0.15), C[k][1] + (k === "d" ? 1 : 0), 0.3, 0.3); });
    ORDER.forEach(k => { show(heads[k], on[k]);
      heads[k].style.transform = k === "a" || back ? "none" : `translateY(${(14 * (1 - ease(seg(t, C[k][0] + 0.15, C[k][0] + 0.45)))).toFixed(1)}px)`; });
    show(follow, back ? on.d : win(t, C.follow, C.d[1] + 1, 0.35, 0.3));

    // the stations on the pictures
    const put = (st, q, o) => { css(st.pin, { left: q[0], top: q[1] }); css(st.name, { left: q[0], top: q[1] }); show(st.pin, o); show(st.name, o); };
    const sA = F.pictures.abadan.station, sH = F.pictures.ahvaz.station;
    put(stA, proj("abadan", back ? 1 : pushOf("abadan", t))(sA[0], sA[1]), on.a);
    put(stH, proj("ahvaz", pushOf("ahvaz", t))(sH[0], sH[1]), back ? 0 : on.c);

    // scene a: the plate; the earlier years' dots stand from frame 0, the last ten years' come one after another
    show(plA.box, on.a);
    plA.then.forEach(d => { d.setAttribute("opacity", 1); d.setAttribute("r", R); });
    dots(plA.now, back ? 0 : t, C.dots_now[0], C.dots_now[1], 1);
    show(plA.nt, 1); show(plA.nn, back ? 0 : seg(t, C.dots_now[1] - 0.2, C.dots_now[1] + 0.2));

    // scene b: the card of the years
    show(card, back ? 0 : win(t, C.b[0] + 0.25, C.b[1], 0.35, 0.3));
    if (cur === "b" && !back) {
      const upTo = NY * seg(t, C.bars[0], C.bars[1]);    // the columns rise one after another from the right
      B.counts.forEach((v, k) => bar(k, (PY1 - yOf(v)) * easeOut(clamp((upTo - k) / 6))));
      const mk = seg(t, C.b_marks, C.b_marks + 0.3);
      means.forEach(pair => pair.forEach(l => l.setAttribute("opacity", mk.toFixed(3)))); sums.forEach(e => show(e, mk));
    }

    // scene c: Ahvaz, its two decades and the highest reading of its station
    show(plC.box, back ? 0 : on.c);
    dots(plC.then, t, C.dots_c[0], C.dots_c[0] + 0.5, 1); dots(plC.now, t, C.dots_c[0] + 0.6, C.dots_c[1], 1);
    show(plC.nt, seg(t, C.dots_c[0] + 0.3, C.dots_c[0] + 0.6)); show(plC.nn, seg(t, C.dots_c[1] - 0.2, C.dots_c[1] + 0.2));
    css(cTop, { left: 96, top: 600 }); show(cTop, (back ? 0 : on.c) * seg(t, C.c_top, C.c_top + 0.3));

    ORDER.forEach(k => show(src[k], on[k]));
  }
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
