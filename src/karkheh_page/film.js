/* «سدِ کرخه پر شد؟»: window.renderAt(t) draws the frame of time t (seconds) from /build/film.json, which
   src/karkheh.py writes (every string, number, the clock, the colours). Every frame is a pure function of t.
   The scenes: a the lake now inside the full lake's shoreline, wiped back to a year ago and forward again; c the river
   from the dam to the marsh; b the marsh on both sides of the border; d two days of dust, one wiped into the other;
   e the Hamoun in the same spring; f the lake again and the question; then frame 0 again (the loop). */
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
const WIDE = 888, DIS = 0.4;                             // the text column; the dissolve between two scenes

async function main() {
  const stage = document.getElementById("stage");
  const F = await (await fetch("/build/film.json")).json();
  const C = F.clock, Wd = F.words, col = F.colours, END = F.end, P = F.places, TG = F.tags;
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const IM = {};
  await Promise.all([["now", F.lake.now], ["last", F.lake.last], ["shore", F.lake.shore], ["card", F.card.file], ["marsh", F.marsh.file],
    ["dusta", F.dust.a], ["dustb", F.dust.b], ["hamoun", F.hamoun.file], ["loc", F.locator.file]].map(async ([k, f]) => { IM[k] = await load(f); }));
  await Promise.all(['900 86px "Vazirmatn"', '900 58px "Vazirmatn"', '800 42px "Vazirmatn"', '700 50px "Vazirmatn"', '500 28px "Vazirmatn"', '400 104px "Lalezar"'].map(f => document.fonts.load(f, "کرخه ۱۴۰۵")));

  const ORDER = ["a", "c", "b", "d", "e", "f"];
  const BOX = { a: F.lake.box, f: F.lake.box, c: F.card.box, b: F.marsh.box, d: F.dust.box, e: F.hamoun.box };
  // a picture is the frame at scale 1; a slow push m about the frame's centre; lon/lat to the frame under that push
  const proj = (box, m) => (lon, lat) => [540 + m * 1080 * ((lon - box[0]) / (box[2] - box[0]) - 0.5), 960 + m * 1920 * ((box[3] - lat) / (box[3] - box[1]) - 0.5)];
  const push = (name, t) => name === "a" ? 1 + 0.04 * Math.pow(Math.sin(Math.PI * seg(t, 0, C.a[1])), 2) : name === "f" ? 1 : 1 + 0.035 * seg(t, C[name][0], C[name][1] + DIS);

  const cv = el("canvas", null, stage); cv.id = "ground"; cv.width = 1080; cv.height = 1920;
  const ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  el("div", null, stage).id = "shade-top"; el("div", null, stage).id = "shade-bot";
  const lay = svg("svg", { width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, stage);
  const edge = {};                                       // the borders: one dashed line a scene, cased so it reads on any ground; not under the headline
  const clipB = svg("clipPath", { id: "below" }, svg("defs", {}, lay)); svg("rect", { x: 0, y: 610, width: 1080, height: 830 }, clipB);    // nor through the source lines
  ["c", "b", "d", "e"].forEach(k => {
    const g = svg("g", { "clip-path": "url(#below)" }, lay);
    edge[k] = { g, back: svg("path", { fill: "none", stroke: "rgba(16,11,6,0.7)", "stroke-width": 9, "stroke-linejoin": "round" }, g),
      front: svg("path", { fill: "none", stroke: "#fff", "stroke-width": 4, "stroke-dasharray": "16 12", "stroke-linejoin": "round" }, g) };
  });
  const riverG = svg("g", {}, lay);
  const riverCase = svg("path", { fill: "none", stroke: "rgba(16,11,6,0.75)", "stroke-width": 11, "stroke-linecap": "round", "stroke-linejoin": "round" }, riverG);
  const riverLine = svg("path", { fill: "none", stroke: col.river, "stroke-width": 6, "stroke-linecap": "round", "stroke-linejoin": "round" }, riverG);
  const riverDone = svg("path", { fill: "none", stroke: col.gold, "stroke-width": 8, "stroke-linecap": "round", "stroke-linejoin": "round" }, riverG);
  const wipe = el("div", null, stage); wipe.id = "wipe";
  const loc = el("div", null, stage); loc.id = "locator"; loc.appendChild(IM.loc);
  css(el("div", "here", loc), { left: (100 * F.locator.dot[0]).toFixed(2) + "%", top: (100 * F.locator.dot[1]).toFixed(2) + "%" });

  // the headlines: one box a scene (the hook is scene a's), a small line under some
  const heads = {};
  [["a", Wd.hook, Wd.small_a], ["c", Wd.head_c, Wd.small_c], ["b", Wd.head_b, null], ["d", Wd.head_d, Wd.small_d], ["e", Wd.head_e, null], ["f", Wd.head_f, null]].forEach(([name, text, small]) => {
    const box = el("div", "head", stage), lines = text.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
    fit(lines, WIDE, 54, 1.42);
    const sm = small ? el("span", "small", box, small) : null; if (sm) fit([sm], WIDE, 36, 1.4);
    heads[name] = { box, sm };
  });
  const tag = el("div", null, stage); tag.id = "tag";
  const tagYr = el("div", "yr", tag), tagVal = el("div", "val", tag), tagN = el("span", "n", tagVal), tagU = el("span", "u", tagVal, Wd.unit);

  // the names: [scene, element, place, dx, dy]
  const chip = (text, cls) => el("div", cls || "chip", stage, text);
  const NAMES = [["a", chip(Wd.full, "chip gold"), "full", 0, 0],
    ["c", chip(Wd.dam), "dam", -120, 44], ["c", chip(Wd.marsh), "marsh", 0, 0], ["c", chip(Wd.iran, "land"), "c_iran", 0, 0], ["c", chip(Wd.iraq, "land"), "c_iraq", 0, 0],
    ["b", chip(Wd.iran_b, "land"), "b_iran", 0, 0], ["b", chip(Wd.iraq_b, "land"), "b_iraq", 0, 0],
    ["d", chip(Wd.iraq, "land"), "d_iraq", 0, 0], ["d", chip(Wd.khuz, "land"), "d_khuz", 0, 0],
    ["e", chip(Wd.iran, "land"), "e_iran", 0, 0], ["e", chip(Wd.afg, "land"), "e_afg", 0, 0]];
  const dots = { a: el("div", "mark", stage), c: el("div", "mark", stage) }, runner = el("div", "runner", stage);
  const follow = el("div", null, stage); follow.id = "follow"; el("span", null, follow, Wd.follow);
  const src = {}; ORDER.forEach(k => { src[k] = el("div", "sources", stage); const ls = Wd["src_" + k].split(" // ").map(s => el("span", null, src[k], s)); fit(ls, WIDE, 20, 1.3); });

  const RV = F.card.river;                               // the Karkheh on the map, from the dam down to the marsh
  const pic = (key, m, a) => { ctx.globalAlpha = a; ctx.drawImage(IM[key], 540 - 540 * m, 960 - 960 * m, 1080 * m, 1920 * m); ctx.globalAlpha = 1; };
  // two pictures and a wipe: `first` on the left of x, `second` on the right
  function wiped(first, second, m, x, a) {
    pic(first, m, a);
    if (x < 1080) { ctx.save(); ctx.beginPath(); ctx.rect(x, 0, 1080 - x, 1920); ctx.clip(); pic(second, m, a); ctx.restore(); }
  }
  // scene a: now on the left of x; x runs to 0 (back to a year ago) and out again to 1080
  const xA = t => t < C.a_back[0] ? 1080 : t < C.a_fwd[0] ? 1080 * (1 - ease(seg(t, C.a_back[0], C.a_back[1]))) : 1080 * ease(seg(t, C.a_fwd[0], C.a_fwd[1]));
  const xD = t => 1080 * (1 - ease(seg(t, C.d_wipe[0], C.d_wipe[1])));      // scene d: the first day gives way to the next
  function ground(name, t, a) {                          // one scene's picture at time t with opacity a; returns the wipe's x (or -1)
    const m = push(name, t);
    if (name === "a") { const x = xA(t); wiped("now", "last", m, x, a); pic("shore", m, a); return x; }
    if (name === "f") { pic("now", m, a); pic("shore", m, a); return -1; }
    if (name === "d") { const x = xD(t); wiped("dusta", "dustb", m, x, a); return x; }
    pic({ c: "card", b: "marsh", e: "hamoun" }[name], m, a);
    return -1;
  }
  const path = pts => pts.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");

  window.renderAt = async function (t0) { draw(clamp(t0, 0, END)); };

  function draw(t) {
    const back = t >= C.out[0];                          // the last frames return to frame 0
    const cur = back ? "f" : ORDER.filter(k => t >= C[k][0]).pop(), i = ORDER.indexOf(cur);
    ctx.fillStyle = "#17110b"; ctx.fillRect(0, 0, 1080, 1920);
    // the ground: the scene's picture; in its first DIS seconds over the scene before it
    const fresh = i > 0 && !back ? seg(t, C[cur][0], C[cur][0] + DIS) : 1;
    if (fresh < 1) ground(ORDER[i - 1], t, 1);
    let wx = ground(cur, t, fresh);
    const home = back ? ease(seg(t, C.out[0], END - 1 / F.fps)) : 0;       // 1 on the last frame: frame 0's picture and words
    if (home > 0) { ground("a", 0, home); wx = -1; }
    css(wipe, { left: wx - 3 }); show(wipe, wx > 2 && wx < 1078 && fresh >= 1 ? 1 : 0);
    // how much of each scene's words stand: in with the dissolve, out before the next scene
    // (in the last frames the question's words leave before frame 0's words come: two headlines never stand together)
    const on = {}; ORDER.forEach(k => { on[k] = back ? (k === "a" ? seg(home, 0.55, 1) : k === "f" ? 1 - seg(home, 0, 0.4) : 0) : win(t, C[k][0] + (k === "a" ? 0 : 0.15), C[k][1] + (k === "f" ? 1 : 0), 0.3, 0.3); });   // the question stays to the scene's end and leaves in the last frames

    // the headlines
    ORDER.forEach(k => {
      show(heads[k].box, on[k]);
      heads[k].box.style.transform = k === "a" || back ? "none" : `translateY(${(14 * (1 - ease(seg(t, C[k][0] + 0.15, C[k][0] + 0.45)))).toFixed(1)}px)`;
    });
    show(heads.a.sm, back ? 0 : seg(t, C.small_a, C.small_a + 0.3));
    show(heads.c.sm, seg(t, C.small_c, C.small_c + 0.3));
    show(heads.d.sm, seg(t, C.small_d, C.small_d + 0.3));
    show(follow, back ? on.f : win(t, C.follow, C.f[1] + 1, 0.35, 0.3));

    // the tag: the lake's day and its measured water (the side of the wipe that holds most of the frame); a season or a day elsewhere
    const lake = cur === "a" || back, xa = back ? 1080 : xA(t), state = xa >= 540 ? TG.now : TG.last;
    tagYr.textContent = lake ? state.day : cur === "b" ? Wd.spring : cur === "d" ? (xD(t) >= 540 ? Wd.day_d1 : Wd.day_d2) : cur === "e" ? Wd.tag_e : "";
    tagN.textContent = state.n;
    show(tagVal, lake ? 1 : 0);
    show(tag, back ? on.a : cur === "a" || cur === "b" || cur === "d" || cur === "e" ? on[cur] : 0);

    // the names and the marks
    const put = (e, q, o, dx = 0, dy = 0) => { const hw = e.offsetWidth / 2; css(e, { left: clamp(q[0] + dx, 96 + hw, 984 - hw), top: q[1] + dy }); show(e, o); };
    NAMES.forEach(([k, e, place, dx, dy]) => {
      const o = on[k];
      // (frame 0's names come back with frame 0's words)
      if (o <= 0.001) { show(e, 0); return; }
      const q = proj(BOX[k], push(k, back ? 0 : t))(P[place][0], P[place][1]);
      put(e, q, o, dx, dy);
    });
    const qa = proj(BOX.a, push("a", back ? 0 : t))(P.dam[0], P.dam[1]); css(dots.a, { left: qa[0], top: qa[1] }); show(dots.a, on.a);

    // the borders
    ["c", "b", "d", "e"].forEach(k => {
      const o = on[k];
      edge[k].g.setAttribute("opacity", o.toFixed(3));
      if (o > 0.001) { const pr = proj(BOX[k], push(k, t)), d = F[{ c: "card", b: "marsh", d: "dust", e: "hamoun" }[k]].border.map(l => path(l.map(p => pr(p[0], p[1])))).join(" "); edge[k].back.setAttribute("d", d); edge[k].front.setAttribute("d", d); }
    });

    // the map: the river's line and the marker running down it from the dam to the marsh
    const cOn = on.c;
    riverG.setAttribute("opacity", cOn.toFixed(3));
    if (cOn > 0.001) {
      const pC = proj(BOX.c, push("c", t)), pts = RV.map(p => pC(p[0], p[1]));
      const f = ease(seg(t, C.c[0] + 0.7, C.c[1] - 1.2)), k = f * (pts.length - 1), k0 = Math.min(Math.floor(k), pts.length - 2), fr = k - k0;
      const here = [lerp(pts[k0][0], pts[k0 + 1][0], fr), lerp(pts[k0][1], pts[k0 + 1][1], fr)];
      riverCase.setAttribute("d", path(pts)); riverLine.setAttribute("d", path(pts)); riverDone.setAttribute("d", path(pts.slice(0, k0 + 1).concat([here])));
      css(runner, { left: here[0], top: here[1] }); css(dots.c, { left: pts[0][0], top: pts[0][1] });
    }
    show(runner, cOn); show(dots.c, cOn);

    // the locator and the sources
    show(loc, back ? on.a : win(t, 0, C.locator[1], 0.3, 0.4));
    ORDER.forEach(k => show(src[k], on[k]));
  }
  await window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
