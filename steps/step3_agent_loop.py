"""Part 3 — the agent loop (heart of Codex, cf. turn.rs / run_turn).

Call model, run tools it asks for, repeat until it answers in words.
"""
from __future__ import annotations

from step1_talk_to_model import ask
from step2_one_tool import TOOLS, run_shell


def agent_loop(task: str, max_rounds: int = 25) -> str:
    messages: list[dict] = [
        {"role": "system", "content": "Use the tools, read before you edit, run tests afterwards."},
        {"role": "user", "content": task},
    ]
    for _ in range(max_rounds):
        import json as _j

        reply = ask(messages, TOOLS)
        messages.append(reply)
        calls = reply.get("tool_calls") or []
        if not calls:  # needs_follow_up == false -> turn ends
            print(reply.get("content"))
            return reply.get("content") or ""
        for tc in calls:
            args = _j.loads(tc["function"]["arguments"] or "{}")
            out = run_shell(args.get("command", ""))
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
    return ""


if __name__ == "__main__":
    agent_loop("The tests fail, find the bug and fix it.")
