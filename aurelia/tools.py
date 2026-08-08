"""
The tool library.

Every tool is a fixed, parameterised function. The model chooses which one to
call and supplies the arguments; it never writes a query and never does the
arithmetic. That is the whole safety argument, expressed as code.

Each function is decorated with @function_tool when the OpenAI Agents SDK is
installed, and stays an ordinary Python function when it is not, so the same
module is testable without a network call.

The queries are written against pandas here for portability. Each carries the
equivalent SQL in its docstring - porting is mechanical, the shape does not change.
"""
from __future__ import annotations

import pandas as pd

from aurelia.analysis.decompose import load as load_csv, analyse, weeks_in_month
from aurelia import db as _db

# Identity decorator: the custom Agent loop needs plain callables with
# __name__ / inspect.signature. The Agents SDK @function_tool wrapper returns
# a non-callable FunctionTool and breaks that path.
def function_tool(f):
    return f

# Postgres when it is reachable, the CSVs otherwise. The analysis code is the
# same either way, which is what makes the tests meaningful.
try:
    _D = _db.load()
except Exception:
    _D = load_csv()


# ---------------------------------------------------------------- helpers
def _resolve_sku(value: str) -> str | None:
    """
    Accept a SKU code, or a product name, and return the code.

    The dictionary lists every code and the prompt says to use them, but a model
    will still occasionally send "Sol Aviator Gold". Failing on that would be
    correct and useless. Resolve it, and only give up when it is genuinely
    ambiguous.
    """
    if not value:
        return None
    p = _D["products"]
    if value in set(p.sku):
        return value

    v = value.lower().replace("-", " ").strip()
    hits = []
    for _, r in p.iterrows():
        size = "" if str(r["size"]) in ("nan", "", "None") else str(r["size"])
        label = f"{r.model} {r.colour} {size}".lower()
        if v == label.strip() or (r.model.lower() in v and str(r.colour).lower() in v
                                  and (not size or size in v)):
            hits.append(r.sku)
    return hits[0] if len(hits) == 1 else None


def _scope(department=None, model=None, sku=None):
    p = _D["products"]
    if sku:
        sku = _resolve_sku(sku) or sku
        return p[p.sku == sku].sku.tolist(), sku
    if model:      return p[p.model == model].sku.tolist(), model
    if department: return p[p.department == department].sku.tolist(), department
    return p.sku.tolist(), "the business"


def _period(week=None, month=None):
    allw = sorted(_D["sales_wk"].week.unique())
    if week:  return [week], week
    if month: return [w for w in weeks_in_month(month) if w in set(allw)], month
    return [allw[-1]], allw[-1]


def _totals(skus, weeks, channel=None):
    s = _D["sales"]
    s = s[s.sku.isin(skus) & s.week.isin(weeks)]
    if channel:
        s = s[s.channel == channel]
    return int(s.units.sum()), float(s.revenue.sum())


def _target(skus, month):
    t = _D["targets"]
    t = t[t.sku.isin(skus) & (t.month == month)]
    return int(t.target_units.sum()), float(t.target_revenue.sum())


def _pct(a, b):
    return round((a - b) / b * 100, 1) if b else None


# ---------------------------------------------------------------- tools
@function_tool
def get_sales(department: str = None, model: str = None, sku: str = None,
              week: str = None, month: str = None, channel: str = None) -> dict:
    """
    Sales for one product, model or department, over one week or one month.

    Returns units, revenue, the split by channel, and the comparison against the
    previous period. Use for "what were X sales" questions.

    SQL equivalent:
        SELECT sum(units), sum(revenue) FROM v_sales JOIN products USING (sku)
        WHERE department = :department AND week = ANY(:weeks)
    """
    skus, label = _scope(department, model, sku)
    weeks, plabel = _period(week, month)
    if not skus:
        return dict(error="nothing matched that product")

    u, r = _totals(skus, weeks, channel)
    su, sr = _totals(skus, weeks, "store")
    eu, er = _totals(skus, weeks, "ecom")

    allw = sorted(_D["sales_wk"].week.unique())
    i = allw.index(weeks[0])
    prev = allw[max(0, i - len(weeks)): i]
    pu, pr = _totals(skus, prev, channel) if prev else (0, 0.0)

    out = dict(scope=label, period=plabel, weeks=weeks,
               units=u, revenue=round(r, 2),
               store_revenue=round(sr, 2), ecom_revenue=round(er, 2),
               store_units=su, ecom_units=eu,
               previous_period=prev[-1] if prev else None,
               previous_revenue=round(pr, 2),
               change_vs_previous_pct=_pct(r, pr))
    if month:
        tu, tr = _target(skus, month)
        out |= dict(target_units=tu, target_revenue=round(tr, 2),
                    vs_target_pct=_pct(r, tr))
    return out


@function_tool
def rank_products(month: str, level: str = "sku", metric: str = "vs_target",
                  department: str = None, direction: str = "worst",
                  limit: int = 10) -> dict:
    """
    Rank departments, models or SKUs for a month.

    metric: vs_target | revenue | units
    direction: worst | best
    Use for "which products are behind", "top 10 by revenue".
    """
    p, tg = _D["products"], _D["targets"]
    weeks, _ = _period(month=month)
    pool = p[p.department == department] if department else p
    key = dict(sku="sku", model="model", department="department")[level]

    rows = []
    for name, grp in pool.groupby(key):
        skus = grp.sku.tolist()
        u, r = _totals(skus, weeks)
        tu, tr = _target(skus, month)
        rows.append(dict(name=name, units=u, revenue=round(r, 2),
                         target_revenue=round(tr, 2), vs_target_pct=_pct(r, tr)))

    sort_key = dict(vs_target="vs_target_pct", revenue="revenue", units="units")[metric]
    rows = [x for x in rows if x[sort_key] is not None]
    rows.sort(key=lambda x: x[sort_key], reverse=(direction == "best"))
    return dict(level=level, month=month, metric=metric, direction=direction,
                results=rows[:limit])


@function_tool
def compare(names: list[str], month: str, level: str = "model") -> dict:
    """Put two or more departments, models or SKUs side by side for a month."""
    key = dict(sku="sku", model="model", department="department")[level]
    p = _D["products"]
    weeks, _ = _period(month=month)
    out = []
    for n in names:
        skus = p[p[key] == n].sku.tolist()
        if not skus:
            out.append(dict(name=n, error="not found")); continue
        u, r = _totals(skus, weeks)
        tu, tr = _target(skus, month)
        out.append(dict(name=n, units=u, revenue=round(r, 2),
                        target_revenue=round(tr, 2), vs_target_pct=_pct(r, tr)))
    return dict(month=month, level=level, results=out)


@function_tool
def get_trend(department: str = None, model: str = None, sku: str = None,
              weeks_back: int = 12, metric: str = "revenue") -> dict:
    """Weekly series for a product, model or department. Use for "is X improving"."""
    skus, label = _scope(department, model, sku)
    allw = sorted(_D["sales_wk"].week.unique())[-weeks_back:]
    series = []
    for w in allw:
        u, r = _totals(skus, [w])
        series.append(dict(week=w, units=u, revenue=round(r, 2)))
    vals = [s[metric if metric in ("units",) else "revenue"] for s in series]
    half = len(vals) // 2
    first, second = sum(vals[:half]), sum(vals[half:])
    return dict(scope=label, metric=metric, series=series,
                direction=("improving" if second > first * 1.02 else
                           "declining" if second < first * 0.98 else "flat"),
                first_half=round(first, 2), second_half=round(second, 2),
                change_pct=_pct(second, first))


@function_tool
def get_stock(sku: str = None, model: str = None, week: str = None) -> dict:
    """
    Current stock position and weeks of cover, by SKU.

    Use for "how much stock do we have", and for size-curve questions - it
    returns every size separately, which is where a healthy total hides a problem.
    """
    skus, label = _scope(None, model, sku)
    weeks, w = _period(week)
    st, sa, p = _D["stock"], _D["sales_wk"], _D["products"]
    rows = []
    for s in skus:
        on_hand = st[(st.sku == s) & (st.week == weeks[-1])].units_on_hand
        recent = sa[(sa.sku == s) & (sa.week.isin(sorted(sa.week.unique())[-8:]))].units.mean()
        oh = int(on_hand.iloc[0]) if len(on_hand) else 0
        rows.append(dict(sku=s,
                         size=str(p[p.sku == s].iloc[0]["size"] or ""),
                         units_on_hand=oh,
                         weekly_rate=round(float(recent or 0), 1),
                         weeks_cover=round(oh / recent, 1) if recent else None))
    return dict(scope=label, week=weeks[-1],
                total_units_on_hand=sum(r["units_on_hand"] for r in rows),
                by_sku=rows)


@function_tool
def get_target_source(sku: str, month: str) -> dict:
    """Where a target came from. Use for "how was that number set"."""
    t = _D["targets"]
    r = t[(t.sku == sku) & (t.month == month)]
    if r.empty:
        return dict(error="no target for that SKU and month")
    r = r.iloc[0]
    return dict(sku=sku, month=month, target_units=int(r.target_units),
                target_revenue=float(r.target_revenue),
                source_document=r.source_document)


@function_tool
def explain_gap(sku: str, month: str) -> dict:
    """
    Why a SKU missed its target. Runs the full diagnostic.

    This is the only expensive tool. Inside it the gap is decomposed into
    measured parts, context checks run, and a residual is left for documents to
    explain. Use ONLY for questions asking why something changed.
    """
    code = _resolve_sku(sku)
    if code is None:
        p = _D["products"]
        near = [x for x in p.sku if sku and sku.split()[0][:3].upper() in x][:6]
        return dict(error=f"'{sku}' is not a SKU code and could not be resolved to one",
                    hint="Use a code from the SKU list in the reference material.",
                    did_you_mean=near or None)
    r = analyse(_D, code, month)
    return r.to_dict()


TOOLS = [get_sales, rank_products, compare, get_trend, get_stock,
         get_target_source, explain_gap]


# --- SQL note -------------------------------------------------------------
# find_exceptions runs several independent checks over the same month and
# expresses each as revenue at risk, so a returns problem and a supply problem
# can be ranked against each other. It is a pull, not a push - nothing here is
# pushed to anyone. Proactive alerting stays out of scope.
# --------------------------------------------------------------------------
@function_tool
def find_exceptions(month: str, department: str = None, limit: int = 10) -> dict:
    """
    Which products need attention this month, and why.

    Use for open questions like "what should we be worried about", "what needs
    looking at", "anything I should know about". Do NOT use when the question
    names a specific product - use explain_gap for that.

    This is not a sort by target variance. It runs several separate checks and
    reports which one fired, so a product selling to target while being returned
    heavily still surfaces. Each finding is expressed as revenue at risk so the
    different kinds of problem can be ranked against one another.

    Products on clearance are excluded, and so are products whose shortfall
    simply matches their department - those are category questions, not product
    problems, and are reported separately.
    """
    prod, sales_wk, st, ret = _D["products"], _D["sales_wk"], _D["stock"], _D["returns"]
    weeks, _ = _period(month=month)
    if not weeks:
        return dict(error=f"no data for {month}")
    pool = prod[prod.department == department] if department else prod

    # department-level context, computed once
    dept_gap = {}
    for dep, g in prod.groupby("department"):
        u, r = _totals(g.sku.tolist(), weeks)
        _, tr = _target(g.sku.tolist(), month)
        dept_gap[dep] = _pct(r, tr)

    flags, category_wide = [], []
    for _, p in pool.iterrows():
        sku = p.sku
        u, r = _totals([sku], weeks)
        tu, tr = _target([sku], month)
        if not tr:
            continue
        gap_pct = _pct(r, tr)
        dgap = dept_gap.get(p.department)

        if p.status in ("clearance", "discontinued"):
            continue                                     # A1 - deliberate

        # A2 - behaving like its department is a category question, not a product one
        if gap_pct is not None and dgap is not None and gap_pct < -10 and abs(gap_pct - dgap) <= 5:
            category_wide.append(dict(sku=sku, model=p.model, department=p.department,
                                      gap_pct=gap_pct, department_gap_pct=dgap))
            continue

        # 1. missing target on its own
        if gap_pct is not None and gap_pct < -15:
            flags.append(dict(sku=sku, model=p.model, department=p.department,
                              issue="behind target", detail=f"{gap_pct}% vs target",
                              revenue_at_risk=round(tr - r, 2), metric=gap_pct))

        # 2. being returned heavily
        rr = ret[(ret.sku == sku) & (ret.week.isin(weeks))].units_returned.sum()
        rate = rr / u if u else 0
        dep_skus = prod[prod.department == p.department].sku.tolist()
        dep_r = ret[(ret.sku.isin(dep_skus)) & (ret.week.isin(weeks))].units_returned.sum()
        dep_u = sales_wk[(sales_wk.sku.isin(dep_skus)) & (sales_wk.week.isin(weeks))].units.sum()
        base = dep_r / dep_u if dep_u else 0
        if base and rate > base * 1.8 and rate > 0.12:
            excess = (rate - base) * u
            flags.append(dict(sku=sku, model=p.model, department=p.department,
                              issue="returns", metric=round(rate * 100, 1),
                              detail=f"{rate*100:.0f}% returned vs {base*100:.0f}% department baseline",
                              revenue_at_risk=round(excess * float(p.price), 2)))

        # 3. about to run out AND nothing on the way
        #    the replenishment policy reorders at 2.5 weeks of cover, so thin stock
        #    is normal operation. It is only an exception if no delivery is coming.
        recent = sales_wk[(sales_wk.sku == sku) &
                          (sales_wk.week.isin(sorted(sales_wk.week.unique())[-8:]))].units.mean()
        oh = st[(st.sku == sku) & (st.week == weeks[-1])].units_on_hand
        oh = int(oh.iloc[0]) if len(oh) else 0
        cover = oh / recent if recent else None
        recent_weeks = sorted(sales_wk.week.unique())[-4:]
        incoming = _D["receipts"][(_D["receipts"].sku == sku) &
                                  (_D["receipts"].week.isin(recent_weeks))].units_received.sum()
        if cover is not None and cover < 1.0 and recent > 3 and incoming == 0:
            lost = max(0.0, (2 - cover)) * recent          # two weeks of exposure
            flags.append(dict(sku=sku, model=p.model, department=p.department,
                              issue="stock about to run out", metric=round(cover, 1),
                              detail=(f"{oh} units left, {cover:.1f} weeks of cover, "
                                      f"no delivery in the last 4 weeks"),
                              revenue_at_risk=round(lost * float(p.price), 2)))

    # one row per product - the worst issue wins, the rest are listed against it
    best = {}
    for f in flags:
        cur = best.get(f["sku"])
        if cur is None or f["revenue_at_risk"] > cur["revenue_at_risk"]:
            f["also"] = ([cur["issue"]] + cur.get("also", [])) if cur else []
            best[f["sku"]] = f
        else:
            cur.setdefault("also", []).append(f["issue"])
    flags = sorted(best.values(), key=lambda f: -f["revenue_at_risk"])

    # grouped by kind of problem, not one long list. A returns fault worth S$18k
    # is smaller than a S$99k sales miss but it is the one nobody can see from a
    # sales report, so it must not be buried under bigger numbers.
    groups = {}
    for f in flags:
        groups.setdefault(f["issue"], []).append(f)
    by_issue = {k: v[:max(3, limit // 3)] for k, v in
                sorted(groups.items(), key=lambda kv: -sum(x["revenue_at_risk"] for x in kv[1]))}

    return dict(month=month, department=department,
                by_issue=by_issue,
                total_revenue_at_risk=round(sum(f["revenue_at_risk"] for f in flags), 2),
                flagged=flags[:limit],
                category_wide_note=(
                    f"{len(category_wide)} products are behind by roughly the same amount as their "
                    f"department and are excluded - those are category questions, not product problems."
                    if category_wide else None),
                category_wide_examples=category_wide[:3])


TOOLS.append(find_exceptions)
