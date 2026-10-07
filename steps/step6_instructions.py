"""Part 6 — instructions: system prompt + AGENTS.md layering + update_plan."""
from __future__ import annotations

import os
import subprocess

SYSTEM = (
    "You are a coding agent. Use the tools, read before you edit, "
    "run the tests afterwards. Prefer apply_patch for edits."
)

MAX_AGENTS_BYTES = 32 * 1024


def git_root(start: str = ".") -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return os.path.abspath(start)


def load_agents_md(start: str = ".") -> str:
    """Walk git root -> cwd, join every AGENTS.md (deeper last), cap 32KB."""
    root = git_root(start)
    cur = os.path.abspath(start)
    chain = []
    while True:
        cand = os.path.join(cur, "AGENTS.md")
        if os.path.isfile(cand):
            chain.append(cand)
        if cur == root or cur == os.path.dirname(cur):
            break
        cur = os.path.dirname(cur)
    chain.reverse()
    text = ""
    for p in chain:
        with open(p) as f:
            text += f"\n# {p}\n" + f.read()
    return text[:MAX_AGENTS_BYTES]


def base_messages(task: str, workspace: str = ".") -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM}]
    agents = load_agents_md(workspace)
    if agents.strip():
        msgs.append({"role": "system", "content": f"Project instructions (AGENTS.md):\n{agents}"})
    msgs.append({"role": "user", "content": task})
    return msgs


# update_plan: at most one step in_progress at a time (Codex rule)
PLAN: list[dict] = []


def update_plan(steps: list[dict]) -> str:
    global PLAN
    n = sum(1 for s in steps if s.get("status") == "in_progress")
    if n > 1:
        return "error: at most one step may be in_progress"
    PLAN = steps
    return "\n".join(f"[{s.get('status')}] {s.get('name')}" for s in steps)
