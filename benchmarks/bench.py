"""Benchmark harness: offline replay + patch-matcher stress + compaction demo.

No API key needed. Live-model runs append JSONL via CODEX_MINI_LOG.
Metrics follow Terminal-Bench/SWE-bench-Pro-Verified practice:
pass@1, wall seconds, model/tool calls, tokens (est. 4 chars/token).
"""
from __future__ import annotations
import json, sys, time
sys.path.insert(0, ".")
from steps.step4_apply_patch import apply_update
from steps.step7_memory import convo_tokens, maybe_compact

def bench_patch_fuzz() -> dict:
    import tempfile, os
    base = "def total(s, pct):\n    discount = pct\n    return s - discount\n"
    cases = [
        ("exact", "    discount = pct\n", "    discount = s * pct // 100\n", True),
        ("trailing-spaces", "    discount = pct   \n", "    discount = s * pct // 100\n", True),
        ("indented", "      discount = pct\n", "    discount = s * pct // 100\n", True),
        ("wrong-context", "    nonsense = 1\n", "    x = 2\n", False),
    ]
    res = []
    for name, old, new, should_pass in cases:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(base); path = f.name
        patch = f"*** Begin Patch ***\n*** Update File: {path}\n@@ total\n def total(s, pct):\n-{old.strip()}\n+{new.strip()}\n     return s - discount\n*** End Patch ***"
        # build with proper prefixes
        lines = [f" def total(s, pct):", f"-{old.strip()}", f"+{new.strip()}", "     return s - discount"]
        t0 = time.time()
        try:
            apply_update(path, lines); ok = True
        except Exception: ok = False
        res.append({"case": name, "ok": ok, "expected": should_pass,
                    "pass": ok == should_pass, "ms": round((time.time()-t0)*1000, 1)})
        os.unlink(path)
    return {"patch_fuzz": res, "pass_rate": sum(r["pass"] for r in res)/len(res)}

def bench_compaction() -> dict:
    msgs = [{"role": "system", "content": "sys"}] + [
        {"role": "user", "content": "x"*400} for _ in range(30)]
    before = convo_tokens(msgs)
    calls = {"n": 0}
    def fake_ask(ms): calls["n"] += 1; return {"content": "handoff summary: bug fixed, tests pass."}
    out = maybe_compact(msgs, fake_ask, limit=1000)
    return {"tokens_before": before, "tokens_after": convo_tokens(out), "model_calls": calls["n"]}

if __name__ == "__main__":
    print(json.dumps({"patch": bench_patch_fuzz(), "compaction": bench_compaction()}, indent=2))
