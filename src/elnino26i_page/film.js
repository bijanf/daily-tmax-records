/* The infographic cut of the El Niño reel. The page shows one moment: window.renderAt(t) draws the frame of time t
   (seconds) from /build/film.json, which src/elnino26i.py writes from the reviewed film (words, numbers, clocks).
   No text or number is typed here; only the running tally of the drops is formatted (Persian digits).
   Cues: the moments inside a scene where the narration says a number (measured from the soundtrack, in seconds
   after the scene's start; the same in both cuts, because each voice piece starts with its scene). */
"use strict";
const CUE = {
  hook: { noah: 4.5 },                               // «طوفانِ نوح»
  autumn: { t0: 0.4, span: 4.1 },                    // the 26 drops turn while he says «بیست و یک ... بیست و شیش»
  iran: { grow0: 0.5, grow1: 1.7 },                  // «بیست و سه درصد» is said from 1.4 to 2.2 s
  winter: { t0: 0.5, span: 3.2, coin: 5.9 },         // «نیمی‌شون ...» 2.1 and 3.6 s; «سکه» 6.0 s
  answer: { rows: [0.5, 1.6, 2.7], question: 5.3 },  // «پاییزِ شهرِ شما» 5.5 s
};
const L = 96, R = 924, W = 828, MID = (L + R) / 2;      // the column the app's buttons leave free, and its centre
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const easeOut = p => 1 - Math.pow(1 - p, 3);
const easeInOut = p => p * p * (3 - 2 * p);
const bump = p => Math.sin(Math.PI * clamp(p));
const faDigits = s => String(s).replace(/\d/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]);
const SVGNS = "http://www.w3.org/2000/svg";
const DROP = "M0,-47 C10,-28 33,-8 33,14 A33,33 0 1,1 -33,14 C-33,-8 -10,-28 0,-47 Z";

function el(tag, cls, parent, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  if (parent) parent.appendChild(e);
  return e;
}
function svg(tag, attrs, parent) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function css(e, o) { Object.assign(e.style, o); return e; }
function px(o) { const r = {}; for (const k in o) r[k] = typeof o[k] === "number" ? o[k] + "px" : o[k]; return r; }
function text(parent, cls, s, o) { return css(el("div", "abs " + cls, parent, s), px(o)); }
function marked(parent, s) {                       // «... {key phrase} ...»: the phrase in the red box
  s.split(/(\{[^}]*\}|\[[^\]]*\])/).forEach(part => {
    if (!part) return;
    if (part[0] === "{" || part[0] === "[") el("span", "key", parent, part.slice(1, -1));
    else parent.appendChild(document.createTextNode(part));
  });
}
function fit(nodes, limit, floor) {                // one size for the nodes, so the widest fits the limit
  let size = parseFloat(getComputedStyle(nodes[0]).fontSize);
  const wide = () => Math.max(...nodes.map(n => n.scrollWidth));
  while (wide() > limit && size > floor) {
    size -= 1;
    nodes.forEach(n => css(n, { fontSize: size + "px", lineHeight: Math.round(size * 1.4) + "px" }));
  }
  return size;
}

async function main() {
  const stage = document.getElementById("stage");
  const cut = new URLSearchParams(location.search).get("cut") || "b";
  const F = await (await fetch("/build/film.json")).json();
  const C = F.cuts[cut];
  const pic = name => "/build/" + F.pictures[name];
  const root = document.documentElement.style;
  for (const k of ["paper", "ink", "mark", "land", "wet", "dry", "pale", "past", "near"]) root.setProperty("--" + k, F.colours[k]);

  // ── the top: the progress bar, the film's name, the counter, the follow line of the last scene ──
  const progress = el("div", null, stage); progress.id = "progress";
  const segs = C.scenes.map(() => el("i", null, el("div", "seg", progress)));
  const app = el("div", null, stage, F.app); app.id = "app";
  const counter = el("div", null, stage); counter.id = "counter";
  const follow = el("div", null, stage); follow.id = "follow";
  { const w = F.follow.split(" "), cutAt = w.indexOf("که");                // the same words, broken before «که»
    el("span", null, follow, w.slice(0, cutAt).join(" ")); el("span", null, follow, w.slice(cutAt).join(" ")); }

  // ── the frame of a scene: the headline (whole from its first frame), the small line, the sources ──
  function frame(sc) {
    const root = el("div", "scene", stage);
    const head = el("div", "head", root);
    const lines = sc.title.split(" // ").map(s => { const ln = el("span", "line", head); marked(ln, s); return ln; });
    const small = el("span", "small", head, sc.small);
    const body = css(el("div", "abs", root), { inset: "0" });
    el("div", "sources", root, sc.source);
    return { root, head, lines, small, body, key: head.querySelector(".key") };
  }

  // ── the hook: this week's Pacific, Iran, the classic index as a bar ──
  function hook(sc) {
    const f = frame(sc), H = F.hook, b = f.body;
    const cardY = 620, cardH = 311;
    const card = css(el("div", "card", b), px({ left: L, top: cardY, width: W, height: cardH }));
    el("img", null, card).src = pic("pacific");
    const bx = H.box, boxL = bx.x0 * W, boxT = bx.y0 * cardH, boxW = (bx.x1 - bx.x0) * W, boxH = (bx.y1 - bx.y0) * cardH;
    const box = css(el("div", "box34", card), px({ left: boxL, top: boxT, width: boxW, height: boxH }));
    const nino = css(el("div", "chip", card, H.nino_label), px({ left: boxL + boxW / 2, top: boxT - 70 }));
    nino.style.translate = "-50% 0";
    css(el("div", "chip", card, H.pac_label), px({ right: 14, bottom: 14 }));
    // Iran, cut out of the Blue Marble, and the dashed way from the warm water to it
    const iranH = 250, iranW = iranH * F.iran.land_size[0] / F.iran.land_size[1];
    const iran = css(el("img", "abs", b), px({ left: L - 4, top: 956, width: iranW, height: iranH }));
    iran.src = pic("iran_land");
    iran.style.filter = "drop-shadow(0 10px 14px rgba(46,33,24,.38)) saturate(1.15) contrast(1.05)";
    const s = svg("svg", { width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, b);
    css(s, { left: "0", top: "0" });
    const x0 = L + boxL + 34, y0 = cardY + cardH + 8, x1 = L + iranW * 0.86, y1 = 956 + iranH * 0.30;
    const d = `M${x0},${y0} C${x0 - 6},${y0 + 62} ${x1 + 86},${y1 + 4} ${x1 + 12},${y1}`;
    const mask = svg("mask", { id: "arcmask", maskUnits: "userSpaceOnUse", x: 0, y: 0, width: 1080, height: 1920 }, svg("defs", {}, s));
    const reveal = svg("path", { d, fill: "none", stroke: "#fff", "stroke-width": 40 }, mask);
    const arc = svg("path", { d, fill: "none", stroke: F.colours.mark, "stroke-width": 7, "stroke-linecap": "round",
      "stroke-dasharray": "4 17", mask: "url(#arcmask)" }, s);
    const len = arc.getTotalLength();
    const tipP = arc.getPointAtLength(len), tipQ = arc.getPointAtLength(len - 6);
    const ang = Math.atan2(tipP.y - tipQ.y, tipP.x - tipQ.x) * 180 / Math.PI;
    const tip = svg("path", { d: "M-22,-15 L4,0 L-22,15 Z", fill: F.colours.mark,
      transform: `translate(${tipP.x},${tipP.y}) rotate(${ang})` }, s);
    svg("circle", { cx: x0, cy: y0, r: 9, fill: F.colours.mark }, s);
    const ask = css(el("div", "abs num", b, F.strong.question), px({ left: L - 4 + iranW * 0.47 - 46, top: 956 + iranH * 0.44 - 46,
      width: 92, height: 92 }));
    css(ask, { borderRadius: "50%", background: F.colours.ink, color: F.colours.paper, fontSize: "70px", lineHeight: "90px",
      textAlign: "center", boxShadow: "0 0 0 5px " + F.colours.paper });
    // the colour key of the map, with its unit
    const keyL = 508, keyW = R - keyL, keyY = 960;
    css(el("div", "abs", b), px({ left: keyL, top: keyY, width: keyW, height: 26 }), { borderRadius: "13px" }).style.cssText +=
      `;border-radius:13px;background:url(${pic("key_pacific")}) 0 0/100% 100%;box-shadow:0 0 0 2px rgba(46,33,24,.55)`;
    H.pac_ticks.forEach((tk, k) => {
      const t = text(b, "unit ltr", tk.label, { top: keyY + 30 });
      const x = keyL + tk.f * keyW;
      if (k === H.pac_ticks.length - 1) t.style.right = (1080 - x) + "px";
      else css(t, { left: x + "px", translate: "-50% 0" });
    });
    H.pac_key.forEach((line, k) => text(b, "unit", line, { right: 1080 - R, top: keyY + 84 + 50 * k }));
    // the classic index: a bar from 0 (right) to 3 (left) that fills from the right
    const barY = 1290, barH = 54, xv = v => R - (v - H.scale[0]) / (H.scale[1] - H.scale[0]) * W;
    css(el("div", "abs", b), px({ left: L, top: barY, width: W, height: barH }), {}).style.cssText +=
      `;border-radius:14px;background:${F.colours.land};box-shadow:0 0 0 2px rgba(46,33,24,.5) inset`;
    const fill = css(el("div", "abs", b), px({ top: barY, height: barH }));
    fill.style.cssText += `;right:${1080 - R}px;border-radius:14px;background:${F.colours.mark}`;
    H.marks.forEach(m => {
      const x = xv(m.v);
      css(el("div", "abs", b), px({ left: x - 2, top: barY - 12, width: 0, height: barH + 24 })).style.borderLeft =
        `4px dashed ${F.colours.ink}`;
      css(text(b, "label", m.label, { left: x, top: barY - 76 }), { translate: "-50% 0" });
    });
    text(b, "unit ltr", H.scale_labels[0], { right: 1080 - R, top: barY - 62 });
    text(b, "unit ltr", H.scale_labels[1], { left: L, top: barY - 62 });
    const value = text(b, "num ltr", H.oni_shown, { top: barY - 4 });
    css(value, { fontSize: "50px", lineHeight: barH + 8 + "px" });
    H.unit.forEach((line, k) => text(b, "unit", line, { right: 1080 - R, top: barY + barH + 12 + 50 * k }));
    return { ...f, update(t) {
      const p = easeInOut(seg(t, 0.2, 1.8)), val = 0.5 + (H.oni - 0.5) * p;
      fill.style.width = (R - xv(val)) + "px";
      css(value, { right: (1080 - xv(val) + 14) + "px", opacity: p >= 1 ? "1" : "0" });
      const a = easeOut(seg(t, 0.1, 1.5));
      reveal.setAttribute("stroke-dasharray", `${len * a} ${len}`);
      arc.setAttribute("stroke-dashoffset", (-t * 34).toFixed(2));
      tip.setAttribute("opacity", a >= 0.97 ? 1 : 0);
      const glow = 0.5 + 0.5 * Math.sin(2 * Math.PI * t / 2.4);
      box.style.boxShadow = `0 0 ${10 + 16 * glow}px ${2 + 3 * glow}px rgba(255,236,200,${(0.25 + 0.45 * glow).toFixed(3)})`;
      const k1 = bump(seg(t, 1.3, 1.9)), k2 = bump(seg(t, CUE.hook.noah, CUE.hook.noah + 0.7));
      ask.style.scale = (easeOut(seg(t, 1.2, 1.6)) * (1 + 0.14 * k1 + 0.2 * k2)).toFixed(4);
      if (f.key) f.key.style.boxShadow = `0 0 0 ${(7 * k2).toFixed(2)}px rgba(160,49,41,.28)`;
    } };
  }

  // ── the drops: one per El Niño season, turning blue (wetter than usual) or hollow, with a running tally ──
  function drops(sc, which) {
    const f = frame(sc), S = F.seasons[which], cue = CUE[which], b = f.body;
    const s = css(svg("svg", { width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, b), { left: "0", top: "0" });
    const pitch = W / S.per_row, top = 734, rowPitch = 142, big = 1.2;
    const marks = S.wetter.map((wet, k) => {
      const row = Math.floor(k / S.per_row), col = k % S.per_row;
      const g = svg("g", {}, s), x = R - pitch / 2 - col * pitch, y = top + row * rowPitch;
      const pale = svg("path", { d: DROP, fill: F.colours.pale }, g);
      const body = wet ? svg("path", { d: DROP, fill: F.colours.wet }, g)
        : svg("path", { d: DROP, fill: F.colours.paper, stroke: F.colours.dry, "stroke-width": 7 }, g);
      const shine = wet ? svg("path", { d: "M-19,14 a19,19 0 0,0 13,18", fill: "none", stroke: "#fff", "stroke-opacity": 0.5,
        "stroke-width": 6, "stroke-linecap": "round" }, g) : null;
      return { g, x, y, pale, body, shine, at: cue.t0 + k * cue.span / S.n, wet };
    });
    const rows = Math.ceil(S.n / S.per_row), countY = top + rows * rowPitch - 46;
    const count = text(b, "num", S.count, { left: which === "winter" ? MID + 66 : MID, top: countY });
    css(count, { fontSize: "156px", lineHeight: "190px", translate: "-50% 0", whiteSpace: "nowrap" });
    const legendY = countY + 216;
    F.legend.forEach((line, k) => {
      const y = legendY + 76 * k;
      const g = svg("g", { transform: `translate(${R - 24},${y + 30}) scale(0.5)` }, s);
      if (k === 0) svg("path", { d: DROP, fill: F.colours.wet }, g);
      else svg("path", { d: DROP, fill: F.colours.paper, stroke: F.colours.dry, "stroke-width": 9 }, g);
      text(b, "label legend", line, { right: 1080 - R + 62, top: y });
    });
    let coin = null;
    if (which === "winter") {                        // «مثلِ شیر یا خط»: a coin, a full drop on one face, a hollow one on the other
      const g = svg("g", {}, s);
      svg("circle", { r: 70, fill: F.colours.paper, stroke: F.colours.ink, "stroke-width": 7 }, g);
      svg("circle", { r: 56, fill: "none", stroke: F.colours.ink, "stroke-opacity": 0.3, "stroke-width": 3 }, g);
      const full = svg("path", { d: DROP, fill: F.colours.wet, transform: "scale(0.82)" }, g);
      const hollow = svg("path", { d: DROP, fill: F.colours.paper, stroke: F.colours.dry, "stroke-width": 8,
        transform: "scale(0.82)" }, g);
      coin = { g, full, hollow, x: L + 74, y: countY + 100 };
    }
    return { ...f, legend: [...b.querySelectorAll(".legend")], count, update(t) {
      let tally = 0;
      marks.forEach(m => {
        const p = seg(t, m.at, m.at + 0.34), q = easeOut(p);
        if (m.wet && p >= 0.5) tally += 1;
        m.pale.setAttribute("opacity", 1 - q);
        m.body.setAttribute("opacity", q);
        if (m.shine) m.shine.setAttribute("opacity", q);
        m.g.setAttribute("transform", `translate(${m.x},${m.y - 18 * (1 - q) * (p > 0 ? 1 : 0)}) scale(${big * (1 + 0.2 * bump(p))})`);
      });
      const done = t >= cue.t0 + cue.span + 0.2;
      count.textContent = done ? S.count : S.count.replace(/^[۰-۹]+/, faDigits(tally));
      count.style.scale = (1 + 0.08 * bump(seg(t, cue.t0 + cue.span + 0.2, cue.t0 + cue.span + 0.7))).toFixed(4);
      if (coin) {
        const spin = easeInOut(seg(t, cue.coin, cue.coin + 1.5)), turn = spin * 3 * Math.PI;   // one and a half turns
        const idle = 0.06 * Math.sin(2 * Math.PI * t / 2.2), c = Math.cos(turn + idle);
        const lift = 46 * Math.sin(Math.PI * spin);
        coin.g.setAttribute("transform", `translate(${coin.x},${coin.y - lift}) scale(${Math.max(0.04, Math.abs(c)).toFixed(4)},1)`);
        coin.full.setAttribute("opacity", c >= 0 ? 1 : 0);
        coin.hollow.setAttribute("opacity", c >= 0 ? 0 : 1);
      }
    } };
  }

  // ── Iran: the El Niño autumns as a percent of every autumn's mean, and the rain as a bar against that mean ──
  function iran(sc) {
    const f = frame(sc), I = F.iran, b = f.body;
    const mapH = 480, mapW = mapH * I.comp_size[0] / I.comp_size[1], mapY = 612;
    const map = css(el("img", "abs", b), px({ left: MID - mapW / 2, top: mapY, width: mapW, height: mapH }));
    map.src = pic("iran_comp");
    map.style.filter = "drop-shadow(0 16px 20px rgba(46,33,24,.34))";
    const barL = L + 40, barW = W - 80, barY = 1112;        // as the reviewed film: 136 to 884
    const stops = I.ramp.map(r => `${r.colour} ${(100 * r.f).toFixed(2)}%`).join(",");
    css(el("div", "abs", b), px({ left: barL, top: barY, width: barW, height: 30 })).style.cssText +=
      `;direction:ltr;border-radius:15px;background:linear-gradient(90deg,${stops});box-shadow:0 0 0 2px rgba(46,33,24,.55)`;
    I.scale.forEach(tk => css(text(b, "unit ltr", tk.label, { left: barL + tk.f * barW, top: barY + 34 }), { translate: "-50% 0" }));
    css(text(b, "unit", I.unit, { left: MID, top: barY + 86 }), { translate: "-50% 0" });
    const rainY = 1322, rainH = 54, xv = v => R - v / I.top * W;
    css(el("div", "abs", b), px({ left: L, top: rainY, width: W, height: rainH })).style.cssText +=
      `;border-radius:14px;background:${F.colours.land};box-shadow:0 0 0 2px rgba(46,33,24,.5) inset`;
    const fill = css(el("div", "abs", b), px({ top: rainY, height: rainH }));
    fill.style.cssText += `;right:${1080 - R}px;border-radius:14px;background:${F.colours.wet}`;
    css(el("div", "abs", b), px({ left: xv(I.mean) - 2, top: rainY - 10, width: 0, height: rainH + 20 })).style.borderLeft =
      `4px dashed ${F.colours.ink}`;
    css(text(b, "label", I.mean_label, { left: xv(I.mean), top: rainY - 70 }), { translate: "-50% 0" });
    text(b, "unit ltr", I.zero, { right: 1080 - R, top: rainY - 58 });
    const value = text(b, "num ltr", I.el_label, { top: rainY - 4 });
    css(value, { fontSize: "50px", lineHeight: rainH + 8 + "px" });
    text(b, "unit", I.rain_unit, { right: 1080 - R, top: rainY + rainH + 12 });
    return { ...f, update(t) {
      const a = easeOut(seg(t, 0.0, 0.9));
      map.style.clipPath = `circle(${(a * 135).toFixed(2)}% at 8% 38%)`;
      const p = easeInOut(seg(t, CUE.iran.grow0, CUE.iran.grow1)), v = I.el * p;
      fill.style.width = (R - xv(v)) + "px";
      value.textContent = p >= 1 ? I.el_label : faDigits(Math.round(v));
      css(value, { right: (1080 - xv(v) + 14) + "px", opacity: p > 0.15 ? "1" : "0" });
    } };
  }

  // ── the answer: the three numbers again, and the question to the viewer ──
  function answer(sc) {
    const f = frame(sc), A = F.answer, b = f.body;
    el("span", "small", f.head, A.note);
    const sizes = [92, 70, 60], tops = [686, 802, 896];
    const rows = A.recap.map((line, k) => {
      const r = text(b, "", line, { left: MID, top: tops[k] });
      css(r, { fontWeight: k === 0 ? "900" : "800", fontSize: sizes[k] + "px", lineHeight: Math.round(sizes[k] * 1.4) + "px",
        whiteSpace: "nowrap", translate: "-50% 0" });
      return r;
    });
    const card = css(el("div", "abs", b), px({ left: MID - 340, top: 1010, width: 680, height: 290 }));
    card.style.cssText += `;border-radius:44px;background:${F.colours.mark};color:${F.colours.paper};text-align:center;` +
      "box-shadow:0 18px 34px rgba(160,49,41,.3);padding-top:22px";
    A.question.forEach(line => css(el("div", null, card, line), { fontWeight: "800", fontSize: "60px", lineHeight: "82px",
      whiteSpace: "nowrap" }));
    const tail = css(el("div", "abs", b), px({ left: 716, top: 1270, width: 50, height: 50 }));
    tail.style.cssText += `;background:${F.colours.mark};rotate:45deg;border-radius:10px`;
    return { ...f, rows, update(t) {
      rows.forEach((r, k) => {
        const p = easeOut(seg(t, CUE.answer.rows[k], CUE.answer.rows[k] + 0.5));
        css(r, { opacity: p.toFixed(3), transform: `translateY(${(26 * (1 - p)).toFixed(2)}px)` });
      });
      const q = seg(t, CUE.answer.question, CUE.answer.question + 0.5);
      const pulse = 1 + 0.018 * Math.sin(2 * Math.PI * Math.max(0, t - CUE.answer.question - 0.5) / 1.6);
      const sc = (0.86 + 0.14 * easeOut(q)) * (1 + 0.05 * bump(q)) * (q >= 1 ? pulse : 1);
      css(card, { opacity: easeOut(q).toFixed(3), scale: sc.toFixed(4) });
      css(tail, { opacity: easeOut(q).toFixed(3), scale: sc.toFixed(4) });
    } };
  }

  const builders = { hook, autumn: sc => drops(sc, "autumn"), winter: sc => drops(sc, "winter"), iran, answer,
    what: window.buildWhat, record: window.buildRecord, strong: window.buildStrong };
  const scenes = C.scenes.map(sc => Object.assign(builders[sc.key](sc, { F, pic, frame }), { sc }));

  await document.fonts.ready;
  await Promise.all([...document.images].map(im => im.decode().catch(() => null)));
  scenes.forEach(s => {                               // the sizes that fit the column (measured once, with the fonts in)
    s.root.style.display = "block";
    fit(s.lines, W, 56);
    fit([...s.head.querySelectorAll(".small")], W, 40);
    if (s.legend) fit(s.legend, W - 62, 40);
    if (s.rows) s.rows.forEach(r => fit([r], W, 48));
    s.root.querySelectorAll(".unit").forEach(u => { if (u.scrollWidth > W) fit([u], W, 34); });
    s.root.style.display = "none";
  });
  fit([...follow.children], W, 36);

  window.renderAt = function (t) {
    t = clamp(t, 0, C.end - 1e-6);
    let i = 0;
    while (i + 1 < C.scenes.length && t >= C.scenes[i + 1].start) i += 1;
    const sc = C.scenes[i], dt = t - sc.start, last = i === C.scenes.length - 1;
    scenes.forEach((s, k) => { s.root.style.display = k === i ? "block" : "none"; });
    scenes[i].update(dt, sc.length);
    const enter = i === 0 ? 1 : easeOut(seg(dt, 0, 0.35));       // the picture settles in; the words are whole at once
    css(scenes[i].body, { opacity: (0.25 + 0.75 * enter).toFixed(3), transform: `translateY(${(14 * (1 - enter)).toFixed(2)}px)` });
    segs.forEach((s, k) => { s.style.width = (k < i ? 100 : k > i ? 0 : 100 * dt / sc.length).toFixed(3) + "%"; });
    counter.textContent = sc.counter;
    counter.style.display = sc.counter && !last ? "block" : "none";
    app.style.display = last ? "none" : "block";
    follow.style.display = last ? "block" : "none";
    if (last) follow.style.opacity = easeOut(seg(dt, CUE.answer.question + 0.9, CUE.answer.question + 1.5)).toFixed(3);
    return i;
  };
  window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
