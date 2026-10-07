"""Part 7 — memory: compaction when conversation exceeds token budget.

Counts tokens ~4 chars each. Before every model call, if over limit,
summarize via the model (Codex compaction prompt style) and keep
system + instructions + summary. Production Codex compacts at ~90-95%
of 272k window via /responses/compact with encrypted blob.
"""
from __future__ import annotations

COMPACT_PROMPT = (
    "You are performing a context checkpoint compaction. "
    "Write a handoff summary: bug, evidence, fix applied, test status, "
    "and exact next step. Start with 'handoff summary'."
)


def convo_tokens(messages: list[dict]) -> int:
    return sum(len(str(m.get("content") or "")) // 4 for m in messages) + sum(
        len(str((tc or {}).get("function", {}).get("arguments", ""))) // 4
        for m in messages for tc in (m.get("tool_calls") or []))


def maybe_compact(messages: list[dict], ask_fn, limit: int = 60000) -> list[dict]:
    """If over limit, replace middle with model-written summary. Returns new list."""
    if convo_tokens(messages) <= limit:
        return messages
    keep_head = [m for m in messages if m.get("role") == "system"]
    summary = ask_fn(
        messages + [{"role": "user", "content": COMPACT_PROMPT}]) .get("content", "")
    compacted = keep_head + [
        {"role": "user", "content": f"handoff summary (prior work compacted):\n{summary}"}]
    print(f"[compacted {convo_tokens(messages)} -> {convo_tokens(compacted)} tokens]")
    return compacted
