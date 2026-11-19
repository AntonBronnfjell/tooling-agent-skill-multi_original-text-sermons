"""TAGNT edition tokens with word-order displacement (`TR»2`, `Byz«3`, `Tyn»4»4`, `Byz«14.24`).

TAGNT lists the words of a verse in one row order (NA's). A token with a displacement suffix means that
edition prints the word elsewhere: `»N` = after the row N rows later, `«N` = after the row N rows earlier,
counted over the verse's TAGNT rows. Rules, measured against MACULA SBLGNT (73 of the 78 verses with an SBL
mark come out in SBLGNT order; 21 of 78 without reordering) and the printed TR/Byz (1Tim 1:1, Acts 20:28):
- a mark the NA27 token on the same row also carries is relative to another base, so NA27's mark is
  subtracted (`NA27»4+SBL»4` = SBL unmoved);
- `»1` on a word followed by `γε` marks the enclitic joined form (μήγε, μήτιγε), not a move;
- a chained repeat of one mark (`Tyn»4»4`, an upstream duplication; 2 rows) counts once when another edition
  on the row carries that mark (Matt 14:26), else it is ignored as unreliable (John 13:19); different marks add;
- a verse-shaped suffix (`Byz«14.24`: Byz prints Rom 16:25-27 after Rom 14:23) moves the word to another
  verse; the DB keeps KJV versification, so such words stay in place (OTHER_VERSE).
"""
import re

from otslib.norm import strip_accents

_TOKEN = re.compile(r"^([^»«]*)((?:[»«][\d.]+)*)$")
_MARK = re.compile(r"([»«])([\d.]+)")
_ENDPUNCT = ".,;·:;·¶"
OTHER_VERSE = "other-verse"
CHAINED = "chained"


def parse_token(tok):
    """'TR»2' -> ('TR', 2); 'Byz«3' -> ('Byz', -3); 'SBL' -> ('SBL', 0); 'Byz«14.24' -> ('Byz', OTHER_VERSE)."""
    m = _TOKEN.match(tok.strip())
    if not m:
        return tok.strip(), 0
    marks = _MARK.findall(m.group(2))
    if any("." in n for _, n in marks):
        return m.group(1), OTHER_VERSE
    if len(marks) > 1 and len(set(marks)) == 1:
        d, n = marks[0]
        return m.group(1), (int(n) * (1 if d == "»" else -1), CHAINED)
    return m.group(1), sum(int(n) * (1 if d == "»" else -1) for d, n in marks)


def displacements(editions):
    """'NA28+TR»2+Byz' -> {'NA28': 0, 'TR': 2, 'Byz': 0}."""
    out = dict(parse_token(t) for t in (editions or "").split("+") if t.strip())
    for tok, d in out.items():
        if isinstance(d, tuple):  # chained repeat: keep only if another edition shares the mark
            out[tok] = d[0] if any(v == d[0] for t, v in out.items() if t != tok) else 0
    return out


def effective(token, row_disps, sub_disps=None):
    """Displacement of `token` on one TAGNT row (a substituted reading's own token wins), NA27-relative."""
    d = sub_disps[token] if sub_disps and token in sub_disps else row_disps.get(token, 0)
    if d == OTHER_VERSE or not d:
        return d
    base = row_disps.get("NA27")
    return d - base if isinstance(base, int) else d


def _is_ge(surface):
    return strip_accents(surface or "").casefold().strip(_ENDPUNCT) == "γε"


def order(entries):
    """entries: [(row index in the verse, displacement, surface)] for one edition, in row order.
    -> list of indices into `entries` in that edition's printed order."""
    keys = []
    for i, (row, d, _) in enumerate(entries):
        if d == 1 and i + 1 < len(entries) and _is_ge(entries[i + 1][2]):
            d = 0
        keys.append((row + d + 0.5 if isinstance(d, int) and d else row, i))
    return [i for _, i in sorted(keys)]


def moved(entries):
    return order(entries) != list(range(len(entries)))
