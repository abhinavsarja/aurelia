"""
Replacement for explain_gap in aurelia/tools.py.

This is where the three sources meet, in order, and where the gate lives.
Paste over the existing explain_gap and add the import at the top of tools.py:

    from aurelia.rag import retrieve
"""

EXPLAIN_GAP = '''
# --- SQL note -------------------------------------------------------------
# The only expensive tool. Inside it the order is fixed and the model cannot
# change it: measure first, then look for documents that explain what was
# measured, then - only if a large share is still unexplained - look outside.
# --------------------------------------------------------------------------
GATE_THRESHOLD = 0.30      # unexplained share above which we look at market news


@function_tool
def explain_gap(sku: str, month: str) -> dict:
    """
    Why a SKU missed its target. Runs the full diagnostic.

    Use ONLY for questions asking WHY something changed. For "what were sales",
    use get_sales.

    Splits the gap into parts that can be measured, checks whether the product is
    simply behaving like its department, finds internal documents that explain
    what is left, and consults market news only if a large share is still
    unexplained.
    """
    r = analyse(_D, sku, month)
    out = r.to_dict()
    ctx = out["context"]

    # A1 - a deliberate wind-down is not a problem to investigate
    if ctx.get("suppress_investigation"):
        out["conclusion"] = (
            f"{sku} is on {ctx['lifecycle_status']}. The decline is intended, "
            "not a performance problem.")
        out["documents"], out["external"], out["gate_opened"] = [], [], False
        return out

    # A2 - behaving like its department is a category question, not a product one
    if ctx.get("explained_by_department"):
        out["conclusion"] = (
            f"{sku} is {ctx['sku_gap_pct']}% against target while its department is "
            f"{ctx['department_gap_pct']}%. Only {abs(ctx['sku_specific_pts'])} points "
            "are specific to this product. This is a category question.")

    # 2. documents that explain the measured findings
    try:
        out["documents"] = retrieve.for_findings(sku, out["weeks"], out["findings"])
    except Exception as e:
        out["documents"] = []
        out["document_error"] = f"{type(e).__name__}: {e}"

    # 3. the gate. Market news is consulted only when internal evidence runs out.
    unexplained = abs(out.get("residual_share") or 0)
    measured = sum(abs(f["share"] or 0) for f in out["findings"] if f["id"] != "RESIDUAL")
    out["explained_share"] = round(measured, 3)
    out["gate_opened"] = bool(unexplained > GATE_THRESHOLD and not ctx.get("explained_by_department"))

    if out["gate_opened"]:
        try:
            out["external"] = retrieve.external(sku, out["weeks"])
        except Exception as e:
            out["external"] = []
            out["external_error"] = f"{type(e).__name__}: {e}"
        out["gate_note"] = (
            f"{unexplained:.0%} of the gap has no internal explanation, so market "
            "sources were checked. Treat anything from them as lower confidence "
            "and do not present it as a cause unless our own numbers support it.")
    else:
        out["external"] = []
        out["gate_note"] = (
            f"Internal evidence accounts for the gap, so market sources were not "
            "consulted.")

    return out
'''

if __name__ == "__main__":
    print(EXPLAIN_GAP)
