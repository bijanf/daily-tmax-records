/* «آبِ کارون کجا می‌رود؟»: window.renderAt(t) draws the frame of time t (seconds) from /build/film.json, which
   src/karun.py writes (every string, number, the clock, the colours). Every frame is a pure function of t.
   The film (since 16 Nov 2026): the Gotvand lake now from frame 0 with a corner locator, wiped back to 1369 within 2 s
   (the skip window) and forward again; a map of the river with a marker running down it; the fields
   south of Ahvaz now, wiped back to 1369 and forward again; the causes; the closing question; frame 0 again (the loop).
   The zoom's pictures (src/zoomkit.py) are no longer drawn: one of them is the locator. */
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
  const C = F.clock, Wd = F.words, col = F.colours, END = F.end, Z = F.zoom, P = F.places, TG = F.tags, CD = F.card;
  const THEN = String(F.before), NOW = String(F.now);
  for (const k in col) document.documentElement.style.setProperty("--" + k, col[k]);
  const load = src => new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error("no picture " + src)); im.src = "/build/" + src; });
  const IM = {};
  await Promise.all([["a" + THEN, `p_gotvand_${THEN}.jpg`], ["a" + NOW, `p_gotvand_${NOW}.jpg`], ["b" + THEN, `p_fields_${THEN}.jpg`], ["b" + NOW, `p_fields_${NOW}.jpg`],
    ["card", CD.file], ["loc", F.locator.file]].map(async ([k, f]) => { IM[k] = await load(f); }));
  await Promise.all(['900 88px "Vazirmatn"', '900 60px "Vazirmatn"', '800 48px "Vazirmatn"', '700 48px "Vazirmatn"', '500 32px "Vazirmatn"', '400 118px "Lalezar"'].map(f => document.fonts.load(f, "کارون ۱۴۰۵")));

  // the places: each picture is the frame (1080 x 1920) at scale 1; a slow push m about the frame's centre
  const BOX = { a: F.grids.gotvand.box, b: F.grids.fields.box, card: CD.box };
  const proj = (box, m) => (lon, lat) => [540 + m * 1080 * ((lon - box[0]) / (box[2] - box[0]) - 0.5), 960 + m * 1920 * ((box[3] - lat) / (box[3] - box[1]) - 0.5)];
  // the zoom's camera: zoomkit.py's forward projection (a globe about the lake, blended into the first place's grid)
  const D2R = Math.PI / 180, p0 = Z.lat0 * D2R, sp0 = Math.sin(p0), cp0 = Math.cos(p0), BA = BOX.a;
  function zproj(i, lon, lat) {
    const Sz = Z.S[i], srel = Sz / Z.s1, wE = Z.wE[i], p = lat * D2R, dl = (lon - Z.lon0) * D2R;
    const xo = 540 + Sz * Z.R * Math.cos(p) * Math.sin(dl), yo = 960 - Sz * Z.R * (cp0 * Math.sin(p) - sp0 * Math.cos(p) * Math.cos(dl));
    const xe = 540 + (lon - Z.lon0) / (BA[2] - BA[0]) * Z.base * srel * 1080, ye = 960 - (lat - Z.lat0) / (BA[3] - BA[1]) * Z.base * srel * 1920;
    return [(1 - wE) * xo + wE * xe, (1 - wE) * yo + wE * ye];
  }
  const zAtScale = sc => { let i = 0; while (i < Z.n - 1 && Math.abs(Z.S[i + 1] - sc) <= Math.abs(Z.S[i] - sc)) i++; return i; };
  const zcache = new Map();
  function zframe(i) {
    if (!zcache.has(i)) {
      const im = new Image(); im.src = "/build/" + Z.dir + "/z" + String(i).padStart(3, "0") + ".jpg";
      zcache.set(i, im.decode().then(() => im));
      if (zcache.size > 8) zcache.delete(zcache.keys().next().value);
    }
    return zcache.get(i);
  }

  const cv = el("canvas", null, stage); cv.id = "ground"; cv.width = 1080; cv.height = 1920;
  const ctx = cv.getContext("2d"); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
  el("div", null, stage).id = "shade-top"; el("div", null, stage).id = "shade-bot";
  const lay = svg("svg", { width: 1080, height: 1920, viewBox: "0 0 1080 1920" }, stage);
  const riverG = svg("g", {}, lay);
  const riverCase = svg("path", { fill: "none", stroke: "rgba(16,11,6,0.75)", "stroke-width": 11, "stroke-linecap": "round", "stroke-linejoin": "round" }, riverG);
  const riverLine = svg("path", { fill: "none", stroke: col.river, "stroke-width": 6, "stroke-linecap": "round", "stroke-linejoin": "round" }, riverG);
  const riverDone = svg("path", { fill: "none", stroke: col.gold, "stroke-width": 8, "stroke-linecap": "round", "stroke-linejoin": "round" }, riverG);
  const wipe = el("div", null, stage); wipe.id = "wipe";
  // the corner locator: where the lake is (Iran's outline, a gold dot on the dam), from frame 0 through the hook
  const loc = el("div", null, stage); loc.id = "locator"; loc.appendChild(IM.loc); el("div", "dot", loc);

  const heads = {};
  [["hook", Wd.hook, null], ["a", Wd.head_a, Wd.small_a], ["c", Wd.head_c, null], ["b", Wd.head_b, Wd.small_b], ["why", Wd.why, Wd.share], ["close", Wd.close, null]].forEach(([name, text, small]) => {
    const box = el("div", "head", stage), lines = text.split(" // ").map(s => { const l = el("span", "line", box); marked(l, s); return l; });
    fit(lines, 828, 58, 1.39);
    const sm = small ? el("span", "small", box, small) : null; if (sm) fit([sm], 828, 40, 1.4);
    heads[name] = { box, sm };
  });

  const tag = el("div", null, stage); tag.id = "tag";
  const tagYr = el("div", "yr", tag), tagVal = el("div", "val", tag), tagN = el("span", "n", tagVal), tagU = el("span", "u", tagVal, Wd.unit_a);

  const label = (text, cls) => el("div", "tagline" + (cls ? " " + cls : ""), stage, text);
  const L = { dam: label(Wd.dam), river: label(Wd.river), cdam: label(Wd.dam), cahvaz: label(Wd.ahvaz), criver: label(Wd.river) };
  const dots = { dam: el("div", "dotw", stage), cdam: el("div", "dotw", stage), cahvaz: el("div", "dotw", stage), marker: el("div", "dotg", stage) };
  // the zoom's own words: the country and the sea where the zoom rests, a gold pin with the river's name
  const FAR = { iran_far: el("div", "far", stage, Wd.iran), gulf: el("div", "far sea", stage, Wd.gulf) };
  const pinRing = el("div", null, stage); pinRing.id = "pinring";
  const pin = el("div", null, stage); pin.id = "pin";
  const pinName = label(Wd.karun, "gold pinname");

  const follow = el("div", null, stage); follow.id = "follow"; Wd.follow.forEach((s, i) => el("span", i ? "gold" : null, follow, s)); fit([...follow.children], 828, 40, 1.4);
  const src = { zoom: el("div", "sources", stage, Wd.src_zoom), pic: el("div", "sources", stage, Wd.src_pic), card: el("div", "sources", stage, Wd.src_card), why: el("div", "sources", stage, Wd.src_why) };
  Object.values(src).forEach(e => fit([e], 828, 22, 1.25));

  const RV = CD.river;                                    // the Karun on the map, upstream to downstream
  const pic = (key, m, a) => { ctx.globalAlpha = a; ctx.drawImage(IM[key], 540 - 540 * m, 960 - 960 * m, 1080 * m, 1920 * m); ctx.globalAlpha = 1; };
  // a place with its wipes: NOW on the left of x, THEN on the right; x runs to 0 (back to THEN) and out again to 1080
  function wiped(k, m, x, a) {
    pic(k + NOW, m, a);
    if (x < 1080) { ctx.save(); ctx.beginPath(); ctx.rect(x, 0, 1080 - x, 1920); ctx.clip(); pic(k + THEN, m, a); ctx.restore(); }
  }
  const wipeX = (t, back, fwd) => t < back[0] ? 1080 : t < fwd[0] ? 1080 * (1 - ease(seg(t, back[0], back[1]))) : 1080 * ease(seg(t, fwd[0], fwd[1]));

  window.renderAt = async function (t0) {
    draw(clamp(t0, 0, END), -1, null);              // no zoom frames: the lake from frame 0, frame 0 again at the end
  };

  function draw(t, zi, zim) {
    const zt = zi >= 0 ? zi / F.fps : Z.t, back = t >= C.out[0];   // back: the last frames, frame 0 again
    ctx.fillStyle = "#17110b"; ctx.fillRect(0, 0, 1080, 1920);
    // which scene: z (a zoom frame), a (the lake), c (the map), b (the fields; the causes stand on it), e (the lake again, the close)
    const inA = t >= C.zoom && t < C.card[0], inC = t >= C.card[0] && t < C.b[0], inB = t >= C.b[0] && t < C.close[0], inE = t >= C.close[0] && t < C.out[0];
    const sq = x => x * x, mA = 1 + 0.045 * sq(Math.sin(Math.PI * seg(t, C.zoom, C.a[1]))), mB = 1 + 0.045 * sq(Math.sin(Math.PI * seg(t, C.b[0], C.close[0] + 0.6))), mC = 1 + 0.05 * seg(t, C.card[0], C.card[1]);
    let xA = 1080, xB = 1080, wx = -1;
    const dC0 = seg(t, C.card[0], C.card[0] + 0.4), dC1 = seg(t, C.card[1] - 0.4, C.card[1]), dE = seg(t, C.back[0], C.back[1]);   // the dissolves
    if (zi >= 0) { ctx.drawImage(zim, 0, 0, 1080, 1920); }
    else if (inA) { xA = wipeX(t, C.a_back, C.a_fwd); wiped("a", mA, xA, 1); wx = xA;
      if (zim) { ctx.globalAlpha = 1 - seg(t, Z.t, Z.t + 0.2); ctx.drawImage(zim, 0, 0, 1080, 1920); ctx.globalAlpha = 1; } }   // the landing dissolves into the live picture
    else if (inC) {
      if (dC0 < 1) pic("a" + NOW, 1, 1);
      pic("card", mC, dC0);
      if (dC1 > 0) pic("b" + NOW, 1, dC1);
    }
    else if (inB) { xB = wipeX(t, C.b_back, C.b_fwd); wiped("b", mB, xB, 1); wx = xB; }
    else { if (dE < 1) pic("b" + NOW, mB, 1); pic("a" + NOW, 1, dE); }
    css(wipe, { left: wx - 3 }); show(wipe, wx > 2 && wx < 1078 ? 1 : 0);

    // the headlines
    const sceneHead = (name, a, b, fo = 0.25) => { const o = win(t, a, b, 0.3, fo); show(heads[name].box, o); heads[name].box.style.transform = `translateY(${(14 * (1 - ease(seg(t, a, a + 0.3)))).toFixed(1)}px)`; };
    show(heads.hook.box, t < C.hook[1] ? win(t, 0, C.hook[1]) : seg(t, C.out[0] - 0.4, C.out[0]));   // on from frame 0, and again for the zoom back out
    sceneHead("a", C.head_a, C.a[1]); if (heads.a.sm) show(heads.a.sm, seg(t, C.head_a + 0.3, C.head_a + 0.6));
    sceneHead("c", C.card[0] + 0.2, C.card[1]);
    sceneHead("b", C.head_b + 0.2, C.b[1]); if (heads.b.sm) show(heads.b.sm, seg(t, C.head_b + 0.5, C.head_b + 0.8));
    sceneHead("why", C.why[0], C.why[1]); if (heads.why.sm) show(heads.why.sm, seg(t, C.share, C.share + 0.3));
    sceneHead("close", C.close[0] + 0.3, C.out[0] - 0.4, 0.3);
    show(follow, win(t, C.follow, C.out[0] - 0.4, 0.35, 0.3));

    // the tag: the summer on screen and its measured number (the side of the wipe that holds most of the frame)
    const stop = inB ? "fields" : "gotvand", x = inB ? xB : xA, yr = x >= 540 ? NOW : THEN;
    tagYr.textContent = Wd.summer.replace("{}", TG[stop][yr].year);
    tagN.textContent = TG[stop][yr].n;
    tagU.textContent = stop === "fields" ? Wd.unit_b : Wd.unit_a;
    css(tag, { top: 1290 });
    show(tag, back ? seg(t, C.out[0], C.out[0] + 0.3) : zi >= 0 ? seg(zt, Z.t - 0.3, Z.t) : inA ? 1 - seg(t, C.a[1] - 0.3, C.a[1]) : inB ? win(t, C.b[0] + 0.3, C.b[1], 0.3, 0.3) : inE ? dE * (1 - seg(t, C.follow - 0.4, C.follow - 0.1)) : 0);

    // the names on the pictures
    const put = (e, q, o, dx = 0, dy = 0) => { const hw = e.offsetWidth / 2; css(e, { left: clamp(q[0] + dx, 96 + hw, 984 - hw), top: q[1] + dy }); show(e, o); };
    const pA = zi >= 0 ? (lon, lat) => zproj(zi, lon, lat) : proj(BOX.a, inE ? 1 : mA);
    const damOn = back ? 1 : inA ? 1 - seg(t, C.a[1] - 0.3, C.a[1]) : inE ? dE : 0;
    const qd = pA(P.dam[0], P.dam[1]);
    css(dots.dam, { left: qd[0], top: qd[1] }); show(dots.dam, damOn); put(L.dam, qd, damOn, -150, -44);
    const pB = proj(BOX.b, mB), riverOn = inB ? win(t, C.b[0] + 0.5, C.close[0], 0.3, 0.3) : 0;
    put(L.river, pB(P.river_b[0], P.river_b[1]), riverOn);

    // the map: the river's line, the marker running down it from the dam to the fields, three names
    const cOn = inC ? Math.min(dC0, 1 - dC1) : 0, pC = proj(BOX.card, mC);
    if (cOn > 0) {
      const pts = RV.map(p => pC(p[0], p[1])), d = a => a.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");
      const f = ease(seg(t, C.card[0] + 0.6, C.card[1] - 0.7)), k = CD.i_dam + f * (CD.i_fields - CD.i_dam), k0 = Math.floor(k), fr = k - k0;
      const here = k0 >= CD.i_fields ? pts[CD.i_fields] : [lerp(pts[k0][0], pts[k0 + 1][0], fr), lerp(pts[k0][1], pts[k0 + 1][1], fr)];
      riverCase.setAttribute("d", d(pts)); riverLine.setAttribute("d", d(pts));
      riverDone.setAttribute("d", d(pts.slice(CD.i_dam, k0 + 1).concat([here])));
      css(dots.marker, { left: here[0], top: here[1] });
      const qa = pC(P.ahvaz[0], P.ahvaz[1]), qm = pC(P.dam[0], P.dam[1]);
      css(dots.cdam, { left: qm[0], top: qm[1] }); css(dots.cahvaz, { left: qa[0], top: qa[1] });
      put(L.cdam, qm, cOn, 150, -40); put(L.cahvaz, qa, cOn, 130, 0); put(L.criver, pts[Math.round((CD.i_dam + CD.i_fields) / 2 - 60)], cOn, -170, 0);
    } else { show(L.cdam, 0); show(L.cahvaz, 0); show(L.criver, 0); }
    riverG.setAttribute("opacity", cOn.toFixed(3));
    show(dots.cdam, cOn); show(dots.cahvaz, cOn); show(dots.marker, cOn);

    // the zoom's own words (functions of the zoom's clock, so the zoom back out ends on frame 0's picture)
    const farOn = 0;
    for (const key in FAR) { const q = zi >= 0 ? zproj(zi, P[key][0], P[key][1]) : [0, 0]; css(FAR[key], { left: q[0], top: q[1] }); show(FAR[key], farOn); }
    const pinOn = zi >= 0 ? 1 - seg(zt, C.pin[0], C.pin[1]) : 0, ph = (zt / 0.9) % 1, rr = 40 + 80 * ph;
    show(pin, pinOn); css(pinRing, { width: rr, height: rr }); show(pinRing, pinOn * (1 - ph));
    // the name stands above the pin: below it, it sat on the head of the Gulf and the pin read as coastal
    css(pinName, { left: 540, top: 960 - 74 }); show(pinName, 0);

    // the sources
    show(src.zoom, 0);
    show(loc, Math.max(win(t, 0, C.locator[1], 0.3, 0.4), back ? seg(t, C.out[0], C.out[0] + 0.3) : 0));
    show(src.pic, back ? 1 : inA ? 1 - seg(t, C.a[1] - 0.3, C.a[1]) : inB ? win(t, C.b[0] + 0.3, C.b[1], 0.3, 0.3) : inE ? dE : 0);
    show(src.card, cOn);
    show(src.why, win(t, C.why[0], C.why[1]));
  }
  await window.renderAt(0);
  window.READY = true;
}
main().catch(e => { window.FAILED = String(e && e.stack || e); });
