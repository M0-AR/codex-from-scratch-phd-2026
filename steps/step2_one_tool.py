"""Part 2 — give the model a tool (shell). One round: model -> tool -> model."""
from __future__ import annotations

import subprocess

from step1_talk_to_model import ask


def tool(name: str, description: str, parameters: dict) -> dict:
    """One-line tool builder -> OpenAI function-calling shape."""
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": parameters},
    }


SHELL = tool(
    "shell",
    "Run a bash command in the workspace. Returns exit code + output.",
    {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
)

TOOLS = [SHELL]


def run_shell(command: str) -> str:
    p = subprocess.run(["bash", "-lc", command], capture_output=True, text=True, timeout=60)
    return f"exit={p.returncode}\n{p.stdout}{p.stderr}"


def run_one_round(task: str) -> None:
    messages = [
        {"role": "system", "content": "Use the tools, read before you edit."},
        {"role": "user", "content": task},
    ]
    reply = ask(messages, TOOLS)
    messages.append(reply)
    for tc in reply.get("tool_calls") or []:
        import json as _j

        args = _j.loads(tc["function"]["arguments"] or "{}")
        if tc["function"]["name"] == "shell":
            out = run_shell(args.get("command", "ls -la"))
            messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": out}
            )
            print(out)
    print(ask(messages, TOOLS).get("content"))


if __name__ == "__main__":
    run_one_round("List the files here.")
