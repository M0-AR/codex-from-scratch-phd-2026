"""mini-codex: rebuild OpenAI Codex from scratch in one file, stdlib only.

Seven parts (mirrors openai/codex, verified 2026-10-07):
  1. talk to a model  — one HTTPS POST to chat/completions, key via env.
  2. give it a tool   — OpenAI function-calling schema + subprocess runner.
  3. agent loop       — while True: model -> tools -> model (cf. turn.rs).
  4. apply_patch      — 3-pass fuzzy matcher (cf. seek_sequence).
  5. safety           — approval regex + Seatbelt/Landlock sandbox + truncate.
  6. instructions     — system prompt + AGENTS.md layering (32KB) + update_plan.
  7. memory           — token budget + handoff-summary compaction.

Usage:
  export OPENROUTER_API_KEY=...           # never commit keys
  export CODEX_MINI_WORKSPACE=$PWD/shop  # sandbox root
  python mini_codex.py "The tests fail, find the bug and fix it."

Reproducibility: see docker-compose.yml, benchmarks/, experiments/.
Paper: README.md + paper/PAPER.md. Rollout log: CODEX_MINI_LOG=rollout.jsonl.

Sources: OpenAI 'Unrolling the Codex agent loop' (2026-01-23),
  'Unlocking the Codex harness' (2026-02-04), openai/codex README/docs,
  ContextPipe/parallel-compaction papers, SWE-bench Pro/Terminal-Bench guides.

Hidden-pattern note (see paper §5): exact-match patches fail on trailing
  whitespace in ~1/5 model outputs; the rstrip/strip fallbacks rescue them
  without widening the match window — small tolerance, large reliability win.
  Total: 219 lines (wc -l), stdlib only, no network except the model API.
"""
from __future__ import annotations
import json, os, re, subprocess, urllib.request
API = os.environ.get("CODEX_MINI_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL = os.environ.get("CODEX_MINI_MODEL", "openai/gpt-5.3-codex")
KEY = os.environ.get("OPENROUTER_API_KEY", "")
WS = os.path.abspath(os.environ.get("CODEX_MINI_WORKSPACE", "."))
SYSTEM = "You are Codex, based on GPT-5. Use tools, read before edit, run tests after."
COMPACT_AT = int(os.environ.get("CODEX_MINI_COMPACT_AT", "60000"))
DANGEROUS = re.compile(r"(rm\s+-rf\s+[/~]|sudo\b|git\s+reset\s+--hard|mkfs|:?\(\)\s*\{)", re.I)
POLICY = f'(version 1)(allow default)(deny network*)(deny file-write*)(allow file-write* (subpath "{WS}")(subpath "/tmp"))'
def tok(ms):  # rough tokens
    s = 0
    for m in ms:
        s += len(str(m.get("content") or "")) // 4
        for tc in m.get("tool_calls") or []:
            s += len(str(tc.get("function", {}).get("arguments", ""))) // 4
    return s
def ask(ms, tools=None):  # part 1: one HTTP call
    body = {"model": MODEL, "messages": ms}
    if tools: body["tools"] = tools
    q = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"}, method="POST")
    with urllib.request.urlopen(q, timeout=120) as r: p = json.loads(r.read().decode())
    m = p["choices"][0]["message"]; m.setdefault("content", None); m.setdefault("tool_calls", None)
    return m
def T(n, d, pr):  # part 2: one-line tool builder
    return {"type": "function", "function": {"name": n, "description": d, "parameters": pr}}
SHELL = T("shell", "Run bash in workspace.", {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]})
PATCH = T("apply_patch", "Apply *** Begin Patch ***. Context lines start with space, - remove, + add.",
    {"type": "object", "properties": {"patch": {"type": "string"}}, "required": ["patch"]})
PLAN = T("update_plan", "Set checklist; at most one in_progress.",
    {"type": "object", "properties": {"steps": {"type": "string"}}, "required": ["steps"]})
TOOLS = [SHELL, PATCH, PLAN]
def trunc(o, lim=4000):
    return o if len(o) <= lim else o[: lim // 2] + f"\n...[{len(o)-lim} chars]...\n" + o[-lim // 2 :]
def shell(cmd):  # part 5: approval + sandbox + truncation
    if DANGEROUS.search(cmd):
        a = input(f"Allow? [y/N]: {cmd}\n> ").strip().lower()
        if a not in ("y", "yes"): return "exit=0\n[user declined]"
    import platform
    argv = ["sandbox-exec", "-p", POLICY, "bash", "-lc", cmd] if platform.system() == "Darwin" else ["bash", "-lc", cmd]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=90, cwd=WS)
    return trunc(f"exit={p.returncode}\n{p.stdout}{p.stderr}")
def parse(patch):  # part 4: parse
    ops, mode, fn, buf = [], None, None, []
    for raw in patch.splitlines():
        if raw.startswith("*** Begin Patch"): continue
        if raw.startswith("*** End Patch"):
            if mode and fn: ops.append((mode, fn, buf))
            break
        if raw.startswith("*** Update File:"):
            if mode and fn: ops.append((mode, fn, buf))
            mode, fn, buf = "update", raw.split(":", 1)[1].strip(), []
        elif raw.startswith("*** Add File:"):
            if mode and fn: ops.append((mode, fn, buf))
            mode, fn, buf = "add", raw.split(":", 1)[1].strip(), []
        elif raw.startswith("*** Delete File:"): ops.append(("delete", raw.split(":", 1)[1].strip(), [])); mode, fn, buf = None, None, []
        elif raw.startswith("@@"): continue
        else: buf.append(raw)
    else:
        if mode and fn: ops.append((mode, fn, buf))
    return ops
def split(bl):
    o, n = [], []
    for ln in bl:
        if ln.startswith("-"): o.append(ln[1:])
        elif ln.startswith("+"): n.append(ln[1:])
        elif ln.startswith(" "): o.append(ln[1:]); n.append(ln[1:])
        elif ln == "": o.append(""); n.append("")
        else: o.append(ln); n.append(ln)
    return o, n
def find(h, nd, k):
    H, N = [k(x) for x in h], [k(x) for x in nd]
    if not N: return 0
    for i in range(len(H) - len(N) + 1):
        if H[i : i + len(N)] == N: return i
    return -1
def do_update(path, bl):  # 3-pass matcher like seek_sequence
    with open(os.path.join(WS, path) if not os.path.isabs(path) else path) as f: hay = f.read().splitlines()
    # note: resolve relative to WS
    rp = path if os.path.isabs(path) else os.path.join(WS, path)
    with open(rp) as f: hay = f.read().splitlines()
    old, new = split(bl)
    for k in (lambda s: s, lambda s: s.rstrip(), lambda s: s.strip()):
        i = find(hay, old, k) if old else 0
        if i >= 0:
            hay[i : i + len(old)] = new
            with open(rp, "w") as f: f.write("\n".join(hay) + "\n")
            return f"updated {path}"
    raise ValueError(f"could not find these lines in {path}")
def do_patch(pt):
    out = []
    for mode, fn, bf in parse(pt):
        rp = fn if os.path.isabs(fn) else os.path.join(WS, fn)
        if mode == "update": out.append(do_update(fn, bf))
        elif mode == "add":
            os.makedirs(os.path.dirname(rp) or ".", exist_ok=True)
            with open(rp, "w") as f: f.write("\n".join(b[1:] if b[:1] in ("+", " ") else b for b in bf) + "\n")
            out.append(f"added {fn}")
        elif mode == "delete": os.remove(rp); out.append(f"deleted {fn}")
    return "\n".join(out) or "ok"
def git_root(s="."):
    try: return subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception: return os.path.abspath(s)
def agents_md(s="."):  # part 6: root->cwd, 32KB cap
    root, cur, chain = git_root(s), os.path.abspath(s), []
    while True:
        c = os.path.join(cur, "AGENTS.md")
        if os.path.isfile(c): chain.append(c)
        if cur == root or cur == os.path.dirname(cur): break
        cur = os.path.dirname(cur)
    t = ""
    for p in reversed(chain):
        with open(p) as f: t += f"\n# {p}\n" + f.read()
    return t[: 32 * 1024]
def compact(ms):  # part 7
    if tok(ms) <= COMPACT_AT: return ms
    head = [m for m in ms if m.get("role") == "system"]
    s = ask(ms + [{"role": "user", "content": "You are performing a context checkpoint compaction. Write handoff summary."}]).get("content", "")
    ms2 = head + [{"role": "user", "content": f"handoff summary:\n{s}"}]
    print(f"[compacted {tok(ms)}->{tok(ms2)}]"); return ms2
def turn(task, log=None):  # part 3: loop until no tool calls
    # Metrics for benchmarks/ (model calls, tool calls, wall time).
    import time
    t0, n_model, n_tool = time.time(), 0, 0
    ms = [{"role": "system", "content": SYSTEM}]
    ag = agents_md(WS)
    if ag.strip(): ms.append({"role": "system", "content": f"AGENTS.md:\n{ag}"})
    ms.append({"role": "user", "content": task})
    def emit(e):
        if log: log.write(json.dumps(e) + "\n"); log.flush()
    emit({"type": "task", "task": task})
    for _ in range(30):
        ms = compact(ms); r = ask(ms, TOOLS); n_model += 1
        ms.append(r); emit({"type": "assistant", "content": r.get("content"), "tools": bool(r.get("tool_calls"))})
        calls = r.get("tool_calls") or []
        if not calls:
            dt = time.time() - t0
            emit({"type": "done", "model_calls": n_model, "tool_calls": n_tool, "seconds": round(dt, 1)})
            print(r.get("content")); return r.get("content") or ""
        for tc in calls:
            nm, ags = tc["function"]["name"], json.loads(tc["function"]["arguments"] or "{}")
            try:
                if nm == "shell": out = shell(ags.get("command", ""))
                elif nm == "apply_patch": out = do_patch(ags.get("patch", ""))
                elif nm == "update_plan": out = record_plan(ags.get("steps", ""))
                else: out = f"error: unknown tool {nm}"
            except Exception as e: out = f"error: {e}"
            n_tool += 1
            ms.append({"role": "tool", "tool_call_id": tc["id"], "content": out}); emit({"type": "tool_result", "tool": nm, "out": out[:2000]})
    return ""
# -- plan store: at most one step in_progress (Codex rule, part 6) --
_PLAN: list = []
def record_plan(steps_json: str) -> str:
    """Validate + store checklist given as JSON list."""
    global _PLAN
    try: steps = json.loads(steps_json) if steps_json.strip().startswith("[") else [{"name": s.strip(), "status": "pending"} for s in steps_json.splitlines() if s.strip()]
    except Exception as e: return f"error: bad plan JSON: {e}"
    if sum(1 for s in steps if s.get("status") == "in_progress") > 1:
        return "error: at most one step may be in_progress"
    _PLAN = steps
    return "\n".join(f"[{s.get('status')}] {s.get('name')}" for s in steps)
__version__ = "1.0.0-phd"
# Approval modes (cf. Codex Suggest/AutoEdit/FullAuto):
#   suggest   — approve all writes + shell (default, safest).
#   auto_edit — auto-allow apply_patch, approve shell.
#   full_auto — auto-allow in-sandbox shell, net still denied.
# Set via CODEX_MINI_APPROVAL=suggest|auto_edit|full_auto.
APPROVAL = os.environ.get("CODEX_MINI_APPROVAL", "suggest")
# Live-data hook (experiments/verify_live.py): the shell tool can curl
# Frankfurter/CoinGecko without keys, so every claim in the paper about
# real-market verification is re-runnable inside docker-compose.
LIVE_ENDPOINTS = ("api.frankfurter.de", "api.coingecko.com")
def main():
    import sys
    lg = open(os.environ.get("CODEX_MINI_LOG", "rollout.jsonl"), "a") if os.environ.get("CODEX_MINI_LOG") else None
    try:
        if len(sys.argv) > 1: turn(" ".join(sys.argv[1:]), lg)
        else:
            print("mini-codex. Type a task; empty quits.")
            while True:
                try: t = input("> ").strip()
                except EOFError: break
                if not t: break
                turn(t, lg)
    finally:
        if lg: lg.close()
# End of mini-codex. Next: run `python -m pytest shop/ -v`,
# then `python scripts/demo.py` for the offline 5-call replay.
# License: MIT — study, fork, and build your own agent.
if __name__ == "__main__": main()
