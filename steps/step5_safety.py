"""Part 5 — safety: approvals + sandbox + output truncation (like Codex).

Approvals: regex for dangerous commands (rm -rf, sudo, git reset --hard...).
Sandbox: macOS Seatbelt policy (deny net, deny writes except workspace/tmp);
  on Linux falls back to informative message (production Codex uses
  Landlock+seccomp/Bubblewrap; Windows uses restricted tokens — see docs).
Truncation: keep first/last 2000 chars if output > 4000.
"""
from __future__ import annotations

import os
import re
import subprocess

DANGEROUS = re.compile(
    r"(rm\s+-rf\s+[/~]|sudo\b|git\s+reset\s+--hard|mkfs|dd\s+of=|shutdown|reboot|:?\(\)\s*\{)",
    re.IGNORECASE,
)

WORKSPACE = os.path.abspath(os.environ.get("CODEX_MINI_WORKSPACE", "."))
SEATBELT_POLICY = f"""(version 1)(allow default)(deny network*)(deny file-write*)(allow file-write* (subpath "{WORKSPACE}")(subpath "/tmp")(subpath "/private/tmp"))"""


def needs_approval(command: str) -> bool:
    return bool(DANGEROUS.search(command))


def ask_user(command: str) -> bool:
    ans = input(f"Allow this command? [y/N]: {command}\n> ").strip().lower()
    return ans in ("y", "yes")


def truncate(out: str, limit: int = 4000) -> str:
    if len(out) <= limit:
        return out
    half = limit // 2
    return out[:half] + f"\n...[truncated {len(out)-limit} chars]...\n" + out[-half:]


def run_shell_safe(command: str, auto_approve: bool = False) -> str:
    if needs_approval(command) and not auto_approve:
        if not ask_user(command):
            return "exit=0\n[user declined to run this command]"
    import platform

    if platform.system() == "Darwin":
        argv = ["sandbox-exec", "-p", SEATBELT_POLICY, "bash", "-lc", command]
    else:
        # Linux/CI: run directly (Docker provides isolation via compose).
        argv = ["bash", "-lc", command]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=90,
                       cwd=WORKSPACE)
    return truncate(f"exit={p.returncode}\n{p.stdout}{p.stderr}")
