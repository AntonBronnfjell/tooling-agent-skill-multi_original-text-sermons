#!/usr/bin/env bash
# Refresh vendored sources from sources/MANIFEST.json (maintenance only).
#
#   fetch_sources.sh          download every "vendored" entry at its pinned URL,
#                             extract (zip member) if needed, xz-compress into
#                             sources/<path>, and record hashes/size in MANIFEST.
#   fetch_sources.sh --check  verify sha256 of the vendored .xz files only
#                             (no network). Prints "OK <path>" per file and
#                             exits non-zero on any mismatch or missing file.
#
# Entries whose status is not "vendored" (deferred, omitted) are skipped.
# If an entry already records upstream_sha256 and the download differs, the
# entry is left untouched and the run fails (the pin no longer reproduces).
# A download that is a Git LFS pointer, or smaller than the entry's optional
# "min_bytes", is rejected before anything is written.
#
# SOURCES_MANIFEST=<file> overrides the manifest path (used for testing).
# Both modes fail closed if the manifest cannot be read or lists no vendored
# entries.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/sources"
MANIFEST="${SOURCES_MANIFEST:-$SRC/MANIFEST.json}"
MAX_BYTES=$((100 * 1024 * 1024))

mode=fetch
case "${1:-}" in
  --check) mode=check ;;
  "") ;;
  *) echo "usage: $0 [--check]" >&2; exit 2 ;;
esac

sha256() { shasum -a 256 "$1" | cut -d' ' -f1; }

# Fields separated by \x1f (a non-whitespace IFS keeps empty fields):
#   path url extract upstream_sha256 sha256 min_bytes
entries() {
  python3 -I -c '
import json, sys
for e in json.load(open(sys.argv[1], encoding="utf-8"))["entries"]:
    if e.get("status") != "vendored":
        continue
    print("\x1f".join([e["path"], e["url"], e.get("extract", ""),
                     e.get("upstream_sha256", ""), e.get("sha256", ""),
                     str(e.get("min_bytes", 0))]))
' "$MANIFEST"
}

# Read the manifest up front (a failure inside "< <(...)" would be ignored).
if ! list="$(entries)"; then
  echo "ERROR: cannot read entries from $MANIFEST" >&2; exit 1
fi
if [[ -z $list ]]; then
  echo "ERROR: no vendored entries in $MANIFEST" >&2; exit 1
fi

fail=0

if [[ $mode == check ]]; then
  while IFS=$'\x1f' read -r path url extract up_sha sha min_bytes; do
    f="$SRC/$path"
    if [[ ! -f $f ]]; then
      echo "MISSING $path"; fail=1
    elif [[ -z $sha ]]; then
      echo "NOHASH $path"; fail=1
    elif [[ $(sha256 "$f") != "$sha" ]]; then
      echo "MISMATCH $path"; fail=1
    else
      echo "OK $path"
    fi
  done <<< "$list"
  exit $fail
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
results="$tmp/results.tsv"
: > "$results"

while IFS=$'\x1f' read -r path url extract up_sha sha min_bytes; do
  dl="$tmp/download"
  if ! curl -fsSL --retry 3 -o "$dl" "$url"; then
    echo "FAILED download $path ($url)" >&2; fail=1; continue
  fi
  got_up="$(sha256 "$dl")"
  if [[ -n $up_sha && $got_up != "$up_sha" ]]; then
    echo "UPSTREAM CHANGED $path (expected $up_sha, got $got_up)" >&2; fail=1; continue
  fi
  raw="$dl"
  if [[ -n $extract ]]; then
    raw="$tmp/raw"
    unzip -p "$dl" "$extract" > "$raw"
  fi
  if [[ "$(head -c 64 "$raw")" == "version https://git-lfs.github.com/spec"* ]]; then
    echo "LFS POINTER $path: got a Git LFS pointer instead of the file ($url)" >&2; fail=1; continue
  fi
  raw_size=$(wc -c < "$raw" | tr -d ' ')
  if (( raw_size < ${min_bytes:-0} )); then
    echo "TOO SMALL $path ($raw_size bytes < min_bytes $min_bytes)" >&2; fail=1; continue
  fi
  dest="$SRC/$path"
  mkdir -p "$(dirname "$dest")"
  xz -9 -T1 -c "$raw" > "$dest.tmp"
  mv "$dest.tmp" "$dest"
  size=$(wc -c < "$dest" | tr -d ' ')
  if (( size >= MAX_BYTES )); then
    echo "TOO BIG $path ($size bytes): split it by book range" >&2; fail=1
  fi
  printf '%s\t%s\t%s\t%s\t%s\n' "$path" "$got_up" "$(sha256 "$raw")" "$(sha256 "$dest")" "$size" >> "$results"
  echo "FETCHED $path ($size bytes)"
done <<< "$list"

python3 -I -c '
import json, sys
manifest, results = sys.argv[1], sys.argv[2]
data = json.load(open(manifest, encoding="utf-8"))
rows = {}
for line in open(results, encoding="utf-8"):
    path, up, raw, sha, size = line.rstrip("\n").split("\t")
    rows[path] = (up, raw, sha, int(size))
for e in data["entries"]:
    if e["path"] in rows:
        e["upstream_sha256"], e["raw_sha256"], e["sha256"], e["bytes"] = rows[e["path"]]
with open(manifest, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
' "$MANIFEST" "$results"

total=$(du -sk "$SRC" | cut -f1)
echo "sources/ total: $((total / 1024)) MB"
if (( total >= 500 * 1024 )); then
  echo "sources/ exceeds 500 MB" >&2; fail=1
fi
exit $fail
