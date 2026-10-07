"""Offline demo: replays the video's 5-call trajectory without spending tokens.

Applies the correct integer-cents patch, runs pytest, prints metrics.
Mirrors benchmarks/bench.py pass/fail contract for CI.
"""
from __future__ import annotations
import subprocess, sys, time
PATCH = """*** Begin Patch ***
*** Update File: shop/shop.py
@@ def total
 def total(subtotal_cents: int, coupon_percent: int) -> int:
     """ + '"""' + """Return total after coupon. BUG: subtracts coupon number itself.""" + '"""' + """
-    discount = coupon_percent
-    return subtotal_cents - discount
+    discount = (subtotal_cents * coupon_percent + 50) // 100
+    return subtotal_cents - discount
*** End Patch ***
"""
def main() -> None:
    sys.path.insert(0, ".")
    from steps.step4_apply_patch import apply_patch
    t0 = time.time()
    print(apply_patch(PATCH))
    p = subprocess.run([sys.executable, "-m", "pytest", "shop/test_shop.py", "-v"],
                       capture_output=True, text=True)
    print(p.stdout[-2000:]); print(p.stderr[-500:])
    print(f"demo: exit={p.returncode} seconds={time.time()-t0:.1f} model_calls=0(off-replay) tool_calls=1")
    sys.exit(p.returncode)
if __name__ == "__main__": main()
