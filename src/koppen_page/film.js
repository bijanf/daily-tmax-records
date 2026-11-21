/* The Köppen film (film.html): window.renderAt(t) draws the frame of time t (seconds) from /build/film.json, which
   src/koppen.py writes (every string, number, the clock, the colours, the map pictures). Nothing is typed here; the
   numbers in this file are pixels of the layout. Every frame is a pure function of t (the frames are rendered out of
   order by several workers).
   The picture: Iran's climate classes on the terrain (the dimmed Blue Marble around it), the recent period (1991-2020)
   and the end of the century (2071-2099, the middle scenario). An edge moves from the left to the right: left of it the
   later map, right of it the recent one; the edge is a salmon stripe on its left and a green one on its right, the
   colours of the headline's two lines (the later and the recent period).
   The scenes: a the whole country in every class's colour and the share of hot dry land; b the same with only the
   freezing-winter climates in colour; c Tehran and the Alborz; d the three scenarios as columns on a card; e the
   question on the recent map; then frame 0 again. */
"use strict";
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const ease = p => p * p * (3 - 2 * p);
const easeOut = p => 1 - Math.pow(1 - clamp(p), 3);
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
const WIDE = 888, LOW = 828;

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const C = F.clock, Wd = F.words, col = F.colours, END = F.end, P = F.pictures;
  window.CUT = { name: "a", end: END };
  for (const k of ["gold", "ink", "paper", "cool", "less", "more"]) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const IMG = {};
  for (const fr of ["iran", "tehran"]) { IMG[fr] = { ground: await load(P[fr].ground) }; for (const k in P[fr].layers) IMG[fr][k] = await load(P[fr].layers[k]); }
  await Promise.all(['900 78px "Vazirmatn"', '800 42px "Vazirmatn"', '700 34px "Vazirmatn"', '500 34px "Vazirmatn"'].map(f => document.fonts.load(f, "خ۱")));

  const ORDER = ["a", "b", "c", "d", "e"];
  const FRAME = { a: "iran", b: "iran", c: "tehran", d: "iran", e: "iran" };
  const KIND = { a: "full", b: "winter", c: "full", d: "full", e: "full" };
  const NOW = "1991_2020", LATER = "2071_2099_ssp245";

  // ── the ground ──
  const cv = el("canvas", null, stage); cv.id = "ground"; cv.width = 1080; cv.height = 1920;
  const ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  const gTop = ctx.createLinearGradient(0, 0, 0, 760);
  [[0, 0.92], [0.55, 0.7], [0.85, 0.25], [1, 0]].forEach(([p, a]) => gTop.addColorStop(p, `rgba(14,12,10,${a})`));
  // a slow push from frame 0 (about the map's centre), so the first frames already move
  const push = t => 1 + 0.025 * seg(t, 0, END);
  function layer(img, m, a, clipX) {                     // a picture under the push, optionally only left of clipX
    ctx.save(); ctx.globalAlpha = a;
    if (clipX !== undefined) { ctx.beginPath(); ctx.rect(0, 0, clipX, 1920); ctx.clip(); }
    ctx.drawImage(img, 540 - 540 * m, 960 - 960 * m, 1080 * m, 1920 * m); ctx.restore();
  }
  // the map of a scene: the recent period, the later one left of the edge (edge x from 96 to 1080 as p goes 0 to 1)
  const edgeX = p => -10 + 1100 * ease(p);
  function map(fr, kind, p, m, a) {
    layer(IMG[fr].ground, m, a);
    layer(IMG[fr][`${NOW}_${kind}`], m, a);
    if (p > 0) layer(IMG[fr][`${LATER}_${kind}`], m, a, edgeX(p));
  }

  // ── the words ──
  const heads = {};
  [["a", Wd.hook, Wd.note_a], ["b", Wd.head_b, Wd.note_b], ["c", Wd.head_c, Wd.note_c], ["d", Wd.head_d], ["e", Wd.head_e]].forEach(([name, text, note]) => {
    const box = el("div", "head", stage), lines = text.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
    const kinds = (F.pair && F.pair[name]) || [];
    lines.forEach((l, i) => { if (kinds[i]) { l.classList.add("pair"); l.querySelectorAll(".key").forEach(k => k.classList.add(kinds[i])); } });
    lines.forEach(l => fit([l], WIDE, 46, 1.38));
    if (note) { const n = el("span", "note", box, note); fit([n], WIDE, 34, 1.3); }
    heads[name] = box;
  });

  // the legend plates: every group (scenes a, c, e) and the winter pair (scene b), each with its scene's source line
  function plate(items, colours, srcText) {
    const box = el("div", "plate", stage), grid = el("div", "grid", box);
    items.forEach((name, k) => { const it = el("div", "item", grid); css(el("i", null, it), { background: colours[k] }); it.appendChild(document.createTextNode(name)); });
    const s = el("div", "src", box), ls = srcText.split(" // ").map(x => el("span", null, s, x)); fit(ls, LOW - 40, 30, 1.24);
    return box;
  }
  const plates = { a: plate(Wd.legend, col.groups, Wd.src_a), b: plate(Wd.legend_d, [col.freezing, col.other], Wd.src_b),
                   c: plate(Wd.legend, col.groups, Wd.src_c), e: plate(Wd.legend, col.groups, Wd.src_e) };

  // places on the close map
  const T = P.tehran.frame, syT = T.sx / Math.cos(T.lat * Math.PI / 180);
  const places = F.places.map(pl => ({ pin: el("div", "pin", stage), name: el("div", "place " + pl.side, stage, pl.name),
    x: T.xc + (pl.lon - T.lon) * T.sx, y: T.yc - (pl.lat - T.lat) * syT }));

  // the card of the scenarios
  const B = F.bars, card = el("div", "card", stage), g = svg("svg", { width: 828, height: 760, viewBox: "0 0 828 760" }, card);
  const BX = [690, 490, 330, 170], BW = 120, BY0 = 590, BH = 440;           // the columns' centres from the right (recent first)
  const yOf = v => BY0 - BH * v / B.top;
  svg("line", { x1: 40, x2: 788, y1: BY0, y2: BY0, stroke: "rgba(29,20,12,0.55)", "stroke-width": 3 }, g);
  const fills = [col.less, col.more, col.more, col.more];
  const cols = B.values.map((v, k) => svg("rect", { x: BX[k] - BW / 2, width: BW, rx: 8, fill: fills[k], stroke: "rgba(29,20,12,0.35)", "stroke-width": 2 }, g));
  const vals = [Wd.v_now, Wd.v_low, Wd.v_mid, Wd.v_high].map((s, k) => css(el("div", "v", card, s), { left: BX[k], top: yOf(B.values[k]) - 76 }));
  [Wd.d_now, Wd.d_low, Wd.d_mid, Wd.d_high].forEach((s, k) => css(el("div", "t", card, s), { left: BX[k], top: BY0 + 14 }));
  css(el("div", "t span", card, Wd.d_later), { left: (BX[1] + BX[3]) / 2, top: BY0 + 70 });
  svg("line", { x1: BX[3] - BW / 2, x2: BX[1] + BW / 2, y1: BY0 + 66, y2: BY0 + 66, stroke: "rgba(29,20,12,0.4)", "stroke-width": 3 }, g);

  const follow = el("div", null, stage); follow.id = "follow"; el("span", null, follow, Wd.follow);

  const on0 = (k, t) => win(t, C[k][0] + (k === "a" ? 0 : 0.15), C[k][1], 0.3, 0.3);
  window.renderAt = function (t0) { draw(clamp(t0, 0, END)); };

  function draw(t) {
    const back = t >= C.out[0];
    const cur = back ? "e" : ORDER.filter(k => t >= C[k][0]).pop();
    const m = push(t);
    ctx.fillStyle = "#0e0c0a"; ctx.fillRect(0, 0, 1080, 1920);
    // the map's state: the edge of each scene (a, b, c wipe from the recent to the later map; d and e show the later)
    // scene e asks about today: it shows the recent map again (and so does frame 0, to which the film returns)
    const wipe = { a: seg(t, C.wipe_a[0], C.wipe_a[1]), b: seg(t, C.wipe_b[0], C.wipe_b[1]), c: seg(t, C.wipe_c[0], C.wipe_c[1]), d: 1, e: 0 };
    const prev = ORDER[Math.max(0, ORDER.indexOf(cur) - 1)];
    const fresh = cur === "a" ? 1 : seg(t, C[cur][0], C[cur][0] + 0.6);
    if (fresh < 1) map(FRAME[prev], KIND[prev], wipe[prev], m, 1);
    map(FRAME[cur], KIND[cur], wipe[cur], m, fresh);
    // the edge of the wipe (scenes a, b, c while it crosses): salmon on its left (later), green on its right (recent)
    const wk = ["a", "b", "c"].includes(cur) && !back ? cur : null, p = wk ? wipe[wk] : 0;
    if (wk && p > 0 && p < 1) { const ex = edgeX(p), top = 650, bot = 1260;      // only over the map: below the note, above the legend
      ctx.save(); ctx.globalAlpha = on0(wk, t); ctx.shadowColor = "rgba(0,0,0,0.6)"; ctx.shadowBlur = 12;
      ctx.fillStyle = col.more; ctx.fillRect(ex - 7, top, 7, bot - top); ctx.fillStyle = col.less; ctx.fillRect(ex, top, 7, bot - top); ctx.restore(); }
    if (cur === "d") { ctx.fillStyle = "rgba(14,12,10,0.45)"; ctx.fillRect(0, 0, 1080, 1920); }
    const home = back ? ease(seg(t, C.out[0], END - 1 / F.fps)) : 0;     // the last frames return to frame 0
    if (home > 0) map("iran", "full", 0, push(0), home);
    ctx.fillStyle = gTop; ctx.fillRect(0, 0, 1080, 760);

    const on = {}; ORDER.forEach(k => { on[k] = back ? (k === "a" ? seg(home, 0.55, 1) : k === "e" ? 1 - seg(home, 0, 0.4) : 0) : win(t, C[k][0] + (k === "a" ? 0 : 0.15), C[k][1] + (k === "e" ? 1 : 0), 0.3, 0.3); });
    ORDER.forEach(k => { show(heads[k], on[k]);
      heads[k].style.transform = k === "a" || back ? "none" : `translateY(${(14 * (1 - ease(seg(t, C[k][0] + 0.15, C[k][0] + 0.45)))).toFixed(1)}px)`; });
    for (const k in plates) show(plates[k], on[k]);
    show(follow, back ? on.e : win(t, C.follow, C.e[1] + 1, 0.35, 0.3));

    // the close map's places
    places.forEach(pl => { const o = back ? 0 : on.c, x = 540 + (pl.x - 540) * m, y = 960 + (pl.y - 960) * m;
      css(pl.pin, { left: x, top: y }); css(pl.name, { left: x, top: y }); show(pl.pin, o); show(pl.name, o); });

    // the card: the columns rise one after another
    show(card, back ? 0 : on.d);
    B.values.forEach((v, k) => { const s = C.bars[0] + k * 0.5, h = BH * v / B.top * easeOut(seg(t, s, s + 0.7));
      cols[k].setAttribute("y", (BY0 - h).toFixed(1)); cols[k].setAttribute("height", Math.max(0, h).toFixed(1)); show(vals[k], seg(t, s + 0.5, s + 0.8)); });
  }
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
