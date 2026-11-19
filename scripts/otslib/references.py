"""Read the machine-read tables and template frontmatter under references/ and templates/.

- tradition_terms(lang): left column of references/tradition-vocabulary.md for that language.
- contested_refs(): `ref` column of references/contested-readings.md (OSIS refs).
- template_sections(name, lang=None): `sections:` (or `sections_<lang>:`) list from templates/<name>.md frontmatter.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REFERENCES = ROOT / "references"
TEMPLATES = ROOT / "templates"


def _table(path: Path) -> list:
    """Rows of the first markdown table in a file, as dicts keyed by lower-cased header."""
    header, rows = None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if header:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
        elif not all(set(c) <= set("-: ") for c in cells):
            rows.append(dict(zip(header, cells)))
    return rows


def frontmatter(path: Path) -> dict:
    """Minimal `key: value` frontmatter between leading `---` lines. No YAML."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out = {}
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = _scalar(value)
    return out


def _scalar(value: str) -> str:
    """YAML-ish scalar: `"x"`/`'x'` -> x; plain `x # comment` -> x."""
    value = value.strip()
    if len(value) >= 2 and value[0] in "\"'":
        end = value.find(value[0], 1)
        if end > 0 and (end == len(value) - 1 or re.match(r"\s*(#.*)?$", value[end + 1:])):
            return value[1:end].strip()
    return re.sub(r"\s+#.*$", "", value).strip()


def tradition_terms(lang: str) -> set:
    return {r["term"].lower() for r in _table(REFERENCES / "tradition-vocabulary.md")
            if r.get("lang", "").lower() == lang.lower() and r.get("term")}


def contested_refs() -> set:
    return {r["ref"].strip("`") for r in _table(REFERENCES / "contested-readings.md") if r.get("ref")}


def template_sections(name: str, lang: str = None) -> list:
    """`sections:` of templates/<name>.md; with lang, `sections_<lang>:` if present (same order)."""
    fm = frontmatter(TEMPLATES / f"{name}.md")
    raw = (lang and fm.get(f"sections_{lang.lower()}")) or fm.get("sections", "")
    return [s.strip() for s in raw.split(",") if s.strip()]
