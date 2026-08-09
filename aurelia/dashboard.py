"""
Dashboard aggregates for the React UI.

Reads the same in-memory cache as the agent tools (db.load). Weekly plan is
monthly target_revenue split evenly across weeks of that month present in data.
"""
from __future__ import annotations

from fastapi import HTTPException

from aurelia import db
from aurelia.analysis.decompose import weeks_in_month
from aurelia.jsonutil import jsonable


def _d():
    return db.load()


def _all_weeks() -> list[str]:
    return [str(w) for w in sorted(_d()["sales_wk"].week.unique())]


def _month_for_week(week: str) -> str:
    y, w = week.split("-W")
    import datetime as dt
    d = dt.date.fromisocalendar(int(y), int(w), 1)
    return f"{d.year}-{d.month:02d}"


def _week_plan_share(week: str, all_weeks: set[str]) -> float:
    """Fraction of the month's target that belongs to this week."""
    month = _month_for_week(week)
    in_month = [w for w in weeks_in_month(month) if w in all_weeks]
    if not in_month or week not in in_month:
        return 0.0
    return 1.0 / len(in_month)


def _resolve_skus(department: str | None, model: str | None, sku: str | None) -> tuple[list[str], str]:
    p = _d()["products"]
    if sku:
        hit = p[p.sku == sku]
        if hit.empty:
            raise HTTPException(400, f"unknown sku: {sku}")
        return hit.sku.tolist(), sku
    if model:
        hit = p[p.model == model]
        if department:
            hit = hit[hit.department == department]
        if hit.empty:
            raise HTTPException(400, f"unknown model: {model}")
        return hit.sku.tolist(), model
    if department:
        hit = p[p.department == department]
        if hit.empty:
            raise HTTPException(400, f"unknown department: {department}")
        return hit.sku.tolist(), department
    return p.sku.tolist(), "All departments"


def _sales_slice(skus: list[str], weeks: list[str], channel: str | None):
    s = _d()["sales"]
    s = s[s.sku.isin(skus) & s.week.isin(weeks)]
    if channel and channel != "all":
        s = s[s.channel == channel]
    return s


def _plan_revenue(skus: list[str], week: str, all_weeks: set[str]) -> float:
    share = _week_plan_share(week, all_weeks)
    if share == 0:
        return 0.0
    month = _month_for_week(week)
    t = _d()["targets"]
    t = t[t.sku.isin(skus) & (t.month == month)]
    return float(t.target_revenue.sum()) * share


def _plan_units(skus: list[str], week: str, all_weeks: set[str]) -> float:
    share = _week_plan_share(week, all_weeks)
    if share == 0:
        return 0.0
    month = _month_for_week(week)
    t = _d()["targets"]
    t = t[t.sku.isin(skus) & (t.month == month)]
    return float(t.target_units.sum()) * share


def catalog() -> dict:
    d = _d()
    prod = d["products"]
    sold = set(d["sales"].sku.unique())
    prod = prod[prod.sku.isin(sold)].sort_values(["department", "model", "sku"])

    departments = []
    for dept, dg in prod.groupby("department", sort=True):
        models = []
        for model, mg in dg.groupby("model", sort=True):
            skus = [
                {"sku": str(r.sku), "colour": str(r.colour or "")}
                for r in mg.itertuples()
            ]
            models.append({"name": str(model), "skus": skus})
        departments.append({"name": str(dept), "models": models})

    return jsonable({
        "weeks": _all_weeks(),
        "channels": ["all", "store", "ecom"],
        "departments": departments,
        "latest_week": db.latest_week(),
    })


def snapshot(
    week: str | None = None,
    department: str | None = None,
    model: str | None = None,
    sku: str | None = None,
    channel: str = "all",
) -> dict:
    d = _d()
    all_weeks = _all_weeks()
    week_set = set(all_weeks)

    if not week:
        week = db.latest_week()
    if week not in week_set:
        raise HTTPException(400, f"unknown week: {week}")
    if channel not in ("all", "store", "ecom"):
        raise HTTPException(400, f"unknown channel: {channel}")

    department = department or None
    model = model or None
    sku = sku or None
    if department == "all":
        department = None
    if model == "all":
        model = None
    if sku == "all":
        sku = None

    skus, scope_label = _resolve_skus(department, model, sku)
    if department and model:
        p = d["products"]
        ok = p[(p.department == department) & (p.model == model)]
        if sku and sku not in set(ok.sku):
            raise HTTPException(400, f"sku {sku} not in {department}/{model}")

    chan = None if channel == "all" else channel
    wi = all_weeks.index(week)

    # ---- KPIs for selected week ----
    sa = _sales_slice(skus, [week], chan)
    actual_rev = float(sa.revenue.sum())
    actual_units = int(sa.units.sum())
    plan_rev = _plan_revenue(skus, week, week_set)
    vs_plan_pct = round((actual_rev - plan_rev) / plan_rev * 100, 1) if plan_rev else None

    st = d["stock"]
    st_w = st[(st.sku.isin(skus)) & (st.week == week)]
    stock_units = int(st_w.units_on_hand.sum()) if not st_w.empty else 0
    cover = round(stock_units / actual_units, 1) if actual_units else None

    # margin estimate: (price - cost)/price minus half of weighted discount
    if not sa.empty:
        merged = sa.merge(
            d["products"][["sku", "price", "cost"]], on="sku", how="left")
        gm_ex_disc = ((merged.price - merged.cost) / merged.price).fillna(0)
        w_disc = (merged.discount_pct.fillna(0) * merged.revenue).sum() / max(actual_rev, 1e-9)
        gm_pct = round(float((gm_ex_disc * merged.revenue).sum() / max(actual_rev, 1e-9) * 100
                             - w_disc * 50), 1)
        fp_units = int(merged.loc[merged.discount_pct.fillna(0) <= 0.01, "units"].sum())
        fp_st = round(fp_units / max(actual_units + stock_units * 0.35, 1e-9) * 100, 1)
    else:
        gm_pct = None
        fp_st = None

    kpis = {
        "net_sales": round(actual_rev, 2),
        "units": actual_units,
        "plan_sales": round(plan_rev, 2),
        "vs_plan_pct": vs_plan_pct,
        "gross_margin_pct": gm_pct,
        "full_price_sell_thru_pct": fp_st,
        "stock_units": stock_units,
        "weeks_cover": cover,
    }

    # ---- Trend: 12 weeks ending at selected ----
    start = max(0, wi - 11)
    trend_weeks = all_weeks[start: wi + 1]
    actual_series, plan_series = [], []
    for w in trend_weeks:
        a = float(_sales_slice(skus, [w], chan).revenue.sum())
        actual_series.append(round(a / 1000, 2))
        plan_series.append(round(_plan_revenue(skus, w, week_set) / 1000, 2))

    trend = {
        "labels": trend_weeks,
        "actual": actual_series,
        "plan": plan_series,
        "highlight_index": len(trend_weeks) - 1,
    }

    # ---- Department variance (always all depts, selected week) ----
    dept_labels, dept_values = [], []
    for dept, dg in d["products"].groupby("department", sort=True):
        dskus = dg.sku.tolist()
        a = float(_sales_slice(dskus, [week], chan).revenue.sum())
        p = _plan_revenue(dskus, week, week_set)
        dept_labels.append(dept)
        dept_values.append(round((a - p) / p * 100, 1) if p else 0.0)

    # ---- Channel split: last 5 weeks, ignore channel filter for split ----
    chan_weeks = all_weeks[max(0, wi - 4): wi + 1]
    stores, ecom = [], []
    for w in chan_weeks:
        base = d["sales"]
        base = base[base.sku.isin(skus) & (base.week == w)]
        stores.append(round(float(base.loc[base.channel == "store", "revenue"].sum()) / 1000, 2))
        ecom.append(round(float(base.loc[base.channel == "ecom", "revenue"].sum()) / 1000, 2))

    # ---- Table drill-down ----
    if department is None:
        level = "dept"
        groups = [
            (name, d["products"][d["products"].department == name].sku.tolist(),
             f"{d['products'][d['products'].department == name].model.nunique()} styles")
            for name in sorted(d["products"].department.unique())
        ]
    elif model is None:
        level = "model"
        sub = d["products"][d["products"].department == department]
        groups = [
            (name, g.sku.tolist(), f"{len(g)} SKUs")
            for name, g in sub.groupby("model", sort=True)
        ]
    else:
        level = "sku"
        sub = d["products"][
            (d["products"].department == department) & (d["products"].model == model)]
        groups = [
            (r.sku, [r.sku], str(r.colour or ""))
            for r in sub.itertuples()
        ]

    table_rows = []
    for key, gskus, sub_label in groups:
        a = float(_sales_slice(gskus, [week], chan).revenue.sum())
        u = int(_sales_slice(gskus, [week], chan).units.sum())
        p = _plan_revenue(gskus, week, week_set)
        vp = round((a - p) / p * 100, 1) if p else None
        st_sum = int(d["stock"][(d["stock"].sku.isin(gskus)) & (d["stock"].week == week)]
                     .units_on_hand.sum())
        # sell-through proxy: units this week / (units + stock)
        sth = round(u / max(u + st_sum, 1) * 100)
        disc = None
        if level == "sku":
            row_s = _sales_slice(gskus, [week], chan)
            disc = round(float(row_s.discount_pct.max() * 100), 0) if not row_s.empty else 0.0
        table_rows.append({
            "key": str(key),
            "name": str(key),
            "sub": str(sub_label),
            "units": int(u),
            "net_sales": float(round(a, 2)),
            "vs_plan_pct": None if vp is None else float(vp),
            "discount_pct": None if disc is None else float(disc),
            "sell_thru_pct": int(sth),
            "stock": int(st_sum),
            "low_stock": bool(st_sum <= 12),
            "selected": bool(level == "sku" and sku is not None and str(sku) == str(key)),
        })

    channel_label = (
        "Retail stores" if channel == "store" else
        "E-commerce" if channel == "ecom" else "All channels"
    )

    return jsonable({
        "week": week,
        "scope_label": str(scope_label),
        "channel": channel,
        "channel_label": channel_label,
        "filters": {
            "department": department or "all",
            "model": model or "all",
            "sku": sku or "all",
            "channel": channel,
        },
        "kpis": kpis,
        "trend": trend,
        "dept_variance": {
            "labels": [str(x) for x in dept_labels],
            "values": [float(x) for x in dept_values],
        },
        "channel_split": {
            "labels": [str(x) for x in chan_weeks],
            "stores": [float(x) for x in stores],
            "ecom": [float(x) for x in ecom],
        },
        "table": {
            "level": level,
            "title": (
                "Performance by department" if level == "dept" else
                f"Styles in {department}" if level == "model" else
                f"SKUs in {model}"
            ),
            "rows": table_rows,
        },
    })
