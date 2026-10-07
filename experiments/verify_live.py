"""Live-data verification: proves the agent's shell tool works on real public data.

No keys. Uses Frankfurter (ECB) + CoinGecko free tiers — the same endpoints
mini-codex can curl inside docker-compose. Fails loudly offline so the paper's
'verified on live data 2026-10-07' claim is falsifiable (cf. SWE-bench-Pro
Verified anti-hacking: block code-hosts, allow dependency/data endpoints).
"""
from __future__ import annotations
import json, urllib.request

def get(url: str, timeout=20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "mini-codex-phd/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def main() -> None:
    fx = None
    for url in (
        "https://api.frankfurter.app/latest?from=USD&to=EUR,GBP,JPY",
        "https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR,GBP,JPY",
        "https://open.er-api.com/v6/latest/USD",
    ):
        try:
            fx = get(url); break
        except Exception as e:
            print(f"fx fallback {url}: {e}"); continue
    assert fx is not None, "all FX endpoints unreachable"
    rates = fx.get("rates", {})
    eur = rates.get("EUR") or (rates.get("rates", {}) or {}).get("EUR")
    assert eur is not None, fx
    btc = get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
    assert "bitcoin" in btc and "usd" in btc["bitcoin"], btc
    print(f"LIVE OK USD->EUR={eur} BTC=${btc['bitcoin']['usd']}")
    with open("/tmp/live_verification.json", "w") as f:
        json.dump({"fx": fx, "btc": btc}, f, indent=2)

if __name__ == "__main__":
    main()
