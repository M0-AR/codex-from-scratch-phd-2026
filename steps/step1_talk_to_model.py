"""Part 1 — talk to a model (OpenRouter / OpenAI-compatible chat completions).

Verified against: OpenAI 'Unrolling the Codex agent loop' (2026-01-23),
openai/codex README, Responses API docs. Uses only stdlib.
"""
from __future__ import annotations

import json
import os
import urllib.request

API_URL = os.environ.get(
    "CODEX_MINI_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"
)
MODEL = os.environ.get("CODEX_MINI_MODEL", "openai/gpt-5.3-codex")
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

SYSTEM = "You are a helpful coding assistant."

# rough token estimate: ~4 chars per token (used later for compaction)
def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def ask(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """POST one chat-completions request, return the first choice message."""
    body: dict = {"model": MODEL, "messages": messages}
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "HTTP-Referer": "https://github.com/mini-codex-phd",
            "X-Title": "mini-codex-phd-step1",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        payload = json.loads(r.read().decode())
    msg = payload["choices"][0]["message"]
    # normalize: ensure keys exist
    msg.setdefault("content", None)
    msg.setdefault("tool_calls", None)
    usage = payload.get("usage", {})
    print(f"[tokens in={usage.get('prompt_tokens', '?')} out={usage.get('completion_tokens', '?')}]")
    return msg


if __name__ == "__main__":
    print(ask([
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "Do the tests in my current folder pass?"},
    ]).get("content"))
