"""
The business dictionary.

Everything the model needs to turn words into parameters. Built from the data
so it can never drift out of step with what is actually in the database.
"""
import datetime as dt
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data"

# things people say that are not what the data calls them
SYNONYMS = {
    "bag": "Bags", "bags": "Bags", "handbag": "Bags", "handbags": "Bags",
    "shoe": "Footwear", "shoes": "Footwear", "footwear": "Footwear",
    "jewelry": "Jewellery", "jewellery": "Jewellery",
    "sunglasses": "Eyewear", "sunnies": "Eyewear", "eyewear": "Eyewear",
    "belt": "Small leather goods", "belts": "Small leather goods",
    "wallet": "Small leather goods", "slg": "Small leather goods",
    "keychain": "Keychains", "keyring": "Keychains",
    "online": "ecom", "web": "ecom", "e-commerce": "ecom", "ecommerce": "ecom",
    "retail": "store", "shops": "store", "stores": "store",
}

def build_context(today: dt.date | None = None) -> str:
    prod = pd.read_csv(DATA / "products.csv")
    sales = pd.read_csv(DATA / "sales.csv")
    today = today or dt.date(2026, 8, 8)

    weeks = sorted(sales.week.unique())
    latest = weeks[-1]
    ly, lw = int(latest[:4]), int(latest[-2:])
    mon, sun = dt.date.fromisocalendar(ly, lw, 1), dt.date.fromisocalendar(ly, lw, 7)

    months = sorted({f"{dt.date.fromisocalendar(int(w[:4]), int(w[-2:]), 1):%Y-%m}"
                     for w in weeks})
    month_list = ", ".join(months)
    depts = sorted(prod.department.unique())
    models = prod.groupby("department").model.unique().to_dict()
    colours = sorted(prod.colour.dropna().unique())

    model_lines = "\n".join(
        f"  {d}: " + ", ".join(sorted(models[d])) for d in depts)

    # every SKU, listed. The model must never construct a code from a name -
    # "Mira Cat-Eye" -> MIR-CE is not guessable, and a wrong code is a hard failure.
    sku_rows = []
    for d in depts:
        sub = prod[prod.department == d].sort_values(["model", "colour", "size"])
        for _, r in sub.iterrows():
            size = f" size {r['size']}" if str(r["size"]) not in ("nan", "", "None") else ""
            sku_rows.append(f"  {r.sku:<16s} {r.model}, {r.colour}{size}")
    sku_lines = "\n".join(sku_rows)

    return f"""
## Today
Today is {today:%A %-d %B %Y}.

## How weeks work
Weeks are ISO weeks, written as YYYY-Www, for example 2026-W31.
A week runs Monday to Sunday. A week is only usable once it has closed and loaded.

The latest closed and published week is {latest} ({mon:%-d %b} to {sun:%-d %b %Y}).
Data is available from {weeks[0]} to {latest}. There is nothing after {latest}.

"last week"      = {latest}
"this month"     = the weeks of {today:%B %Y} that have closed
"last month"     = all weeks whose Monday falls in {(today.replace(day=1) - dt.timedelta(days=1)):%B %Y}
Months are written YYYY-MM. A month contains the weeks whose MONDAY falls in it.
Months with data: {month_list}. Nothing before or after those.

## Departments
{", ".join(depts)}

## Models by department
{model_lines}

## Every SKU
Use these codes exactly. Do NOT construct a code from a product name.
{sku_lines}

## Channels
store, ecom

## Words people use for the same thing
{chr(10).join(f"  '{k}' means {v}" for k, v in SYNONYMS.items())}
""".strip()

if __name__ == "__main__":
    print(build_context())
