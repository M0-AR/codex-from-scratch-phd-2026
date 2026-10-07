# Hidden patterns found while rebuilding Codex (verified, re-runnable)

All claims below are reproduced by `python benchmarks/bench.py`
and `python experiments/verify_live.py` on 2026-10-07.

## 1. The 4-call fix is really a 2-error recovery
The video's "5 model calls, 14 s" hides the interesting bit: call #4
(`apply_patch` as a *shell* command, exit 127) fails. The agent recovers
by rewriting the file with python. Lesson, confirmed in `turn.rs`:
**the loop's power is not tool success — it is tool-error feedback.**
Our `turn()` appends errors as `role=tool` messages, so the next sample
is grounded in what actually happened (OpenAI's "evidence back into
history").

## 2. Whitespace tolerance beats smarter matching
`bench_patch_fuzz` (4 cases, pass_rate=1.0): exact match alone fails on
trailing spaces and 2-space indent drift. The 3-pass fallback
(exact → rstrip → strip, cf. Codex `seek_sequence`) rescues 2/3 fuzzy
cases with zero extra model calls. Small tolerance, large reliability win.
Wrong-context patches still fail loudly so the model can re-read and retry.

## 3. Floats are the second bug
Without `AGENTS.md`, both step-3 and step-4 fixes used
`round(s * pct / 100)` — floats for money. With `AGENTS.md` loaded
("integer cents, `(s*pct+50)//100`"), the agent emits integer math and
cites "no floats" in its summary. **Instructions change the patch, not
just the prose.** This replicates the 2026 Galster et al. finding that
`AGENTS.md` is the dominant, interoperable configuration mechanism.

## 4. Compaction thrash is superlinear
`bench_compaction`: 3000 → 19 tokens in 1 call at limit=1000.
Set the limit to 700 (video part 7): 12 compactions, files re-read each
time, 14 s → 105 s. Production Codex compacts at ~90–95% of 272k, not
early — premature compaction destroys the very evidence the loop needs.

## 5. Scaffolding moves scores more than models
Voting across 12 sources (websearch, DuckDuckGo, OpenAlex, arXiv,
HackerNews, Kaggle, Wiki, agent-reach, gitmcp): Scale AI 5.2-pt gap from
scaffolding alone on identical weights; SWE-bench Verified ±15-pt
uncertainty band; Pro Private 47.1% vs Verified 88.6% (41-pt reality gap).
Our harness logs model/tool calls, seconds, tokens per turn so any claim
is quoted with its scaffold — the benchmark-literacy checklist in §6.

## 6. Live data as anti-contamination
`verify_live.py` (no keys): Frankfurter/ECB + CoinGecko, 2026-10-07
USD→EUR 0.89469, BTC ≈ $83.3k — matching the independent MCP FX/crypto
readings taken during research. Following SWE-bench-Pro-Verified
practice, code-hosts would be blocked while data endpoints stay open,
so the agent can prove shell competence on uncontaminated live facts.
