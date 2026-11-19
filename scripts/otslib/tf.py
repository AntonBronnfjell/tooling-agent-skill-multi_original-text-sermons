"""Minimal Text-Fabric (.tf) reader: node features and the oslots edge, plain or xz-compressed."""
import lzma
from pathlib import Path


def _lines(path):
    path = Path(path)
    opener = lzma.open if path.suffix == ".xz" else open
    with opener(path, "rt", encoding="utf-8-sig") as f:
        it = iter(f)
        for line in it:  # header: `@...` lines up to the first blank line
            if not line.rstrip("\r\n"):
                break
        for line in it:
            yield line.rstrip("\r\n")


def parse_spec(spec):
    """'1-5,8' -> [1, 2, 3, 4, 5, 8]."""
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        a, sep, b = part.partition("-")
        if sep:
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(a))
    return out


def read_feature(path):
    """-> {node: value}. A line is `value` (node = previous node + 1) or `nodespec<TAB>value`
    where nodespec is a node, a range `a-b` or a list `1-5,8`; the value then applies to all of them."""
    out = {}
    nxt = 1
    for line in _lines(path):
        spec, tab, value = line.partition("\t")
        if tab:
            nodes = parse_spec(spec)
        else:
            nodes, value = [nxt], line
        for n in nodes:
            out[n] = value
        if nodes:
            nxt = nodes[-1] + 1
    return out


def read_oslots(path, nodes=None):
    """-> {node: [slot, ...]} from an `@edge` oslots file; lines are `slotspec` (node = previous + 1)
    or `nodespec<TAB>slotspec`. `nodes` (a container) restricts which nodes are kept (speed/memory)."""
    out = {}
    nxt = 1
    for line in _lines(path):
        spec, tab, slots = line.partition("\t")
        if tab:
            ns = parse_spec(spec)
        else:
            ns, slots = [nxt], line
        for n in ns:
            if nodes is None or n in nodes:
                out[n] = parse_spec(slots)
        if ns:
            nxt = ns[-1] + 1
    return out
