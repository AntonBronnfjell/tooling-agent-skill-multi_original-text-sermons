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

# `order_flags.reason` values. ERROR in check_sermon: KNOWN_SCRAMBLED. WARN: ORDER_UNCERTAIN, NO_GROUND_TRUTH,
# REBUILT. Informational (lookup note only): KJV_BREAK and reasons starting with PLACEMENT.
KNOWN_SCRAMBLED_REASON = "known scrambled"
ORDER_UNCERTAIN = "order uncertain"
NO_GROUND_TRUTH = "no ground truth"
REBUILT = "rebuilt from TAGNT marks"
KJV_BREAK = "verse break follows KJV"
PLACEMENT = "placement differs"

# Verses whose word order, rebuilt from TAGNT marks, is an order no printed edition has (checked by hand).
# TR: checked against Scrivener 1894. THGNT/WH/NA: found by scanning every verse these witnesses get
# reordered from TAGNT marks (THGNT 124, WH 108, NA 12) for article/article or article/punctuation
# pairs, a postpositive (δέ γάρ οὖν τε μέν) opening a clause, an elided word before a consonant,
# and adjacent duplicates, then reading each hit against SBL: e.g. THGNT/WH `ἔστιν τοῦτ᾽ τὸν` for
# τοῦτ᾽ ἔστιν, Matt.12.14 `δὲ οἱ Φαρισαῖοι … Ἐξελθόντες`, WH Matt.18.8 `ἢ ἢ`, THGNT 1Cor.8.8
# `ἐὰν φάγωμεν μὴ ὑστερούμεθα`, THGNT 2Pet.1.18 `ἁγίῳ τῷ.`, WH Matt.21.30 (verse halves swapped).
_TOUT_ESTIN = ("1Pet.3.20 Acts.1.19 Acts.19.4 Heb.2.14 Heb.7.5 Heb.9.11 Heb.10.20 Heb.11.16 Heb.13.15 "
               "Mark.7.2 Matt.27.46 Phlm.1.12 Rom.7.18 Rom.9.8 Rom.10.6 Rom.10.7 Rom.10.8").split()
KNOWN_SCRAMBLED = {
    "TR": {"1Tim.1.2", "Acts.1.24", "John.19.31", "Luke.12.56", "Rev.17.4"},
    "THGNT": {"1Cor.8.8", "2Pet.1.18", "Matt.12.14", "Matt.18.8", "Mark.10.19", "John.14.7", *_TOUT_ESTIN},
    "WH": {"Heb.2.14", "Matt.12.14", "Matt.18.8", "Matt.21.30"},
    "NA": {"Matt.12.14"},
}


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
