# User translations (local, gitignored)

Drop your own comparison translations here as `*.csv`; `scripts/build_db.py` loads them into the
`translations` table next to the vendored ones. Everything in this directory except this README is
gitignored, so licensed texts never get committed.

Format:

```
# version=RVR1960 lang=es
ref,text
Juan 1:1,"En el principio era el Verbo, y el Verbo era con Dios, y el Verbo era Dios."
John.3.16,"Porque de tal manera amó Dios al mundo..."
```

- Line 1: `# version=NAME lang=xx` (required; `NAME` becomes the version label, `xx` the language code).
- Line 2: header `ref,text`.
- Then one verse per row. `ref` may be any form the reference parser accepts (OSIS `John.1.1`,
  English or Spanish names and abbreviations, `Jn 1:1`, `Juan 1:1`). Use KJV/English versification.
- Standard CSV quoting: wrap texts containing commas or quotes in double quotes, doubling inner quotes.
- Rows with an unparseable reference are skipped; the build reports the count and the first few.
