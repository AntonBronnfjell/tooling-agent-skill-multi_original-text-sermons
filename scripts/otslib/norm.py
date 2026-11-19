"""Text normalization for Hebrew/Greek matching and display."""
import re
import unicodedata

_PUNCT = re.compile("[.,;·:׃׀]")
_WS = re.compile(r"\s+")
# Greek elision marks: U+2019 (SBLGNT/MACULA), U+1FBD (STEPBible), U+02BC, ASCII apostrophe
_ELISION = re.compile("[\u2019\u1fbd\u02bc']")


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
    s = _PUNCT.sub("", s)
    s = _WS.sub(" ", s).strip()
    return s.casefold() if lang == "grc" else s


def strip_accents(s):
    return nfc("".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)))
