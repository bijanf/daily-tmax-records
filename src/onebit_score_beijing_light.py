"""The light score of the eight-winter Tehran and Beijing NO2 film with the reasons (tehran_beijing_fa, 30 s): the light
score of onebit_score_compare8m_light.py, on the clock of onebit_beijing.py, in Mahur on A (the same intervals as the
Istanbul film's Mahur on C, transposed down 3 semitones).

The engine, the checks and the mix are the Istanbul film's own score, imported and run with three changes made in this
module, not in the imported file:
  - the film (onebit_beijing instead of onebit_compare8m), the base name and the narration folder (narration_bj);
  - the narration: n1 and n4 are new (Beijing's lines), n2, n3 and n5 are the Istanbul film's, copied in narration_bj;
  - the key: every note moves by KEY_SHIFT semitones (C Mahur to A Mahur), so each interval is unchanged.

The narration (the offline voice, ganji, length scale 0.9; shorter words rather than a faster voice):
    N1 0.20-5.50 s   N2 5.50-10.20 s   N3 10.20-14.20 s   N4 17.00-19.45 s   N5 19.50-28.75 s

    python -I src/onebit_score_beijing_light.py     writes the three reels and their WAVs, then runs the checks
    (the environment must give ONEBIT_TTS_BIN and ONEBIT_TTS_MODEL when a narration segment is synthesized)
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import onebit  # noqa: E402
import onebit_beijing as bj  # noqa: E402
import onebit_score_compare8m_light as base  # noqa: E402

_istanbul_notes = base.score_notes                  # the Istanbul film's notes, before this module patches them

BASE = "tehran_beijing_fa"
NARR_DIR = onebit.ROOT / "data" / "air" / "compare" / "narration_bj"
KEY_SHIFT = -3                                      # semitones: C Mahur -> A Mahur
N4_END = 19.45                                      # s: N4's window ends before N5's lead (19.47 s)
N1_TEXT = "هشت زمستان از فضا: پکن و تهران؛ دی‌اکسیدِ نیتروژن کجا بیشتر است؟"
N2_TEXT = "رنگِ روشن یعنی دی‌اکسیدِ نیتروژنِ بیشتر."
N5_TEXT = ("یک دلیلِ احتمالی، وارونگیِ هواست. دلیل‌های دیگر می‌توانند خودروهای فرسوده، سوختِ کم‌کیفیت و سوءمدیریت باشند. "
           "شما چه فکر می‌کنید؟")
N4_TEXT = "میانگین، بیشتر از سه برابرِ پکن."

NARRATION = (
    dict(name="n1", start=0.20, end=5.50, length=0.88, noise=0.0, text=N1_TEXT),   # the longer line: the floor of the
                                                                                  # length scale (0.88), to fit 5.30 s
    dict(name="n2", start=5.50, end=10.20, length=base.LENGTH_SCALE, noise=0.0, text=N2_TEXT),
    dict(name="n3", start=10.20, end=14.20, length=base.LENGTH_SCALE, noise=0.0,
         text="در هر هشت زمستان، در تهران بیشتر بود."),
    dict(name="n4", start=17.00, end=N4_END, length=base.LENGTH_SCALE, noise=0.0, text=N4_TEXT),
    dict(name="n5", start=19.50, end=base.END, length=0.88, noise=0.0, text=N5_TEXT),   # 0.88: the new «احتمالی» must
                                                                                     # keep the speech inside 28.75 s
)


LIFT_T = (15.00, 15.50, 16.00, 28.85)               # s: the rising phrase into the hold and the ending, an octave up
                                                    # (the lowest notes of A Mahur would fall below the light score's C4 range)


def score_notes() -> list:
    """The Istanbul film's notes (checked there), moved down KEY_SHIFT semitones; the phrase into the hold and the ending
    are lifted an octave so that every note stays in the light score's range (60-84). Intervals are unchanged."""
    out = []
    for nt in _istanbul_notes():
        m = nt.midi + KEY_SHIFT + (12 if any(abs(nt.t - t) < 1e-9 for t in LIFT_T) else 0)
        assert base.light.NOTE_RANGE[0] <= m <= base.light.NOTE_RANGE[1], (nt.t, m)
        out.append(dataclasses.replace(nt, midi=m))
    return out


def main() -> None:
    base.film = bj
    base.BASE = BASE
    base.NARR_DIR = NARR_DIR
    base.NARRATION = NARRATION
    base.score_notes = score_notes
    base.CHIP_MARKS = tuple((t, m) for t, (_, m) in zip(bj.CHIP_T, base.CHIP_MARKS))   # the marks follow the chips
    base.main()


if __name__ == "__main__":
    main()
