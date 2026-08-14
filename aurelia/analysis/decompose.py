"""
AURELIA - gap decomposition.

Splits the gap between actual and target into parts that can be measured exactly.
Anything that cannot be measured is left as a residual for documents to explain.

The whole system depends on this module being right, so it is deliberately
boring arithmetic with no model involvement anywhere.

    revenue gap = availability effect + demand effect + price effect

and that identity holds exactly, by construction. See test_decompose.py.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import datetime as dt
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data"

# A week counts as supply-constrained when closing stock could not have covered
# normal demand. 0.5 means "less than half a week of cover left at week end".
CONSTRAINED_COVER = 0.5
# How many recent unconstrained weeks to average for the demand estimate.
RATE_WINDOW = 8
MIN_RATE_WEEKS = 3


# ---------------------------------------------------------------- loading
# This is used only for tests. The app uses aurelia.db.load() at startup.
def load() -> dict[str, pd.DataFrame]:
    """CSV loader for unit tests only. The app uses aurelia.db.load() at startup."""
    f = lambda n: pd.read_csv(DATA / f"{n}.csv")
    d = {n: f(n) for n in ["products", "sales", "stock", "returns", "receipts", "targets"]}
    d["sales_wk"] = (d["sales"].groupby(["week", "sku"], as_index=False)
                     .agg(units=("units", "sum"), revenue=("revenue", "sum"),
                          discount_pct=("discount_pct", "max")))
    return d


#Just tells what weeks should be considered for the month in question.
def weeks_in_month(month: str) -> list[str]:
    """'Tells what weeks should be considered for the month in question."""
    y, m = map(int, month.split("-"))
    out = []
    for w in range(1, 54):
        try:
            d = dt.date.fromisocalendar(y, w, 1)
        except ValueError:
            continue
        if d.year == y and d.month == m:
            out.append(f"{y}-W{w:02d}")
    return out


# ---------------------------------------------------------------- findings
@dataclass
class Finding:
    id: str
    label: str
    units: float           # signed: negative is a loss
    revenue: float         # signed
    share: float           # share of the total gap, 0..1
    quantified: bool       # may the model attach a percentage to this?
    confidence: str        # high | medium | low
    basis: str             # how it was derived, in one sentence
    evidence: dict = field(default_factory=dict)


@dataclass
class Decomposition:
    sku: str
    period: str
    weeks: list[str]
    actual_units: int
    target_units: int
    actual_revenue: float
    target_revenue: float
    gap_units: int
    gap_revenue: float
    gap_pct: float
    findings: list[Finding]
    residual_units: float
    residual_revenue: float
    residual_share: float
    context: dict
    reconciles: bool

    def to_dict(self):
        d = asdict(self)
        d["findings"] = [asdict(f) for f in self.findings]
        return d


# ---------------------------------------------------------------- helpers
def _unconstrained_weeks(sales_wk, stock, sku, weeks, _rough=None):
    """
    Weeks the product was available all week.

    The test is closing stock above zero. It is deliberately crude: anything
    that depends on an estimate of demand would be circular, because the
    estimate is the thing these weeks are used to produce.
    """
    st = stock[stock.sku == sku].set_index("week").units_on_hand
    sa = sales_wk[sales_wk.sku == sku].set_index("week").units
    return [(w, float(sa.get(w, 0))) for w in weeks
            if w in st.index and st.get(w, 0) > 0]


def _rate_of_sale(sales_wk, stock, sku, period_weeks, all_weeks):
    """
    Units per week when the product was actually available.

    Preference order matters. Weeks inside the period being analysed are used
    first, because demand shifts - a campaign ending, a season turning - and an
    older window would measure a different world. Only if the product was
    unavailable for almost the whole period do we look further back, and the
    confidence drops when we do.
    """
    hist = sales_wk[sales_wk.sku == sku]
    if hist.empty:
        return 0.0, "no history", [], "low"

    prior = sorted(w for w in all_weeks if w < period_weeks[0])

    # 1. unconstrained weeks inside the period
    inside = _unconstrained_weeks(sales_wk, stock, sku, period_weeks)
    if len(inside) >= MIN_RATE_WEEKS:
        rate = sum(u for _, u in inside) / len(inside)
        return rate, f"mean of {len(inside)} in-period weeks with stock available", [w for w, _ in inside], "high"
    if inside:
        rate = sum(u for _, u in inside) / len(inside)
        wk = ", ".join(w for w, _ in inside)
        return rate, f"only {len(inside)} week(s) in the period had stock ({wk})", [w for w, _ in inside], "medium"

    # 2. nothing in-period was available - fall back to recent unconstrained weeks
    back = _unconstrained_weeks(sales_wk, stock, sku, prior[-RATE_WINDOW * 2:])[-RATE_WINDOW:]
    if back:
        rate = sum(u for _, u in back) / len(back)
        return rate, f"no in-period week had stock; mean of {len(back)} earlier available weeks", [w for w, _ in back], "low"

    tail = hist[hist.week.isin(prior[-RATE_WINDOW:])]
    return float(tail.units.mean() or 0), "no unconstrained history", list(tail.week), "low"


def _constrained(stock, sales_wk, sku, weeks, rate):
    """Weeks where stock could not have covered normal demand."""
    st = stock[stock.sku == sku].set_index("week").units_on_hand
    sa = sales_wk[sales_wk.sku == sku].set_index("week").units
    out = []
    for w in weeks:
        closing = st.get(w)
        if closing is None or closing > 0:
            continue                        # stock lasted the week
        sold = sa.get(w, 0)
        out.append(dict(week=w, sold=int(sold), closing=0,
                        expected=round(rate, 1),
                        lost=max(0.0, round(rate - sold, 1))))
    return out


# ---------------------------------------------------------------- main
def decompose(d, sku: str, month: str) -> Decomposition:
    sales_wk, stock, prod, tg = d["sales_wk"], d["stock"], d["products"], d["targets"]
    weeks = [w for w in weeks_in_month(month) if w in set(sales_wk.week)]
    all_weeks = sorted(sales_wk.week.unique())

    act = sales_wk[(sales_wk.sku == sku) & (sales_wk.week.isin(weeks))]
    Ua = int(act.units.sum())
    Ra = float(act.revenue.sum())

    t = tg[(tg.sku == sku) & (tg.month == month)]
    Ut = int(t.target_units.sum())
    Rt = float(t.target_revenue.sum())

    gap_u, gap_r = Ua - Ut, Ra - Rt
    Pt = Rt / Ut if Ut else 0.0                 # target price per unit
    Pa = Ra / Ua if Ua else Pt                  # realised price per unit

    

    rate, rate_basis, rate_weeks, rate_conf = _rate_of_sale(sales_wk, stock, sku, weeks, all_weeks)

    con = _constrained(stock, sales_wk, sku, weeks, rate) # Which weeks lost due to loss of stock
    Ul = sum(c["lost"] for c in con)            # units lost to unavailability

    # --- the identity -------------------------------------------------
    #   gap_revenue = availability_gap + demand_gap + price_gap
    availability_r = -Ul * Pt
    demand_u = (Ua + Ul) - Ut
    demand_r = demand_u * Pt
    price_r = (Pa - Pt) * Ua
    # ------------------------------------------------------------------

    # MAIN ARITHMENTICS TO UNDERSTAND THE GAP

    # Ul — units lost to stockouts: sum of lost over no stock weeks
    #   (closing stock hit 0). lost ≈ max(0, normal_rate − units_sold).
    
    # demand_u — volume gap after putting stockouts back: (Ua + Ul) − Ut.
    #   Negative ⇒ still short of target even with stock (“demand with stock”).
    
    # price_r — revenue gap from price/discount: (Pa − Pt) * Ua.
    #   Positive ⇒ sold above target price; negative ⇒ cheaper / discounted.
    
    # With availability_r = -Ul * Pt and demand_r = demand_u * Pt, the three
    # revenue pieces should add to gap_r (see reconciles below).

    # a share of a near-zero gap is arithmetic noise, not information
    material = abs(gap_r) >= 0.02 * abs(Rt or 1)
    denom = gap_r if (gap_r and material) else None
    sh = lambda v: round(v / denom, 3) if denom else None
    findings = []

    if Ul > 0:
        findings.append(Finding(
            id="B1", label="Out of stock",
            units=-round(Ul, 1), revenue=round(availability_r, 2),
            share=sh(availability_r),
            quantified=True, confidence=rate_conf,
            basis=(f"{len(con)} of {len(weeks)} weeks could not cover normal demand of "
                   f"{rate:.0f} units/week; {rate_basis}"),
            evidence=dict(weeks=con, rate_of_sale=round(rate, 1), rate_from=rate_weeks)))

    if abs(price_r) > max(1.0, 0.005 * abs(gap_r or 1)):
        findings.append(Finding(
            id="C1/C2", label="Price and discount",
            units=0.0, revenue=round(price_r, 2),
            share=sh(price_r),
            quantified=True, confidence="high",
            basis=(f"realised price S${Pa:.2f} against target price S${Pt:.2f} "
                   f"across {Ua} units"),
            evidence=dict(realised_price=round(Pa, 2), target_price=round(Pt, 2))))

    if abs(demand_u) > 0:
        findings.append(Finding(
            id="RESIDUAL", label="Demand with stock available",
            units=round(demand_u, 1), revenue=round(demand_r, 2),
            share=sh(demand_r),
            quantified=True, confidence="high",
            basis=("units that could have been sold at the normal rate with stock on "
                   "hand and no price change, but were not"),
            evidence=dict()))

    check = availability_r + demand_r + price_r
    reconciles = abs(check - gap_r) < max(1.0, 0.005 * abs(gap_r))

    return Decomposition(
        sku=sku, period=month, weeks=weeks,
        actual_units=Ua, target_units=Ut,
        actual_revenue=round(Ra, 2), target_revenue=round(Rt, 2),
        gap_units=gap_u, gap_revenue=round(gap_r, 2),
        gap_pct=round(gap_r / Rt * 100, 1) if Rt else 0.0,
        findings=findings,
        residual_units=round(demand_u, 1), residual_revenue=round(demand_r, 2),
        residual_share=sh(demand_r),
        context={}, reconciles=reconciles)


# ---------------------------------------------------------------- context
def context(d, sku: str, month: str) -> dict:
    """
    Checks that change what the gap MEANS, run before any cause is attributed.

    These are not causes. They decide whether there is a SKU-level question to
    answer at all. A SKU down 38% inside a department down 37% is not a broken
    product, and reporting a cause for it would send someone to fix the wrong thing.
    """
    sales_wk, stock, prod, tg, ret = (d["sales_wk"], d["stock"], d["products"],
                                      d["targets"], d["returns"])
    weeks = [w for w in weeks_in_month(month) if w in set(sales_wk.week)]
    p = prod[prod.sku == sku].iloc[0]
    out = {}

    def gap_pct(skus):
        a = sales_wk[(sales_wk.sku.isin(skus)) & (sales_wk.week.isin(weeks))].revenue.sum()
        t = tg[(tg.sku.isin(skus)) & (tg.month == month)].target_revenue.sum()
        return round((a - t) / t * 100, 1) if t else None

    sku_gap = gap_pct([sku])
    siblings = prod[(prod.model == p.model) & (prod.sku != sku)].sku.tolist()
    dept_skus = prod[prod.department == p.department].sku.tolist()

    out["sku_gap_pct"] = sku_gap
    out["model_gap_pct"] = gap_pct(prod[prod.model == p.model].sku.tolist())
    out["department_gap_pct"] = gap_pct(dept_skus)

    # Scenario 1 - deliberate wind-down
    out["lifecycle_status"] = p.status
    out["suppress_investigation"] = p.status in ("clearance", "discontinued")

    # Scenario 2 - is the SKU just behaving like its department?
    dg = out["department_gap_pct"]
    if sku_gap is not None and dg is not None:
        out["sku_specific_pts"] = round(sku_gap - dg, 1)
        out["explained_by_department"] = abs(sku_gap - dg) <= 5.0
    else:
        out["sku_specific_pts"] = None
        out["explained_by_department"] = False

    # Scenario 3 - was the period before this one abnormally high?
    prior = sorted(w for w in sales_wk.week.unique() if w < weeks[0])
    h = sales_wk[(sales_wk.sku == sku) & (sales_wk.week.isin(prior))]
    if len(h) >= 12:
        recent = h.tail(len(weeks)).units.mean()
        base = h.tail(12).units.median()
        out["prior_period_vs_median"] = round(recent / base, 2) if base else None
        out["prior_period_spike"] = bool(base and recent / base > 1.4)
    else:
        out["prior_period_spike"] = False

    # Scenario 4 - too new to have a trend worth comparing against
    out["product_age_weeks"] = None
    out["too_new"] = False
    if pd.notna(p.launch_date):
        launched = dt.date.fromisoformat(str(p.launch_date)[:10])
        y, wk = int(weeks[0][:4]), int(weeks[0][-2:])
        age = (dt.date.fromisocalendar(y, wk, 1) - launched).days // 7
        out["product_age_weeks"] = age
        out["too_new"] = age < 8

    # Scenario 5 - returns above the department baseline
    r_sku = ret[(ret.sku == sku) & (ret.week.isin(weeks))].units_returned.sum()
    u_sku = sales_wk[(sales_wk.sku == sku) & (sales_wk.week.isin(weeks))].units.sum()
    dep_r = ret[(ret.sku.isin(dept_skus)) & (ret.week.isin(weeks))].units_returned.sum()
    dep_u = sales_wk[(sales_wk.sku.isin(dept_skus)) & (sales_wk.week.isin(weeks))].units.sum()
    rate = r_sku / u_sku if u_sku else 0
    base = dep_r / dep_u if dep_u else 0
    out["return_rate_pct"] = round(rate * 100, 1)
    out["department_return_rate_pct"] = round(base * 100, 1)
    # needs to be both proportionally and absolutely elevated - a 2% baseline
    # makes 4% look like a doubling, which is noise, not a fault
    out["returns_elevated"] = bool(base and rate > base * 1.8 and rate > 0.12)

    # Scenario 6 - did a sibling take the volume?
    if siblings:
        sib = gap_pct(siblings)
        out["sibling_gap_pct"] = sib
        out["possible_cannibalisation"] = bool(
            sku_gap is not None and sib is not None and sku_gap < -10 and sib > 10)
    else:
        out["sibling_gap_pct"] = None
        out["possible_cannibalisation"] = False

    return out


def analyse(d, sku: str, month: str) -> Decomposition:
    """Decomposition plus the context checks. This is what the pipeline calls."""
    r = decompose(d, sku, month)
    r.context = context(d, sku, month)
    return r
