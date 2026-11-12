"""THE SWEEP of the third Hamoun film (hamoun3_fa, two parts): the page of each part is stepped every 0.25 s in
headless Chromium (rest frames alone do not show what slides through a transition) and three things are asserted:

    1. every visible piece of text is inside x 96-924 and above y 1540 (Instagram's own buttons and caption);
    2. no two pieces of text lie on each other (the parts of one block, such as a card or one headline, apart);
    3. nothing that belongs to a scene of the other part is ever visible.

A text box is measured by its ink (a font's line box is taller than its letters); cards, pins, chips and tags by
their own box. Run it after every change of words, clock or layout, before rendering:

    python -I src/onebit_hamoun3_sweep.py          # exit code 1 if anything is found
    python -I src/onebit_hamoun3_sweep.py 0.1      # a finer step (transitions shorter than 0.25 s)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit_hamoun3 as film  # noqa: E402  (mounts the page and the build folder)
from playwright.sync_api import sync_playwright  # noqa: E402

base = film.base
STEP = float(sys.argv[1]) if len(sys.argv) > 1 else 0.25        # seconds between the frames looked at
JS = """(t) => { window.renderAt(t); const out = [];
 const sel = '.head .line, .head .small, .tag .yr, .tag .sub, .tag .n, .tag .u, .tag .subl, .card, .legend span, .tick, .row .name, .row .less, .country, .place, .rivername, .pin, .chip, #follow span, #follow .next, #when .d, #when .h, .sources';
 document.querySelectorAll(sel).forEach(e => { let o = 1, v = true;
   for (let n = e; n && n.id !== 'stage'; n = n.parentElement) { const cs = getComputedStyle(n); o *= parseFloat(cs.opacity); if (cs.visibility === 'hidden' || cs.display === 'none') v = false; }
   if (!v || o < 0.5) return; const r = e.getBoundingClientRect(); const isBox = ['card', 'pin', 'chip', 'rivername', 'next'].some(c => e.classList.contains(c));
   if (r.width < 1 || !e.textContent.trim() && !isBox) return;
   const rg = document.createRange(); rg.selectNodeContents(e); const q = rg.getBoundingClientRect();
   const fs0 = parseFloat(getComputedStyle(e).fontSize), trim = isBox ? 0 : Math.max(0, (q.height - 1.05 * fs0) / 2);   // the ink, not the font's tall line box
   const b = isBox ? r : { left: q.left, right: q.right, top: q.top + trim, bottom: q.bottom - trim };
   const group = e.closest('.card') ? 'card' : e.closest('.next') ? 'next' : e.closest('.head') ? 'head' + [...document.querySelectorAll('.head')].indexOf(e.closest('.head')) : e.closest('.tag') ? 'tag' : e.closest('#when') ? 'when' : e.closest('#follow') ? 'follow' : '';
   out.push([String(e.className || e.id), e.textContent.trim().slice(0, 30), Math.round(b.left), Math.round(b.top), Math.round(b.right), Math.round(b.bottom), +o.toFixed(2), parseFloat(getComputedStyle(e).fontSize), group]); });
 return out; }"""
FOREIGN = dict(p1=["غبار", "نفر", "خشکسالی", "اختلاف", "دیده‌اید", "بفرستید", "طالبان", "ماهیگیری", "شهریور", "بادِ"],
               p2=["کجا رفت", "بالای میانگین", "بارش", "سدها", "سدِ", "یک‌سومِ", "قسمتِ بعد", "چاه‌نیمه", "میانگین"])
srv = base.serve(); port = srv.server_address[1]
fail = 0
with sync_playwright() as pw:
    for cut in film.CUTS:
        browser, page = base.open_page(pw, port, cut)
        end = page.evaluate("window.CUT.end")
        bad, over, foreign, n, small, seen = [], {}, [], 0, {}, {}
        k = 0
        while k * STEP <= end + 1e-9:
            t = round(min(k * STEP, end), 2); k += 1
            boxes = page.evaluate(JS, t)
            for cls, txt, l, tp, r, b, o, fs, grp in boxes:
                n += 1
                if l < 96 - 1 or r > 924 + 1 or b > 1540 + 1:
                    bad.append((t, cls, txt, l, tp, r, b))
                small[cls] = min(small.get(cls, 999), fs)
                seen.setdefault(txt, [t, t])[1] = t
                if any(w in txt for w in FOREIGN[cut]):
                    foreign.append((t, cls, txt))
            for i in range(len(boxes)):
                for j in range(i + 1, len(boxes)):
                    a, c = boxes[i], boxes[j]
                    if a[8] and a[8] == c[8]:
                        continue                      # the parts of one block (a card, one headline, the tag)
                    w = min(a[4], c[4]) - max(a[2], c[2]); h = min(a[5], c[5]) - max(a[3], c[3])
                    if w > 6 and h > 6:
                        key = (a[1], c[1])
                        over.setdefault(key, [t, t, w, h])
                        over[key][1] = t; over[key][2] = max(over[key][2], w); over[key][3] = max(over[key][3], h)
        browser.close()
        print(f"\n{cut}: {n} visible text boxes in {k} steps of {STEP} s; outside x 96-924 or below y 1540: {len(bad)}; "
              f"text on text: {len(over)}; from the other part: {len(foreign)}")
        for x in bad[:25]: print("   outside", x)
        for (a, c), (t0, t1, w, h) in sorted(over.items(), key=lambda kv: kv[1][0]): print(f"   overlap {t0:5.2f}-{t1:5.2f} s  {w}x{h} px  «{a}» on «{c}»")
        for x in foreign[:12]: print("   foreign", x)
        print("   smallest font size per kind (px):", {a: v for a, v in sorted(small.items())})
        fail += len(bad) + len(over) + len(foreign)
print("\nSWEEP", "CLEAN" if not fail else f"NOT CLEAN ({fail})")
sys.exit(1 if fail else 0)
