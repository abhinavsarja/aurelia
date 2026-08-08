"""
The decomposition is the one thing in this system that must never be wrong,
because a wrong split is silent - it looks like a confident answer.

These tests assert the identity holds for every SKU and every month, not just
the ones in the demo.

    python tests/test_decompose.py
"""
import sys

from aurelia.analysis.decompose import load, decompose, analyse

d = load()
skus = sorted(d["products"].sku)
months = sorted(d["targets"].month.unique())

fails, checked, no_target = [], 0, 0
worst = 0.0

for sku in skus:
    for m in months:
        r = decompose(d, sku, m)
        if r.target_revenue == 0:
            no_target += 1
            continue
        checked += 1

        # 1. the parts must equal the whole
        total = sum(f.revenue for f in r.findings)
        drift = abs(total - r.gap_revenue)
        worst = max(worst, drift)
        if drift > max(1.0, 0.005 * abs(r.gap_revenue)):
            fails.append(f"{sku} {m}: parts {total:,.2f} vs gap {r.gap_revenue:,.2f}")

        # 2. the module must agree with itself
        if not r.reconciles:
            fails.append(f"{sku} {m}: reconciles flag is False")

        # 3. shares must sum to 1 whenever they are shown at all
        sh = [f.share for f in r.findings if f.share is not None]
        if sh and abs(sum(sh) - 1.0) > 0.02:
            fails.append(f"{sku} {m}: shares sum to {sum(sh):.3f}")

        # 4. a loss must never be reported as a gain
        for f in r.findings:
            if f.id == "B1" and f.units > 0:
                fails.append(f"{sku} {m}: stock-out reported as a gain")

print(f"checked {checked} sku-months ({no_target} skipped, no target)")
print(f"largest reconciliation drift: S${worst:,.4f}")
if fails:
    print(f"\n{len(fails)} FAILURES")
    for f in fails[:20]:
        print("  ", f)
    sys.exit(1)
print("\nall identities hold")

# the five scenarios must actually be detectable
print("\nscenario checks")
def chk(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL':4s}  {name:38s} {detail}")
    return ok

r = analyse(d, "MRL-CB-TAN", "2026-07")
b1 = next((f for f in r.findings if f.id == "B1"), None)
ok = chk("hero: stock-out is the largest part", b1 is not None and b1.share > 0.5,
         f"{b1.share:.0%} of the gap" if b1 else "not detected")
ok &= chk("hero: a residual remains for documents", abs(r.residual_share or 0) > 0.15,
          f"{r.residual_share:.0%} unexplained")

c = analyse(d, "SOL-AV-GLD", "2026-07").context
ok &= chk("false alarm caught by department check", c["explained_by_department"],
          f"sku {c['sku_gap_pct']}% vs dept {c['department_gap_pct']}%")

c = analyse(d, "MRL-CB-OLV", "2026-07").context
ok &= chk("clearance line suppressed", c["suppress_investigation"], c["lifecycle_status"])

c = analyse(d, "SIE-TT-NVY", "2026-07").context
ok &= chk("returns spike detected", c["returns_elevated"],
          f"{c['return_rate_pct']}% vs {c['department_return_rate_pct']}% baseline")

c = analyse(d, "SOL-AV-GLD", "2026-07").context
ok &= chk("no false returns flag on a normal line", not c["returns_elevated"],
          f"{c['return_rate_pct']}%")

c = analyse(d, "NOV-ST-GLD", "2026-07").context
unexplained = not any(c[k] for k in ["suppress_investigation", "explained_by_department",
                                     "returns_elevated", "possible_cannibalisation"])
ok &= chk("unexplained case stays unexplained", unexplained, "no internal cause found")

sys.exit(0 if ok else 1)
