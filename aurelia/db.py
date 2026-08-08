"""
Data access.

The six tables are loaded from Postgres into DataFrames once at startup, and the
rest of the system works on those. At under 100,000 rows that is about 50MB of
memory and roughly a second to load - and it means the analysis code is identical
whether it is running against the database or against the CSVs in a test.

Reads go through the v_ views, never the base tables, so an unpublished week is
invisible rather than half-visible.
"""
from __future__ import annotations
import os, logging
import pandas as pd
from sqlalchemy import create_engine, text

log = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://aurelia:local@localhost:5432/aurelia")

_engine = None
_cache: dict[str, pd.DataFrame] | None = None
_meta: dict = {}

QUERIES = {
    "products": "SELECT sku, model, department, colour, size, price, cost, launch_date, status FROM products",
    "sales":    "SELECT week, sku, channel, units, revenue, discount_pct FROM v_sales",
    "stock":    "SELECT week, sku, units_on_hand FROM v_stock",
    "returns":  "SELECT week, sku, units_returned, reason FROM v_returns",
    "receipts": "SELECT week, sku, units_received, expected_date, actual_date FROM v_receipts",
    "targets":  "SELECT month, sku, target_units, target_revenue, source_document FROM v_targets",
}


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def load(force: bool = False) -> dict[str, pd.DataFrame]:
    """Load every table into memory. Called at startup and after a weekly publish."""
    global _cache, _meta
    if _cache is not None and not force:
        return _cache

    d = {}
    with engine().connect() as c:
        for name, q in QUERIES.items():
            d[name] = pd.read_sql(text(q), c)

        pub = pd.read_sql(text(
            "SELECT load_id, week, kind, status, published_at "
            "FROM data_load WHERE status='published' ORDER BY load_id DESC"), c)

    if d["sales"].empty:
        raise RuntimeError(
            "No published sales data. Has db/load_csv.sql been run, and did it publish?")

    # the weekly grain the analysis works on
    d["sales_wk"] = (d["sales"].groupby(["week", "sku"], as_index=False)
                     .agg(units=("units", "sum"), revenue=("revenue", "sum"),
                          discount_pct=("discount_pct", "max")))

    weeks = sorted(d["sales"].week.unique())
    _meta = dict(first_week=weeks[0], latest_week=weeks[-1],
                 weeks=len(weeks), skus=int(d["products"].sku.nunique()),
                 published_loads=pub.to_dict("records"))
    _cache = d
    log.info("loaded %s SKUs, %s weeks (%s to %s)",
             _meta["skus"], _meta["weeks"], _meta["first_week"], _meta["latest_week"])
    return _cache


def meta() -> dict:
    load()
    return _meta


def latest_week() -> str:
    return meta()["latest_week"]
