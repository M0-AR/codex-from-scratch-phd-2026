# AGENTS.md — project instructions (loaded like real Codex)

Run tests with: `python -m pytest shop/test_shop.py -v` (or `pytest -v`).

Rules:
- Prices are integer cents. Never use floats for money.
- Round to nearest cent with integers: `(subtotal * pct + 50) // 100`.
- Read a file before editing it. Run tests after every edit.
- Prefer `apply_patch` over rewriting whole files.
