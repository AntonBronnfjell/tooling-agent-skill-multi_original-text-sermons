"""Read the machine-read tables and template frontmatter under references/ and templates/.

- tradition_terms(lang): left column of references/tradition-vocabulary.md for that language.
- contested_refs(): `ref` column of references/contested-readings.md (OSIS refs).
- template_sections(name): `sections:` list from templates/<name>.md frontmatter.
"""
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
            out[key.strip()] = value.strip()
    return out


def tradition_terms(lang: str) -> set:
    return {r["term"].lower() for r in _table(REFERENCES / "tradition-vocabulary.md")
            if r.get("lang", "").lower() == lang.lower() and r.get("term")}


def contested_refs() -> set:
    return {r["ref"].strip("`") for r in _table(REFERENCES / "contested-readings.md") if r.get("ref")}


def template_sections(name: str) -> list:
    raw = frontmatter(TEMPLATES / f"{name}.md").get("sections", "")
    return [s.strip() for s in raw.split(",") if s.strip()]
