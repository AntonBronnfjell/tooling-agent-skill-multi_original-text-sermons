"""Scripture reference parsing (OSIS ids, English/Spanish names, KJV versification)."""
import re
import unicodedata
from typing import NamedTuple, Optional


class RefError(ValueError):
    pass


class Ref(NamedTuple):
    book: str
    chapter: int
    verse: Optional[int]
    verse_end: Optional[int]


# (OSIS, [English full + SBL abbreviations], [Spanish full + common abbreviations])
_TABLE = [
    ("Gen", ["Genesis", "Gen", "Ge", "Gn"], ["Génesis", "Gén", "Gn"]),
    ("Exod", ["Exodus", "Exod", "Ex", "Exo"], ["Éxodo", "Éx", "Exo"]),
    ("Lev", ["Leviticus", "Lev", "Le", "Lv"], ["Levítico", "Lev", "Lv"]),
    ("Num", ["Numbers", "Num", "Nu", "Nm"], ["Números", "Núm", "Nm"]),
    ("Deut", ["Deuteronomy", "Deut", "Dt", "De"], ["Deuteronomio", "Deut", "Dt"]),
    ("Josh", ["Joshua", "Josh", "Jos"], ["Josué", "Jos"]),
    ("Judg", ["Judges", "Judg", "Jdg", "Jg"], ["Jueces", "Jue", "Jc"]),
    ("Ruth", ["Ruth", "Rut", "Ru"], ["Rut", "Rt"]),
    ("1Sam", ["1 Samuel", "1 Sam", "1 Sm", "1 S"], ["1 Samuel", "1 Sam", "1 Sm"]),
    ("2Sam", ["2 Samuel", "2 Sam", "2 Sm"], ["2 Samuel", "2 Sam", "2 Sm", "2 S"]),
    ("1Kgs", ["1 Kings", "1 Kgs", "1 Ki"], ["1 Reyes", "1 Re", "1 Rey", "1 R"]),
    ("2Kgs", ["2 Kings", "2 Kgs", "2 Ki"], ["2 Reyes", "2 Re", "2 Rey", "2 R"]),
    ("1Chr", ["1 Chronicles", "1 Chr", "1 Ch"], ["1 Crónicas", "1 Cr", "1 Crón"]),
    ("2Chr", ["2 Chronicles", "2 Chr", "2 Ch"], ["2 Crónicas", "2 Cr", "2 Crón"]),
    ("Ezra", ["Ezra", "Ezr"], ["Esdras", "Esd"]),
    ("Neh", ["Nehemiah", "Neh", "Ne"], ["Nehemías", "Neh", "Ne"]),
    ("Esth", ["Esther", "Esth", "Est"], ["Ester", "Est"]),
    ("Job", ["Job", "Jb"], ["Job", "Jb"]),
    ("Ps", ["Psalms", "Psalm", "Ps", "Pss", "Psa"], ["Salmos", "Salmo", "Sal", "Slm", "Sl"]),
    ("Prov", ["Proverbs", "Prov", "Pr", "Prv"], ["Proverbios", "Prov", "Pr", "Prv"]),
    ("Eccl", ["Ecclesiastes", "Eccl", "Eccles", "Ec", "Qoh"], ["Eclesiastés", "Qohélet", "Ecl", "Ec", "Qo"]),
    ("Song", ["Song of Solomon", "Song of Songs", "Song", "Cant", "SS", "Sg"],
     ["Cantares", "Cantar de los Cantares", "Cantar", "Cant", "Cnt", "Ct"]),
    ("Isa", ["Isaiah", "Isa", "Is"], ["Isaías", "Isa", "Is"]),
    ("Jer", ["Jeremiah", "Jer", "Je"], ["Jeremías", "Jer", "Jr"]),
    ("Lam", ["Lamentations", "Lam", "La"], ["Lamentaciones", "Lam", "Lm"]),
    ("Ezek", ["Ezekiel", "Ezek", "Eze", "Ez"], ["Ezequiel", "Ezeq", "Eze"]),
    ("Dan", ["Daniel", "Dan", "Dn"], ["Daniel", "Dan", "Dn"]),
    ("Hos", ["Hosea", "Hos", "Ho"], ["Oseas", "Os"]),
    ("Joel", ["Joel", "Jl"], ["Joel", "Jl"]),
    ("Amos", ["Amos", "Am"], ["Amós", "Am"]),
    ("Obad", ["Obadiah", "Obad", "Ob"], ["Abdías", "Abd", "Ab"]),
    ("Jonah", ["Jonah", "Jon", "Jnh"], ["Jonás", "Jon"]),
    ("Mic", ["Micah", "Mic", "Mi"], ["Miqueas", "Miq", "Mi"]),
    ("Nah", ["Nahum", "Nah", "Na"], ["Nahúm", "Nah", "Na"]),
    ("Hab", ["Habakkuk", "Hab"], ["Habacuc", "Hab"]),
    ("Zeph", ["Zephaniah", "Zeph", "Zep"], ["Sofonías", "Sof"]),
    ("Hag", ["Haggai", "Hag", "Hg"], ["Hageo", "Hag"]),
    ("Zech", ["Zechariah", "Zech", "Zec"], ["Zacarías", "Zac"]),
    ("Mal", ["Malachi", "Mal"], ["Malaquías", "Mal"]),
    ("Matt", ["Matthew", "Matt", "Mt"], ["Mateo", "Mat", "Mt"]),
    ("Mark", ["Mark", "Mk", "Mr"], ["Marcos", "Mar", "Mr", "Mc"]),
    ("Luke", ["Luke", "Lk", "Lu"], ["Lucas", "Luc", "Lc"]),
    ("John", ["John", "Jn", "Joh"], ["Juan", "Jn"]),
    ("Acts", ["Acts", "Ac"], ["Hechos", "Hch", "Hec"]),
    ("Rom", ["Romans", "Rom", "Ro", "Rm"], ["Romanos", "Rom", "Ro", "Rm"]),
    ("1Cor", ["1 Corinthians", "1 Cor", "1 Co"], ["1 Corintios", "1 Cor", "1 Co"]),
    ("2Cor", ["2 Corinthians", "2 Cor", "2 Co"], ["2 Corintios", "2 Cor", "2 Co"]),
    ("Gal", ["Galatians", "Gal", "Ga"], ["Gálatas", "Gál", "Ga"]),
    ("Eph", ["Ephesians", "Eph", "Ep"], ["Efesios", "Ef", "Efes"]),
    ("Phil", ["Philippians", "Phil", "Php", "Pp"], ["Filipenses", "Fil", "Flp"]),
    ("Col", ["Colossians", "Col"], ["Colosenses", "Col"]),
    ("1Thess", ["1 Thessalonians", "1 Thess", "1 Th"], ["1 Tesalonicenses", "1 Tes", "1 Ts"]),
    ("2Thess", ["2 Thessalonians", "2 Thess", "2 Th"], ["2 Tesalonicenses", "2 Tes", "2 Ts"]),
    ("1Tim", ["1 Timothy", "1 Tim", "1 Ti"], ["1 Timoteo", "1 Tim", "1 Ti", "1 Tm"]),
    ("2Tim", ["2 Timothy", "2 Tim", "2 Ti"], ["2 Timoteo", "2 Tim", "2 Ti", "2 Tm"]),
    ("Titus", ["Titus", "Tit"], ["Tito", "Tit"]),
    ("Phlm", ["Philemon", "Phlm", "Phm"], ["Filemón", "Flm", "Filem"]),
    ("Heb", ["Hebrews", "Heb"], ["Hebreos", "Heb", "Hb"]),
    ("Jas", ["James", "Jas", "Jm"], ["Santiago", "Sant", "Stg", "St"]),
    ("1Pet", ["1 Peter", "1 Pet", "1 Pe"], ["1 Pedro", "1 Ped", "1 Pe", "1 P"]),
    ("2Pet", ["2 Peter", "2 Pet", "2 Pe"], ["2 Pedro", "2 Ped", "2 Pe", "2 P"]),
    ("1John", ["1 John", "1 Jn", "1 Jo"], ["1 Juan", "1 Jn"]),
    ("2John", ["2 John", "2 Jn", "2 Jo"], ["2 Juan", "2 Jn"]),
    ("3John", ["3 John", "3 Jn", "3 Jo"], ["3 Juan", "3 Jn"]),
    ("Jude", ["Jude", "Jud"], ["Judas", "Jud", "Jds"]),
    ("Rev", ["Revelation", "Revelation of John", "Rev", "Re", "Apocalypse"], ["Apocalipsis", "Apoc", "Ap"]),
]

BOOKS = [t[0] for t in _TABLE]


def _key(s):
    s = unicodedata.normalize("NFD", s.casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)


def _build_aliases():
    out = {}
    for osis, en, es in _TABLE:
        for name in [osis] + en + es:
            k = _key(name)
            if out.setdefault(k, osis) != osis:
                raise RuntimeError(f"alias collision: {name!r}")
    return out


_ALIASES = _build_aliases()

_REF_RE = re.compile(
    r"^\s*(.+?)[\s.]*(\d+)(?:\s*[:.]\s*(\d+)(?:\s*[-–]\s*(\d+))?)?\s*$"
)


_ORDINALS = [
    ("primerade", "1"), ("segundade", "2"), ("tercerade", "3"),
    ("primero", "1"), ("primera", "1"), ("segundo", "2"), ("segunda", "2"),
    ("tercero", "3"), ("tercera", "3"), ("1st", "1"), ("2nd", "2"), ("3rd", "3"),
    ("first", "1"), ("second", "2"), ("third", "3"),
    ("iii", "3"), ("ii", "2"), ("i", "1"),
]


def _lookup(book_text):
    k = _key(book_text)
    if k in _ALIASES:
        return _ALIASES[k]
    # roman / ordinal prefixes: "I Juan", "Primera de Juan" (only after a direct miss)
    for prefix, n in _ORDINALS:
        if k.startswith(prefix):
            hit = _ALIASES.get(n + k[len(prefix):])
            if hit:
                return hit
    return None


def parse_ref(text):
    m = _REF_RE.match(text or "")
    if not m:
        raise RefError(f"cannot parse reference: {text!r}")
    book = _lookup(m.group(1))
    if book is None:
        raise RefError(f"unknown book: {m.group(1).strip()!r}")
    chap = int(m.group(2))
    verse = int(m.group(3)) if m.group(3) else None
    end = int(m.group(4)) if m.group(4) else None
    return Ref(book, chap, verse, end)


def to_osis(ref):
    s = f"{ref.book}.{ref.chapter}"
    if ref.verse is not None:
        s += f".{ref.verse}"
        if ref.verse_end is not None:
            s += f"-{ref.verse_end}"
    return s
