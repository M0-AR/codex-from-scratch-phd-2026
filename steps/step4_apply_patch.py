"""Part 4 — edit files with patches (cf. Codex seek_sequence, 3-pass matcher)."""
from __future__ import annotations


def parse_patch(patch_text: str) -> list[tuple[str, str, list[str]]]:
    """Parse '*** Begin Patch / *** Update File: f / @@ hint / lines / *** End Patch'."""
    ops: list[tuple[str, str, list[str]]] = []
    mode = fname = None
    buf: list[str] = []
    for raw in patch_text.splitlines():
        if raw.startswith("*** Begin Patch"):
            continue
        if raw.startswith("*** End Patch"):
            if mode and fname:
                ops.append((mode, fname, buf))
            break
        if raw.startswith("*** Update File:"):
            if mode and fname:
                ops.append((mode, fname, buf))
            mode, fname, buf = "update", raw.split(":", 1)[1].strip(), []
        elif raw.startswith("*** Add File:"):
            if mode and fname:
                ops.append((mode, fname, buf))
            mode, fname, buf = "add", raw.split(":", 1)[1].strip(), []
        elif raw.startswith("*** Delete File:"):
            ops.append(("delete", raw.split(":", 1)[1].strip(), []))
            mode = fname = None
            buf = []
        elif raw.startswith("@@"):
            continue
        else:
            buf.append(raw)
    else:
        if mode and fname:
            ops.append((mode, fname, buf))
    return ops


def _split(lines: list[str]):
    old, new = [], []
    for ln in lines:
        if ln.startswith("-"):
            old.append(ln[1:])
        elif ln.startswith("+"):
            new.append(ln[1:])
        elif ln.startswith(" "):
            old.append(ln[1:])
            new.append(ln[1:])
        elif ln == "":
            old.append("")
            new.append("")
        else:  # tolerate missing prefix: treat as context
            old.append(ln)
            new.append(ln)
    return old, new


def _find(hay: list[str], needle: list[str], key) -> int:
    H = [key(x) for x in hay]
    N = [key(x) for x in needle]
    n = len(N)
    if n == 0:
        return 0
    for i in range(len(H) - n + 1):
        if H[i : i + n] == N:
            return i
    return -1


def apply_update(path: str, lines: list[str]) -> None:
    with open(path) as f:
        hay = f.read().splitlines()
    old, new = _split(lines)
    for key in (lambda s: s, lambda s: s.rstrip(), lambda s: s.strip()):
        i = _find(hay, old, key) if old else 0
        if i >= 0:
            hay[i : i + len(old)] = new
            with open(path, "w") as f:
                f.write("\n".join(hay) + "\n")
            return
    raise ValueError(f"could not find these lines in {path}:\n" + "\n".join(old))


def apply_patch(patch_text: str) -> str:
    out = []
    for mode, fname, buf in parse_patch(patch_text):
        if mode == "update":
            apply_update(fname, buf)
            out.append(f"updated {fname}")
        elif mode == "add":
            with open(fname, "w") as f:
                f.write("\n".join([b[1:] if b.startswith(("+", " ")) else b for b in buf]) + "\n")
            out.append(f"added {fname}")
        elif mode == "delete":
            import os

            os.remove(fname)
            out.append(f"deleted {fname}")
    return "\n".join(out) or "ok"
