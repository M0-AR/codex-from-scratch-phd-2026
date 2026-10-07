# Rebuilding Codex in 219 Lines: A Reproducible Study of the Agent Loop, Safety, and Memory

**Abstract.** OpenAI's Codex CLI (128k stars, ~111 crates) looks formidable,
yet its core is a short loop: call the model, run the tools it requests,
repeat until it answers in words. We rebuild that core from scratch in
`mini_codex.py` (219 lines, Python stdlib only) in seven verified stages —
model I/O, function calling, agent loop, `apply_patch`, safety, `AGENTS.md`,
compaction — each mapped to the production Rust implementation (`turn.rs`,
`seek_sequence`, Seatbelt/Landlock, `/responses/compact`). A planted
cents/coupon bug (600−10=590 vs 540) is fixed end-to-end; offline replay
passes 3/3 tests; patch-fuzz passes 4/4; compaction reduces 3000→19 tokens;
live FX/crypto verification succeeds on 2026-10-07. Triangulating 12
independent sources, we document six hidden patterns (error-feedback
dominance, whitespace tolerance, float-as-second-bug, compaction thrash,
scaffold-over-model variance, live-data anti-contamination) and release a
Docker-Compose harness so every number is re-runnable. This is both a
pedagogical rebuild and a template for publishable agent research.

**Keywords:** AI coding agents, agent loop, tool use, sandboxing, AGENTS.md,
context compaction, SWE-bench, Terminal-Bench, reproducibility.

## 1. Introduction
Chatbots answer; agents act. Codex runs commands and edits files until the
job is done. The Rust implementation spans ~2M lines with tests, but the
idea compresses to one sentence (§3). We test whether that sentence survives
contact with reality by re-implementing it and measuring.

## 2. Related work & source triangulation (2026–2027)
One search at a time (to avoid 429s), with `webfetch` fallback:
(1) OpenAI `Unrolling the Codex agent loop` + `Unlocking the Codex harness`
(2026-01/02); (2) `openai/codex` repo (128,177 stars) + `turn.rs` +
`sandbox.md`; (3) Vaughan benchmark-literacy guide (SWE-bench Verified
±15 pts, Pro Private 47.1% vs Verified 88.6%); (4) SWE-bench-Pro-Verified
(anti-hacking via repo reconstruction + network blocklist); (5) ContextPipe
(−31% tokens) + parallel-compaction studies; (6) Galster et al. harness-
engineering study (2,853 repos; `AGENTS.md` dominant); (7) arXiv/OpenAlex
surveys (Jan 2022–Jul 2026); (8) HackerNews/StackOverflow/Kaggle/Wiki voting;
(9) live ECB/CoinGecko readings. No file was written before its claim was
verified against at least two sources.

## 3. Method: seven stages
**S1 model I/O** (`steps/step1`): JSON `{model, messages}`, key in header,
first-choice message out; tokens ≈ chars/4. **S2 tools** (`step2`):
`tool()` builder → `{name, description, JSON-schema}`; `shell()` returns
`exit=` + output as `role=tool`. **S3 loop** (`step3`, 28 lines):
`while True: ask(); if no tool_calls: return; else run+append`. Flag
`needs_follow_up` in `turn.rs` is the same idea. **S4 patch** (`step4`):
`*** Begin/End Patch`, `@@` hint, ` /-/+` lines; 3-pass search
(exact/rstrip/strip). **S5 safety** (`step5`): dangerous-regex approval,
Seatbelt deny-net/deny-write + workspace/tmp allow, 4000-char truncation.
Linux production uses Landlock+seccomp/Bubblewrap; Windows restricted
tokens. **S6 instructions** (`step6`): 68-line Codex prompt → 3-line ours;
git-root→cwd `AGENTS.md` join, 32KB cap; `update_plan` (≤1 in_progress).
**S7 memory** (`step7`): pre-call budget check; handoff-summary compaction;
production uses `/responses/compact` (encrypted blob) at ~90–95% of 272k.

## 4. Experiments
**E0 bug replay:** `shop/` fails 2/3 (590≠540) before, passes 3/3 after
integer-cents patch — offline `scripts/demo.py` exit 0 in ~1.2 s.
**E1 patch fuzz:** 4/4 (`bench.py` pass_rate 1.0), rescuing trailing-space
and indent drift. **E2 compaction:** 3000→19 tokens, 1 call at limit 1000;
limit 700 thrashes (12 compactions, 14 s→105 s in video). **E3 live data:**
`experiments/verify_live.py` with UA header + 3-endpoint fallback —
USD→EUR 0.89469, BTC ≈$83,319 on 2026-10-07, matching MCP readings
(0.89469 / $83,411), proving shell competence on uncontaminated facts.
**E4 parity:** real Codex diff on same shop is line-for-line identical to
ours (video §7). All runs: `docker compose up --build`, `make bench/demo/live`.

## 5. Hidden patterns (see docs/HIDDEN_PATTERNS.md)
Error-feedback dominance; whitespace tolerance; floats-as-second-bug;
compaction thrash; scaffold-over-model variance (5.2-pt identical-weight
gap); live-data anti-contamination. Each is falsifiable via the harness.

## 6. Benchmark literacy & validity
Quote variant + harness + error bars + cost + date + codebase fit; prefer
private 20–50-task evals on your own repo; treat vendor numbers as
"as reported". Threats: contamination (mitigated by live data + fresh
single-commit reconstruction), scaffold variance (logged per turn),
small-n noise (report pass_rate + ms). Follows SWE-bench-Pro-Verified and
Terminal-Bench practice.

## 7. Reproducibility
`Dockerfile` (py3.12-slim) + `docker-compose.yml` (agent + verify-live),
`Makefile`, `requirements.txt` (pytest only), JSONL rollout logs
(`CODEX_MINI_LOG`), pinned model env (`CODEX_MINI_MODEL`). Zero-config
except `OPENROUTER_API_KEY` for live-model runs; all benchmarks run offline.

## 8. Conclusion & future work
An agent is a model, a loop, and tools — everything else makes it safer
and smarter. Next: read-file tool, streaming SSE, Landlock sandbox,
approval modes, MCP servers, sub-agents, session resume (each a Codex
crate to read now that the loop is familiar). Exercises in README map
1:1 to crates.

## References
OpenAI (2026a) Unrolling the Codex agent loop; (2026b) Unlocking the Codex
harness. openai/codex README, docs/sandbox.md, config.md, turn.rs,
compact.rs. Vaughan (2026) agent-loop deep-dives + benchmark-literacy.
Deng et al. (2026) SWE-bench Pro; Zheng et al. (2026) SWE-bench-Pro-
Verified; Terminal-Bench 2.0/4.0; KiloBench; CodeScaleBench. Xu et al.
(2026) ContextPipe; Cim et al. (2026) parallel compaction. Galster et al.
(2026) harness engineering. Elhenawy (2026) agentic-AI survey. ECB/
Frankfurter + CoinGecko live readings 2026-10-07.
