"""Text normalization for Hebrew/Greek matching and display."""
import re
import unicodedata

_PUNCT = re.compile("[.,;·:׃׀]")
_WS = re.compile(r"\s+")
# Greek elision marks: U+2019 (SBLGNT/MACULA), U+1FBD (STEPBible), U+1FBF (psili used as elision),
# U+02BC, ASCII apostrophe
_ELISION = re.compile("[\u2019\u1fbd\u1fbf\u02bc']")
# editorial brackets (single and double, ASCII and U+27E6/U+27E7)
_BRACKETS = re.compile("[\\[\\]\u27e6\u27e7]")
# Hebrew vowel points, dagesh, rafe, shin/sin dots, qamats qatan (cantillation is already gone)
_HEB_POINTS = re.compile("[\u05b0-\u05bc\u05bf\u05c1\u05c2\u05c7]")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def display(s, lang):
    s = nfc(s)
    if lang == "heb":
        s = "".join(c for c in s if not ("֑" <= c <= "֯" or c == "ֽ"))
    return nfc(s)


def match_key(s, lang):
    s = display(s, lang).replace("־", " ")
    if lang == "grc":
        s = _ELISION.sub("'", s)
    s = _BRACKETS.sub("", s)
    s = _PUNCT.sub("", s)
    s = _WS.sub(" ", s).strip()
    return s.casefold() if lang == "grc" else s


def strip_accents(s):
    return nfc("".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)))


def strip_points(s):
    """Remove Hebrew vowel points (for matching pointed text against unpointed quotes)."""
    return nfc(_HEB_POINTS.sub("", s))
